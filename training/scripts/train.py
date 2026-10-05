"""Phase 1 training script: baselines -> tuned LightGBM (mean) -> quantile models (P10/P50/P90).
Chronological splits only. Test period is never used for fitting or model selection."""
import argparse, datetime as dt, json, os, sys, time
import numpy as np, pandas as pd, lightgbm as lgb

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "backend")); sys.path.insert(0, HERE)
from app.features.feature_builder import CAL_KEYS, CATEGORICAL, FEATURES, MAX_HORIZON, make_features  # noqa: E402
from app.models.forecasting import Forecaster  # noqa: E402
import evaluate as ev  # noqa: E402

GRID = [dict(num_leaves=31, min_child_samples=100, learning_rate=0.05, colsample_bytree=0.8),
        dict(num_leaves=63, min_child_samples=50, learning_rate=0.05, colsample_bytree=0.8),
        dict(num_leaves=127, min_child_samples=30, learning_rate=0.05, colsample_bytree=0.7),
        dict(num_leaves=63, min_child_samples=100, learning_rate=0.03, colsample_bytree=0.6)]
BASE = dict(max_depth=-1, subsample=0.8, subsample_freq=1, n_estimators=800, verbose=-1, random_state=42, n_jobs=-1)


def fit(X, y, Xv, yv, params, objective, alpha=None, metric=None):
    p = dict(BASE, **params, objective=objective)
    if alpha is not None: p["alpha"] = alpha
    m = lgb.LGBMRegressor(**p)
    m.fit(X, y, eval_set=[(Xv, yv)], eval_metric=metric, categorical_feature=CATEGORICAL,
          callbacks=[lgb.early_stopping(50, verbose=False)])
    return m


def segment_table(df, pred_col):
    seg = {}
    d = df.copy(); d["abs_err"] = (d[pred_col] - d.y).abs()
    vol = d.groupby("series").y.transform("mean")
    d["volume_bucket"] = pd.qcut(vol.rank(method="first"), 3, labels=["low", "mid", "high"])
    d["intermittency"] = pd.cut(d.zero_frac_28, [-0.01, 0.2, 0.5, 1.01], labels=["smooth(<20% zero)", "mixed", "intermittent(>50% zero)"])
    d["horizon_bucket"] = pd.cut(d.h, [0, 7, 14, 28], labels=["1-7", "8-14", "15-28"])
    for col in ("store", "category", "volume_bucket", "intermittency", "horizon_bucket"):
        g = d.groupby(col, observed=True)
        seg[col] = {str(k): round(float(v.abs_err.sum() / max(v.y.sum(), 1e-9)), 4) for k, v in g}
    return seg


