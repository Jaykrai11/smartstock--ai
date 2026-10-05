"""Step 4-5: wide -> long conversion, joins, data-quality checks, panel export.

Reads M5-format files from <raw>/m5/, writes
  data/processed/sales_daily.parquet   (date x item_id x store_id, long format)
  data/processed/panel.npz + series.json  (dense arrays used by training / serving)
  data/processed/dq_report.json
"""
import argparse, json, os
import numpy as np, pandas as pd

EVENT_CODE = {"": 0, "Sporting": 1, "Cultural": 2, "National": 3, "Religious": 4}


def load_and_validate(raw, stores=None, n_items=None):
    cal = pd.read_csv(f"{raw}/m5/calendar.csv").fillna("")
    sales = pd.read_csv(f"{raw}/m5/sales_train_validation.csv")
    prices = pd.read_csv(f"{raw}/m5/sell_prices.csv")
    dq = {}
    # ---- quality checks (fail early) ----
    dcols = [c for c in sales.columns if c.startswith("d_")]
    assert sales["id"].is_unique, "duplicate series ids"
    assert cal["date"].is_unique and pd.to_datetime(cal["date"]).is_monotonic_increasing, "calendar dates invalid"
    assert dcols == cal["d"].tolist()[: len(dcols)], "d_ columns do not align with calendar"
    assert len(cal) >= len(dcols) + 28, "calendar must extend >= 28 days past last sales day (needed for forecasting)"
    dq["missing_sales_values"] = int(sales[dcols].isna().sum().sum()); assert dq["missing_sales_values"] == 0
    dq["negative_sales_values"] = int((sales[dcols] < 0).sum().sum()); assert dq["negative_sales_values"] == 0
    dq["nonpositive_prices"] = int((prices["sell_price"] <= 0).sum()); assert dq["nonpositive_prices"] == 0
    dq["duplicate_price_rows"] = int(prices.duplicated(["store_id", "item_id", "wm_yr_wk"]).sum()); assert dq["duplicate_price_rows"] == 0
    # ---- subset (documented, not whole M5) ----
    if stores: sales = sales[sales.store_id.isin(stores)]
    if n_items:
        top = sales.assign(tot=sales[dcols].sum(1)).groupby("item_id").tot.sum().nlargest(n_items).index
        sales = sales[sales.item_id.isin(top)]
    sales = sales.sort_values(["item_id", "store_id"]).reset_index(drop=True)
    dq["n_series"] = len(sales); dq["n_days"] = len(dcols)
    zero = (sales[dcols].values == 0).mean(); dq["share_zero_sales"] = round(float(zero), 4)
    mx = sales[dcols].values.max(1); med = np.median(sales[dcols].values, 1)
    dq["series_with_spike_gt_20x_median"] = int(((mx > 20 * np.maximum(med, 1))).sum())  # documented, NOT removed (real demand)
    return cal, sales, prices, dcols, dq


def build(raw, out, stores=None, n_items=None):
    os.makedirs(out, exist_ok=True)
    cal, sales, prices, dcols, dq = load_and_validate(raw, stores, n_items)
    T = len(dcols)
    # long format
    long = sales.melt(id_vars=["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"], value_vars=dcols, var_name="d", value_name="sales")
    long = long.merge(cal[["d", "date", "wm_yr_wk", "event_name_1", "event_type_1"]], on="d").merge(prices, on=["store_id", "item_id", "wm_yr_wk"], how="left")
    long["date"] = pd.to_datetime(long["date"])
    long = long.sort_values(["item_id", "store_id", "date"])
    dq["missing_price_share_before_fill"] = round(float(long.sell_price.isna().mean()), 4)
    long["sell_price"] = long.groupby(["item_id", "store_id"]).sell_price.transform(lambda s: s.ffill().bfill())
    assert long.sell_price.notna().all(), "series without any price"
    long[["id", "item_id", "dept_id", "cat_id", "store_id", "state_id", "date", "sales", "sell_price", "event_name_1", "event_type_1"]].to_parquet(f"{out}/sales_daily.parquet", index=False)
    # dense panel
    S = len(sales)
    sales_arr = sales[dcols].values.astype(np.float32)
    price_arr = long.pivot_table(index=["item_id", "store_id"], columns="date", values="sell_price").reindex(pd.MultiIndex.from_frame(sales[["item_id", "store_id"]])).values.astype(np.float32)
    dates = pd.to_datetime(cal["date"])
    ev = cal["event_type_1"].map(lambda x: EVENT_CODE.get(x, 0)).values
    calarr = dict(cal_dow=dates.dt.dayofweek.values, cal_month=dates.dt.month.values, cal_week=dates.dt.isocalendar().week.values.astype(int),
                  cal_quarter=dates.dt.quarter.values, cal_dom=dates.dt.day.values, cal_event_flag=(ev > 0).astype(int), cal_event_type=ev)
    np.savez_compressed(f"{out}/panel.npz", sales=sales_arr, price=price_arr, dates=np.array(cal["date"].tolist(), dtype="U10"), **calarr)
    meta = sales[["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]].copy()
    maps = {c: {v: i for i, v in enumerate(sorted(meta[c].unique()))} for c in ["item_id", "store_id", "dept_id", "cat_id"]}
    for c, m in maps.items(): meta[c.replace("_id", "_idx")] = meta[c].map(m)
    json.dump({"series": meta.to_dict("records"), "maps": maps}, open(f"{out}/series.json", "w"))
    json.dump(dq, open(f"{out}/dq_report.json", "w"), indent=2)
    print("DQ report:", dq); print(f"long table rows: {len(long):,}; panel {sales_arr.shape}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw"); ap.add_argument("--out", default="data/processed")
    ap.add_argument("--stores", nargs="*"); ap.add_argument("--n-items", type=int)
    a = ap.parse_args(); build(a.raw, a.out, a.stores, a.n_items)
