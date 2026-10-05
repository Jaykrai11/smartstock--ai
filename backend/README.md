# SmartStock AI API

FastAPI service: LightGBM demand forecasts (mean + P10/P50/P90), safety stock, PuLP inventory placement and Monte-Carlo scenario simulation.

* Interactive docs: `/docs` · Health: `/health`
* Set `ALLOWED_ORIGINS` to the deployed frontend URL.
* Keep any secrets (DB URLs, API keys, or tokens) in the hosting provider's environment settings, never in git.

Inventory parameters (lead times, costs, capacities, current stock) are simulated for the portfolio demo.
