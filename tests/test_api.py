import json, os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import config


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def ids(c):
    cat = c.get("/catalog").json(); return cat["items"][0], cat["stores"][0]


def test_health_and_model_info(c):
    assert c.get("/health").json()["status"] == "ok"
    mi = c.get("/model-info").json(); assert mi["model_version"] and "test_metrics" in mi


def test_forecast(c, ids):
    r = c.post("/forecast", json={"item_id": ids[0], "store_id": ids[1], "horizon": 14}); assert r.status_code == 200
    d = r.json(); assert len(d["daily"]) == 14 and len(d["history"]) == 56
    assert all(x["p10"] <= x["p50"] <= x["p90"] for x in d["daily"]) and d["totals"]["p90"] >= d["totals"]["mean"]


def test_recommendation_contract(c, ids):
    d = c.post("/recommendation", json={"item_id": ids[0], "store_id": ids[1]}).json()
    assert d["action"] in {"INCREASE", "REDUCE", "MAINTAIN"} and d["inventory"]["delta"] == round(d["inventory"]["recommended"] - d["inventory"]["current"], 1)
    assert d["reason"] and 0 <= d["service_level"] <= 1 and d["solver"]["status"] == "Optimal"


def test_recommendation_respects_overrides(c, ids):
    d = c.post("/recommendation", json={"item_id": ids[0], "store_id": ids[1], "current_inventory": 0, "store_capacity": 3, "warehouse_supply": 1000}).json()
    assert d["inventory"]["recommended"] <= 3 and "capacity_constraint" in d["reason"]


def test_optimize_and_simulate(c, ids):
    o = c.post("/optimize", json={"service_level": 0.9}).json(); assert o["solver"]["status"] == "Optimal" and o["summary"]["n_rows"] == len(o["rows"])
    s = c.post("/simulate", json={"item_id": ids[0], "store_id": ids[1], "demand_multiplier": 1.5, "n_simulations": 50}).json()
    assert 0 <= s["results"]["smartstock_policy"]["fill_rate"] <= 1 and len(s["trajectory"]) == 28


@pytest.mark.parametrize("body,code", [({"item_id": "NOPE", "store_id": "CA_1"}, 404), ({"item_id": "x", "store_id": "y", "horizon": 99}, 422),
                                       ({"store_id": "CA_1"}, 422), ({"item_id": "x", "store_id": "y", "price_multiplier": -1}, 422)])
def test_invalid_inputs(c, body, code):
    assert c.post("/forecast", json=body).status_code == code


def test_cors_allows_configured_origin(c):
    r = c.options("/forecast", headers={"Origin": config.ALLOWED_ORIGINS[0], "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert r.headers.get("access-control-allow-origin") == config.ALLOWED_ORIGINS[0]
    r = c.options("/forecast", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


def test_artifact_parity_recorded():
    p = json.load(open(os.path.join(config.ARTIFACT_DIR, "parity_check.json"))); assert p["max_abs_diff"] < 1e-6
