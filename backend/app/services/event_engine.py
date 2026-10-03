"""
Event Processing Layer — Event Engine Service for Stratify SME Operating System.

Central service for dispatching, evaluating, storing, and querying standardized business events.

Every event contains:
  - severity (INFO | WARNING | HIGH | CRITICAL)
  - timestamp (datetime UTC)
  - source (service domain or agent)
  - related_entities (list of entity reference dicts)
  - explanation (detailed reason/trigger description)
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.business import Company, Customer, Invoice, Product, Sales, Supplier
from app.models.history import BusinessEvent
from app.models.memory import CustomerChurnLog, SupplierDelayLog

logger = logging.getLogger(__name__)


class EventEngineService:
    """Core Event Processing Layer service."""

    @staticmethod
    async def create_event(
        db: AsyncSession,
        event_type: str,
        severity: str,
        source: str,
        explanation: str,
        related_entities: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> BusinessEvent:
        """
        Creates and persists a standardized business event.
        Guarantees severity, timestamp, source, related_entities, and explanation.
        """
        severity_clean = (severity or "INFO").upper()
        rel_entities = related_entities or []

        # Extract primary entity_type and entity_id for legacy query compatibility
        primary_entity_type = rel_entities[0].get("entity_type") if rel_entities else None
        primary_entity_id = rel_entities[0].get("entity_id") if rel_entities else None

        full_metadata = dict(metadata or {})
        full_metadata["related_entities"] = rel_entities
        full_metadata["explanation"] = explanation

        event = BusinessEvent(
            event_type=event_type,
            description=description or explanation,
            explanation=explanation,
            severity=severity_clean,
            source=source or "system",
            entity_type=primary_entity_type,
            entity_id=primary_entity_id,
            timestamp=datetime.utcnow(),
            metadata_json=full_metadata,
        )

        db.add(event)
        await db.flush()
        logger.info("EventEngine: Stored event [%s] (%s) - %s", event_type, severity_clean, explanation[:80])
        return event

    # ------------------------------------------------------------------
    # Specialized Emitters for Key Business Actions
    # ------------------------------------------------------------------

    @staticmethod
    async def record_inventory_low(
        db: AsyncSession,
        product_id: int,
        sku: str,
        name: str,
        current_stock: int,
        reorder_point: int,
        source: str = "inventory_service",
    ) -> BusinessEvent:
        """Emits an InventoryLow business event."""
        severity = "CRITICAL" if current_stock == 0 else "WARNING"
        explanation = (
            f"Inventory low for product '{name}' (SKU: {sku}). Current stock of {current_stock} "
            f"is below reorder threshold of {reorder_point}."
        )
        related_entities = [
            {"entity_type": "product", "entity_id": product_id, "name": name, "sku": sku}
        ]
        metadata = {
            "current_stock": current_stock,
            "reorder_point": reorder_point,
            "product_id": product_id,
        }
        return await EventEngineService.create_event(
            db=db,
            event_type="InventoryLow",
            severity=severity,
            source=source,
            explanation=explanation,
            related_entities=related_entities,
            metadata=metadata,
        )

    @staticmethod
    async def record_cashflow_warning(
        db: AsyncSession,
        shortfall_amount: float,
        ap_outstanding: float,
        ar_outstanding: float,
        days_horizon: int = 30,
        source: str = "financial_service",
    ) -> BusinessEvent:
        """Emits a CashflowWarning business event."""
        severity = "CRITICAL" if shortfall_amount > 10000.0 else "WARNING"
        explanation = (
            f"Cashflow warning for next {days_horizon} days: Accounts Payable (${ap_outstanding:,.2f}) "
            f"exceeds Accounts Receivable (${ar_outstanding:,.2f}) with projected liquidity shortfall of ${shortfall_amount:,.2f}."
        )
        related_entities = [{"entity_type": "financial_account", "name": "Company Treasury"}]
        metadata = {
            "shortfall_amount": shortfall_amount,
            "ap_outstanding": ap_outstanding,
            "ar_outstanding": ar_outstanding,
            "days_horizon": days_horizon,
        }
        return await EventEngineService.create_event(
            db=db,
            event_type="CashflowWarning",
            severity=severity,
            source=source,
            explanation=explanation,
            related_entities=related_entities,
            metadata=metadata,
        )

    @staticmethod
    async def record_supplier_delay(
        db: AsyncSession,
        supplier_id: int,
        name: str,
        purchase_order_id: Optional[int],
        days_delayed: int,
        impact: Optional[str] = None,
        source: str = "supply_chain_service",
    ) -> BusinessEvent:
        """Emits a SupplierDelay business event."""
        severity = "CRITICAL" if days_delayed > 3 else "WARNING"
        po_str = f"PO #{purchase_order_id}" if purchase_order_id else "Order"
        explanation = (
            f"Supplier '{name}' delayed {po_str} delivery by {days_delayed} day(s)."
            + (f" Impact: {impact}" if impact else "")
        )
        related_entities = [{"entity_type": "supplier", "entity_id": supplier_id, "name": name}]
        if purchase_order_id:
            related_entities.append({"entity_type": "purchase_order", "entity_id": purchase_order_id})

        metadata = {
            "supplier_id": supplier_id,
            "days_delayed": days_delayed,
            "purchase_order_id": purchase_order_id,
            "impact": impact,
        }
        return await EventEngineService.create_event(
            db=db,
            event_type="SupplierDelay",
            severity=severity,
            source=source,
            explanation=explanation,
            related_entities=related_entities,
            metadata=metadata,
        )

    @staticmethod
    async def record_customer_churn_risk(
        db: AsyncSession,
        customer_id: int,
        name: str,
        churn_probability: float,
        risk_factors: Optional[List[str]] = None,
        source: str = "customer_service",
    ) -> BusinessEvent:
        """Emits a CustomerChurnRisk business event."""
        severity = "CRITICAL" if churn_probability >= 0.70 else "WARNING"
        pct_str = f"{churn_probability * 100:.1f}%"
        factors_str = f" Risk factors: {', '.join(risk_factors)}." if risk_factors else ""
        explanation = f"Customer '{name}' (ID: {customer_id}) flagged with high churn probability of {pct_str}.{factors_str}"
        related_entities = [{"entity_type": "customer", "entity_id": customer_id, "name": name}]
        metadata = {
            "customer_id": customer_id,
            "churn_probability": churn_probability,
            "risk_factors": risk_factors or [],
        }
        return await EventEngineService.create_event(
            db=db,
            event_type="CustomerChurnRisk",
            severity=severity,
            source=source,
            explanation=explanation,
            related_entities=related_entities,
            metadata=metadata,
        )

    @staticmethod
    async def record_revenue_increase(
        db: AsyncSession,
        amount: float,
        description_text: str,
        customer_id: Optional[int] = None,
        sale_id: Optional[int] = None,
        source: str = "sales_service",
    ) -> BusinessEvent:
        """Emits a RevenueIncrease business event."""
        explanation = f"Revenue increase of ${amount:,.2f} recorded: {description_text}"
        related_entities = []
        if customer_id:
            related_entities.append({"entity_type": "customer", "entity_id": customer_id})
        if sale_id:
            related_entities.append({"entity_type": "sales", "entity_id": sale_id})

        metadata = {"revenue_amount": amount, "sale_id": sale_id, "customer_id": customer_id}
        return await EventEngineService.create_event(
            db=db,
            event_type="RevenueIncrease",
            severity="INFO",
            source=source,
            explanation=explanation,
            related_entities=related_entities,
            metadata=metadata,
        )

    @staticmethod
    async def record_invoice_overdue(
        db: AsyncSession,
        invoice_id: int,
        invoice_number: str,
        party_name: str,
        days_overdue: int,
        amount: float,
        source: str = "collections_service",
    ) -> BusinessEvent:
        """Emits an InvoiceOverdue business event."""
        severity = "CRITICAL" if days_overdue > 14 else "WARNING"
        explanation = (
            f"Invoice #{invoice_number} for '{party_name}' is overdue by {days_overdue} days. "
            f"Outstanding balance: ${amount:,.2f}."
        )
        related_entities = [{"entity_type": "invoice", "entity_id": invoice_id, "name": invoice_number}]
        metadata = {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "days_overdue": days_overdue,
            "amount": amount,
        }
        return await EventEngineService.create_event(
            db=db,
            event_type="InvoiceOverdue",
            severity=severity,
            source=source,
            explanation=explanation,
            related_entities=related_entities,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Queries & Filtering
    # ------------------------------------------------------------------

    @staticmethod
    async def get_events(
        db: AsyncSession,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        source: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BusinessEvent]:
        """Queries stored events with optional filtering and pagination."""
        stmt = select(BusinessEvent).order_by(BusinessEvent.timestamp.desc())

        if event_type:
            stmt = stmt.where(BusinessEvent.event_type == event_type)
        if severity:
            stmt = stmt.where(BusinessEvent.severity == severity.upper())
        if source:
            stmt = stmt.where(BusinessEvent.source == source)
        if entity_type:
            stmt = stmt.where(BusinessEvent.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(BusinessEvent.entity_id == entity_id)
        if start_date:
            stmt = stmt.where(BusinessEvent.timestamp >= start_date)
        if end_date:
            stmt = stmt.where(BusinessEvent.timestamp <= end_date)

        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_event_by_id(db: AsyncSession, event_id: int) -> Optional[BusinessEvent]:
        """Fetches a single business event by ID."""
        stmt = select(BusinessEvent).where(BusinessEvent.id == event_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_summary_stats(db: AsyncSession) -> Dict[str, Any]:
        """Aggregates event metrics (counts by severity, event type, recent criticals)."""
        all_events_stmt = select(BusinessEvent)
        events = (await db.execute(all_events_stmt)).scalars().all()

        total_events = len(events)
        severity_counts = {"INFO": 0, "WARNING": 0, "HIGH": 0, "CRITICAL": 0}
        event_type_counts: Dict[str, int] = {}
        recent_critical = 0
        now = datetime.utcnow()
        cutoff_24h = now - timedelta(days=1)
        last_ts = None

        for ev in events:
            sev = (ev.severity or "INFO").upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            etype = ev.event_type
            event_type_counts[etype] = event_type_counts.get(etype, 0) + 1

            if ev.timestamp and (not last_ts or ev.timestamp > last_ts):
                last_ts = ev.timestamp

            if sev in ("HIGH", "CRITICAL") and ev.timestamp and ev.timestamp >= cutoff_24h:
                recent_critical += 1

        return {
            "total_events": total_events,
            "severity_counts": severity_counts,
            "event_type_counts": event_type_counts,
            "recent_critical_count": recent_critical,
            "last_event_timestamp": last_ts.isoformat() if last_ts else None,
        }

    # ------------------------------------------------------------------
    # Automated Evaluation Engine
    # ------------------------------------------------------------------

    @staticmethod
    async def evaluate_system_events(db: AsyncSession) -> List[BusinessEvent]:
        """
        Scans operational models and creates missing business events for:
          - InventoryLow
          - InvoiceOverdue
          - CustomerChurnRisk
          - SupplierDelay
          - CashflowWarning
        Deduplicates against recently emitted events (last 1 hour).
        """
        generated: List[BusinessEvent] = []
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)

        # 1. Low Inventory Scan
        low_products_stmt = select(Product).where(Product.stock_level <= Product.reorder_point)
        low_products = (await db.execute(low_products_stmt)).scalars().all()
        for prod in low_products:
            # Check if event was already emitted recently
            existing = (await db.execute(
                select(BusinessEvent).where(
                    BusinessEvent.event_type == "InventoryLow",
                    BusinessEvent.entity_type == "product",
                    BusinessEvent.entity_id == prod.id,
                    BusinessEvent.timestamp >= recent_cutoff,
                )
            )).scalars().first()

            if not existing:
                ev = await EventEngineService.record_inventory_low(
                    db=db,
                    product_id=prod.id,
                    sku=prod.sku,
                    name=prod.name,
                    current_stock=prod.stock_level,
                    reorder_point=prod.reorder_point,
                    source="system_evaluator",
                )
                generated.append(ev)

        # 2. Overdue Invoice Scan
        now = datetime.utcnow()
        overdue_invoices_stmt = select(Invoice).where(
            Invoice.status.in_(["UNPAID", "PARTIAL"]),
            Invoice.due_date < now,
        )
        overdue_invoices = (await db.execute(overdue_invoices_stmt)).scalars().all()
        for inv in overdue_invoices:
            days_overdue = (now - inv.due_date).days
            existing = (await db.execute(
                select(BusinessEvent).where(
                    BusinessEvent.event_type == "InvoiceOverdue",
                    BusinessEvent.entity_type == "invoice",
                    BusinessEvent.entity_id == inv.id,
                    BusinessEvent.timestamp >= recent_cutoff,
                )
            )).scalars().first()

            if not existing:
                outstanding = inv.total_amount - (inv.paid_amount or 0.0)
                party_name = f"Customer #{inv.customer_id}" if inv.customer_id else f"Supplier #{inv.supplier_id}"
                ev = await EventEngineService.record_invoice_overdue(
                    db=db,
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    party_name=party_name,
                    days_overdue=days_overdue,
                    amount=outstanding,
                    source="system_evaluator",
                )
                generated.append(ev)

        # 3. Customer Churn Risk Scan
        churn_stmt = select(CustomerChurnLog).where(CustomerChurnLog.churn_probability >= 0.40).order_by(CustomerChurnLog.timestamp.desc())
        churn_logs = (await db.execute(churn_stmt)).scalars().all()
        processed_customers = set()
        for clog in churn_logs:
            if clog.customer_id in processed_customers:
                continue
            processed_customers.add(clog.customer_id)

            cust = (await db.execute(select(Customer).where(Customer.id == clog.customer_id))).scalars().first()
            cust_name = cust.name if cust else f"Customer #{clog.customer_id}"

            existing = (await db.execute(
                select(BusinessEvent).where(
                    BusinessEvent.event_type == "CustomerChurnRisk",
                    BusinessEvent.entity_type == "customer",
                    BusinessEvent.entity_id == clog.customer_id,
                    BusinessEvent.timestamp >= recent_cutoff,
                )
            )).scalars().first()

            if not existing:
                ev = await EventEngineService.record_customer_churn_risk(
                    db=db,
                    customer_id=clog.customer_id,
                    name=cust_name,
                    churn_probability=clog.churn_probability,
                    risk_factors=clog.risk_factors or [],
                    source="system_evaluator",
                )
                generated.append(ev)

        # 4. Cashflow Liquidity Scan
        ap_stmt = select(func.sum(Invoice.total_amount - Invoice.paid_amount)).where(Invoice.invoice_type == "AP", Invoice.status != "PAID")
        ar_stmt = select(func.sum(Invoice.total_amount - Invoice.paid_amount)).where(Invoice.invoice_type == "AR", Invoice.status != "PAID")
        ap_total = (await db.execute(ap_stmt)).scalar() or 0.0
        ar_total = (await db.execute(ar_stmt)).scalar() or 0.0

        if ap_total > ar_total:
            shortfall = ap_total - ar_total
            existing = (await db.execute(
                select(BusinessEvent).where(
                    BusinessEvent.event_type == "CashflowWarning",
                    BusinessEvent.timestamp >= recent_cutoff,
                )
            )).scalars().first()

            if not existing:
                ev = await EventEngineService.record_cashflow_warning(
                    db=db,
                    shortfall_amount=shortfall,
                    ap_outstanding=ap_total,
                    ar_outstanding=ar_total,
                    days_horizon=30,
                    source="system_evaluator",
                )
                generated.append(ev)

        return generated
