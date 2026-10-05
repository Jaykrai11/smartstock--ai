from fastapi import APIRouter, HTTPException, Request

from app.engine import UnknownSeries
from app.schemas import ForecastRequest, ForecastResponse

router = APIRouter(tags=["forecast"])


@router.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest, request: Request):
    try:
        return request.app.state.engine.forecast(req.item_id, req.store_id, req.horizon, req.price_multiplier)
    except UnknownSeries as e:
        raise HTTPException(404, str(e))
