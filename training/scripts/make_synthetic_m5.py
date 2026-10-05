"""Generate a SYNTHETIC dataset in the exact M5 file format (calendar.csv,
sales_train_validation.csv, sell_prices.csv) so the whole pipeline runs offline.

To use the REAL M5 data instead: download it from
https://www.kaggle.com/c/m5-forecasting-accuracy/data into data/raw/m5/ and skip this script.
"""
import argparse, os
import numpy as np, pandas as pd

STORES = {"CA_1": "CA", "CA_2": "CA", "TX_1": "TX", "WI_1": "WI"}
DEPTS = {"FOODS_1": "FOODS", "FOODS_2": "FOODS", "HOUSEHOLD_1": "HOUSEHOLD", "HOBBIES_1": "HOBBIES"}
EVENTS = [("SuperBowl", "Sporting", "02-12"), ("Easter", "Religious", "04-09"), ("Mother's Day", "Cultural", "05-14"),
          ("MemorialDay", "National", "05-29"), ("IndependenceDay", "National", "07-04"), ("LaborDay", "National", "09-04"),
          ("Halloween", "Cultural", "10-31"), ("Thanksgiving", "National", "11-23"), ("Christmas", "National", "12-25"),
          ("NewYear", "National", "01-01")]


def main(a):
    rng = np.random.default_rng(a.seed)
    out = os.path.join(a.out, "m5"); os.makedirs(out, exist_ok=True)
    T, EXTRA = a.days, 56
    dates = pd.date_range(a.start, periods=T + EXTRA)
    cal = pd.DataFrame({"date": dates.strftime("%Y-%m-%d")})
    cal["wm_yr_wk"] = ((dates - dates[0]).days // 7 + 11101).astype(int)
    cal["weekday"] = dates.day_name(); cal["wday"] = (dates.dayofweek + 2 - 1) % 7 + 1
    cal["month"] = dates.month; cal["year"] = dates.year; cal["d"] = [f"d_{i+1}" for i in range(len(dates))]
    for c in ("event_name_1", "event_type_1", "event_name_2", "event_type_2"): cal[c] = ""
    md = dates.strftime("%m-%d")
    for name, typ, day in EVENTS:
        m = md == day; cal.loc[m, "event_name_1"] = name; cal.loc[m, "event_type_1"] = typ
    for st in ("CA", "TX", "WI"): cal[f"snap_{st}"] = (dates.day <= 10).astype(int)
    cal.to_csv(f"{out}/calendar.csv", index=False)

    ev_flag = (cal.event_name_1 != "").values.astype(float)
    items, rows, prices = [], [], []
    for dept, cat in DEPTS.items():
        for k in range(1, a.items_per_dept + 1):
            items.append((f"{dept}_{k:03d}", dept, cat))
    n_weeks = cal.wm_yr_wk.nunique()
    wk_index = (cal.wm_yr_wk - cal.wm_yr_wk.min()).values
    dow = dates.dayofweek.values; doy = dates.dayofyear.values
    for item_id, dept, cat in items:
        base_price = float(np.round(rng.uniform(1.5, 12), 2))
        item_lvl = rng.lognormal(0.9, 0.9)           # item popularity
        wk_amp = rng.uniform(0.1, 0.5); yr_amp = rng.uniform(0.0, 0.35); trend = rng.normal(0, 0.15)
        wk_phase = rng.uniform(0, 7)
        for store, state in STORES.items():
            lvl = item_lvl * rng.lognormal(0, 0.35) * (1.2 if state == "CA" else 1.0)
            disc = np.ones(n_weeks)
            promo = rng.random(n_weeks) < 0.12
            disc[promo] = rng.uniform(0.7, 0.9, promo.sum())
            wk_price = np.round(base_price * disc * (1 + 0.03 * (np.arange(n_weeks) // 40)), 2)
            for w in np.unique(cal.wm_yr_wk):
                prices.append((store, item_id, int(w), wk_price[w - cal.wm_yr_wk.min()]))
            p_t = wk_price[wk_index] / base_price
            mu = lvl * (1 + wk_amp * np.sin(2 * np.pi * (dow + wk_phase) / 7)) \
                 * (1 + yr_amp * np.sin(2 * np.pi * doy / 365.25)) * (1 + trend * np.arange(T + EXTRA) / T) \
                 * (1 + 0.35 * ev_flag) * np.exp(-1.6 * (p_t - 1))
            y = rng.negative_binomial(2.5, 2.5 / (2.5 + np.clip(mu[:T], 1e-3, None)))
            rows.append([f"{item_id}_{store}_validation", item_id, dept, cat, store, state] + list(y))
    sales = pd.DataFrame(rows, columns=["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"] + [f"d_{i+1}" for i in range(T)])
    sales.to_csv(f"{out}/sales_train_validation.csv", index=False)
    pd.DataFrame(prices, columns=["store_id", "item_id", "wm_yr_wk", "sell_price"]).to_csv(f"{out}/sell_prices.csv", index=False)
    print(f"wrote synthetic M5-format data: {len(sales)} series x {T} days -> {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/raw"); p.add_argument("--days", type=int, default=900)
    p.add_argument("--items-per-dept", type=int, default=5); p.add_argument("--start", default="2022-01-03")
    p.add_argument("--seed", type=int, default=42)
    main(p.parse_args())
