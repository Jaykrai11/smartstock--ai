import pandas as pd
from app.models.optimizer import optimize_allocation


def _df(rows):
    return pd.DataFrame(rows, columns=["item_id", "store_id", "current", "target", "hold", "penalty", "transport"])


def test_cheapest_transport_first_when_supply_short():
    df = _df([["A", "S1", 0, 10, 0.01, 5, 1], ["A", "S2", 0, 10, 0.01, 5, 3]])
    r, info = optimize_allocation(df, {"A": 15}, {})
    assert info["status"] == "Optimal" and list(r.ship) == [10, 5]            # hand-checked: S1 full, S2 gets the remainder


def test_capacity_binds():
    r, _ = optimize_allocation(_df([["A", "S1", 0, 10, 0.01, 5, 1]]), {"A": 100}, {"S1": 6})
    assert r.recommended.iloc[0] == 6 and r.shortage.iloc[0] == 4 and bool(r.capacity_bound.iloc[0])


def test_overstock_is_pulled_back():
    r, _ = optimize_allocation(_df([["A", "S1", 20, 10, 1.0, 5, 0.1]]), {"A": 0}, {})
    assert r.recommended.iloc[0] == 10 and r["remove"].iloc[0] == 10


def test_supply_never_exceeded():
    df = _df([["A", "S1", 0, 50, 0.1, 5, 1], ["A", "S2", 0, 50, 0.1, 5, 1], ["B", "S1", 0, 5, 0.1, 5, 1]])
    r, _ = optimize_allocation(df, {"A": 30, "B": 5}, {})
    assert r[r.item_id == "A"].ship.sum() <= 30 and r[r.item_id == "B"].ship.sum() == 5
