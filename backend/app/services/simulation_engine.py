"""
Digital Twin / Simulation Engine — What-if business scenario modelling.

The simulation engine creates a projected snapshot of the business state
after applying hypothetical changes (price, hiring, suppliers, inventory, loans).

Architecture:
  - Reads current DB state as the baseline
  - Applies scenario deltas mathematically
  - Returns projected KPIs without writing to DB
  - Completely decoupled from routing and AI layers
"""

import logging
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Customer, Employee, Invoice, Product, Sales
from app.schemas.decision import SimulationInput, SimulationOutput
from app.utils.helpers import clamp, safe_divide

logger = logging.getLogger(__name__)


class SimulationEngineService:
    """
    Stateless digital twin simulator.
    Projects the impact of business decisions without modifying live data.
    """

    @staticmethod
    async def simulate(db: AsyncSession, scenario: SimulationInput) -> SimulationOutput:
        """
        Run a digital twin simulation for the given input scenario.

        Steps:
          1. Load current business baseline from DB
          2. Apply each scenario delta
          3. Compute projected revenue, profit, cash flow, and risk
          4. Return structured output with insights and warnings
        """
        logger.info("Digital twin simulation started: %s", scenario.model_dump(exclude_none=True))

        # ----- Baseline from DB -----
        baseline_revenue = (await db.execute(select(func.sum(Sales.total_price)))).scalar() or 0.0
        baseline_costs = (
            await db.execute(select(func.sum(Invoice.total_amount)).where(Invoice.supplier_id.isnot(None)))
        ).scalar() or 0.0

        total_ar = (
            await db.execute(
                select(func.sum(Invoice.total_amount)).where(
                    Invoice.customer_id.isnot(None),
                    Invoice.status.in_(["UNPAID", "PARTIAL"]),
                )
            )
        ).scalar() or 0.0
        total_ap = (
            await db.execute(
                select(func.sum(Invoice.total_amount)).where(
                    Invoice.supplier_id.isnot(None),
                    Invoice.status.in_(["UNPAID", "PARTIAL"]),
                )
            )
        ).scalar() or 0.0

        current_salaries = (await db.execute(select(func.sum(Employee.salary)))).scalar() or 0.0
        active_customers = (
            await db.execute(select(func.count(Customer.id)).where(Customer.is_active == 1))
        ).scalar() or 0

        products = (await db.execute(select(Product))).scalars().all()

        # ----- Apply Scenario Deltas -----
        projected_revenue = baseline_revenue
        projected_costs = baseline_costs
        insights: List[str] = []
        warnings: List[str] = []

        # 1. Price changes
        if scenario.price_changes:
            for product_id_str, new_price in scenario.price_changes.items():
                try:
                    pid = int(product_id_str)
                    product = next((p for p in products if p.id == pid), None)
                    if product and new_price > 0:
                        old_price = product.price
                        price_delta_pct = (new_price - old_price) / old_price
                        # Estimate revenue impact: demand elasticity factor of -0.5
                        demand_change = -0.5 * price_delta_pct
                        revenue_change = baseline_revenue * 0.1 * (price_delta_pct + demand_change)
                        projected_revenue += revenue_change
                        direction = "increase" if new_price > old_price else "decrease"
                        insights.append(
                            f"Price {direction} for product #{pid}: ${old_price:.2f} → ${new_price:.2f} "
                            f"(estimated revenue delta: ${revenue_change:+,.0f})"
                        )
                        if new_price < product.cost:
                            warnings.append(f"Product #{pid} new price ${new_price:.2f} is BELOW COST (${product.cost:.2f})!")
                except (ValueError, TypeError) as exc:
                    logger.warning("Invalid price change entry: %s — %s", product_id_str, exc)

        # 2. New hires
        if scenario.new_hires and scenario.new_hires > 0:
            annual_cost = scenario.new_hires * (scenario.avg_new_hire_salary or 50000.0)
            projected_costs += annual_cost
            productivity_uplift = projected_revenue * 0.05 * scenario.new_hires
            projected_revenue += productivity_uplift
            insights.append(
                f"Hiring {scenario.new_hires} employee(s) at ${scenario.avg_new_hire_salary:,.0f}/year: "
                f"cost +${annual_cost:,.0f}/yr, productivity uplift +${productivity_uplift:,.0f}"
            )
            if scenario.new_hires > 5:
                warnings.append("Hiring more than 5 employees simultaneously may strain onboarding resources.")

        # 3. Supplier strategy
        if scenario.supplier_change:
            if scenario.supplier_change == "diversify":
                procurement_saving = projected_costs * 0.05  # Estimate 5% cost reduction
                projected_costs -= procurement_saving
                insights.append(f"Supplier diversification estimated to reduce procurement costs by ${procurement_saving:,.0f}.")
            elif scenario.supplier_change == "single_source":
                negotiation_saving = projected_costs * 0.08
                projected_costs -= negotiation_saving
                insights.append(f"Single-source consolidation could save ${negotiation_saving:,.0f} via volume discounts.")
                warnings.append("Single-source strategy increases supply chain concentration risk significantly.")

        # 4. Inventory investment
        if scenario.inventory_investment and scenario.inventory_investment > 0:
            projected_costs += scenario.inventory_investment
            revenue_uplift = scenario.inventory_investment * 1.3  # Assume 30% return on inventory
            projected_revenue += revenue_uplift
            insights.append(
                f"Inventory investment of ${scenario.inventory_investment:,.0f} projected to generate "
                f"${revenue_uplift:,.0f} in additional sales (1.3× return assumption)."
            )
            if scenario.inventory_investment > total_ar * 0.5:
                warnings.append("Inventory investment exceeds 50% of current AR — ensure sufficient cash coverage.")

        # 5. Loan
        annual_interest = 0.0
        if scenario.loan_amount and scenario.loan_amount > 0:
            annual_interest = scenario.loan_amount * ((scenario.loan_interest_rate_pct or 5.0) / 100)
            projected_costs += annual_interest
            projected_revenue += scenario.loan_amount * 0.15  # Assume loan generates 15% revenue uplift
            insights.append(
                f"Loan of ${scenario.loan_amount:,.0f} at {scenario.loan_interest_rate_pct:.1f}%/yr: "
                f"interest cost ${annual_interest:,.0f}/yr, projected revenue uplift ${scenario.loan_amount * 0.15:,.0f}."
            )
            if scenario.loan_amount > baseline_revenue * 0.5:
                warnings.append("Loan amount exceeds 50% of annual revenue — high leverage risk.")

        # 6. Marketing spend
        if scenario.marketing_spend and scenario.marketing_spend > 0:
            annual_marketing = scenario.marketing_spend * 12
            projected_costs += annual_marketing
            # Marketing ROI: 3× return in year 1
            marketing_revenue = annual_marketing * 3
            projected_revenue += marketing_revenue
            insights.append(
                f"Marketing spend of ${scenario.marketing_spend:,.0f}/mo generates "
                f"~${marketing_revenue:,.0f}/yr at assumed 3× ROI."
            )

        # ----- Compute Projections -----
        projected_profit = projected_revenue - projected_costs
        net_cash = total_ar + (scenario.loan_amount or 0) - total_ap - projected_costs * 0.1
        projected_cash_flow = net_cash

        # Risk score: 0.0 (safe) → 1.0 (critical)
        risk_factors = []
        if projected_profit < 0:
            risk_factors.append(0.40)
        if scenario.loan_amount and scenario.loan_amount > baseline_revenue:
            risk_factors.append(0.25)
        if len(warnings) > 2:
            risk_factors.append(0.20)
        if projected_revenue < baseline_revenue * 0.8:
            risk_factors.append(0.15)

        risk_score = clamp(sum(risk_factors), 0.0, 1.0)

        # Inventory health
        low_stock_products = [p for p in products if p.stock_level <= p.reorder_point]
        effective_inventory = len(low_stock_products)
        if scenario.inventory_investment and scenario.inventory_investment > 0:
            effective_inventory = max(0, effective_inventory - 2)  # Assume investment resolves 2 issues

        inventory_health = (
            "CRITICAL" if effective_inventory > 10
            else "AT_RISK" if effective_inventory > 3
            else "HEALTHY"
        )

        # Business health score
        profit_margin = safe_divide(projected_profit, projected_revenue, 0.0)
        health_score = int(
            clamp(
                (profit_margin * 50)  # up to 50 points from margin
                + ((1 - risk_score) * 30)  # up to 30 points from low risk
                + (20 if inventory_health == "HEALTHY" else 5 if inventory_health == "AT_RISK" else 0),
                0,
                100,
            )
        )

        scenario_label = f"Scenario: {', '.join(insights[:2]) or 'Baseline projection'}"

        return SimulationOutput(
            scenario_label=scenario_label,
            projected_revenue=round(projected_revenue, 2),
            projected_profit=round(projected_profit, 2),
            projected_cash_flow=round(projected_cash_flow, 2),
            risk_score=round(risk_score, 3),
            inventory_health=inventory_health,
            business_health_score=health_score,
            key_insights=insights,
            warnings=warnings,
        )
