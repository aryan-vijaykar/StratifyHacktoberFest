from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------
class PurchaseOrderBase(OrmBase):
    supplier_id: int
    material_id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: int = Field(default=1, gt=0)
    unit_cost: float = Field(default=0.0, ge=0)
    expected_delivery_date: datetime
    actual_delivery_date: Optional[datetime] = None
    status: str = Field(default="PENDING", pattern="^(PENDING|SHIPPED|DELIVERED|CANCELLED)$")


class PurchaseOrderCreate(PurchaseOrderBase):
    pass


class PurchaseOrderUpdate(OrmBase):
    supplier_id: Optional[int] = None
    material_id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    unit_cost: Optional[float] = Field(default=None, ge=0)
    expected_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    status: Optional[str] = Field(default=None, pattern="^(PENDING|SHIPPED|DELIVERED|CANCELLED)$")


class PurchaseOrderSchema(PurchaseOrderBase):
    id: int
    order_date: datetime


# ---------------------------------------------------------------------------
# Transportation Log
# ---------------------------------------------------------------------------
class TransportationLogBase(OrmBase):
    purchase_order_id: int
    carrier: str = Field(..., min_length=1, max_length=255)
    shipping_cost: float = Field(default=0.0, ge=0)
    transit_days: int = Field(default=1, gt=0)
    revenue_at_sale: float = Field(default=0.0, ge=0)


class TransportationLogCreate(TransportationLogBase):
    pass


class TransportationLogUpdate(OrmBase):
    purchase_order_id: Optional[int] = None
    carrier: Optional[str] = None
    shipping_cost: Optional[float] = Field(default=None, ge=0)
    transit_days: Optional[int] = Field(default=None, gt=0)
    revenue_at_sale: Optional[float] = Field(default=None, ge=0)


class TransportationLogSchema(TransportationLogBase):
    id: int


# ---------------------------------------------------------------------------
# Margins Output
# ---------------------------------------------------------------------------
class ShipmentMarginResponse(BaseModel):
    purchase_order_id: int
    carrier: str
    shipping_cost: float
    unit_cost: float
    quantity: int
    revenue_at_sale: float
    margin_profit: float
    margin_pct: float
