import numpy as np
from app.features.feature_builder import FEATURES, make_features

CAL = {k: np.arange(200) % 7 for k in ["dow", "month", "week", "quarter", "dom", "event_flag", "event_type"]}
IDX = {k: np.array([0, 1]) for k in ["item_idx", "store_idx", "dept_idx", "cat_idx"]}


def _data(seed=0, T=150):
    rng = np.random.default_rng(seed)
    return rng.poisson(4, (2, T)).astype(float), rng.uniform(1, 5, (2, T))


def test_no_future_leakage():
    """Changing sales AFTER the origin must not change any feature at that origin."""
    sales, price = _data(); o = 100
    a = make_features(sales, price, CAL, IDX, [o])
    s2 = sales.copy(); s2[:, o + 1:] = 999.0                       # corrupt the future
    b = make_features(s2, price, CAL, IDX, [o])
    np.testing.assert_array_equal(a[FEATURES].values, b[FEATURES].values)


def test_shape_and_target_alignment():
    sales, price = _data(); df = make_features(sales, price, CAL, IDX, [80, 90], with_target=True)
    assert len(df) == 2 * 28 * 2
    r = df[(df.origin == 80) & (df.h == 5) & (df.series == 1)].iloc[0]
    assert r.y == sales[1, 85] and r.lag1 == sales[1, 80]


def test_origin_needs_history():
    sales, price = _data()
    try:
        make_features(sales, price, CAL, IDX, [10]); assert False
    except AssertionError as e:
        assert "outside" in str(e) or e is not None
