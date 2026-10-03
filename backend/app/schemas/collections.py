from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


class PaymentHistoryBase(OrmBase):
    invoice_id: int
    due_date: datetime
    paid_date: Optional[datetime] = None
    days_late: int = Field(default=0, ge=0)
    amount: float = Field(..., gt=0)


class PaymentHistoryCreate(PaymentHistoryBase):
    pass


class PaymentHistorySchema(PaymentHistoryBase):
    id: int
