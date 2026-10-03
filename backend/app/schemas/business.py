"""
Business Schemas — Pydantic V2 models for request validation and response serialization.

Follows the pattern:
  XxxBase     → shared fields
  XxxCreate   → fields required for POST (creation)
  XxxUpdate   → optional fields for PATCH (partial update)
  XxxSchema   → full response schema (includes DB-generated fields)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Shared Base Config
# ---------------------------------------------------------------------------
class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
class CompanyBase(OrmBase):
    name: str = Field(..., min_length=1, max_length=255)
    industry: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    cash_balance: float = Field(default=0.0, ge=0)
    annual_revenue_target: float = Field(default=0.0, ge=0)
    founded_year: Optional[int] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(OrmBase):
    name: Optional[str] = None
    industry: Optional[str] = None
    cash_balance: Optional[float] = None
    annual_revenue_target: Optional[float] = None


class CompanySchema(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
class CustomerBase(OrmBase):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    credit_score: int = Field(default=700, ge=300, le=850)
    credit_limit: float = Field(default=10000.0, ge=0)
    payment_terms_days: int = Field(default=30, ge=0)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(OrmBase):
    name: Optional[str] = None
    phone: Optional[str] = None
    credit_score: Optional[int] = Field(default=None, ge=300, le=850)
    credit_limit: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[int] = Field(default=None, ge=0, le=1)


class CustomerSchema(CustomerBase):
    id: int
    clv: float
    is_active: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------
class SupplierBase(OrmBase):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: int = Field(default=30, ge=0)
    reliability_score: float = Field(default=1.0, ge=0.0, le=1.0)
    average_lead_days: int = Field(default=7, ge=0)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(OrmBase):
    name: Optional[str] = None
    reliability_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    average_lead_days: Optional[int] = None
    payment_terms_days: Optional[int] = None


class SupplierSchema(SupplierBase):
    id: int
    total_orders_placed: int
    total_delayed_orders: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
class ProductBase(OrmBase):
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: str = "unit"
    price: float = Field(..., gt=0)
    cost: float = Field(..., gt=0)
    stock_level: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=10, ge=0)
    reorder_quantity: int = Field(default=50, ge=0)
    supplier_id: Optional[int] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(OrmBase):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    cost: Optional[float] = Field(default=None, gt=0)
    stock_level: Optional[int] = Field(default=None, ge=0)
    reorder_point: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[int] = Field(default=None, ge=0, le=1)


class ProductSchema(ProductBase):
    id: int
    is_active: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
class InventoryBase(OrmBase):
    product_id: int
    current_stock: int = Field(..., ge=0)
    reserved_stock: int = Field(default=0, ge=0)
    warehouse_location: Optional[str] = None


class InventoryUpdate(OrmBase):
    current_stock: Optional[int] = Field(default=None, ge=0)
    reserved_stock: Optional[int] = Field(default=None, ge=0)
    warehouse_location: Optional[str] = None


class InventorySchema(InventoryBase):
    id: int
    last_updated: datetime


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------
class SalesBase(OrmBase):
    product_id: int
    customer_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    discount_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    channel: str = "direct"


class SalesCreate(SalesBase):
    """total_price is calculated server-side from quantity × unit_price × (1 - discount)."""
    pass


class SalesSchema(SalesBase):
    id: int
    total_price: float
    date: datetime


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
class InvoiceBase(OrmBase):
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_type: str = Field(default="AR", pattern="^(AR|AP)$")
    due_date: datetime
    total_amount: float = Field(..., gt=0)
    tax_amount: float = Field(default=0.0, ge=0)
    discount_amount: float = Field(default=0.0, ge=0)
    status: str = Field(default="UNPAID", pattern="^(UNPAID|PARTIAL|PAID|OVERDUE)$")
    notes: Optional[str] = None
    customer_id: Optional[int] = None
    supplier_id: Optional[int] = None

    @field_validator("customer_id", "supplier_id", mode="before")
    @classmethod
    def at_least_one_party(cls, v: Optional[int]) -> Optional[int]:
        return v


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(OrmBase):
    status: Optional[str] = Field(default=None, pattern="^(UNPAID|PARTIAL|PAID|OVERDUE)$")
    paid_amount: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class InvoiceSchema(InvoiceBase):
    id: int
    paid_amount: float
    issue_date: datetime


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------
class EmployeeBase(OrmBase):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    role: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    salary: float = Field(..., gt=0)
    employment_type: str = Field(default="full_time", pattern="^(full_time|part_time|contractor)$")


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeSchema(EmployeeBase):
    id: int
    is_active: int
    hire_date: datetime


# ---------------------------------------------------------------------------
# Business Event
# ---------------------------------------------------------------------------
class BusinessEventCreate(OrmBase):
    event_type: str
    description: str
    severity: str = "INFO"
    source: str = "user"
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None


class BusinessEventSchema(BusinessEventCreate):
    id: int
    timestamp: datetime


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    response: str
    model_used: str
    context_summary: Dict[str, Any]



# ---------------------------------------------------------------------------
# Chat / AI
# ---------------------------------------------------------------------------
class ChatRequest(OrmBase):
    question: str = Field(..., min_length=1)


class ChatResponse(OrmBase):
    response: str
    model_used: str
    context_summary: Optional[Dict[str, Any]] = None
