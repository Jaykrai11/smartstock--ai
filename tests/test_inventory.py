import numpy as np
from app.models import inventory as inv


def test_targets_hand_check():
    mean = np.full((1, 28), 2.0); p10 = np.full((1, 28), 0.0); p90 = np.full((1, 28), 2 * inv.Z90)   # sigma_daily = 1.0
    t = inv.inventory_targets(mean, p10, p90, lead_time=3, review_days=7, service_level=0.95)
    assert t["base"][0] == 20.0                                  # 2/day * 10 days
    assert abs(t["safety_stock"][0] - inv.z_for(0.95) * np.sqrt(10)) < 1e-9


def test_action_bands():
    assert inv.decide_action(10, 30) == "INCREASE" and inv.decide_action(30, 10) == "REDUCE" and inv.decide_action(20, 21) == "MAINTAIN"


def test_policy_sim_no_demand_only_holding():
    N, H = 1, 14
    r = inv.run_policy(np.zeros((N, H)), np.full((N, H), 10.0), 2, 7, np.array([5.0]), np.array([0.1]), np.array([9.0]), np.array([0.5]))
    assert r["lost_units"][0] == 0 and r["fill_rate"][0] == 1.0 and r["stockout_cost"][0] == 0


def test_policy_sim_stockout_counted():
    r = inv.run_policy(np.full((1, 7), 5.0), np.zeros((1, 7)), 1, 7, np.array([10.0]), np.array([0.1]), np.array([1.0]), np.array([0.0]))
    assert r["lost_units"][0] == 25 and abs(r["fill_rate"][0] - 10 / 35) < 1e-9
