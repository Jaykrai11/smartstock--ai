"""Step 18: back-test inventory policies on the untouched test window using ACTUAL demand.
Policies (weekly review, lost-sales, lead times/costs are SIMULATED assumptions):
  cover_days   : order up to MA28 * (L+R+3)                           (naive rule of thumb)
  classic_ss   : order up to MA28*(L+R) + z*hist_std*sqrt(L+R)         (textbook safety stock)
  smartstock   : order up to LightGBM demand + z*sigma(P10..P90)       (this project)
Only differences produced by this simulation are reported."""
import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app.models.forecasting import Forecaster  # noqa: E402
from app.models import inventory as inv  # noqa: E402

R = 7


def agg(res):
    return dict(fill_rate=round(1 - res["lost_units"].sum() / res["units_demanded"].sum(), 4),
                stockout_day_rate=round(float(res["stockout_day_rate"].mean()), 4), avg_inventory_units=round(float(res["avg_inventory"].sum()), 1),
                holding_cost=round(float(res["holding_cost"].sum()), 1), stockout_cost=round(float(res["stockout_cost"].sum()), 1),
                transport_cost=round(float(res["transport_cost"].sum()), 1), total_cost=round(float(res["total_cost"].sum()), 1))


def main(a):
    fc = Forecaster.load(a.models, f"{a.data}/panel.npz", f"{a.data}/series.json")
    sales, price = fc.sales, fc.price; S, T = sales.shape; D = T - 1; o0 = D - 112; H = 112
    idx = fc.idx["store_idx"]
    avg = sales[:, :o0 + 1].mean(1); ops = inv.make_sim_ops(avg, price[:, o0], idx, seed=7)
    lead = ops["lead_time_days"]; demand = sales[:, o0 + 1: D + 1].astype(float)
    origins = [o0 + 7 * j for j in range(H // 7)]
    fcs = [fc.forecast(range(S), origin=o, horizon=14) for o in origins]
    out = {"assumptions": "lead times 2-7d, holding 1% of price/unit/day, stockout 50% of price/unit, transport 3% of price/unit (SIMULATED)",
           "window": dict(origin=str(fc.dates[o0]), days=H, review_days=R, n_series=S), "results": {}}
    for sl in (0.90, 0.95, 0.98):
        z = inv.z_for(sl); S_cov, S_cls, S_ai = (np.zeros((S, H)) for _ in range(3))
        for j, o in enumerate(origins):
            t = 7 * j; w28 = sales[:, o - 27: o + 1]; ma = w28.mean(1); sd = w28.std(1)
            S_cov[:, t] = ma * (lead + R + 3); S_cls[:, t] = ma * (lead + R) + z * sd * np.sqrt(lead + R)
            f = fcs[j]; S_ai[:, t] = inv.order_up_to_path(f["mean"], inv.sigma_daily(f["p10"], f["p90"]), lead, R, z)[:, 0]
        start = S_cov[:, 0]
        res = {}
        for name, Sl in (("cover_days", S_cov), ("classic_ss", S_cls), ("smartstock", S_ai)):
            r = inv.run_policy(demand, Sl, lead, R, start, ops["holding_cost_per_unit_day"], ops["stockout_cost_per_unit"], ops["transport_cost_per_unit"])
            res[name] = agg(r)
        res["smartstock_vs_classic"] = dict(total_cost_change_pct=round(100 * (res["smartstock"]["total_cost"] / res["classic_ss"]["total_cost"] - 1), 2),
                                            fill_rate_change_pts=round(100 * (res["smartstock"]["fill_rate"] - res["classic_ss"]["fill_rate"]), 2),
                                            avg_inventory_change_pct=round(100 * (res["smartstock"]["avg_inventory_units"] / res["classic_ss"]["avg_inventory_units"] - 1), 2))
        out["results"][f"service_level_{sl}"] = res
        print(f"service target {sl}:"); [print(f"   {k:22s}", v) for k, v in res.items()]
    json.dump(out, open(os.path.join(a.models, "business_simulation.json"), "w"), indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default="data/processed"); ap.add_argument("--models", default="training/outputs")
    main(ap.parse_args())
