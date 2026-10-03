"""
Predictive Schemas — Request/response models for all ML forecast and risk endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


class PredictionResponse(OrmBase):
    """Generic shape returned by every prediction endpoint."""

    prediction: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    important_features: List[str]
    business_impact: str
    suggested_action: str
    metadata: Optional[Dict[str, Any]] = None


class ProductPrediction(PredictionResponse):
    """Prediction scoped to a specific product."""

    product_id: int
    sku: str
    name: str


class CustomerRiskPrediction(PredictionResponse):
    """Risk assessment scoped to a specific customer."""

    customer_id: int
    name: str
    churn_probability: float
    late_payment_risk: str
    clv: float


class SupplierRiskPrediction(PredictionResponse):
    """Risk assessment scoped to a specific supplier."""

    supplier_id: int
    name: str
    delay_risk: str
    reliability_score: float


class PricingRecommendation(OrmBase):
    """Optimal pricing recommendation for a single product."""

    product_id: int
    sku: str
    name: str
    current_price: float
    recommended_price: float
    expected_profit_per_unit: float
    expected_revenue_uplift: float
    demand_impact: str
    confidence_score: float
    suggested_action: str
