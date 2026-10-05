from fastapi import APIRouter, HTTPException, Request

from app.engine import UnknownSeries
from app.schemas import OptimizeRequest, OptimizeResponse

router = APIRouter(tags=["optimize"])


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest, request: Request):
    try:
        return request.app.state.engine.optimize(**req.model_dump())
    except UnknownSeries as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
