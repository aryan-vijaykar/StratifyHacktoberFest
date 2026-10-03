"""
Dashboard & Analytics Router — Real-time business health computed from live DB.

Endpoints:
  GET /dashboard        — Key financial metrics
  GET /business-health  — Health score and profitability ratios
  GET /alerts           — Active operational alerts
  GET /timeline         — Recent business events feed
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.business import Customer, Invoice, Product, Sales
from app.models.history import BusinessEvent

router = APIRouter(tags=["Dashboard & Analytics"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dashboard Summary
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """High-level KPIs calculated from live transaction data."""

    # Total Revenue (all-time)
    total_revenue = (await db.execute(select(func.sum(Sales.total_price)))).scalar() or 0.0

    # This month's revenue
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = (
        await db.execute(
            select(func.sum(Sales.total_price)).where(Sales.date >= month_start)
        )
    ).scalar() or 0.0

    # Accounts Receivable (AR) — unpaid customer invoices
    total_ar = (
        await db.execute(
            select(func.sum(Invoice.total_amount)).where(
                Invoice.customer_id.isnot(None), Invoice.status.in_(["UNPAID", "PARTIAL", "OVERDUE"])
            )
        )
    ).scalar() or 0.0

    # Accounts Payable (AP) — unpaid supplier bills
    total_ap = (
        await db.execute(
            select(func.sum(Invoice.total_amount)).where(
                Invoice.supplier_id.isnot(None), Invoice.status.in_(["UNPAID", "PARTIAL", "OVERDUE"])
            )
        )
    ).scalar() or 0.0

    # Low stock products
    low_stock_count = (
        await db.execute(select(func.count(Product.id)).where(Product.stock_level <= Product.reorder_point))
    ).scalar() or 0

    # Active customers
    active_customers = (
        await db.execute(select(func.count(Customer.id)).where(Customer.is_active == 1))
    ).scalar() or 0

    # Total sales count this month
    monthly_orders = (
        await db.execute(select(func.count(Sales.id)).where(Sales.date >= month_start))
    ).scalar() or 0

    return {
        "metrics": {
            "total_revenue": round(total_revenue, 2),
            "monthly_revenue": round(monthly_revenue, 2),
            "accounts_receivable": round(total_ar, 2),
            "accounts_payable": round(total_ap, 2),
            "net_working_capital": round(total_ar - total_ap, 2),
            "low_stock_alerts": low_stock_count,
            "active_customers": active_customers,
            "monthly_orders": monthly_orders,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Business Health Score
# ---------------------------------------------------------------------------

@router.get("/business-health")
async def get_business_health(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Composite business health score derived from profitability, liquidity, and risk indicators."""

    total_sales = (await db.execute(select(func.sum(Sales.total_price)))).scalar() or 0.0

    # Total supplier costs (AP invoices)
    total_costs = (
        await db.execute(
            select(func.sum(Invoice.total_amount)).where(Invoice.supplier_id.isnot(None))
        )
    ).scalar() or 0.0

    gross_profit = total_sales - total_costs
    gpm = (gross_profit / total_sales * 100) if total_sales > 0 else 0.0
    operating_ratio = (total_costs / total_sales) if total_sales > 0 else 0.0

    # Overdue invoices
    overdue_count = (
        await db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.status == "UNPAID", Invoice.due_date < datetime.utcnow()
            )
        )
    ).scalar() or 0

    # Low stock items
    low_stock = (
        await db.execute(select(func.count(Product.id)).where(Product.stock_level <= Product.reorder_point))
    ).scalar() or 0

    # Compute health score (starts at 100, deductions for risk factors)
    health_score = 100
    if operating_ratio > 0.85:
        health_score -= 25
    elif operating_ratio > 0.70:
        health_score -= 10
    if total_sales < total_costs:
        health_score -= 20
    if overdue_count > 5:
        health_score -= 20
    elif overdue_count > 0:
        health_score -= 10
    if low_stock > 10:
        health_score -= 15
    elif low_stock > 3:
        health_score -= 5

    health_score = max(0, min(100, health_score))

    if health_score >= 75:
        status_label = "Healthy"
    elif health_score >= 50:
        status_label = "At Risk"
    else:
        status_label = "Critical"

    return {
        "status": status_label,
        "health_score": health_score,
        "gross_profit_margin_pct": round(gpm, 2),
        "operating_ratio": round(operating_ratio, 4),
        "overdue_invoices": overdue_count,
        "low_stock_products": low_stock,
        "gross_profit": round(gross_profit, 2),
        "generated_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@router.get("/alerts")
async def get_alerts(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """Returns prioritised operational alerts from current business data."""
    alerts: List[Dict[str, Any]] = []

    # 1. Overdue invoices
    overdue_invoices = (
        await db.execute(
            select(Invoice).where(Invoice.status == "UNPAID", Invoice.due_date < datetime.utcnow())
        )
    ).scalars().all()

    if overdue_invoices:
        total_overdue = sum(inv.total_amount for inv in overdue_invoices)
        alerts.append({
            "severity": "CRITICAL",
            "category": "FINANCIAL",
            "title": "Overdue Invoices Require Immediate Action",
            "message": (
                f"{len(overdue_invoices)} invoice(s) are past due, "
                f"totalling ${total_overdue:,.2f}. Contact customers immediately."
            ),
            "count": len(overdue_invoices),
        })

    # 2. Low stock products
    low_stock_products = (
        await db.execute(select(Product).where(Product.stock_level <= Product.reorder_point))
    ).scalars().all()

    for product in low_stock_products:
        severity = "CRITICAL" if product.stock_level == 0 else "WARNING"
        alerts.append({
            "severity": severity,
            "category": "INVENTORY",
            "title": f"Low Stock: {product.name}",
            "message": (
                f"SKU {product.sku} has {product.stock_level} units remaining "
                f"(reorder point: {product.reorder_point}). "
                f"Suggested reorder: {product.reorder_quantity} units."
            ),
            "product_id": product.id,
        })

    # 3. Invoices due in next 7 days (not yet overdue)
    soon_due = datetime.utcnow() + timedelta(days=7)
    upcoming = (
        await db.execute(
            select(Invoice).where(
                Invoice.status == "UNPAID",
                Invoice.due_date >= datetime.utcnow(),
                Invoice.due_date <= soon_due,
            )
        )
    ).scalars().all()

    if upcoming:
        total_upcoming = sum(inv.total_amount for inv in upcoming)
        alerts.append({
            "severity": "WARNING",
            "category": "FINANCIAL",
            "title": "Invoices Due Within 7 Days",
            "message": f"{len(upcoming)} invoice(s) totalling ${total_upcoming:,.2f} due within the next 7 days.",
            "count": len(upcoming),
        })

    return sorted(alerts, key=lambda x: {"CRITICAL": 0, "WARNING": 1, "INFO": 2}.get(x["severity"], 3))


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

@router.get("/timeline")
async def get_timeline(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Chronological feed of business events (newest first)."""
    stmt = select(BusinessEvent).order_by(BusinessEvent.timestamp.desc()).limit(limit)
    events = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": ev.id,
            "event_type": ev.event_type,
            "severity": ev.severity,
            "source": ev.source,
            "description": ev.description,
            "timestamp": ev.timestamp.isoformat(),
            "entity_type": ev.entity_type,
            "entity_id": ev.entity_id,
            "metadata": ev.metadata_json,
        }
        for ev in events
    ]
