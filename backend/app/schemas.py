from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    item_id: str = Field(examples=["FOODS_1_001"])
    store_id: str = Field(examples=["CA_1"])
    horizon: int = Field(28, ge=1, le=28)
    price_multiplier: float = Field(1.0, ge=0.5, le=2.0, description="Planned future price relative to current price")


class DailyForecast(BaseModel):
    date: str
    mean: float
    p10: float
    p50: float
    p90: float


class HistoryPoint(BaseModel):
    date: str
    sales: float


class ForecastTotals(BaseModel):
    mean: float
    p50: float
    p90: float


class ForecastResponse(BaseModel):
    model_version: str
    item_id: str
    store_id: str
    origin_date: str
    horizon: int
    totals: ForecastTotals
    daily: List[DailyForecast]
    history: List[HistoryPoint]


class OptimizeRequest(BaseModel):
    item_ids: Optional[List[str]] = Field(None, max_length=40, description="Default: all items")
    service_level: float = Field(0.95, ge=0.5, le=0.999)
    review_days: int = Field(7, ge=1, le=14)
    lead_time_days: Optional[int] = Field(None, ge=1, le=14, description="Override all lead times")
    warehouse_supply: Optional[Dict[str, float]] = Field(None, description="Units available per item_id (default: 90% of total shortfall)")
    store_capacity: Optional[Dict[str, float]] = Field(None, description="Unit capacity per store_id")


class PlacementRow(BaseModel):
    item_id: str
    store_id: str
    current: float
    recommended: float
    delta: float
    action: str
    reason: List[str]
    target_before_constraints: float
    safety_stock: float
    expected_service_level: float
    lead_time_days: int
    shortage_units: float


class OptimizeResponse(BaseModel):
    model_version: str
    solver: dict
    summary: dict
    rows: List[PlacementRow]


class RecommendationRequest(BaseModel):
    item_id: str
    store_id: str
    current_inventory: Optional[float] = Field(None, ge=0, description="Default: simulated value")
    lead_time_days: Optional[int] = Field(None, ge=1, le=14)
    service_level: float = Field(0.95, ge=0.5, le=0.999)
    review_days: int = Field(7, ge=1, le=14)
    warehouse_supply: Optional[float] = Field(None, ge=0, description="Units available to allocate across stores (default: 90% of total shortfall)")
    store_capacity: Optional[float] = Field(None, ge=0, description="Capacity for this item at the selected store")
    horizon: int = Field(28, ge=1, le=28)


class RecommendationResponse(BaseModel):
    model_version: str
    generated_at: str
    item_id: str
    store_id: str
    forecast: dict
    inventory: dict
    service_level: float
    target_service_level: float
    action: str
    reason: List[str]
    placement: List[PlacementRow]
    daily: List[DailyForecast]
    solver: dict
    assumptions: dict


class SimulateRequest(BaseModel):
    item_id: str
    store_id: str
    demand_multiplier: float = Field(1.0, ge=0.1, le=5.0)
    lead_time_days: Optional[int] = Field(None, ge=1, le=14)
    service_level: float = Field(0.95, ge=0.5, le=0.999)
    review_days: int = Field(7, ge=1, le=14)
    starting_inventory: Optional[float] = Field(None, ge=0)
    horizon: int = Field(28, ge=7, le=28)
    n_simulations: int = Field(300, ge=20, le=2000)
    planner_aware: bool = Field(False, description="If true both policies plan with the multiplied demand (a known promotion); if false they are surprised by it (stress test)")
    seed: int = 0
