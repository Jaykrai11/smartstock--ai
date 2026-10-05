from fastapi import APIRouter, HTTPException, Request

from app.engine import UnknownSeries
from app.schemas import RecommendationRequest, RecommendationResponse

router = APIRouter(tags=["recommendation"])


@router.post("/recommendation", response_model=RecommendationResponse)
def recommendation(req: RecommendationRequest, request: Request):
    try:
        return request.app.state.engine.recommendation(**req.model_dump())
    except UnknownSeries as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
