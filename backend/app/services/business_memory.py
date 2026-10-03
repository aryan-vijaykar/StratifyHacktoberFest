import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.business import Company, Customer, Invoice, Product, Sales, Supplier
from app.models.history import BusinessEvent, DecisionHistory, RecommendationHistory
from app.models.materials import MaterialPriceHistory, RawMaterial
from app.models.memory import (
    CompanyMemory,
    CustomerChurnLog,
    CustomerComplaintLog,
    FinancialForecastHistory,
    FinancialMonthlyTrend,
    FinancialWarningLog,
    SupplierDelayLog,
    SupplierPriceChangeLog,
    SupplierQualityLog,
)
from app.services.event_engine import EventEngineService

logger = logging.getLogger(__name__)



class BusinessMemoryService:
    """Maintains unified persistent memory engine across all 5 core pillars."""

    # ------------------------------------------------------------------
    # 1. Company Memory
    # ------------------------------------------------------------------

    @staticmethod
    async def get_company_profile(db: AsyncSession) -> Dict[str, Any]:
        """Legacy helper returning basic company profile dict."""
        stmt = select(Company).limit(1)
        company = (await db.execute(stmt)).scalars().first()
        if company:
            return {
                "name": company.name,
                "industry": company.industry,
                "tax_id": company.tax_id,
                "cash_balance": company.cash_balance,
            }
        return {"name": "Default SME Ltd", "industry": "Retail", "cash_balance": 50000.0}

    @staticmethod
    async def get_company_memory(db: AsyncSession) -> Dict[str, Any]:
        """Retrieve full Company Memory including goals, preferred suppliers, and business rules."""
        comp_stmt = select(Company).limit(1)
        company = (await db.execute(comp_stmt)).scalars().first()
        if not company:
            company = Company(
                name="Default SME Ltd",
                industry="Manufacturing & Retail",
                cash_balance=50000.0,
                annual_revenue_target=500000.0,
            )
            db.add(company)
            await db.flush()

        mem_stmt = select(CompanyMemory).where(CompanyMemory.company_id == company.id)
        mem = (await db.execute(mem_stmt)).scalars().first()
        if not mem:
            mem = CompanyMemory(
                company_id=company.id,
                profile_summary=f"{company.name} operating in {company.industry or 'Retail'} industry.",
                goals={
                    "annual_revenue_target": company.annual_revenue_target or 500000.0,
                    "target_gpm_pct": 0.35,
                    "target_cash_reserve": 25000.0,
                },
                industry_sector=company.industry or "General SME",
                preferred_suppliers=[],
                business_rules={
                    "min_gross_margin_pct": 0.35,
                    "reorder_safety_multiplier": 1.5,
                    "max_credit_limit_unreviewed": 15000.0,
                    "min_vendor_reliability_score": 0.80,
                },
            )
            db.add(mem)
            await db.flush()

        return {
            "id": mem.id,
            "company_id": company.id,
            "name": company.name,
            "industry": company.industry or mem.industry_sector,
            "tax_id": company.tax_id,
            "cash_balance": company.cash_balance,
            "annual_revenue_target": company.annual_revenue_target,
            "profile_summary": mem.profile_summary,
            "goals": mem.goals or {},
            "industry_sector": mem.industry_sector,
            "preferred_suppliers": mem.preferred_suppliers or [],
            "business_rules": mem.business_rules or {},
            "created_at": mem.created_at.isoformat() if mem.created_at else datetime.utcnow().isoformat(),
            "updated_at": mem.updated_at.isoformat() if mem.updated_at else datetime.utcnow().isoformat(),
        }


    @staticmethod
    async def update_company_memory(db: AsyncSession, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update or initialize Company Memory parameters."""
        comp_stmt = select(Company).limit(1)
        company = (await db.execute(comp_stmt)).scalars().first()
        if not company:
            company = Company(name="Default SME Ltd", industry="Retail", cash_balance=50000.0)
            db.add(company)
            await db.flush()

        mem_stmt = select(CompanyMemory).where(CompanyMemory.company_id == company.id)
        mem = (await db.execute(mem_stmt)).scalars().first()
        if not mem:
            mem = CompanyMemory(company_id=company.id)
            db.add(mem)

        if "profile_summary" in memory_data and memory_data["profile_summary"] is not None:
            mem.profile_summary = memory_data["profile_summary"]
        if "goals" in memory_data and memory_data["goals"] is not None:
            mem.goals = memory_data["goals"]
        if "industry_sector" in memory_data and memory_data["industry_sector"] is not None:
            mem.industry_sector = memory_data["industry_sector"]
            company.industry = memory_data["industry_sector"]
        if "preferred_suppliers" in memory_data and memory_data["preferred_suppliers"] is not None:
            mem.preferred_suppliers = memory_data["preferred_suppliers"]
        if "business_rules" in memory_data and memory_data["business_rules"] is not None:
            mem.business_rules = memory_data["business_rules"]

        mem.updated_at = datetime.utcnow()
        await db.flush()
        return await BusinessMemoryService.get_company_memory(db)

    # ------------------------------------------------------------------
    # 2. Supplier Memory
    # ------------------------------------------------------------------

    @staticmethod
    async def get_supplier_memory(db: AsyncSession, supplier_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve complete Supplier Memory (delays, quality issues, price changes)."""
        supplier = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalars().first()
        if not supplier:
            return None

        delays = (await db.execute(
            select(SupplierDelayLog)
            .where(SupplierDelayLog.supplier_id == supplier_id)
            .order_by(SupplierDelayLog.timestamp.desc())
        )).scalars().all()

        quality = (await db.execute(
            select(SupplierQualityLog)
            .where(SupplierQualityLog.supplier_id == supplier_id)
            .order_by(SupplierQualityLog.timestamp.desc())
        )).scalars().all()

        prices = (await db.execute(
            select(SupplierPriceChangeLog)
            .where(SupplierPriceChangeLog.supplier_id == supplier_id)
            .order_by(SupplierPriceChangeLog.effective_date.desc())
        )).scalars().all()

        return {
            "supplier_id": supplier.id,
            "name": supplier.name,
            "email": supplier.email,
            "reliability_score": supplier.reliability_score,
            "average_lead_days": supplier.average_lead_days,
            "total_orders_placed": supplier.total_orders_placed,
            "total_delayed_orders": supplier.total_delayed_orders,
            "delays": [
                {
                    "id": d.id,
                    "purchase_order_id": d.purchase_order_id,
                    "days_delayed": d.days_delayed,
                    "reason": d.reason,
                    "impact": d.impact,
                    "timestamp": d.timestamp.isoformat(),
                } for d in delays
            ],
            "quality_issues": [
                {
                    "id": q.id,
                    "defect_rate": q.defect_rate,
                    "rejected_quantity": q.rejected_quantity,
                    "description": q.description,
                    "severity": q.severity,
                    "timestamp": q.timestamp.isoformat(),
                } for q in quality
            ],
            "price_changes": [
                {
                    "id": p.id,
                    "product_id": p.product_id,
                    "material_id": p.material_id,
                    "old_price": p.old_price,
                    "new_price": p.new_price,
                    "price_change_pct": p.price_change_pct,
                    "reason": p.reason,
                    "effective_date": p.effective_date.isoformat(),
                } for p in prices
            ],
        }

    @staticmethod
    async def log_supplier_delay(
        db: AsyncSession,
        supplier_id: int,
        days_delayed: int,
        purchase_order_id: Optional[int] = None,
        reason: Optional[str] = None,
        impact: Optional[str] = None,
    ) -> SupplierDelayLog:
        """Log a supplier delivery delay event and adjust vendor reliability metrics."""
        supplier = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalars().first()
        if supplier:
            supplier.total_delayed_orders = (supplier.total_delayed_orders or 0) + 1
            supplier.total_orders_placed = max((supplier.total_orders_placed or 0), supplier.total_delayed_orders)
            # Adjust reliability score downwards on delay
            rel = max(0.0, supplier.reliability_score - (0.05 * days_delayed))
            supplier.reliability_score = round(rel, 2)

        log = SupplierDelayLog(
            supplier_id=supplier_id,
            purchase_order_id=purchase_order_id,
            days_delayed=days_delayed,
            reason=reason,
            impact=impact,
        )
        db.add(log)
        await db.flush()
        # Emit structured SupplierDelay event via EventEngineService
        await EventEngineService.record_supplier_delay(
            db=db,
            supplier_id=supplier_id,
            name=supplier.name if supplier else str(supplier_id),
            purchase_order_id=purchase_order_id,
            days_delayed=days_delayed,
            impact=impact,
            source="supply_chain_service",
        )
        return log

    @staticmethod
    async def log_supplier_quality(
        db: AsyncSession,
        supplier_id: int,
        defect_rate: float,
        rejected_quantity: int,
        description: str,
        severity: str = "MEDIUM",
    ) -> SupplierQualityLog:
        """Log a supplier quality breach."""
        log = SupplierQualityLog(
            supplier_id=supplier_id,
            defect_rate=defect_rate,
            rejected_quantity=rejected_quantity,
            description=description,
            severity=severity,
        )
        db.add(log)
        await db.flush()
        await BusinessMemoryService.store_event(
            db=db,
            event_type="SUPPLIER_QUALITY_ISSUE",
            description=f"Supplier quality issue logged (defect rate: {defect_rate * 100:.1f}%): {description}",
            severity=severity,
            source="user",
            entity_type="supplier",
            entity_id=supplier_id,
        )
        return log

    @staticmethod
    async def log_supplier_price_change(
        db: AsyncSession,
        supplier_id: int,
        old_price: float,
        new_price: float,
        product_id: Optional[int] = None,
        material_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> SupplierPriceChangeLog:
        """Log a supplier unit price shift."""
        pct_change = ((new_price - old_price) / (old_price or 1.0)) * 100.0
        log = SupplierPriceChangeLog(
            supplier_id=supplier_id,
            product_id=product_id,
            material_id=material_id,
            old_price=old_price,
            new_price=new_price,
            price_change_pct=round(pct_change, 2),
            reason=reason,
        )
        db.add(log)
        await db.flush()
        await BusinessMemoryService.store_event(
            db=db,
            event_type="PRICE_CHANGE",
            description=f"Supplier price changed from ${old_price:.2f} to ${new_price:.2f} ({pct_change:+.1f}%).",
            severity="INFO" if pct_change <= 5.0 else "WARNING",
            source="system",
            entity_type="supplier",
            entity_id=supplier_id,
        )
        return log

    # ------------------------------------------------------------------
    # 3. Customer Memory
    # ------------------------------------------------------------------

    @staticmethod
    async def get_customer_memory(db: AsyncSession, customer_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve complete Customer Memory (CLV, purchase frequency, complaints, churn history)."""
        customer = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalars().first()
        if not customer:
            return None

        # Purchase statistics
        sales_stmt = select(Sales).where(Sales.customer_id == customer_id).order_by(Sales.date.desc())
        sales_list = (await db.execute(sales_stmt)).scalars().all()

        last_order = sales_list[0].date.isoformat() if sales_list else None
        order_count = len(sales_list)

        complaints = (await db.execute(
            select(CustomerComplaintLog)
            .where(CustomerComplaintLog.customer_id == customer_id)
            .order_by(CustomerComplaintLog.timestamp.desc())
        )).scalars().all()

        churn = (await db.execute(
            select(CustomerChurnLog)
            .where(CustomerChurnLog.customer_id == customer_id)
            .order_by(CustomerChurnLog.timestamp.desc())
        )).scalars().all()

        return {
            "customer_id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "company_name": customer.company_name,
            "clv": customer.clv,
            "credit_score": customer.credit_score,
            "credit_limit": customer.credit_limit,
            "is_active": bool(customer.is_active),
            "purchase_frequency_orders": order_count,
            "last_order_date": last_order,
            "complaints": [
                {
                    "id": c.id,
                    "subject": c.subject,
                    "description": c.description,
                    "status": c.status,
                    "resolution_notes": c.resolution_notes,
                    "timestamp": c.timestamp.isoformat(),
                } for c in complaints
            ],
            "churn_history": [
                {
                    "id": ch.id,
                    "churn_probability": ch.churn_probability,
                    "churn_risk_level": ch.churn_risk_level,
                    "risk_factors": ch.risk_factors or [],
                    "action_taken": ch.action_taken,
                    "timestamp": ch.timestamp.isoformat(),
                } for ch in churn
            ],
        }

    @staticmethod
    async def log_customer_complaint(
        db: AsyncSession,
        customer_id: int,
        subject: str,
        description: str,
        status: str = "OPEN",
        resolution_notes: Optional[str] = None,
    ) -> CustomerComplaintLog:
        """Record a customer complaint event."""
        log = CustomerComplaintLog(
            customer_id=customer_id,
            subject=subject,
            description=description,
            status=status,
            resolution_notes=resolution_notes,
        )
        db.add(log)
        await db.flush()
        await BusinessMemoryService.store_event(
            db=db,
            event_type="COMPLAINT",
            description=f"Customer complaint logged: {subject}",
            severity="WARNING",
            source="user",
            entity_type="customer",
            entity_id=customer_id,
        )
        return log

    @staticmethod
    async def update_customer_churn(
        db: AsyncSession,
        customer_id: int,
        churn_probability: float,
        churn_risk_level: str = "LOW",
        risk_factors: Optional[List[str]] = None,
        action_taken: Optional[str] = None,
    ) -> CustomerChurnLog:
        """Log a customer churn probability and risk evaluation."""
        log = CustomerChurnLog(
            customer_id=customer_id,
            churn_probability=churn_probability,
            churn_risk_level=churn_risk_level,
            risk_factors=risk_factors or [],
            action_taken=action_taken,
        )
        db.add(log)
        await db.flush()

        if churn_risk_level in ("HIGH", "CRITICAL"):
            # Look up customer name for enriched event
            cust = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalars().first()
            cust_name = cust.name if cust else f"Customer #{customer_id}"
            await EventEngineService.record_customer_churn_risk(
                db=db,
                customer_id=customer_id,
                name=cust_name,
                churn_probability=churn_probability,
                risk_factors=risk_factors or [],
                source="ai_risk_agent",
            )
        return log

    # ------------------------------------------------------------------
    # 4. Financial Memory
    # ------------------------------------------------------------------

    @staticmethod
    async def get_financial_memory(db: AsyncSession) -> Dict[str, Any]:
        """Retrieve Financial Memory (monthly trends, warnings, historical forecasts)."""
        trends = (await db.execute(
            select(FinancialMonthlyTrend).order_by(FinancialMonthlyTrend.year.desc(), FinancialMonthlyTrend.month.desc()).limit(12)
        )).scalars().all()

        warnings = (await db.execute(
            select(FinancialWarningLog).order_by(FinancialWarningLog.timestamp.desc()).limit(20)
        )).scalars().all()

        forecasts = (await db.execute(
            select(FinancialForecastHistory).order_by(FinancialForecastHistory.timestamp.desc()).limit(20)
        )).scalars().all()

        return {
            "monthly_trends": [
                {
                    "id": t.id,
                    "year": t.year,
                    "month": t.month,
                    "total_revenue": t.total_revenue,
                    "gross_profit": t.gross_profit,
                    "operating_expenses": t.operating_expenses,
                    "net_cash_flow": t.net_cash_flow,
                    "ar_outstanding": t.ar_outstanding,
                    "ap_outstanding": t.ap_outstanding,
                    "created_at": t.created_at.isoformat(),
                } for t in trends
            ],
            "previous_warnings": [
                {
                    "id": w.id,
                    "warning_type": w.warning_type,
                    "severity": w.severity,
                    "message": w.message,
                    "metadata_json": w.metadata_json,
                    "timestamp": w.timestamp.isoformat(),
                } for w in warnings
            ],
            "previous_forecasts": [
                {
                    "id": f.id,
                    "forecast_type": f.forecast_type,
                    "predicted_value": f.predicted_value,
                    "confidence": f.confidence,
                    "parameters": f.parameters,
                    "timestamp": f.timestamp.isoformat(),
                } for f in forecasts
            ],
        }

    @staticmethod
    async def record_financial_snapshot(
        db: AsyncSession,
        year: int,
        month: int,
        total_revenue: float,
        gross_profit: float,
        operating_expenses: float,
        net_cash_flow: float,
        ar_outstanding: float = 0.0,
        ap_outstanding: float = 0.0,
    ) -> FinancialMonthlyTrend:
        """Record or update a monthly financial performance snapshot."""
        stmt = select(FinancialMonthlyTrend).where(
            FinancialMonthlyTrend.year == year,
            FinancialMonthlyTrend.month == month,
        )
        trend = (await db.execute(stmt)).scalars().first()
        if not trend:
            trend = FinancialMonthlyTrend(year=year, month=month)
            db.add(trend)

        trend.total_revenue = total_revenue
        trend.gross_profit = gross_profit
        trend.operating_expenses = operating_expenses
        trend.net_cash_flow = net_cash_flow
        trend.ar_outstanding = ar_outstanding
        trend.ap_outstanding = ap_outstanding
        await db.flush()
        return trend

    @staticmethod
    async def record_financial_warning(
        db: AsyncSession,
        warning_type: str,
        message: str,
        severity: str = "WARNING",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FinancialWarningLog:
        """Record a financial liquidity or margin warning."""
        log = FinancialWarningLog(
            warning_type=warning_type,
            severity=severity,
            message=message,
            metadata_json=metadata,
        )
        db.add(log)
        await db.flush()
        return log

    @staticmethod
    async def record_forecast_history(
        db: AsyncSession,
        forecast_type: str,
        predicted_value: float,
        confidence: float = 0.8,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> FinancialForecastHistory:
        """Record a 90-day revenue or 30-day cash flow forecast snapshot."""
        history = FinancialForecastHistory(
            forecast_type=forecast_type,
            predicted_value=predicted_value,
            confidence=confidence,
            parameters=parameters,
        )
        db.add(history)
        await db.flush()
        return history

    # ------------------------------------------------------------------
    # 5. Decision Memory
    # ------------------------------------------------------------------

    @staticmethod
    async def get_decision_memory(db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Legacy helper returning decision history."""
        stmt = select(DecisionHistory).order_by(DecisionHistory.timestamp.desc()).limit(limit)
        decisions = (await db.execute(stmt)).scalars().all()
        return [
            {
                "user_action": d.user_action,
                "business_outcome": d.business_outcome,
                "feedback": d.feedback,
                "timestamp": d.timestamp.isoformat(),
            } for d in decisions
        ]

    @staticmethod
    async def get_decision_memory_list(
        db: AsyncSession,
        limit: int = 50,
        agent_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve unified Decision Memory (all AI agent recommendations + owner acceptance status)."""
        stmt = select(RecommendationHistory).order_by(RecommendationHistory.timestamp.desc())
        if agent_name:
            stmt = stmt.where(RecommendationHistory.agent_name == agent_name)
        stmt = stmt.limit(limit)

        recs = (await db.execute(stmt)).scalars().all()
        results = []

        for rec in recs:
            # Query linked decision history if exists
            dec_stmt = select(DecisionHistory).where(DecisionHistory.recommendation_id == rec.id)
            dec = (await db.execute(dec_stmt)).scalars().first()

            results.append({
                "id": rec.id,
                "agent_name": rec.agent_name,
                "recommendation": rec.recommendation,
                "reasoning": rec.reasoning,
                "confidence": rec.confidence,
                "risk_level": rec.risk_level,
                "was_accepted": dec.user_action if dec else rec.status,
                "final_outcome": dec.business_outcome if dec else None,
                "outcome_revenue_impact": dec.outcome_revenue_impact if dec else None,
                "timestamp": rec.timestamp.isoformat(),
            })

        return results

    @staticmethod
    async def record_decision_outcome(
        db: AsyncSession,
        recommendation_id: int,
        user_action: str,
        modification_notes: Optional[str] = None,
        business_outcome: Optional[str] = None,
        outcome_revenue_impact: Optional[float] = None,
        feedback: Optional[str] = None,
    ) -> DecisionHistory:
        """Record owner decision outcome and feedback for an AI recommendation."""
        rec = (await db.execute(select(RecommendationHistory).where(RecommendationHistory.id == recommendation_id))).scalars().first()
        if rec:
            rec.status = user_action
            await db.flush()

        dec = DecisionHistory(
            recommendation_id=recommendation_id,
            user_action=user_action,
            modification_notes=modification_notes,
            business_outcome=business_outcome,
            outcome_revenue_impact=outcome_revenue_impact,
            feedback=feedback,
        )
        db.add(dec)
        await db.flush()

        await BusinessMemoryService.store_event(
            db=db,
            event_type="DECISION_RECORDED",
            description=f"Owner recorded decision ({user_action}) on Recommendation #{recommendation_id}.",
            severity="INFO",
            source="user",
        )
        return dec

    # ------------------------------------------------------------------
    # Context Compiler for AI Agents
    # ------------------------------------------------------------------

    @staticmethod
    async def get_episodic_memory(db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        stmt = select(BusinessEvent).order_by(BusinessEvent.timestamp.desc()).limit(limit)
        events = (await db.execute(stmt)).scalars().all()
        return [
            {
                "event_type": ev.event_type,
                "description": ev.description,
                "timestamp": ev.timestamp.isoformat(),
                "severity": ev.severity,
                "metadata_json": ev.metadata_json,
            } for ev in events
        ]

    @staticmethod
    async def compile_context(db: AsyncSession) -> Dict[str, Any]:
        """Compiles rich multi-domain context for all specialist and CEO agents."""
        company_mem = await BusinessMemoryService.get_company_memory(db)
        recent_events = await BusinessMemoryService.get_episodic_memory(db, limit=10)
        recent_decisions = await BusinessMemoryService.get_decision_memory_list(db, limit=5)
        financial_mem = await BusinessMemoryService.get_financial_memory(db)

        low_stock_products = []
        try:
            stmt = select(Product).where(Product.stock_level <= Product.reorder_point)
            products = (await db.execute(stmt)).scalars().all()
            low_stock_products = [
                {
                    "sku": p.sku,
                    "name": p.name,
                    "stock_level": p.stock_level,
                    "stock": p.stock_level,
                    "reorder_point": p.reorder_point,
                    "reorder": p.reorder_point,
                } for p in products
            ]
        except Exception as e:
            logger.error("Could not fetch low stock products for context: %s", e)

        top_customers = []
        try:
            stmt = select(Customer).order_by(Customer.clv.desc()).limit(5)
            customers = (await db.execute(stmt)).scalars().all()
            top_customers = [
                {
                    "id": c.id,
                    "name": c.name,
                    "clv": c.clv,
                    "credit_score": c.credit_score,
                } for c in customers
            ]
        except Exception as e:
            logger.error("Could not fetch top customers for context: %s", e)

        risky_suppliers = []
        try:
            stmt = select(Supplier).order_by(Supplier.reliability_score.asc()).limit(5)
            suppliers = (await db.execute(stmt)).scalars().all()
            risky_suppliers = [
                {
                    "id": s.id,
                    "name": s.name,
                    "reliability_score": s.reliability_score,
                    "average_lead_days": s.average_lead_days,
                } for s in suppliers
            ]
        except Exception as e:
            logger.error("Could not fetch risky suppliers for context: %s", e)

        material_price_history = []
        try:
            stmt = select(RawMaterial)
            materials = (await db.execute(stmt)).scalars().all()
            for m in materials:
                hist_stmt = (
                    select(MaterialPriceHistory)
                    .where(MaterialPriceHistory.material_id == m.id)
                    .order_by(MaterialPriceHistory.recorded_at.desc())
                    .limit(10)
                )
                histories = (await db.execute(hist_stmt)).scalars().all()
                material_price_history.append({
                    "material_id": m.id,
                    "name": m.name,
                    "current_price": m.current_unit_price,
                    "unit": m.unit,
                    "history": [
                        {
                            "recorded_price": h.recorded_price,
                            "recorded_at": h.recorded_at.isoformat(),
                            "source": h.source,
                        } for h in histories
                    ],
                })
        except Exception as e:
            logger.error("Could not fetch material price history for context: %s", e)

        return {
            "profile": company_mem,
            "company_memory": company_mem,
            "business_rules": company_mem.get("business_rules", {}),
            "goals": company_mem.get("goals", {}),
            "recent_events": recent_events,
            "recent_decisions": recent_decisions,
            "decision_history": recent_decisions,
            "financial_memory": financial_mem,
            "low_stock_products": low_stock_products,
            "top_customers": top_customers,
            "risky_suppliers": risky_suppliers,
            "material_price_history": material_price_history,
        }

    # ------------------------------------------------------------------
    # Write helpers (called by routers and agent pipeline)
    # ------------------------------------------------------------------

    @staticmethod
    async def store_event(
        db: AsyncSession,
        event_type: str,
        description: str,
        severity: str = "INFO",
        source: str = "system",
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BusinessEvent:
        """Persist a business event to the episodic memory log."""
        event = BusinessEvent(
            event_type=event_type,
            description=description,
            severity=severity,
            source=source,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata,
        )
        db.add(event)
        await db.flush()
        logger.info("BusinessEvent stored: %s — %s", event_type, description[:80])
        return event

    @staticmethod
    async def store_recommendation(
        db: AsyncSession,
        agent_name: str,
        recommendation: str,
        reasoning: Optional[str] = None,
        roi: float = 0.0,
        confidence: float = 0.8,
        risk_level: str = "MEDIUM",
        business_impact: Optional[str] = None,
        affected_departments: Optional[List[str]] = None,
        supporting_evidence: Optional[List[Any]] = None,
    ) -> RecommendationHistory:
        """Persist an AI agent recommendation to the recommendation history (Decision Memory)."""
        rec = RecommendationHistory(
            agent_name=agent_name,
            recommendation=recommendation,
            reasoning=reasoning,
            roi=roi,
            confidence=confidence,
            risk_level=risk_level,
            business_impact=business_impact,
            affected_departments=affected_departments or [],
            supporting_evidence=supporting_evidence or [],
            status="PENDING",
        )
        db.add(rec)
        await db.flush()
        logger.info("Recommendation stored in Decision Memory: %s — %.0f%% confidence", agent_name, confidence * 100)
        return rec
