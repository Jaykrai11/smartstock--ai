"""Safety-stock, order-up-to targets, action/reason logic and a vectorised inventory simulator.
All cost / lead-time / capacity inputs are SIMULATION assumptions (M5 contains none of them)."""
from __future__ import annotations

from statistics import NormalDist
from typing import Dict, List

import numpy as np

Z90 = 1.2815515655446004
_ND = NormalDist()


def z_for(service_level: float) -> float:
    return _ND.inv_cdf(min(max(service_level, 0.5), 0.9999))


def sigma_daily(p10: np.ndarray, p90: np.ndarray) -> np.ndarray:
    """Daily demand std-dev implied by the P10-P90 band (normal approximation)."""
    return np.maximum((p90 - p10) / (2 * Z90), 0.05)


def inventory_targets(mean, p10, p90, lead_time, review_days, service_level, demand_mult=1.0) -> Dict[str, np.ndarray]:
    """Order-up-to target = expected demand over (lead time + review period) + z * sigma over that window."""
    mean, p10, p90 = (np.atleast_2d(a) for a in (mean, p10, p90))
    n, H = mean.shape
    lt = np.broadcast_to(np.asarray(lead_time), (n,)).astype(int)
    cover = np.minimum(H, lt + int(review_days))
    cs = np.cumsum(mean, 1); cv = np.cumsum(sigma_daily(p10, p90) ** 2, 1)
    r = np.arange(n)
    base = demand_mult * cs[r, cover - 1]
    sig = demand_mult * np.sqrt(cv[r, cover - 1])
    ltd = demand_mult * cs[r, np.minimum(H, lt) - 1]
    ss = z_for(service_level) * sig
    return dict(cover_days=cover, base=base, sigma=sig, safety_stock=ss, target=base + ss, lead_time_demand=ltd)


def expected_service_level(inventory, base, sigma) -> np.ndarray:
    """P(demand over the cover window <= inventory) under a normal approximation."""
    z = (np.asarray(inventory) - base) / np.maximum(sigma, 1e-6)
    return np.array([_ND.cdf(float(v)) for v in np.atleast_1d(z)])


def decide_action(current: float, recommended: float, tol: float = 0.10, min_units: float = 2.0) -> str:
    delta = recommended - current
    band = max(min_units, tol * recommended)
    return "INCREASE" if delta > band else "REDUCE" if delta < -band else "MAINTAIN"


def reason_codes(action, current, target, safety_stock, lead_time_demand, lead_time, recent_rate, fc_rate,
                 shortage=0.0, capacity_bound=False, supply_bound=False) -> List[str]:
    r: List[str] = []
    if fc_rate > 1.10 * recent_rate + 0.05: r.append("forecast_growth")
    if fc_rate < 0.90 * recent_rate - 0.05: r.append("forecast_decline")
    if current < lead_time_demand: r.append("low_stock")
    if lead_time >= 5: r.append("lead_time_risk")
    if target > 0 and safety_stock / target > 0.30: r.append("high_demand_uncertainty")
    if action == "INCREASE" and not r: r.append("target_service_level")
    if action == "REDUCE": r.append("overstock")
    if capacity_bound: r.append("capacity_constraint")
    if supply_bound or shortage > 0.5: r.append("supply_constraint")
    return r or ["on_target"]


def make_sim_ops(avg_daily: np.ndarray, price: np.ndarray, store_idx: np.ndarray, seed: int = 7) -> Dict[str, np.ndarray]:
    """SIMULATED operational parameters (clearly not part of M5)."""
    rng = np.random.default_rng(seed)
    S = len(avg_daily)
    lead = rng.integers(2, 8, S)
    cur = np.round(avg_daily * rng.uniform(2, 30, S))
    ops = dict(lead_time_days=lead, current_inventory=cur, holding_cost_per_unit_day=0.01 * price,
               stockout_cost_per_unit=0.5 * price, transport_cost_per_unit=0.03 * price)
    store_cap = {}
    for s in np.unique(store_idx):
        store_cap[int(s)] = float(np.ceil(1.1 * 20 * avg_daily[store_idx == s].sum()))
    ops["store_capacity"] = np.array([store_cap[int(s)] for s in store_idx])
    share = np.array([avg_daily[i] / max(avg_daily[store_idx == store_idx[i]].sum(), 1e-9) for i in range(S)])
    ops["item_capacity"] = np.ceil(ops["store_capacity"] * share * 1.5)
    return ops


