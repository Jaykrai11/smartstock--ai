"""Forecaster: loads the trained LightGBM boosters + inference data and produces
mean / P10 / P50 / P90 daily forecasts. Same code path is used by training scripts
(backtests) and by the live API, which is what guarantees train/serve parity."""
from __future__ import annotations

import json
import os
from typing import Dict, List, Sequence

import lightgbm as lgb
import numpy as np
import pandas as pd

from app.features.feature_builder import CAL_KEYS, FEATURES, MAX_HORIZON, make_features

MODEL_FILES = {"mean": "lightgbm_mean.txt", "p10": "lightgbm_p10.txt", "p50": "lightgbm_p50.txt", "p90": "lightgbm_p90.txt"}


class Forecaster:
    def __init__(self, boosters: Dict[str, lgb.Booster], data: Dict[str, np.ndarray], series: List[dict], maps: dict):
        self.boosters, self.series, self.maps = boosters, series, maps
        self.sales, self.price, self.dates = data["sales"], data["price"], data["dates"]
        self.cal = {k: data[f"cal_{k}"] for k in CAL_KEYS}
        self.idx = {k: np.array([s[k] for s in series]) for k in ("item_idx", "store_idx", "dept_idx", "cat_idx")}
        self.key2i = {(s["item_id"], s["store_id"]): i for i, s in enumerate(series)}

    @classmethod
    def load(cls, model_dir: str, data_npz: str, series_json: str) -> "Forecaster":
        boosters = {k: lgb.Booster(model_file=os.path.join(model_dir, f)) for k, f in MODEL_FILES.items()}
        data = dict(np.load(data_npz, allow_pickle=False))
        meta = json.load(open(series_json))
        return cls(boosters, data, meta["series"], meta["maps"])

    @property
    def n_days(self) -> int:
        return self.sales.shape[1]

    def predict_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[FEATURES]
        out = {k: np.clip(b.predict(X), 0, None) for k, b in self.boosters.items()}
        q = np.sort(np.stack([out["p10"], out["p50"], out["p90"]], 1), axis=1)   # no quantile crossing
        return pd.DataFrame({"mean": out["mean"], "p10": q[:, 0], "p50": q[:, 1], "p90": q[:, 2]})

    def forecast(self, series_idx: Sequence[int], origin: int | None = None, horizon: int = MAX_HORIZON,
                 price_multiplier: float = 1.0) -> Dict[str, np.ndarray]:
        """Forecast days origin+1..origin+horizon. Returns arrays of shape (n_series, horizon)."""
        sidx = np.asarray(list(series_idx))
        origin = self.n_days - 1 if origin is None else origin
        assert 1 <= horizon <= MAX_HORIZON
        df = make_features(self.sales[sidx], self.price[sidx], self.cal, {k: v[sidx] for k, v in self.idx.items()},
                           [origin], range(1, horizon + 1), future_price_mult=price_multiplier)
        pred = self.predict_rows(df)
        n = len(sidx)
        return {k: pred[k].values.reshape(horizon, n).T for k in pred.columns}

    def future_dates(self, origin: int | None = None, horizon: int = MAX_HORIZON) -> List[str]:
        o = self.n_days - 1 if origin is None else origin
        return [str(d) for d in self.dates[o + 1: o + 1 + horizon]]
