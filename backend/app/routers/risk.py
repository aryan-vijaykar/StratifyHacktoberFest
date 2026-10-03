"""
Risk & Pricing Router — Phase 3 risk intelligence and pricing optimisation.

Endpoints:
  GET /risk/customers   — Customer churn + payment risk assessment
  GET /risk/suppliers   — Supplier delay + price increase risk
  GET /pricing          — Optimal pricing recommendations per product
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.prediction_engine import PredictionEngineService

router = APIRouter(tags=["Risk & Pricing Intelligence"])


@router.get("/risk/customers")
async def customer_risk(db: AsyncSession = Depends(get_db)):
    """
    Multi-factor customer risk assessment.
    Predicts churn probability, late payment risk, and CLV for every customer.
    """
    return await PredictionEngineService.predict_customer_risk(db)


@router.get("/risk/suppliers")
async def supplier_risk(db: AsyncSession = Depends(get_db)):
    """
    Supplier delivery delay probability and price increase risk assessment.
    Helps prioritise dual-sourcing and contract renegotiation.
    """
    return await PredictionEngineService.predict_supplier_risk(db)


@router.get("/pricing")
async def pricing_recommendations(db: AsyncSession = Depends(get_db)):
    """
    Margin-optimised pricing recommendations for every product in the catalogue.
    Includes expected profit per unit, revenue uplift, and demand impact estimate.
    """
    return await PredictionEngineService.pricing_recommendation(db)
