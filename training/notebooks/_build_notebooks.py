"""Generates the 9 notebooks. Re-run to regenerate:  python training/notebooks/_build_notebooks.py"""
import os, nbformat as nbf

SETUP = '''import os, sys, subprocess
if "google.colab" in sys.modules and not os.path.isdir("smartstock-ai"):          # Colab/Kaggle: clone your repo first
    subprocess.run(["git", "clone", "https://github.com/<you>/smartstock-ai.git"], check=True); os.chdir("smartstock-ai")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "training/requirements.txt"], check=True)
ROOT = os.getcwd()
while not os.path.isdir(os.path.join(ROOT, "backend")) and ROOT != "/": ROOT = os.path.dirname(ROOT)
os.chdir(ROOT); sys.path[:0] = [os.path.join(ROOT, "backend"), os.path.join(ROOT, "training", "scripts")]
import numpy as np, pandas as pd, matplotlib.pyplot as plt
RAW_OK = os.path.exists("data/raw/m5/sales_train_validation.csv")
if not RAW_OK:   # no real M5 download present -> generate M5-format synthetic data so the notebook runs anywhere
    subprocess.run([sys.executable, "training/scripts/make_synthetic_m5.py"], check=True)
if not os.path.exists("data/processed/panel.npz"):
    subprocess.run([sys.executable, "training/scripts/prepare_data.py"], check=True)
def ensure_trained():
    if not os.path.exists("training/outputs/metrics.json"):
        subprocess.run([sys.executable, "training/scripts/train.py"], check=True)'''

