"""
Decision Schemas — Request/response models for the multi-agent decision engine,
digital twin simulator, and explainability layer.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Agent Report
# ---------------------------------------------------------------------------
class AgentReport(OrmBase):
    """Structured output from a single specialist agent."""

    agent_name: str
    analysis: str
    recommendations: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: str          # LOW | MEDIUM | HIGH
    supporting_evidence: List[str]


# ---------------------------------------------------------------------------
# CEO Summary (Phase 4)
# ---------------------------------------------------------------------------
class CEOSummary(OrmBase):
    """Aggregated executive summary produced by the CEO Agent."""

    executive_summary: str
    top_priorities: List[str]
    strategic_decisions: List[str]
    business_risks: List[str]
    growth_opportunities: List[str]
    agent_reports: List[AgentReport]


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------
class RecommendationItem(OrmBase):
    """A single prioritized business recommendation with full explainability."""

    title: str
    recommendation: str
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    roi_estimate: float          # % return on investment
    risk_level: str              # LOW | MEDIUM | HIGH
    business_impact: str
    affected_departments: List[str]
    supporting_evidence: List[str]
    agent_source: str


class RecommendationsResponse(OrmBase):
    total: int
    recommendations: List[RecommendationItem]


# ---------------------------------------------------------------------------
# Digital Twin / Simulation
# ---------------------------------------------------------------------------
class SimulationInput(OrmBase):
    """What-if scenario parameters for the digital twin."""

    price_changes: Optional[Dict[str, float]] = Field(
        default=None,
        description="Map of product_id → new_price (e.g. {'1': 29.99})"
    )
    new_hires: Optional[int] = Field(default=0, ge=0, description="Number of new employees to model")
    avg_new_hire_salary: Optional[float] = Field(default=50000.0, gt=0)
    supplier_change: Optional[str] = Field(
        default=None,
        description="Supplier strategy: 'diversify' | 'single_source'"
    )
    inventory_investment: Optional[float] = Field(
        default=0.0, ge=0, description="Additional inventory spend in $"
    )
    loan_amount: Optional[float] = Field(
        default=0.0, ge=0, description="Business loan amount to model"
    )
    loan_interest_rate_pct: Optional[float] = Field(
        default=5.0, ge=0, description="Annual loan interest rate %"
    )
    marketing_spend: Optional[float] = Field(
        default=0.0, ge=0, description="Additional monthly marketing spend $"
    )


class SimulationOutput(OrmBase):
    """Projected business state after applying the simulated scenario."""

    scenario_label: str
    projected_revenue: float
    projected_profit: float
    projected_cash_flow: float
    risk_score: float            # 0.0 (safe) → 1.0 (critical)
    inventory_health: str        # HEALTHY | AT_RISK | CRITICAL
    business_health_score: int   # 0–100
    key_insights: List[str]
    warnings: List[str]


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------
class ExplainRequest(OrmBase):
    recommendation_id: int


class ExplainResponse(OrmBase):
    recommendation_id: int
    reason: str
    evidence: List[str]
    confidence: float
    business_impact: str
    affected_departments: List[str]


# ---------------------------------------------------------------------------
# Decision History
# ---------------------------------------------------------------------------
class DecisionFeedback(OrmBase):
    """User feedback on a recommendation outcome."""

    recommendation_id: int
    user_action: str = Field(..., pattern="^(APPROVED|REJECTED|MODIFIED)$")
    modification_notes: Optional[str] = None
    business_outcome: Optional[str] = None
    outcome_revenue_impact: Optional[float] = None
    feedback: Optional[str] = None


class DecisionHistorySchema(OrmBase):
    id: int
    recommendation_id: Optional[int]
    user_action: str
    modification_notes: Optional[str]
    business_outcome: Optional[str]
    outcome_revenue_impact: Optional[float]
    feedback: Optional[str]
    timestamp: datetime


# ---------------------------------------------------------------------------
# Strategic Growth (Phase 5)
# ---------------------------------------------------------------------------
class StrategyBrief(OrmBase):
    capital_allocation: str
    next_product_focus: str
    cost_reductions: str
    promotional_offers: str
    supporting_evidence: Dict[str, str]  # citations of specialist findings
