from fastapi import APIRouter, Request

router = APIRouter(tags=["meta"])


@router.get("/health")
def health(request: Request):
    e = getattr(request.app.state, "engine", None)
    return {"status": "ok" if e else "loading", "model_version": e.version if e else None}


@router.get("/model-info")
def model_info(request: Request):
    return request.app.state.engine.model_info()


@router.get("/catalog")
def catalog(request: Request):
    e = request.app.state.engine
    return {"items": e.items, "stores": e.stores, "series": [{"item_id": s["item_id"], "store_id": s["store_id"], "category": s["cat_id"]} for s in e.series]}


@router.get("/overview")
def overview(request: Request):
    return request.app.state.engine.overview()
