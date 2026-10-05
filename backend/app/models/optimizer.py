"""PuLP placement optimizer.
Minimise  transport*(ship+remove) + holding*(inventory after) + stockout_penalty*shortage
s.t.  shipments per SKU <= warehouse supply (+ units removed from stores)   [supply]
      sum over SKUs of stock in a store <= store capacity                    [capacity]
      shortage >= target - stock after                                       [service-level target, soft]
      remove <= current stock, all variables >= 0 (integers)               """
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd
import pulp


def optimize_allocation(df: pd.DataFrame, supply: Dict[str, float], store_capacity: Dict[str, float],
                        integer: bool = True, time_limit: int = 20) -> tuple[pd.DataFrame, dict]:
    """df columns: item_id, store_id, current, target, hold, penalty, transport  (hold = cost over the cover window)."""
    df = df.reset_index(drop=True).copy()
    cat = pulp.LpInteger if integer else pulp.LpContinuous
    prob = pulp.LpProblem("smartstock_placement", pulp.LpMinimize)
    x = [pulp.LpVariable(f"ship_{i}", 0, cat=cat) for i in range(len(df))]
    y = [pulp.LpVariable(f"remove_{i}", 0, float(r.current), cat=cat) for i, r in df.iterrows()]
    sh = [pulp.LpVariable(f"short_{i}", 0) for i in range(len(df))]
    after = [float(r.current) + x[i] - y[i] for i, r in df.iterrows()]
    prob += pulp.lpSum(float(r.transport) * (x[i] + y[i]) + float(r.hold) * after[i] + float(r.penalty) * sh[i] for i, r in df.iterrows())
    for i, r in df.iterrows():
        prob += sh[i] >= float(np.ceil(r.target)) - after[i]
    for item, g in df.groupby("item_id"):
        prob += pulp.lpSum(x[i] for i in g.index) <= float(supply.get(item, 0)) + pulp.lpSum(y[i] for i in g.index), f"supply_{item}"
    for store, g in df.groupby("store_id"):
        cap = store_capacity.get(store)
        if cap is not None:
            prob += pulp.lpSum(after[i] for i in g.index) <= float(cap), f"cap_{store}"
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit))
    status = pulp.LpStatus[prob.status]
    df["ship"] = [max(0.0, round(v.value() or 0.0)) if integer else (v.value() or 0.0) for v in x]
    df["remove"] = [max(0.0, round(v.value() or 0.0)) if integer else (v.value() or 0.0) for v in y]
    df["recommended"] = df.current + df.ship - df.remove
    df["shortage"] = np.maximum(np.ceil(df.target) - df.recommended, 0)
    cap_used = df.groupby("store_id").recommended.transform("sum")
    df["capacity_bound"] = [bool(store_capacity.get(s) is not None and u >= store_capacity[s] - 0.5) for s, u in zip(df.store_id, cap_used)]
    sup_used = df.groupby("item_id").ship.transform("sum") - df.groupby("item_id").remove.transform("sum")
    df["supply_bound"] = [bool(sup_used.iloc[i] >= supply.get(df.item_id.iloc[i], 0) - 0.5 and df.shortage.iloc[i] > 0.5) for i in range(len(df))]
    info = dict(status=status, objective=float(pulp.value(prob.objective) or 0.0), n_vars=len(df) * 3)
    return df, info
