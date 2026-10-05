from fastapi import APIRouter, HTTPException, Request

from app.engine import UnknownSeries
from app.schemas import SimulateRequest

router = APIRouter(tags=["simulation"])


@router.post("/simulate")
def simulate(req: SimulateRequest, request: Request):
    try:
        return request.app.state.engine.simulate(**req.model_dump())
    except UnknownSeries as e:
        raise HTTPException(404, str(e))