def order_up_to_path(mean, sigma, lead, review_days, z, demand_mult=1.0) -> np.ndarray:
    """S[n, t]: order-up-to level if we review on day t = demand over next (L+R) days + z*sigma."""
    mean, sigma = np.atleast_2d(mean), np.atleast_2d(sigma)
    n, H = mean.shape
    lead = np.broadcast_to(np.asarray(lead), (n,)).astype(int)
    W = H + int(lead.max()) + review_days + 1
    pm = np.concatenate([mean, np.repeat(mean[:, -1:], W - H, 1)], 1)
    pv = np.concatenate([sigma ** 2, np.repeat(sigma[:, -1:] ** 2, W - H, 1)], 1)
    cm = np.concatenate([np.zeros((n, 1)), np.cumsum(pm, 1)], 1); cv = np.concatenate([np.zeros((n, 1)), np.cumsum(pv, 1)], 1)
    t = np.arange(H)[None, :]; c = (lead + review_days)[:, None]
    hi = np.minimum(t + c, W)
    d = np.take_along_axis(cm, hi, 1) - np.take_along_axis(cm, np.broadcast_to(t, hi.shape), 1)
    v = np.take_along_axis(cv, hi, 1) - np.take_along_axis(cv, np.broadcast_to(t, hi.shape), 1)
    return demand_mult * d + z * demand_mult * np.sqrt(v)


def run_policy(demand, S_level, lead, review_days, start_inv, hold, pen, trans) -> Dict[str, np.ndarray]:
    """Periodic-review, order-up-to, lost-sales simulation (vectorised over rows = series or Monte-Carlo paths).
    Day t: receive arrivals -> (if review day) order up to S[t] -> demand is served -> holding cost on end stock."""
    N, H = demand.shape
    lead = np.broadcast_to(np.asarray(lead), (N,)).astype(int)
    arr = np.zeros((N, H + int(lead.max()) + 2)); on = np.asarray(start_inv, float).copy()
    rows = np.arange(N); inv_path = np.zeros((N, H)); lost = np.zeros((N, H)); ordered = np.zeros(N)
    for t in range(H):
        on += arr[:, t]
        if t % review_days == 0:
            pos = on + arr[:, t + 1:].sum(1)
            q = np.maximum(S_level[:, t] - pos, 0)
            arr[rows, t + lead] += q; ordered += q
        sold = np.minimum(on, demand[:, t]); lost[:, t] = demand[:, t] - sold; on -= sold; inv_path[:, t] = on
    hold_c = hold * inv_path.sum(1); stock_c = pen * lost.sum(1); trans_c = trans * ordered
    dem = np.maximum(demand.sum(1), 1e-9)
    return dict(fill_rate=1 - lost.sum(1) / dem, stockout_day_rate=(lost > 0).mean(1), avg_inventory=inv_path.mean(1),
                holding_cost=hold_c, stockout_cost=stock_c, transport_cost=trans_c, total_cost=hold_c + stock_c + trans_c,
                lost_units=lost.sum(1), units_demanded=demand.sum(1), inv_path=inv_path)


def sample_demand(mean, sigma, n_sims, rng, mult=1.0) -> np.ndarray:
    """Negative-binomial demand paths with given daily mean / std (Poisson if under-dispersed). -> (n_sims, H)"""
    mu = np.maximum(mean * mult, 1e-6); var = np.maximum((sigma * mult) ** 2, mu * 1.0001)
    n = mu ** 2 / (var - mu); p = n / (n + mu)
    return rng.negative_binomial(n[None, :], p[None, :], size=(n_sims, len(mu))).astype(float)
