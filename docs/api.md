# API reference

Base URL: `http://localhost:7860` locally, or your deployed Render service URL. Interactive docs: `/docs`.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | – | `{status, model_version}` |
| GET | `/model-info` | – | version, training date, test metrics vs baselines, P90 coverage, business back-test |
| GET | `/catalog` | – | products, stores, valid series |
| GET | `/overview` | – | dashboard KPIs, network demand curve, top actions |
| POST | `/forecast` | `item_id, store_id, horizon (1-28), price_multiplier` | daily mean/P10/P50/P90, totals, 56-day history |
| POST | `/optimize` | `item_ids?, service_level, review_days, lead_time_days?, warehouse_supply?, store_capacity?` | PuLP allocation table (all selected SKU×store) + solver status |
| POST | `/recommendation` | `item_id, store_id, current_inventory?, lead_time_days?, service_level, warehouse_supply?, store_capacity?` | forecast + recommended stock + action + reason codes + placement across stores |
| POST | `/simulate` | `item_id, store_id, demand_multiplier, lead_time_days?, service_level, starting_inventory?, planner_aware, n_simulations` | Monte-Carlo KPIs for baseline vs SmartStock + trajectories |

Errors: `404` unknown item/store, `422` invalid input (horizon > 28, negative price multiplier, missing fields), `503` optimizer failure.

## Example

```bash
curl -X POST $API/recommendation -H 'content-type: application/json' \
  -d '{"item_id":"FOODS_1_001","store_id":"CA_1","current_inventory":5,"service_level":0.95}'
```

```json
{ "model_version": "lightgbm-v1.0", "item_id": "FOODS_1_001", "store_id": "CA_1",
  "forecast": {"horizon_days": 28, "mean_total": 27.88, "p50_total": 27.88, "p90_total": 35.54},
  "inventory": {"current": 5, "recommended": 22, "delta": 17, "safety_stock": 7.4, "lead_time_days": 7},
  "service_level": 0.9512, "action": "INCREASE", "reason": ["low_stock", "lead_time_risk", "high_demand_uncertainty"] }
```

## Definitions
* **Forecast**: global LightGBM, direct multi-horizon. `mean` = Poisson-objective model; P10/P50/P90 = quantile models (sorted to prevent crossing).
* **Total P90**: computed from aggregated daily variance (daily σ from the P10–P90 band, days treated as independent), *not* a sum of daily P90s.
* **Target stock** = expected demand over (lead time + review period) + z(service level) × σ over that window.
* **Optimizer**: minimise transport + holding + shortage penalty subject to warehouse supply (per SKU), store capacity and non-negativity; stock can be pulled back from overstocked stores.
* Lead times, costs, supply, capacity and current stock are **simulated**.
