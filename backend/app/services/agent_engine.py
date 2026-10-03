"""
Multi-Agent Decision Engine — Phase 4 core intelligence layer.

Architecture:
  - Each specialist agent is an independent class with a single async `analyse()` method
  - The CEO Agent collects all specialist reports and produces an executive synthesis
  - All agents receive: business context, historical memory, and prediction data
  - Agents return standardised AgentReport dicts — never ORM objects

Agents:
  FinanceAgent      — Cash flow, margins, AR/AP, overdue invoices
  OperationsAgent   — Inventory, supply chain, fulfilment efficiency
  MarketingAgent    — Customer acquisition, CLV, campaign opportunity
  SupplierAgent     — Procurement risk, vendor management
  CustomerAgent     — Retention, churn, satisfaction, credit risk
  RiskAgent         — Cross-functional risk aggregation
  CEOAgent          — Synthesises all agent reports into executive decisions
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Customer, Invoice, Product, Sales, Supplier
from app.services.business_memory import BusinessMemoryService
from app.services.prediction_engine import PredictionEngineService
from app.utils.helpers import clamp, safe_divide
from app.utils.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


# ============================================================
# Base Agent
# ============================================================

class BaseAgent:
    """
    Abstract base for all specialist agents.
    Subclasses implement `analyse()` returning a standardised report dict.
    """

    name: str = "BaseAgent"
    role: str = "General Analysis"
    focus: str = "Business Operations"

    async def analyse(
        self,
        db: AsyncSession,
        context: Dict[str, Any],
        predictions: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise NotImplementedError


# ============================================================
# Procurement Agent
# ============================================================

class ProcurementAgent(BaseAgent):
    """Analyses raw material cost trends, price history, and purchasing timing."""

    name = "ProcurementAgent"
    role = "Chief Procurement & Raw Materials Intelligence"
    focus = "Raw material spot pricing, cost forecasting, price trend analysis, and stockpile/delay decisions"

    async def analyse(
        self,
        db: AsyncSession,
        context: Dict[str, Any],
        predictions: Dict[str, Any],
    ) -> Dict[str, Any]:
        from app.services.ollama_client import OllamaClient
        
        prompt = PromptBuilder.build_procurement_agent_prompt(context)
        
        # Build raw data context for fallback
        material_history = context.get("material_price_history", [])
        
        try:
            res = await OllamaClient.chat_json(prompt)
            if "analysis" in res and "recommendations" in res:
                return {
                    "agent_name": self.name,
                    "analysis": res["analysis"],
                    "recommendations": res["recommendations"][:4],
                    "confidence": round(float(res.get("confidence", 0.85)), 2),
                    "risk_level": res.get("risk_level", "MEDIUM"),
                    "supporting_evidence": res.get("supporting_evidence", [])[:4],
                }
        except Exception as exc:
            logger.warning("Ollama backend unavailable for ProcurementAgent (%s) — serving fallback analysis.", exc)
            
        # Robust Python heuristic fallback
        recs = []
        evidence = []
        risk_level = "LOW"
        
        for item in material_history:
            name = item["name"]
            curr_price = item["current_price"]
            histories = item.get("history", [])
            
            if histories:
                avg_price = sum(h["recorded_price"] for h in histories) / len(histories)
                price_diff_pct = (curr_price - avg_price) / (avg_price or 1.0)
                
                if price_diff_pct < -0.05:
                    rec = f"{name}: STOCKPILE - Spot price (${curr_price:.2f}) is lower than historical average (${avg_price:.2f}), suggesting stockpile."
                    recs.append(rec)
                    evidence.append(f"{name} spot ${curr_price:.2f} vs avg ${avg_price:.2f}")
                elif price_diff_pct > 0.05:
                    rec = f"{name}: DELAY - Spot price (${curr_price:.2f}) is higher than historical average (${avg_price:.2f}), suggesting delay."
                    recs.append(rec)
                    evidence.append(f"{name} spot ${curr_price:.2f} vs avg ${avg_price:.2f}")
                    risk_level = "MEDIUM"
                else:
                    rec = f"{name}: HOLD - Spot price (${curr_price:.2f}) is close to historical average (${avg_price:.2f}), suggesting hold."
                    recs.append(rec)
                    evidence.append(f"{name} spot ${curr_price:.2f} stable with avg ${avg_price:.2f}")
            else:
                recs.append(f"{name}: HOLD - Spot price is ${curr_price:.2f} (no history available).")
                evidence.append(f"{name} spot is ${curr_price:.2f}")
                
        analysis_str = f"Procurement status: Checked {len(material_history)} raw materials. Spot prices and trailing trends analysed."
        if not material_history:
            analysis_str = "Procurement status: No raw materials logged in the system."
            recs.append("Add raw materials with historical pricing to enable automated timing analysis.")
            
        return {
            "agent_name": self.name,
            "analysis": analysis_str,
            "recommendations": recs[:4],
            "confidence": 0.90,
            "risk_level": risk_level,
            "supporting_evidence": evidence[:4],
        }


# ============================================================
# Finance Agent
# ============================================================

class FinanceAgent(BaseAgent):
    """Analyses financial health: margins, liquidity, AR/AP, and revenue trends."""

    name = "FinanceAgent"
    role = "Chief Financial Intelligence"
    focus = "Cash flow, profitability, receivables, payables, and financial risk"

    async def analyse(
        self,
        db: AsyncSession,
        context: Dict[str, Any],
        predictions: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Revenue metrics
        total_revenue = (await db.execute(select(func.sum(Sales.total_price)))).scalar() or 0.0
        total_costs = (
            await db.execute(
                select(func.sum(Invoice.total_amount)).where(Invoice.supplier_id.isnot(None))
            )
        ).scalar() or 0.0
        gross_profit = total_revenue - total_costs
        gpm = safe_divide(gross_profit, total_revenue, 0.0) * 100

        # AR/AP
        total_ar = (
            await db.execute(
                select(func.sum(Invoice.total_amount)).where(
                    Invoice.customer_id.isnot(None),
                    Invoice.status.in_(["UNPAID", "PARTIAL", "OVERDUE"]),
                )
            )
        ).scalar() or 0.0
        total_ap = (
            await db.execute(
                select(func.sum(Invoice.total_amount)).where(
                    Invoice.supplier_id.isnot(None),
                    Invoice.status.in_(["UNPAID", "PARTIAL", "OVERDUE"]),
                )
            )
        ).scalar() or 0.0

        cash_forecast = predictions.get("cashflow", {})
        revenue_forecast = predictions.get("revenue", {})

        recs = []
        evidence = []

        if gpm < 25:
            recs.append("URGENT: Gross margin below 25% — review cost structure and pricing immediately.")
            evidence.append(f"Gross profit margin: {gpm:.1f}%")
        elif gpm < 35:
            recs.append("Improve gross margin to 35%+ by optimising supplier costs or raising prices.")
            evidence.append(f"Current GPM: {gpm:.1f}% (target: 35%+)")
        else:
            recs.append("Gross margin is healthy — maintain current pricing discipline.")
            evidence.append(f"Gross profit margin: {gpm:.1f}% ✓")

        if total_ar > total_ap * 2:
            recs.append(f"Strong AR position (${total_ar:,.0f}). Prioritise collections to improve cash velocity.")
        elif total_ap > total_ar:
            recs.append(f"Payables (${total_ap:,.0f}) exceed receivables (${total_ar:,.0f}). Accelerate collections or defer non-critical payments.")
            evidence.append("Negative net working capital position")

        if revenue_forecast:
            recs.append(f"Revenue forecast: {revenue_forecast.get('prediction', 'N/A')}. Align cost budgets accordingly.")

        confidence = 0.90 if total_revenue > 0 else 0.50

        return {
            "agent_name": self.name,
            "analysis": (
                f"Financial position: Revenue ${total_revenue:,.2f} | "
                f"Costs ${total_costs:,.2f} | GPM {gpm:.1f}% | "
                f"AR ${total_ar:,.2f} | AP ${total_ap:,.2f}"
            ),
            "recommendations": recs[:4],
            "confidence": round(confidence, 2),
            "risk_level": "HIGH" if gpm < 20 or total_ap > total_ar else ("MEDIUM" if gpm < 35 else "LOW"),
            "supporting_evidence": evidence,
        }


# ============================================================
# Operations Agent
# ============================================================

class OperationsAgent(BaseAgent):
    """Manages inventory health, supply chain efficiency, and operational bottlenecks."""

    name = "OperationsAgent"
    role = "Chief Operations Intelligence"
    focus = "Inventory management, supply chain, fulfilment, and operational efficiency"

    async def analyse(
        self,
        db: AsyncSession,
        context: Dict[str, Any],
        predictions: Dict[str, Any],
    ) -> Dict[str, Any]:
        from app.models.business import Customer, Sales
        from sqlalchemy import func

        low_stock = context.get("low_stock_products", [])
        risky_suppliers = context.get("risky_suppliers", [])

        total_products = (await db.execute(select(func.count(Product.id)))).scalar() or 0
        out_of_stock = (
            await db.execute(select(func.count(Product.id)).where(Product.stock_level == 0))
        ).scalar() or 0

        recs = []
        evidence = []

        # Geographic sales density analysis
        regions = ["East", "West", "North", "South"]
        density_data = {}
        for r_name in regions:
            vol_stmt = select(func.sum(Sales.total_price)).join(Customer).where(Customer.region == r_name)
            sales_volume = (await db.execute(vol_stmt)).scalar() or 0.0
            
            count_stmt = select(func.count(Sales.id)).join(Customer).where(Customer.region == r_name)
            tx_count = (await db.execute(count_stmt)).scalar() or 0
            
            trend = "GROWING" if tx_count > 5 else "STABLE"
            staffing = "INCREASE" if sales_volume > 5000 else "OPTIMAL"
            marketing = "HIGH" if sales_volume < 2000 else "LOW"
            
            density_data[r_name] = {
                "sales_volume": float(sales_volume),
                "sales_count": int(tx_count),
                "demand_trend": trend,
                "staffing_recommendation": staffing,
                "marketing_priority": marketing
            }
            if marketing == "HIGH" and sales_volume > 0:
                recs.append(f"Geographic opportunity: Region '{r_name}' sales volume is underperforming (${sales_volume:,.0f}). Raise marketing budget.")
                evidence.append(f"Region '{r_name}' sales underperforming")

        if out_of_stock > 0:
            recs.append(f"CRITICAL: {out_of_stock} SKU(s) are completely out of stock — expedite reorders immediately.")
            if f"{out_of_stock}/{total_products} SKUs at zero stock" not in evidence:
                evidence.append(f"{out_of_stock}/{total_products} SKUs at zero stock")

        if low_stock:
            recs.append(
                f"{len(low_stock)} products at or below reorder threshold. "
                f"Initiate purchase orders for: {', '.join(p['sku'] for p in low_stock[:3])}."
            )
            evidence.append(f"Low stock SKUs: {[p['sku'] for p in low_stock]}")

        if risky_suppliers:
            worst = risky_suppliers[0]
            recs.append(
                f"Supplier '{worst['name']}' has {worst['reliability_score']:.0%} reliability. "
                f"Source a backup vendor for affected product lines."
            )
            evidence.append(f"Lowest reliability supplier: {worst['name']} ({worst['reliability_score']:.0%})")

        demand_preds = predictions.get("demand", [])
        immediate = [p for p in demand_preds if p.get("metadata", {}).get("urgency") == "IMMEDIATE"]
        if immediate:
            recs.append(f"Immediate reorder required for {len(immediate)} product(s) with zero stock and estimated demand.")

        ops_score = clamp(100 - (out_of_stock * 20) - (len(low_stock) * 5), 0, 100)

        return {
            "agent_name": self.name,
            "analysis": (
                f"Inventory status: {total_products} total SKUs, "
                f"{out_of_stock} out of stock, {len(low_stock)} below reorder point. "
                f"Operations score: {ops_score}/100"
            ),
            "recommendations": recs[:4],
            "confidence": 0.88,
            "risk_level": "CRITICAL" if out_of_stock > 2 else ("HIGH" if low_stock else "LOW"),
            "supporting_evidence": evidence,
            "geographic_sales_density": density_data,
        }


# ============================================================
# Marketing Agent
# ============================================================

class MarketingAgent(BaseAgent):
    """Identifies revenue growth opportunities through customer segmentation and campaign analysis."""

    name = "MarketingAgent"
    role = "Chief Marketing Intelligence"
    focus = "Customer acquisition, retention, CLV maximisation, and growth opportunities"

    async def analyse(
        self,
        db: AsyncSession,
        context: Dict[str, Any],
        predictions: Dict[str, Any],
    ) -> Dict[str, Any]:
        top_customers = context.get("top_customers", [])
        customer_risk = predictions.get("customer_risk", [])

        total_customers = (
            await db.execute(select(func.count(Customer.id)).where(Customer.is_active == 1))
        ).scalar() or 0

        high_clv = [c for c in top_customers if c.get("clv", 0) > 5000]
        high_churn = [c for c in customer_risk if c.get("churn_probability", 0) > 0.40]

        recs = []
        evidence = []

        if high_clv:
            recs.append(
                f"Introduce a VIP programme for {len(high_clv)} high-CLV customer(s). "
                f"Top customer CLV: ${max(c['clv'] for c in high_clv):,.0f}."
            )
            evidence.append(f"High-CLV customers identified: {len(high_clv)}")

        if high_churn:
            recs.append(
                f"{len(high_churn)} customer(s) have >40% churn probability. "
                f"Launch targeted retention campaign with personalised offers."
            )
            evidence.append(f"At-risk customers: {[c['name'] for c in high_churn[:3]]}")

        recs.append(
            f"With {total_customers} active customers, a 10% CLV increase could add "
            f"${sum(c.get('clv', 0) for c in top_customers) * 0.1:,.0f} in incremental revenue."
        )

        recs.append("Analyse top-selling products to identify upsell/cross-sell bundles for existing customers.")

        return {
            "agent_name": self.name,
            "analysis": (
                f"Customer base: {total_customers} active customers. "
                f"{len(high_churn)} at-risk of churn. "
                f"{len(high_clv)} high-value accounts identified."
            ),
            "recommendations": recs[:4],
            "confidence": 0.80,
            "risk_level": "HIGH" if len(high_churn) > total_customers * 0.3 else "MEDIUM",
            "supporting_evidence": evidence,
        }


# ============================================================
# Supplier Agent
# ============================================================

class SupplierAgent(BaseAgent):
    """Manages supplier relationships, procurement risk, and vendor performance."""

    name = "SupplierAgent"
    role = "Chief Procurement Intelligence"
    focus = "Vendor risk, lead times, supplier diversification, and procurement optimisation"

    async def analyse(
        self,
        db: AsyncSession,
        context: Dict[str, Any],
        predictions: Dict[str, Any],
    ) -> Dict[str, Any]:
        from datetime import datetime
        from app.models.supply_chain import PurchaseOrder, TransportationLog

        suppliers = (await db.execute(select(Supplier))).scalars().all()
        supplier_risk = predictions.get("supplier_risk", [])

        high_risk = [s for s in supplier_risk if s.get("delay_risk") == "HIGH"]
        avg_reliability = (
            sum(s.reliability_score for s in suppliers) / len(suppliers) if suppliers else 1.0
        )

        recs = []
        evidence = []

        # 1. Invoice Payment Delay Analysis (days-late average per supplier)
        supplier_delays = {}
        for s in suppliers:
            ap_stmt = select(Invoice).where(
                Invoice.supplier_id == s.id,
                Invoice.invoice_type == "AP",
                Invoice.status.in_(["UNPAID", "PARTIAL", "OVERDUE"])
            )
            ap_invoices = (await db.execute(ap_stmt)).scalars().all()
            
            late_days = []
            now_dt = datetime.utcnow()
            for inv in ap_invoices:
                if inv.due_date < now_dt:
                    late_days.append((now_dt - inv.due_date).days)
            
            avg_late = sum(late_days) / len(late_days) if late_days else 0.0
            supplier_delays[s.id] = avg_late
            if avg_late > 10.0:
                recs.append(f"Supplier '{s.name}' has AP invoice payment delay averaging {avg_late:.1f} days. Adjust cash allocation priority.")
                evidence.append(f"AP invoice delay for {s.name}: {avg_late:.1f} days avg")

        # 2. Transportation Margin Erosion Detection
        supplier_erosion_count = {}
        for s in suppliers:
            po_stmt = select(PurchaseOrder).where(PurchaseOrder.supplier_id == s.id)
            pos = (await db.execute(po_stmt)).scalars().all()
            
            erosion_shipments = 0
            for po in pos:
                log_stmt = select(TransportationLog).where(TransportationLog.purchase_order_id == po.id)
                log = (await db.execute(log_stmt)).scalars().first()
                if log:
                    gross_margin = log.revenue_at_sale - (po.quantity * po.unit_cost)
                    if gross_margin > 0:
                        erosion_pct = (log.shipping_cost / gross_margin) * 100
                        if erosion_pct > 30.0:
                            erosion_shipments += 1
                            
            supplier_erosion_count[s.id] = erosion_shipments
            if erosion_shipments > 0:
                recs.append(f"Supplier '{s.name}' flagged: {erosion_shipments} shipment(s) with transport cost consuming >30% of margin.")
                evidence.append(f"Margin erosion for {s.name}: {erosion_shipments} shipments")

        if high_risk:
            names = [s["name"] for s in high_risk[:3]]
            recs.append(f"HIGH RISK: {len(high_risk)} supplier(s) flagged ({', '.join(names)}). Activate backup vendor protocol.")
            if f"High-risk suppliers: {names}" not in evidence:
                evidence.append(f"High-risk suppliers: {names}")

        if avg_reliability < 0.80:
            recs.append(
                f"Average supplier reliability is {avg_reliability:.0%} — below the 80% threshold. "
                f"Initiate supplier performance review across the vendor base."
            )

        if len(suppliers) < 3:
            recs.append("Single or dual sourcing detected. Diversify to 3+ suppliers per key product category to reduce concentration risk.")
            evidence.append(f"Total suppliers on record: {len(suppliers)}")

        recs.append("Negotiate fixed-price contracts with strategic suppliers for 6-12 months to hedge against price increases.")

        has_delay_risk = any(delay > 10 for delay in supplier_delays.values())
        has_erosion_risk = any(erosion > 0 for erosion in supplier_erosion_count.values())
        
        overall_risk = "CRITICAL" if (has_delay_risk and has_erosion_risk) else (
            "HIGH" if (high_risk or avg_reliability < 0.70 or has_delay_risk or has_erosion_risk) else "MEDIUM"
        )

        return {
            "agent_name": self.name,
            "analysis": (
                f"Supplier network: {len(suppliers)} vendors. "
                f"Average reliability: {avg_reliability:.0%}. "
                f"{len(high_risk)} high-risk supplier(s) identified. "
                f"Supply Chain: delays={has_delay_risk}, erosion={has_erosion_risk}."
            ),
            "recommendations": recs[:4],
            "confidence": 0.87,
            "risk_level": overall_risk,
            "supporting_evidence": evidence,
        }


# ============================================================
# Customer Agent
# ============================================================

class CustomerAgent(BaseAgent):
    """Deep-dives into individual customer health, payment behaviour, and relationship management."""

    name = "CustomerAgent"
    role = "Chief Customer Success Intelligence"
    focus = "Customer health, satisfaction, credit risk, retention, and lifetime value growth"

    async def analyse(
        self,
        db: AsyncSession,
        context: Dict[str, Any],
        predictions: Dict[str, Any],
    ) -> Dict[str, Any]:
        customer_risk = predictions.get("customer_risk", [])
        high_payment_risk = [c for c in customer_risk if c.get("late_payment_risk") == "HIGH"]
        low_clv = [c for c in customer_risk if c.get("clv", 0) < 500 and c.get("churn_probability", 0) > 0.2]

        recs = []
        evidence = []

        # Collections Risk Analysis
        high_collections_risk = [c for c in customer_risk if c.get("collections_risk_score", 0) > 70.0]
        if high_collections_risk:
            for c in high_collections_risk[:2]:
                recs.append(
                    f"Customer '{c['name']}' has high collections risk ({c['collections_risk_score']:.0f}/100). "
                    f"Escalate collections or suspend further credit shipment."
                )
                evidence.append(f"High collections risk: {c['name']} ({c['collections_risk_score']:.0f}/100)")

        if high_payment_risk:
            recs.append(
                f"{len(high_payment_risk)} customer(s) have HIGH late payment risk. "
                f"Implement prepayment or reduced credit terms for these accounts."
            )
            evidence.append(f"High payment risk count: {len(high_payment_risk)}")

        if low_clv:
            recs.append(
                f"{len(low_clv)} low-CLV customers show churn signals. "
                f"Prioritise re-engagement campaigns before they lapse."
            )

        recs.append("Implement a customer NPS survey to identify satisfaction gaps before they become churn events.")
        recs.append("Review payment terms for overdue accounts — consider early payment discounts of 1-2% for prompt payers.")

        total_clv = sum(c.get("clv", 0) for c in customer_risk)
        has_critical_collections = any(c.get("collections_risk_score", 0) > 85.0 for c in customer_risk)

        return {
            "agent_name": self.name,
            "analysis": (
                f"Customer portfolio: Total CLV tracked = ${total_clv:,.2f}. "
                f"{len(high_payment_risk)} high-payment-risk accounts. "
                f"{len(high_collections_risk)} high-collections-risk accounts."
            ),
            "recommendations": recs[:4],
            "confidence": 0.83,
            "risk_level": "CRITICAL" if (len(high_payment_risk) > 3 or has_critical_collections) else (
                "HIGH" if (high_payment_risk or high_collections_risk) else "MEDIUM"
            ),
            "supporting_evidence": evidence,
        }


# ============================================================
# Risk Agent
# ============================================================

class RiskAgent(BaseAgent):
    """Cross-functional risk aggregation and enterprise risk management."""

    name = "RiskAgent"
    role = "Chief Risk Intelligence"
    focus = "Operational, financial, market, and strategic risk aggregation"

    async def analyse(
        self,
        db: AsyncSession,
        context: Dict[str, Any],
        predictions: Dict[str, Any],
    ) -> Dict[str, Any]:
        low_stock = context.get("low_stock_products", [])
        risky_suppliers = context.get("risky_suppliers", [])
        customer_risk = predictions.get("customer_risk", [])
        supplier_risk = predictions.get("supplier_risk", [])
        cashflow = predictions.get("cashflow", {})

        # Aggregate risk signals
        risk_signals = []
        if len(low_stock) > 5:
            risk_signals.append(f"Inventory risk: {len(low_stock)} SKUs below reorder point")
        if any(c.get("churn_probability", 0) > 0.60 for c in customer_risk):
            risk_signals.append("Customer concentration risk: critical accounts showing churn signals")
        if any(c.get("collections_risk_score", 0) > 70.0 for c in customer_risk):
            risk_signals.append("Collections risk: customer accounts flagged for payment delinquency")
        if any(s.get("delay_risk") == "HIGH" for s in supplier_risk):
            risk_signals.append("Supply chain risk: high-risk supplier(s) active in critical product lines")

        net_balance = cashflow.get("metadata", {}).get("net_balance", 0)
        if net_balance < -5000:
            risk_signals.append(f"Liquidity risk: negative net cash position (${net_balance:+,.0f})")

        overall_risk = "CRITICAL" if len(risk_signals) >= 3 else ("HIGH" if len(risk_signals) >= 2 else "MEDIUM")

        recs = [
            f"Risk signal detected: {sig}" for sig in risk_signals[:3]
        ] + [
            "Establish monthly risk review cadence with department heads.",
            "Implement business continuity plan for top 3 identified risks.",
        ]

        return {
            "agent_name": self.name,
            "analysis": (
                f"Risk assessment: {len(risk_signals)} active risk signal(s) detected. "
                f"Overall enterprise risk level: {overall_risk}"
            ),
            "recommendations": recs[:4],
            "confidence": 0.85,
            "risk_level": overall_risk,
            "supporting_evidence": risk_signals,
        }


# ============================================================
# CEO Agent — Orchestrator
# ============================================================

class CEOAgent:
    """
    CEO Agent orchestrates all specialist agents and synthesises their reports
    into an actionable executive decision package.

    Workflow:
      1. Compile business context from memory
      2. Run all prediction models
      3. Invoke all 6 specialist agents in parallel (sequential here for simplicity)
      4. Synthesise into executive summary
      5. Return prioritised recommendations with full explainability
    """

    SPECIALIST_AGENTS = [
        ProcurementAgent(),
        FinanceAgent(),
        OperationsAgent(),
        MarketingAgent(),
        SupplierAgent(),
        CustomerAgent(),
        RiskAgent(),
    ]

    async def run(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Full agent orchestration pipeline.
        Returns: CEO summary + all agent reports + prioritised recommendations.
        """
        logger.info("CEO Agent orchestration pipeline started.")

        # Step 1: Compile context
        context = await BusinessMemoryService.compile_context(db)

        # Step 2: Run all predictions
        predictions = {
            "revenue": await PredictionEngineService.predict_revenue_90_days(db),
            "cashflow": await PredictionEngineService.predict_cash_flow(db),
            "demand": await PredictionEngineService.predict_demand(db),
            "customer_risk": await PredictionEngineService.predict_customer_risk(db),
            "supplier_risk": await PredictionEngineService.predict_supplier_risk(db),
            "pricing": await PredictionEngineService.pricing_recommendation(db),
        }

        # Step 3: Run specialist agents
        agent_reports = []
        for agent in self.SPECIALIST_AGENTS:
            try:
                report = await agent.analyse(db, context, predictions)
                agent_reports.append(report)
                logger.info("Agent %s completed analysis.", agent.name)
            except Exception as exc:
                logger.error("Agent %s failed: %s", agent.name, exc)
                agent_reports.append({
                    "agent_name": agent.name,
                    "analysis": f"Analysis failed: {exc}",
                    "recommendations": [],
                    "confidence": 0.0,
                    "risk_level": "UNKNOWN",
                    "supporting_evidence": [],
                })

        # Step 3.5: CEO Strategic Growth Brief Generation
        from app.utils.prompt_builder import PromptBuilder
        from app.services.ollama_client import OllamaClient
        from app.models.history import RecommendationHistory
        import json
        
        # Build prompt
        strategy_prompt = PromptBuilder.build_strategy_brief_prompt(agent_reports, context)
        
        strategy_brief_data = None
        try:
            strategy_brief_data = await OllamaClient.chat_json(strategy_prompt)
            required_keys = ["capital_allocation", "next_product_focus", "cost_reductions", "promotional_offers"]
            if not all(k in strategy_brief_data for k in required_keys):
                strategy_brief_data = None
        except Exception as exc:
            logger.warning("Ollama backend unavailable for CEO strategy brief (%s) — invoking fallback brief.", exc)
            
        if not strategy_brief_data:
            # Fallback Brief Heuristics based on agent analyses
            cap_alloc = "Allocate 60% of liquid capital to inventory reordering and 40% to buffer cash-flow deficits."
            cap_cite = "[FinanceAgent]"
            for rep in agent_reports:
                if rep["agent_name"] == "FinanceAgent":
                    cap_alloc = f"Optimize cash balance. {rep['analysis']}"
                    cap_cite = f"[{rep['agent_name']}]"
                    break
                    
            prod_focus = "Prioritize procurement of raw materials showing high price volatility to lock in lower pricing."
            prod_cite = "[ProcurementAgent]"
            for rep in agent_reports:
                if rep["agent_name"] == "ProcurementAgent":
                    prod_focus = f"Hedging raw material spot price risks. {rep['analysis']}"
                    prod_cite = f"[{rep['agent_name']}]"
                    break
                    
            cost_red = "Negotiate fixed-price supply contracts with critical vendors to minimize transportation cost margin erosion."
            cost_cite = "[SupplierAgent]"
            for rep in agent_reports:
                if rep["agent_name"] == "SupplierAgent":
                    cost_red = f"Remediate margin erosion. {rep['analysis']}"
                    cost_cite = f"[{rep['agent_name']}]"
                    break
                    
            promo_off = "Launch targeted marketing campaigns and early payment incentives to secure high-CLV customer segments."
            promo_cite = "[CustomerAgent]"
            for rep in agent_reports:
                if rep["agent_name"] == "CustomerAgent":
                    promo_off = f"Mitigate customer churn. {rep['analysis']}"
                    promo_cite = f"[{rep['agent_name']}]"
                    break
                    
            strategy_brief_data = {
                "capital_allocation": cap_alloc,
                "next_product_focus": prod_focus,
                "cost_reductions": cost_red,
                "promotional_offers": promo_off,
                "supporting_evidence": {
                    "capital_allocation": f"Grounded in {cap_cite} recommendations.",
                    "next_product_focus": f"Grounded in {prod_cite} recommendations.",
                    "cost_reductions": f"Grounded in {cost_cite} recommendations.",
                    "promotional_offers": f"Grounded in {promo_cite} recommendations."
                }
            }
            
        # Store in RecommendationHistory
        rec_obj = RecommendationHistory(
            agent_name="CEOAgent",
            recommendation=json.dumps(strategy_brief_data),
            reasoning=json.dumps(strategy_brief_data.get("supporting_evidence", {})),
            roi=20.0,
            confidence=0.90,
            risk_level="MEDIUM",
            business_impact="CEO Strategic Briefing Alignment",
            affected_departments=["Management", "Finance", "Operations", "Sales"],
            supporting_evidence=list(strategy_brief_data.get("supporting_evidence", {}).values())
        )
        db.add(rec_obj)
        await db.flush()

        # Step 4: CEO synthesis
        all_recommendations = []
        for report in agent_reports:
            for idx, rec in enumerate(report.get("recommendations", [])):
                all_recommendations.append({
                    "title": f"{report['agent_name']} Recommendation #{idx + 1}",
                    "recommendation": rec,
                    "reasoning": report.get("analysis", ""),
                    "confidence": report.get("confidence", 0.5),
                    "roi_estimate": self._estimate_roi(report, idx),
                    "risk_level": report.get("risk_level", "MEDIUM"),
                    "business_impact": self._business_impact(report),
                    "affected_departments": [report["agent_name"].replace("Agent", "").strip()],
                    "supporting_evidence": report.get("supporting_evidence", []),
                    "agent_source": report["agent_name"],
                })

        # Sort by confidence × inverse_risk
        risk_weight = {"LOW": 1.0, "MEDIUM": 0.7, "HIGH": 0.5, "CRITICAL": 0.3, "UNKNOWN": 0.5}
        all_recommendations.sort(
            key=lambda r: r["confidence"] * risk_weight.get(r["risk_level"], 0.5),
            reverse=True,
        )

        # Executive summary
        critical_agents = [r["agent_name"] for r in agent_reports if r.get("risk_level") in ("HIGH", "CRITICAL")]
        profile = context.get("profile", {})

        executive_summary = (
            f"Executive briefing for {profile.get('name', 'the business')}: "
            f"{len(agent_reports)} specialist agents completed analysis. "
            f"{len(critical_agents)} department(s) flagged as high/critical risk: "
            f"{', '.join(critical_agents) if critical_agents else 'None'}. "
            f"90-day revenue projection: {predictions['revenue'].get('prediction', 'N/A')}. "
            f"Cash flow outlook: {predictions['cashflow'].get('metadata', {}).get('risk_level', 'N/A')}."
        )

        low_stock = context.get("low_stock_products", [])
        top_priorities = (
            [f"Resolve {len(low_stock)} inventory stockout(s) immediately."] if low_stock else []
        ) + [r["recommendation"] for r in all_recommendations[:4]]

        return {
            "executive_summary": executive_summary,
            "top_priorities": top_priorities[:5],
            "strategic_decisions": [r["recommendation"] for r in all_recommendations[:3]],
            "business_risks": [r["analysis"] for r in agent_reports if r.get("risk_level") in ("HIGH", "CRITICAL")][:3],
            "growth_opportunities": [
                r["recommendation"] for r in all_recommendations
                if r["agent_source"] == "MarketingAgent"
            ][:3],
            "agent_reports": agent_reports,
            "all_recommendations": all_recommendations,
            "strategy_brief": strategy_brief_data,
            "predictions": {
                "revenue": predictions["revenue"],
                "cashflow": predictions["cashflow"],
            },
            "context_snapshot": {
                "company": profile.get("name"),
                "cash_balance": profile.get("cash_balance", 0),
                "low_stock_count": len(low_stock),
                "total_agents_run": len(agent_reports),
            },
        }

    @staticmethod
    def _estimate_roi(report: Dict[str, Any], rec_index: int) -> float:
        """Simple heuristic ROI estimate based on agent type and recommendation position."""
        base_roi = {"FinanceAgent": 25.0, "MarketingAgent": 35.0, "OperationsAgent": 20.0,
                    "SupplierAgent": 15.0, "CustomerAgent": 30.0, "RiskAgent": 10.0, "ProcurementAgent": 20.0}
        base = base_roi.get(report.get("agent_name", ""), 15.0)
        return round(base * (1 - rec_index * 0.1) * report.get("confidence", 0.7), 1)

    @staticmethod
    def _business_impact(report: Dict[str, Any]) -> str:
        impacts = {
            "FinanceAgent": "Direct revenue and margin improvement",
            "OperationsAgent": "Reduced operational downtime and fulfilment cost",
            "MarketingAgent": "Customer revenue growth and retention improvement",
            "SupplierAgent": "Supply chain resilience and cost reduction",
            "CustomerAgent": "Customer satisfaction and lifetime value increase",
            "RiskAgent": "Enterprise risk reduction and business continuity",
            "ProcurementAgent": "Procurement cost savings and margin hedging",
        }
        return impacts.get(report.get("agent_name", ""), "Positive business outcome expected")
