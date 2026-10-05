"""Leakage-safe feature builder, shared by training AND serving.

Direct multi-horizon design: for an *origin* day `o` (last observed day) and a
horizon `h` (1..28) we predict sales on day `o+h`. Every feature uses only:
  * sales / prices up to and including day `o`, and
  * information known in advance about the target day (calendar, events, price plan).
No future sales are ever read. `lag1` = sales on the origin day itself,
`lag7` = sales 6 days before it, etc.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, Sequence

import numpy as np
import pandas as pd

LAGS = (1, 7, 14, 28)
ROLL_WINDOWS = (7, 14, 28, 56)
MIN_ORIGIN = 55          # need 56 days of history ending at the origin
MAX_HORIZON = 28
CATEGORICAL = ["item_idx", "store_idx", "dept_idx", "cat_idx"]
CAL_KEYS = ["dow", "month", "week", "quarter", "dom", "event_flag", "event_type"]

FEATURES = (
    [f"lag{k}" for k in LAGS]
    + [f"roll_mean_{w}" for w in ROLL_WINDOWS]
    + [f"roll_std_{w}" for w in (7, 14, 28)]
    + ["zero_frac_28", "same_dow_mean4", "price", "price_rel_56", "price_ratio_target"]
    + ["h", "t_dow", "t_month", "t_week", "t_quarter", "t_dom", "t_event_flag", "t_event_type"]
    + CATEGORICAL
)


def make_features(
    sales: np.ndarray,                 # (S, T) observed daily sales
    price: np.ndarray,                 # (S, T) observed prices (ffilled)
    cal: Dict[str, np.ndarray],        # arrays of length >= T + max horizon
    idx: Dict[str, np.ndarray],        # item_idx, store_idx, dept_idx, cat_idx -> (S,)
    origins: Iterable[int],
    horizons: Sequence[int] = range(1, MAX_HORIZON + 1),
    with_target: bool = False,
    future_price_mult: float = 1.0,
) -> pd.DataFrame:
    """Return one row per (series, origin, horizon)."""
    S, T = sales.shape
    sales = sales.astype(np.float64)
    cs = np.concatenate([np.zeros((S, 1)), np.cumsum(sales, 1)], 1)
    cs2 = np.concatenate([np.zeros((S, 1)), np.cumsum(sales ** 2, 1)], 1)
    cz = np.concatenate([np.zeros((S, 1)), np.cumsum(sales == 0, 1)], 1)
    cols: Dict[str, list] = {}

    def add(name, arr):
        cols.setdefault(name, []).append(np.asarray(arr))

    for o in origins:
        o = int(o)
        assert MIN_ORIGIN <= o < T, f"origin {o} outside [{MIN_ORIGIN}, {T - 1}]"
        base = {f"lag{k}": sales[:, o - k + 1] for k in LAGS}
        for w in ROLL_WINDOWS:
            m = (cs[:, o + 1] - cs[:, o + 1 - w]) / w
            base[f"roll_mean_{w}"] = m
            if w in (7, 14, 28):
                var = (cs2[:, o + 1] - cs2[:, o + 1 - w]) / w - m ** 2
                base[f"roll_std_{w}"] = np.sqrt(np.clip(var, 0, None))
        base["zero_frac_28"] = (cz[:, o + 1] - cz[:, o - 27]) / 28
        price_o = price[:, o]
        base["price"] = price_o
        base["price_rel_56"] = price_o / np.clip(price[:, o - 55:o + 1].mean(1), 1e-6, None)
        for h in horizons:
            t = o + h
            k0 = math.ceil(h / 7)
            same = [t - 7 * k for k in range(k0, k0 + 4)]
            assert max(same) <= o and min(same) >= 0
            price_t = price[:, t] if t < price.shape[1] else price_o * future_price_mult
            for n, v in base.items():
                add(n, v)
            add("same_dow_mean4", sales[:, same].mean(1))
            add("snaive", sales[:, same[0]])
            add("price_ratio_target", price_t / np.clip(price_o, 1e-6, None))
            add("h", np.full(S, h))
            for key in CAL_KEYS:
                add(f"t_{key}", np.full(S, cal[key][t]))
            for key in CATEGORICAL:
                add(key, idx[key])
            add("series", np.arange(S))
            add("origin", np.full(S, o))
            if with_target:
                add("y", sales[:, t])

    df = pd.DataFrame({k: np.concatenate(v) for k, v in cols.items()})
    for c in FEATURES:
        if c not in CATEGORICAL:
            df[c] = df[c].astype("float32")
    return df
