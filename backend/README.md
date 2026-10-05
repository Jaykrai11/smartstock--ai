---
title: SmartStock AI API
emoji: 📦
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# SmartStock AI — backend

FastAPI service: LightGBM demand forecasts (mean + P10/P50/P90), safety stock, PuLP inventory placement and Monte-Carlo scenario simulation.

* Interactive docs: `/docs`  ·  Health: `/health`
* Set the Space **variable** `ALLOWED_ORIGINS` to your Vercel URL(s), e.g. `https://smartstock-ai.vercel.app`
  (optional `ALLOWED_ORIGIN_REGEX=https://smartstock-ai-.*\.vercel\.app` for preview deployments).
* No secrets are needed for this deployment. If you add any (DB URL, API keys), put them in Space **Secrets**, never in git.

Inventory parameters (lead times, costs, capacities, current stock) are simulated for the portfolio demo.