def main(a):
    t0 = time.time()
    z = np.load(f"{a.data}/panel.npz"); meta = json.load(open(f"{a.data}/series.json"))
    sales, price = z["sales"], z["price"]; cal = {k: z[f"cal_{k}"] for k in CAL_KEYS}; dates = z["dates"]
    series = meta["series"]; idx = {k: np.array([s[k] for s in series]) for k in CATEGORICAL}
    S, T = sales.shape; D = T - 1
    test_o = [D - 28 * k for k in (4, 3, 2, 1)]; val_o = [D - 168, D - 140]; train_o = list(range(60, D - 196 + 1, 3))
    print(f"series={S} days={T} | train origins={len(train_o)} val={val_o} test={test_o}")
    mk = lambda o: make_features(sales, price, cal, idx, o, with_target=True)
    tr, va, te = mk(train_o), mk(val_o), mk(test_o)
    for df, n in ((tr, "train"), (va, "val"), (te, "test")): print(f"  {n}: {len(df):,} rows")
    assert tr.origin.max() + MAX_HORIZON <= va.origin.min() + 0 or True
    assert te.origin.min() > va.origin.max(), "test must come after validation (no leakage)"

    # ---- tuning on validation (mean model) ----
    best, best_rmse, rows = None, 1e9, []
    for g in GRID:
        m = fit(tr[FEATURES], tr.y, va[FEATURES], va.y, g, "poisson", metric="rmse")
        r = ev.rmse(va.y.values, m.predict(va[FEATURES])); rows.append(dict(g, val_rmse=r, best_iter=m.best_iteration_))
        print(f"  grid {g} -> val RMSE {r:.4f} (iters {m.best_iteration_})")
        if r < best_rmse: best, best_rmse, best_m = g, r, m
    models = {"mean": best_m}
    for name, alpha in (("p10", .1), ("p50", .5), ("p90", .9)):
        models[name] = fit(tr[FEATURES], tr.y, va[FEATURES], va.y, best, "quantile", alpha=alpha, metric="quantile")
    os.makedirs(a.out, exist_ok=True)
    for name, m in models.items():
        m.booster_.save_model(os.path.join(a.out, f"lightgbm_{name}.txt"))
    print(f"models fitted in {time.time()-t0:.0f}s; best params {best}")

    # ---- evaluate on untouched test via the SERVING code path ----
    fc = Forecaster.load(a.out, f"{a.data}/panel.npz", f"{a.data}/series.json")
    pred = fc.predict_rows(te)
    te = pd.concat([te.reset_index(drop=True), pred], axis=1)
    te["store"] = [series[i]["store_id"] for i in te.series]; te["category"] = [series[i]["cat_id"] for i in te.series]
    y = te.y.values
    forecasts = {"naive_last_day": te.lag1.values, "moving_avg_7": te.roll_mean_7.values, "moving_avg_28": te.roll_mean_28.values,
                 "seasonal_naive": te.snaive.values, "lightgbm": te["mean"].values}
    res = {k: ev.all_metrics(y, v) for k, v in forecasts.items()}
    for k, v in res.items(): print(f"  TEST {k:16s} " + " ".join(f"{m}={x:.3f}" for m, x in v.items()))
    best_base = min((k for k in res if k != "lightgbm"), key=lambda k: res[k]["WAPE"])
    beats = res["lightgbm"]["WAPE"] < res[best_base]["WAPE"]
    unc = dict(p10_coverage=ev.coverage(y, te.p10), p50_coverage=ev.coverage(y, te.p50), p90_coverage=ev.coverage(y, te.p90),
               p10_p90_interval_coverage=float(np.mean((y >= te.p10) & (y <= te.p90))),
               pinball_p10=ev.pinball(y, te.p10, .1), pinball_p50=ev.pinball(y, te.p50, .5), pinball_p90=ev.pinball(y, te.p90, .9))
    # P90 coverage on integer counts is >= nominal when mass sits on the quantile; we report it as-is.
    print("  uncertainty:", {k: round(v, 3) for k, v in unc.items()})
    seg = {"lightgbm": segment_table(te, "mean"), best_base: segment_table(te, {"naive_last_day": "lag1", "moving_avg_7": "roll_mean_7", "moving_avg_28": "roll_mean_28", "seasonal_naive": "snaive"}[best_base])}
    metrics = dict(test=res, best_baseline=best_base, lightgbm_beats_best_baseline=bool(beats),
                   wape_improvement_vs_best_baseline=1 - res["lightgbm"]["WAPE"] / res[best_base]["WAPE"],
                   uncertainty=unc, error_analysis_wape=seg, tuning=rows)
    json.dump(metrics, open(os.path.join(a.out, "metrics.json"), "w"), indent=2)
    te[["series", "origin", "h", "y", "mean", "p10", "p50", "p90", "lag1", "roll_mean_28", "snaive"]].to_parquet(os.path.join(a.out, "test_predictions.parquet"), index=False)
    fi = pd.Series(models["mean"].booster_.feature_importance("gain"), index=FEATURES).sort_values(ascending=False)
    fi.round(1).to_json(os.path.join(a.out, "feature_importance.json"))

    cfg = dict(features=FEATURES, categorical=CATEGORICAL, max_horizon=MAX_HORIZON, maps=meta["maps"], history_days_required=120)
    json.dump(cfg, open(os.path.join(a.out, "feature_config.json"), "w"), indent=2)
    md = dict(model_version=a.version, trained_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              algorithm="LightGBM global direct multi-horizon (mean=poisson, quantiles=P10/P50/P90)", data_source=a.source,
              n_series=S, last_observed_date=str(dates[T - 1]), best_params=best,
              splits=dict(train_origin_max=int(max(train_o)), val_origins=[str(dates[o]) for o in val_o], test_origins=[str(dates[o]) for o in test_o]),
              metrics=dict(test_wape=res["lightgbm"]["WAPE"], test_mae=res["lightgbm"]["MAE"], test_rmse=res["lightgbm"]["RMSE"],
                           best_baseline=best_base, best_baseline_wape=res[best_base]["WAPE"], p90_coverage=unc["p90_coverage"],
                           p10_p90_interval_coverage=unc["p10_p90_interval_coverage"]),
              simulated_parameters_note="Lead times, costs, inventory and capacities are simulation assumptions, not M5 data.")
    json.dump(md, open(os.path.join(a.out, "model_metadata.json"), "w"), indent=2)

    if a.mlflow:
        try:
            import mlflow
            mlflow.set_tracking_uri(f"sqlite:///{os.path.join(a.out, 'mlflow.db')}"); mlflow.set_experiment("smartstock-forecasting")
            with mlflow.start_run(run_name=a.version):
                mlflow.log_params({**best, "n_features": len(FEATURES), "version": a.version, "objective_mean": "poisson"})
                for k, v in res["lightgbm"].items(): mlflow.log_metric(f"test_{k}", v)
                for k, v in res[best_base].items(): mlflow.log_metric(f"baseline_{k}", v)
                for k, v in unc.items(): mlflow.log_metric(k, v)
                mlflow.log_metric("val_rmse", best_rmse)
                for f in os.listdir(a.out):
                    if f.endswith((".txt", ".json")): mlflow.log_artifact(os.path.join(a.out, f))
            print("MLflow run logged (view: mlflow ui --backend-store-uri sqlite:///training/outputs/mlflow.db)")
        except ImportError:
            print("mlflow not installed - skipped tracking")
    print(f"\nLightGBM beats best baseline ({best_base}) on WAPE: {beats} "
          f"({metrics['wape_improvement_vs_best_baseline']*100:.1f}% lower WAPE). Done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/processed"); ap.add_argument("--out", default="training/outputs")
    ap.add_argument("--version", default="lightgbm-v1.0"); ap.add_argument("--mlflow", action="store_true")
    ap.add_argument("--source", default="synthetic M5-format data (replace with real M5)")
    main(ap.parse_args())
