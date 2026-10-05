from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.engine import Engine
from app.routes import forecast, meta, optimize, recommendation, simulation


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = Engine(config.ARTIFACT_DIR)      # models loaded ONCE, not per request
    app.state.engine.overview()                         # warm the dashboard cache
    yield


app = FastAPI(title="SmartStock AI", version="1.0.0", lifespan=lifespan,
              description="Demand forecasting (LightGBM P10/P50/P90), safety stock and PuLP inventory placement. Inventory parameters are simulated.")
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS, allow_origin_regex=config.ALLOWED_ORIGIN_REGEX,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"], allow_credentials=False)
for r in (meta.router, forecast.router, optimize.router, recommendation.router, simulation.router):
    app.include_router(r)


@app.get("/", include_in_schema=False)
def root():
    return {"service": "SmartStock AI", "docs": "/docs", "health": "/health"}
