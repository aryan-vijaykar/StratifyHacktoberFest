"""
Forecast Router — Phase 3 predictive intelligence endpoints.

Endpoints:
  GET /forecast/revenue     — 90-day revenue projection
  GET /forecast/cashflow    — 30-day cash flow forecast
  GET /forecast/demand      — Per-product demand forecast + reorder suggestions
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.prediction_engine import PredictionEngineService

router = APIRouter(prefix="/forecast", tags=["Predictive Forecasting"])


@router.get("/revenue")
async def forecast_revenue(db: AsyncSession = Depends(get_db)):
    """
    90-day revenue forecast using weighted historical sales velocity.
    Returns confidence score, key features, business impact, and suggested actions.
    """
    return await PredictionEngineService.predict_revenue_90_days(db)


@router.get("/cashflow")
async def forecast_cashflow(db: AsyncSession = Depends(get_db)):
    """
    30-day cash flow forecast based on outstanding AR/AP balances.
    Identifies liquidity risk and recommends corrective actions.
    """
    return await PredictionEngineService.predict_cash_flow(db)


@router.get("/demand")
async def forecast_demand(db: AsyncSession = Depends(get_db)):
    """
    Per-product demand forecast with urgency classification and reorder quantity recommendations.
    Returns a list of predictions — one per active product.
    """
    return await PredictionEngineService.predict_demand(db)