NB = {
"01_data_understanding": [
 ("md", "# 01 · Data understanding\nM5 files: `calendar.csv`, `sales_train_validation.csv` (wide: one column per day) and `sell_prices.csv`. If the real M5 files are not in `data/raw/m5/`, the first cell generates a synthetic dataset in the **same format**."),
 ("code", '''cal = pd.read_csv("data/raw/m5/calendar.csv"); sales = pd.read_csv("data/raw/m5/sales_train_validation.csv"); prices = pd.read_csv("data/raw/m5/sell_prices.csv")
print("calendar", cal.shape, "| sales (wide)", sales.shape, "| prices", prices.shape)
display(sales.iloc[:3, :10]); display(cal.head(3)); display(prices.head(3))'''),
 ("code", '''import json; print(json.dumps(json.load(open("data/processed/dq_report.json")), indent=2))   # data-quality report from prepare_data.py'''),
 ("md", "**Observed vs simulated.** Demand, prices and calendar are *observed* (or synthetic stand-ins here). Lead times, costs, inventory and capacity are *simulated* later and always labelled as such.")],
"02_eda": [
 ("md", "# 02 · EDA — business-focused views only"),
 ("code", '''d = pd.read_parquet("data/processed/sales_daily.parquet"); d["dow"] = d.date.dt.day_name()
fig, ax = plt.subplots(1, 3, figsize=(15, 3.6))
d.groupby(d.date.dt.dayofweek).sales.mean().plot.bar(ax=ax[0], title="Avg units by weekday (0=Mon)")
d.groupby([d.date.dt.to_period("M"), "cat_id"]).sales.sum().unstack().plot(ax=ax[1], title="Monthly units by category")
z = d.groupby(["item_id", "store_id"]).sales.apply(lambda s: (s == 0).mean()); z.hist(bins=20, ax=ax[2]); ax[2].set_title("Share of zero-sales days per series (intermittency)")
plt.tight_layout(); plt.show()'''),
 ("code", '''d["promo"] = d.sell_price < 0.92 * d.groupby(["item_id", "store_id"]).sell_price.transform("mean")
print(d.groupby(["cat_id", "promo"]).sales.mean().unstack().round(2).rename(columns={False: "regular", True: "promo"}))
print("event days vs normal:", d.groupby(d.event_name_1.fillna("") != "").sales.mean().round(2).to_dict())''')],
"03_data_preparation": [
 ("md", "# 03 · Data preparation and leakage-safe features\nWide→long, joins and QA live in `training/scripts/prepare_data.py`. Features come from `backend/app/features/feature_builder.py` — the *same* code the API runs."),
 ("code", '''d = pd.read_parquet("data/processed/sales_daily.parquet"); print(d.shape); display(d.head())
from app.features.feature_builder import make_features, FEATURES, CAL_KEYS
z = np.load("data/processed/panel.npz"); import json; meta = json.load(open("data/processed/series.json"))["series"]
cal = {k: z[f"cal_{k}"] for k in CAL_KEYS}; idx = {k: np.array([s[k] for s in meta]) for k in ["item_idx","store_idx","dept_idx","cat_idx"]}
X = make_features(z["sales"], z["price"], cal, idx, [600], with_target=True); print(len(FEATURES), "features;", X.shape); display(X[FEATURES[:10] + ["y"]].head())'''),
 ("code", '''# Leakage check: corrupt every observation AFTER the origin -> features must not change
s2 = z["sales"].copy(); s2[:, 601:] = 9999
X2 = make_features(s2, z["price"], cal, idx, [600], with_target=False)
assert np.array_equal(X[FEATURES].values, X2[FEATURES].values); print("no future information in features ✔")''')],
"04_baselines": [
 ("md", "# 04 · Baselines (naive, moving average, seasonal naive) on rolling-origin test windows"),
 ("code", '''import evaluate as ev
from app.features.feature_builder import make_features, CAL_KEYS
import json
z = np.load("data/processed/panel.npz"); meta = json.load(open("data/processed/series.json"))["series"]
cal = {k: z[f"cal_{k}"] for k in CAL_KEYS}; idx = {k: np.array([s[k] for s in meta]) for k in ["item_idx","store_idx","dept_idx","cat_idx"]}
D = z["sales"].shape[1] - 1; te = make_features(z["sales"], z["price"], cal, idx, [D - 28 * k for k in (4, 3, 2, 1)], with_target=True)
rows = {n: ev.all_metrics(te.y, te[c]) for n, c in {"naive_last_day": "lag1", "moving_avg_7": "roll_mean_7", "moving_avg_28": "roll_mean_28", "seasonal_naive": "snaive"}.items()}
pd.DataFrame(rows).T.round(3)''')],
"05_lightgbm": [
 ("md", "# 05 · LightGBM — global direct multi-horizon model\nTrained by `training/scripts/train.py` (4 hyper-parameter candidates on a chronological validation window; test period untouched)."),
 ("code", '''import json; ensure_trained(); m = json.load(open("training/outputs/metrics.json"))
display(pd.DataFrame(m["test"]).T.round(3)); print("beats best baseline:", m["lightgbm_beats_best_baseline"], f'({m["wape_improvement_vs_best_baseline"]:.1%} lower WAPE vs {m["best_baseline"]})')
pd.Series(json.load(open("training/outputs/feature_importance.json"))).head(12)[::-1].plot.barh(title="Feature importance (gain)"); plt.show()'''),
 ("code", '''import json; display(pd.DataFrame(m["error_analysis_wape"]["lightgbm"]).T)   # WAPE by store / category / volume / intermittency / horizon''')],
"06_uncertainty": [
 ("md", "# 06 · Uncertainty — P10 / P50 / P90 quantile models and coverage"),
 ("code", '''import json; ensure_trained(); m = json.load(open("training/outputs/metrics.json")); print({k: round(v, 3) for k, v in m["uncertainty"].items()})
t = pd.read_parquet("training/outputs/test_predictions.parquet"); s = t[(t.series == t.series.unique()[3]) & (t.origin == t.origin.max())]
plt.fill_between(s.h, s.p10, s.p90, alpha=.25, label="P10–P90"); plt.plot(s.h, s.p50, label="P50"); plt.plot(s.h, s.y, "k.", label="actual"); plt.legend(); plt.title("One series, last test origin"); plt.show()'''),
 ("md", "A P90 forecast should cover ~90% of actuals. Quantiles of *count* data with many zeros are lumpy (the P10 is usually 0), so judge calibration mainly on P50/P90 and the P10–P90 band.")],
"07_inventory_optimization": [
 ("md", "# 07 · Safety stock + PuLP placement\n**All costs, lead times and capacities are simulation assumptions.**"),
 ("code", '''from app.models.optimizer import optimize_allocation
df = pd.DataFrame([["A","S1",0,10,.01,5,1], ["A","S2",0,10,.01,5,3]], columns=["item_id","store_id","current","target","hold","penalty","transport"])
r, info = optimize_allocation(df, {"A": 15}, {}); display(r[["store_id","current","target","ship","recommended","shortage"]]); print(info)
assert list(r.ship) == [10, 5]   # hand check: only 15 units for 20 needed -> fill the cheaper-to-ship store first'''),
 ("code", '''from app.engine import Engine
e = Engine("backend/model_artifacts"); out = e.recommendation("FOODS_1_001", "CA_1"); print({k: out[k] for k in ("inventory", "action", "reason", "service_level")})
pd.DataFrame(out["placement"])''')],
"08_business_simulation": [
 ("md", "# 08 · Business simulation — baseline policies vs SmartStock on actual test-window demand"),
 ("code", '''import json
if not os.path.exists("training/outputs/business_simulation.json"): subprocess.run([sys.executable, "training/scripts/simulate_business.py"], check=True)
b = json.load(open("training/outputs/business_simulation.json")); print(b["assumptions"])
for k, v in b["results"].items(): print("\\n", k); display(pd.DataFrame({p: v[p] for p in ("cover_days", "classic_ss", "smartstock")}).T)'''),
 ("md", "Report only what this table shows. On synthetic data it demonstrates the mechanism, not a real-world saving.")],
"09_export_model_artifacts": [
 ("md", "# 09 · Export artifacts + parity check"),
 ("code", '''import json; ensure_trained()
if not os.path.exists("training/outputs/business_simulation.json"): subprocess.run([sys.executable, "training/scripts/simulate_business.py"], check=True)
subprocess.run([sys.executable, "training/scripts/export_artifacts.py"], check=True)
print(json.load(open("backend/model_artifacts/parity_check.json"))); print(sorted(os.listdir("backend/model_artifacts")))''')],
}

for name, cells in NB.items():
    nb = nbf.v4.new_notebook(); nb.cells = [nbf.v4.new_code_cell(SETUP)] + [nbf.v4.new_markdown_cell(c) if k == "md" else nbf.v4.new_code_cell(c) for k, c in cells]
    nbf.write(nb, os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.ipynb"))
print("wrote", len(NB), "notebooks")
