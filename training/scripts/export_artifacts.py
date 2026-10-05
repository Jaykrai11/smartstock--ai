"""Step 19: package everything the live API needs into backend/model_artifacts/ and PROVE parity:
the exported (compact) bundle must give the same forecasts as the full training panel."""
import argparse, json, os, shutil, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app.models.forecasting import Forecaster  # noqa: E402
from app.models import inventory as inv  # noqa: E402

KEEP = 120   # days of history the feature builder needs (>= 56) plus slack


def main(a):
    os.makedirs(a.dest, exist_ok=True)
    for f in ("lightgbm_mean.txt", "lightgbm_p10.txt", "lightgbm_p50.txt", "lightgbm_p90.txt", "feature_config.json", "model_metadata.json", "metrics.json", "business_simulation.json"):
        shutil.copy(os.path.join(a.models, f), os.path.join(a.dest, f))
    z = dict(np.load(f"{a.data}/panel.npz")); T = z["sales"].shape[1]
    keys = [k for k in z if k.startswith("cal_")] + ["dates"]
    bundle = dict(sales=z["sales"][:, -KEEP:], price=z["price"][:, -KEEP:])
    for k in keys: bundle[k] = z[k][T - KEEP:]                 # includes the 56 future calendar days
    np.savez_compressed(os.path.join(a.dest, "inference_data.npz"), **bundle)
    meta = json.load(open(f"{a.data}/series.json"))
    avg = bundle["sales"][:, -56:].mean(1); idx = np.array([s["store_idx"] for s in meta["series"]])
    ops = inv.make_sim_ops(avg, bundle["price"][:, -1], idx, seed=7)
    ops = {k: np.asarray(v).tolist() for k, v in ops.items()}; ops["avg_daily_56"] = avg.round(4).tolist()
    ops["_note"] = "SIMULATED operational parameters (not part of M5)."
    json.dump(meta, open(os.path.join(a.dest, "series.json"), "w")); json.dump(ops, open(os.path.join(a.dest, "ops_params.json"), "w"))
    # ---- parity: full training panel vs exported compact bundle ----
    full = Forecaster.load(a.models, f"{a.data}/panel.npz", f"{a.data}/series.json")
    comp = Forecaster.load(a.dest, os.path.join(a.dest, "inference_data.npz"), os.path.join(a.dest, "series.json"))
    S = range(len(meta["series"])); f1, f2 = full.forecast(S), comp.forecast(S)
    maxdiff = max(float(np.abs(f1[k] - f2[k]).max()) for k in f1)
    assert full.future_dates() == comp.future_dates(), "calendar mismatch"
    assert maxdiff < 1e-6, f"PARITY FAILED: max abs diff {maxdiff}"
    json.dump({"max_abs_diff": maxdiff, "n_series": len(list(S)), "origin_date": str(comp.dates[comp.n_days - 1])}, open(os.path.join(a.dest, "parity_check.json"), "w"))
    size = sum(os.path.getsize(os.path.join(a.dest, f)) for f in os.listdir(a.dest)) / 1e6
    print(f"exported to {a.dest} ({size:.1f} MB); parity max abs diff = {maxdiff:.2e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default="data/processed"); ap.add_argument("--models", default="training/outputs")
    ap.add_argument("--dest", default="backend/model_artifacts"); main(ap.parse_args())
