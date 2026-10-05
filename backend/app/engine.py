"""Service layer: loads artifacts ONCE at startup and exposes forecast / optimize / recommend / simulate."""
from __future__ import annotations

import datetime as dt
import json
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.models import inventory as inv
from app.models.forecasting import Forecaster
from app.models.optimizer import optimize_allocation

ASSUMPTIONS = {"note": "Lead times, holding/stock-out/transport costs, current inventory, warehouse supply and capacities are SIMULATED for this portfolio demo; only demand/price/calendar come from the retail dataset."}


class UnknownSeries(KeyError):
    pass


class Engine:
    def __init__(self, art_dir: str):
        L = lambda f: json.load(open(os.path.join(art_dir, f)))
        self.fc = Forecaster.load(art_dir, os.path.join(art_dir, "inference_data.npz"), os.path.join(art_dir, "series.json"))
        self.metadata, self.metrics, self.bizsim = L("model_metadata.json"), L("metrics.json"), L("business_simulation.json")
        ops = L("ops_params.json"); self.ops = {k: np.array(v) for k, v in ops.items() if not k.startswith("_")}
        self.version = self.metadata["model_version"]
        self.series = self.fc.series; self.S = len(self.series)
        self.items = sorted({s["item_id"] for s in self.series}); self.stores = sorted({s["store_id"] for s in self.series})
        self.base = self.fc.forecast(range(self.S))          # cached baseline forecast for every series (28d)
        self.n = self.fc.n_days; self._overview = None

    # ---------- helpers ----------
    def idx(self, item: str, store: str) -> int:
        try:
            return self.fc.key2i[(item, store)]
        except KeyError:
            raise UnknownSeries(f"No series for item_id={item!r}, store_id={store!r}")

    def _fc(self, i: int, horizon: int, price_multiplier: float = 1.0) -> Dict[str, np.ndarray]:
        if price_multiplier == 1.0:
            return {k: v[i, :horizon] for k, v in self.base.items()}
        r = self.fc.forecast([i], horizon=horizon, price_multiplier=price_multiplier)
        return {k: v[0] for k, v in r.items()}

    @staticmethod
    def _totals(f) -> dict:
        """Quantiles of TOTAL demand over the horizon. Summing daily P90s would overstate risk, so we aggregate
        variance instead (daily sigma from the P10-P90 band, days treated as independent => a mild under-estimate if
        demand errors are positively correlated)."""
        m = float(f["mean"].sum()); sd = float(np.sqrt((inv.sigma_daily(f["p10"], f["p90"]) ** 2).sum()))
        return dict(mean=round(m, 2), p50=round(m, 2), p90=round(m + inv.Z90 * sd, 2))

    def _daily(self, f, horizon):
        d = self.fc.future_dates(horizon=horizon)
        return [dict(date=d[t], mean=round(float(f["mean"][t]), 3), p10=round(float(f["p10"][t]), 3), p50=round(float(f["p50"][t]), 3), p90=round(float(f["p90"][t]), 3)) for t in range(horizon)]

    # ---------- /forecast ----------
    def forecast(self, item, store, horizon=28, price_multiplier=1.0) -> dict:
        i = self.idx(item, store); f = self._fc(i, horizon, price_multiplier)
        hist = [dict(date=str(d), sales=float(v)) for d, v in zip(self.fc.dates[self.n - 56:self.n], self.fc.sales[i, -56:])]
        return dict(model_version=self.version, item_id=item, store_id=store, origin_date=str(self.fc.dates[self.n - 1]), horizon=horizon,
                    totals=self._totals(f),
                    daily=self._daily(f, horizon), history=hist)

    # ---------- planning core (targets + PuLP) ----------
    def _plan(self, sidx: List[int], lead, cur, sl, review, supply: Optional[Dict[str, float]] = None, caps: Optional[Dict[str, float]] = None):
        sidx = np.asarray(sidx)
        f = {k: self.base[k][sidx] for k in ("mean", "p10", "p90")}
        t = inv.inventory_targets(f["mean"], f["p10"], f["p90"], lead, review, sl)
        item = [self.series[i]["item_id"] for i in sidx]; store = [self.series[i]["store_id"] for i in sidx]
        df = pd.DataFrame(dict(item_id=item, store_id=store, current=np.asarray(cur, float), target=t["target"],
                               hold=self.ops["holding_cost_per_unit_day"][sidx] * t["cover_days"],
                               penalty=self.ops["stockout_cost_per_unit"][sidx], transport=self.ops["transport_cost_per_unit"][sidx]))
        short = np.maximum(np.ceil(df.target) - df.current, 0)
        auto_supply = {it: float(np.round(0.9 * short[df.item_id == it].sum())) for it in set(item)}
        supply = {**auto_supply, **(supply or {})}
        res, info = optimize_allocation(df, supply, caps or {})
        if info["status"] not in ("Optimal",):
            raise RuntimeError(f"optimizer status: {info['status']}")
        res["base"], res["sigma"], res["safety_stock"] = t["base"], t["sigma"], t["safety_stock"]
        res["lead_time_demand"], res["cover_days"], res["lead"] = t["lead_time_demand"], t["cover_days"], np.broadcast_to(np.asarray(lead), (len(df),)).astype(int)
        res["exp_sl"] = inv.expected_service_level(res.recommended.values, t["base"], t["sigma"])
        acts, reasons = [], []
        for k, i in enumerate(sidx):
            r = res.iloc[k]; a = inv.decide_action(r.current, r.recommended); acts.append(a)
            rec_rate = float(self.fc.sales[i, -28:].mean()); fc_rate = float(f["mean"][k, :int(r.cover_days)].mean())
            reasons.append(inv.reason_codes(a, r.current, r.target, r.safety_stock, r.lead_time_demand, int(r.lead), rec_rate, fc_rate, r.shortage, bool(r.capacity_bound), bool(r.supply_bound)))
        res["action"], res["reason"] = acts, reasons
        return res, info, supply

    @staticmethod
    def _row(r) -> dict:
        return dict(item_id=r.item_id, store_id=r.store_id, current=round(float(r.current), 1), recommended=round(float(r.recommended), 1),
                    delta=round(float(r.recommended - r.current), 1), action=r.action, reason=list(r.reason),
                    target_before_constraints=round(float(np.ceil(r.target)), 1), safety_stock=round(float(r.safety_stock), 1),
                    expected_service_level=round(float(r.exp_sl), 4), lead_time_days=int(r.lead), shortage_units=round(float(r.shortage), 1))

    # ---------- /recommendation ----------
    def recommendation(self, item_id, store_id, current_inventory=None, lead_time_days=None, service_level=0.95, review_days=7,
                       warehouse_supply=None, store_capacity=None, horizon=28) -> dict:
        item, store = item_id, store_id
        i = self.idx(item, store)
        grp = [j for j, s in enumerate(self.series) if s["item_id"] == item]
        lead = self.ops["lead_time_days"][grp].copy(); cur = self.ops["current_inventory"][grp].copy()
        caps = {self.series[j]["store_id"]: float(self.ops["item_capacity"][j]) for j in grp}
        pos = grp.index(i)
        if lead_time_days is not None: lead[pos] = lead_time_days
        if current_inventory is not None: cur[pos] = current_inventory
        if store_capacity is not None: caps[store] = store_capacity
        res, info, supply = self._plan(grp, lead, cur, service_level, review_days, {item: warehouse_supply} if warehouse_supply is not None else None, caps)
        r = res.iloc[pos]; f = self._fc(i, horizon)
        row = self._row(r)
        return dict(model_version=self.version, generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), item_id=item, store_id=store,
                    forecast=dict(horizon_days=horizon, mean_total=self._totals(f)["mean"], p50_total=self._totals(f)["p50"], p90_total=self._totals(f)["p90"]),
                    inventory=dict(current=row["current"], recommended=row["recommended"], delta=row["delta"], safety_stock=row["safety_stock"],
                                   lead_time_days=row["lead_time_days"], lead_time_demand=round(float(r.lead_time_demand), 1), cover_days=int(r.cover_days),
                                   target_before_constraints=row["target_before_constraints"]),
                    service_level=row["expected_service_level"], target_service_level=service_level, action=row["action"], reason=row["reason"],
                    placement=[self._row(res.iloc[k]) for k in range(len(res))], daily=self._daily(f, horizon),
                    solver=dict(info, warehouse_supply_units=supply[item]), assumptions=ASSUMPTIONS)

    # ---------- /optimize ----------
    def optimize(self, item_ids=None, service_level=0.95, review_days=7, lead_time_days=None, warehouse_supply=None, store_capacity=None) -> dict:
        items = item_ids or self.items
        bad = [x for x in items if x not in self.items]
        if bad: raise UnknownSeries(f"Unknown item_id(s): {bad}")
        grp = [j for j, s in enumerate(self.series) if s["item_id"] in set(items)]
        lead = self.ops["lead_time_days"][grp] if lead_time_days is None else np.full(len(grp), lead_time_days)
        frac = len(items) / len(self.items); caps = {}
        for j in grp: caps.setdefault(self.series[j]["store_id"], float(np.ceil(self.ops["store_capacity"][j] * frac)))
        if store_capacity: caps.update(store_capacity)
        res, info, supply = self._plan(grp, lead, self.ops["current_inventory"][grp], service_level, review_days, warehouse_supply, caps)
        rows = [self._row(res.iloc[k]) for k in range(len(res))]
        summary = dict(n_rows=len(rows), actions={a: int((res.action == a).sum()) for a in ("INCREASE", "REDUCE", "MAINTAIN")},
                       units_to_ship=float(res.ship.sum()), units_to_remove=float(res["remove"].sum()), shortage_units=float(res.shortage.sum()),
                       mean_expected_service_level=round(float(res.exp_sl.mean()), 4), total_supply=float(sum(supply[i] for i in items)))
        return dict(model_version=self.version, solver=info, summary=summary, rows=rows)

    # ---------- /simulate ----------
    def simulate(self, item_id, store_id, demand_multiplier=1.0, lead_time_days=None, service_level=0.95, review_days=7, starting_inventory=None,
                 horizon=28, n_simulations=300, planner_aware=False, seed=0) -> dict:
        item, store = item_id, store_id
        i = self.idx(item, store); f = self._fc(i, horizon); z = inv.z_for(service_level); R = review_days; N = n_simulations
        lead = int(lead_time_days or self.ops["lead_time_days"][i]); start = float(self.ops["current_inventory"][i] if starting_inventory is None else starting_inventory)
        rng = np.random.default_rng(seed); sig = inv.sigma_daily(f["p10"], f["p90"])
        demand = inv.sample_demand(f["mean"], sig, N, rng, demand_multiplier)
        pm = demand_multiplier if planner_aware else 1.0
        S_ai = np.repeat(inv.order_up_to_path(f["mean"], sig, lead, R, z, pm), N, 0)
        w = self.fc.sales[i, -28:].astype(float); ma, sd = w.mean() * pm, w.std() * pm
        S_base = np.full((N, horizon), ma * (lead + R) + z * sd * np.sqrt(lead + R))
        cost = lambda k: np.full(N, float(self.ops[k][i]))
        out, paths = {}, {}
        for name, Sl in (("baseline_policy", S_base), ("smartstock_policy", S_ai)):
            r = inv.run_policy(demand, Sl, np.full(N, lead), R, np.full(N, start), cost("holding_cost_per_unit_day"), cost("stockout_cost_per_unit"), cost("transport_cost_per_unit"))
            out[name] = {k: round(float(r[k].mean()), 4) for k in ("fill_rate", "stockout_day_rate", "avg_inventory", "holding_cost", "stockout_cost", "transport_cost", "total_cost")}
            out[name]["prob_any_stockout"] = round(float((r["lost_units"] > 0).mean()), 4)
            paths[name] = [round(float(v), 2) for v in r["inv_path"].mean(0)]
        d = self.fc.future_dates(horizon=horizon)
        trajectory = [dict(date=d[t], demand_mean=round(float(demand[:, t].mean()), 2), demand_p10=round(float(np.percentile(demand[:, t], 10)), 2),
                           demand_p90=round(float(np.percentile(demand[:, t], 90)), 2), baseline_inventory=paths["baseline_policy"][t],
                           smartstock_inventory=paths["smartstock_policy"][t]) for t in range(horizon)]
        delta = {k: round(out["smartstock_policy"][k] - out["baseline_policy"][k], 4) for k in out["baseline_policy"]}
        return dict(model_version=self.version, item_id=item, store_id=store,
                    scenario=dict(demand_multiplier=demand_multiplier, lead_time_days=lead, service_level=service_level, review_days=R, starting_inventory=start,
                                  horizon=horizon, n_simulations=N, planner_aware=planner_aware),
                    results=out, difference_smartstock_minus_baseline=delta, trajectory=trajectory, assumptions=ASSUMPTIONS)

    # ---------- /overview (dashboard) ----------
    def overview(self) -> dict:
        if self._overview is None:
            o = self.optimize()
            rows = sorted(o["rows"], key=lambda r: (r["action"] != "INCREASE", -r["delta"]))[:8]
            hist = self.fc.sales[:, -56:].sum(0); fut = self.base["mean"].sum(0)
            dh = [str(d) for d in self.fc.dates[self.n - 56:self.n]]; df_ = self.fc.future_dates()
            net = [dict(date=d, actual=round(float(v), 1)) for d, v in zip(dh, hist)] + [dict(date=d, forecast=round(float(v), 1)) for d, v in zip(df_, fut)]
            sim = self.bizsim["results"].get("service_level_0.95", {})
            self._overview = dict(model_version=self.version, n_series=self.S, n_items=len(self.items), n_stores=len(self.stores),
                                  forecast_units_28d=round(float(self.base["mean"].sum()), 0), actions=o["summary"]["actions"],
                                  mean_expected_service_level=o["summary"]["mean_expected_service_level"], shortage_units=o["summary"]["shortage_units"],
                                  network_demand=net, top_actions=rows, backtest_95=sim.get("smartstock_vs_classic"), backtest_note=self.bizsim.get("assumptions"))
        return self._overview

    def model_info(self) -> dict:
        m = self.metrics
        return dict(**self.metadata, loaded_series=self.S, test_metrics=m["test"], best_baseline=m["best_baseline"], uncertainty=m["uncertainty"],
                    wape_improvement_vs_best_baseline=m["wape_improvement_vs_best_baseline"], error_analysis_wape=m["error_analysis_wape"]["lightgbm"],
                    business_backtest=self.bizsim)
