from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# Base class mimicking schemas.business structure
class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Raw Material
# ---------------------------------------------------------------------------
class RawMaterialBase(OrmBase):
    name: str = Field(..., min_length=1, max_length=255)
    unit: str = Field(..., min_length=1, max_length=50)
    current_unit_price: float = Field(default=0.0, ge=0)
    supplier_id: Optional[int] = None
    reorder_threshold: float = Field(default=0.0, ge=0)


class RawMaterialCreate(RawMaterialBase):
    product_ids: Optional[List[int]] = Field(default=None)


class RawMaterialUpdate(OrmBase):
    name: Optional[str] = None
    unit: Optional[str] = None
    current_unit_price: Optional[float] = None
    supplier_id: Optional[int] = None
    reorder_threshold: Optional[float] = None
    product_ids: Optional[List[int]] = Field(default=None)


class RawMaterialSchema(RawMaterialBase):
    id: int
    product_ids: List[int] = []


# ---------------------------------------------------------------------------
# Material Price History
# ---------------------------------------------------------------------------
class MaterialPriceHistoryBase(OrmBase):
    material_id: int
    recorded_price: float = Field(..., ge=0)
    source: str = Field(default="MANUAL", pattern="^(MANUAL|DOC_INGESTED)$")


class MaterialPriceHistoryCreate(MaterialPriceHistoryBase):
    pass


class MaterialPriceHistorySchema(MaterialPriceHistoryBase):
    id: int
    recorded_at: datetime


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------
class ProductForecastRequest(BaseModel):
    product_id: int


class ProductForecastResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    price: float
    original_cogs: float
    projected_cogs: float
    original_margin: float
    projected_margin: float


# ---------------------------------------------------------------------------
# Buying Advice (Seasonal & Price Trend Analysis)
# ---------------------------------------------------------------------------
class MaterialBuyingAdviceSchema(BaseModel):
    material_id: int
    name: str
    current_unit_price: float
    historical_average: float
    best_month_to_buy: Optional[str] = None
    advice: str  # STOCKPILE | DELAY | HOLD | INSIGNIFICANT_DATA
    justification: str
