"""
Decision Intelligence Router — Phase 4 multi-agent decision engine endpoints.

Endpoints:
  GET  /agents              — Run all specialist agents and return individual reports
  GET  /recommendations     — Prioritised recommendations from CEO agent
  POST /simulate            — Digital twin: what-if scenario analysis
  GET  /decision-history    — Past AI recommendations and user decision outcomes
  POST /decision-history    — Submit feedback/outcome for a recommendation
  GET  /explain/{rec_id}    — Explainability: full reasoning for a specific recommendation
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.history import DecisionHistory, RecommendationHistory
from app.schemas.decision import (
    DecisionFeedback,
    DecisionHistorySchema,
    ExplainResponse,
    RecommendationsResponse,
    SimulationInput,
    SimulationOutput,
    StrategyBrief,
)
from app.services.agent_engine import CEOAgent
from app.services.business_memory import BusinessMemoryService
from app.services.simulation_engine import SimulationEngineService
import json

router = APIRouter(tags=["Decision Intelligence Engine"])
logger = logging.getLogger(__name__)

# Singleton CEO agent instance (stateless — safe to reuse)
_ceo_agent = CEOAgent()


# ============================================================
# Agents — Run all specialist agents
# ============================================================

@router.get("/agents")
async def run_agents(db: AsyncSession = Depends(get_db)):
    """
    Execute all 6 specialist agents and return their individual analysis reports.
    Does NOT invoke the CEO synthesis — use /recommendations for the full package.
    """
    result = await _ceo_agent.run(db)
    return {
        "agents": result["agent_reports"],
        "total_agents": len(result["agent_reports"]),
        "context_snapshot": result["context_snapshot"],
    }


# ============================================================
# Recommendations — Full CEO orchestration
# ============================================================

@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(db: AsyncSession = Depends(get_db)):
    """
    Run the full CEO agent pipeline and return prioritised recommendations.

    Pipeline:
      1. All 6 specialist agents analyse the business
      2. CEO agent synthesises reports
      3. Recommendations sorted by confidence × risk weight
      4. Stored in RecommendationHistory for future retrieval
    """
    result = await _ceo_agent.run(db)
    all_recs = result.get("all_recommendations", [])

    # Persist top recommendations to history
    for rec in all_recs[:5]:
        await BusinessMemoryService.store_recommendation(
            db=db,
            agent_name=rec["agent_source"],
            recommendation=rec["recommendation"],
            reasoning=rec["reasoning"],
            roi=rec["roi_estimate"],
            confidence=rec["confidence"],
            risk_level=rec["risk_level"],
            business_impact=rec["business_impact"],
            affected_departments=rec["affected_departments"],
            supporting_evidence=rec["supporting_evidence"],
        )

    return RecommendationsResponse(
        total=len(all_recs),
        recommendations=all_recs,
    )


# ============================================================
# Simulate — Digital Twin
# ============================================================

@router.post("/simulate", response_model=SimulationOutput)
async def simulate_scenario(
    scenario: SimulationInput,
    db: AsyncSession = Depends(get_db),
):
    """
    Digital twin simulation: project the business impact of a what-if scenario.

    Accepts changes to: prices, hiring, supplier strategy, inventory investment,
    loan financing, and marketing spend.

    Returns projected: revenue, profit, cash flow, risk score, inventory health,
    and business health score — without modifying live data.
    """
    return await SimulationEngineService.simulate(db, scenario)


# ============================================================
# Decision History
# ============================================================

@router.get("/decision-history", response_model=List[DecisionHistorySchema])
async def get_decision_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the history of user decisions on AI recommendations."""
    decisions = (
        await db.execute(
            select(DecisionHistory).order_by(DecisionHistory.timestamp.desc()).limit(limit)
        )
    ).scalars().all()
    return decisions


@router.post("/decision-history", response_model=DecisionHistorySchema, status_code=status.HTTP_201_CREATED)
async def record_decision(feedback: DecisionFeedback, db: AsyncSession = Depends(get_db)):
    """
    Record a user's decision on an AI recommendation and the observed business outcome.
    This closes the feedback loop and improves future agent accuracy.
    """
    # Optionally update the recommendation status
    if feedback.recommendation_id:
        rec = (
            await db.execute(
                select(RecommendationHistory).where(RecommendationHistory.id == feedback.recommendation_id)
            )
        ).scalars().first()
        if rec:
            rec.status = feedback.user_action
            await db.flush()

    decision = DecisionHistory(
        recommendation_id=feedback.recommendation_id,
        user_action=feedback.user_action,
        modification_notes=feedback.modification_notes,
        business_outcome=feedback.business_outcome,
        outcome_revenue_impact=feedback.outcome_revenue_impact,
        feedback=feedback.feedback,
    )
    db.add(decision)
    await db.flush()
    await db.refresh(decision)
    return decision


# ============================================================
# Explainability
# ============================================================

@router.get("/explain/{recommendation_id}", response_model=ExplainResponse)
async def explain_recommendation(recommendation_id: int, db: AsyncSession = Depends(get_db)):
    """
    Return full explainability data for a specific recommendation.

    Includes: reasoning, evidence, confidence, business impact, affected departments.
    """
    rec = (
        await db.execute(
            select(RecommendationHistory).where(RecommendationHistory.id == recommendation_id)
        )
    ).scalars().first()

    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation #{recommendation_id} not found. Generate recommendations first via GET /recommendations.",
        )

    return ExplainResponse(
        recommendation_id=rec.id,
        reason=rec.reasoning or "Reasoning not recorded for this recommendation.",
        evidence=rec.supporting_evidence or [],
        confidence=rec.confidence,
        business_impact=rec.business_impact or "Business impact not specified.",
        affected_departments=rec.affected_departments or [],
    )


# ============================================================
# Strategic Growth Strategy Brief
# ============================================================

@router.get("/recommendations/strategy", response_model=StrategyBrief)
async def get_strategy_brief(db: AsyncSession = Depends(get_db)):
    """Retrieve the latest CEO Strategic Growth Brief."""
    result = (await db.execute(
        select(RecommendationHistory)
        .where(RecommendationHistory.agent_name == "CEOAgent")
        .order_by(RecommendationHistory.timestamp.desc())
    )).scalars().first()
    
    if not result:
        # Run CEOAgent pipeline to generate dynamically
        ceo_res = await _ceo_agent.run(db)
        brief = ceo_res.get("strategy_brief")
        if not brief:
            raise HTTPException(status_code=404, detail="Strategy brief not found")
        return brief
        
    try:
        data = json.loads(result.recommendation)
        return StrategyBrief(
            capital_allocation=data["capital_allocation"],
            next_product_focus=data["next_product_focus"],
            cost_reductions=data["cost_reductions"],
            promotional_offers=data["promotional_offers"],
            supporting_evidence=data.get("supporting_evidence", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse stored strategy brief: {e}")
