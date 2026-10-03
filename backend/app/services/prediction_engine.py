"""
Prediction Engine Service — Statistical and ML-based forecasting for business metrics.

Models implemented:
  1. Revenue Forecast (90-day rolling mean extrapolation)
  2. Cash Flow Forecast (AR vs AP net balance projection)
  3. Demand Forecast (per-product reorder velocity estimation)
  4. Customer Risk Model (churn probability + payment risk)
  5. Supplier Risk Model (delivery delay probability)
  6. Pricing Recommendation (margin-optimised pricing)

Architecture:
  - All methods are static async — no shared state
  - Methods accept AsyncSession and return plain dicts (JSON-serialisable)
  - Designed to be called by both forecast routers and AI agents independently
"""

import logging
from typing import Any, Dict, List

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Customer, Invoice, Product, Sales, Supplier
from app.utils.helpers import clamp, safe_divide

logger = logging.getLogger(__name__)


class PredictionEngineService:
    """
    Stateless collection of forecasting and risk-scoring algorithms.
    Each method is an independent ML service — no cross-dependencies.
    """

    # ----------------------------------------------------------------
    # 1. Revenue Forecast (90 days)
    # ----------------------------------------------------------------

    @staticmethod
    async def predict_revenue_90_days(db: AsyncSession) -> Dict[str, Any]:
        """
        Projects 90-day revenue using rolling historical sales data.
        Confidence scales with data volume: sparse data → lower confidence.
        """
        sales_values = (await db.execute(select(Sales.total_price))).scalars().all()

        if len(sales_values) < 3:
            forecasted = 15000.0
            confidence = 0.40
            note = "Insufficient historical data — using baseline estimate."
        elif len(sales_values) < 20:
            forecasted = float(np.mean(sales_values) * 90)
            confidence = 0.60
            note = "Low data volume — estimate may be unreliable."
        else:
            # Use exponential weighted mean to give more weight to recent sales
            arr = np.array(sales_values, dtype=float)
            weights = np.exp(np.linspace(-1, 0, len(arr)))
            weighted_mean = float(np.average(arr, weights=weights))
            forecasted = weighted_mean * 90
            confidence = clamp(0.5 + len(sales_values) * 0.01, 0.60, 0.95)
            note = "Based on weighted historical sales velocity."

        return {
            "prediction": f"Projected 90-day revenue: ${forecasted:,.2f}",
            "confidence_score": round(confidence, 2),
            "important_features": ["historical_sales_velocity", "weighted_mean", "data_volume"],
            "business_impact": (
                "Enables accurate cash flow planning, hiring decisions, "
                "and inventory investment for the next quarter."
            ),
            "suggested_action": (
                "If confidence < 70%, focus on increasing data capture frequency. "
                "If confidence ≥ 80%, use this figure for budget planning."
            ),
            "metadata": {
                "data_points": len(sales_values),
                "forecasted_value": round(forecasted, 2),
                "note": note,
            },
        }

    # ----------------------------------------------------------------
    # 2. Cash Flow Forecast
    # ----------------------------------------------------------------

    @staticmethod
    async def predict_cash_flow(db: AsyncSession) -> Dict[str, Any]:
        """
        Projects net cash movement over 30 days based on AR/AP balance.
        """
        ar_amounts = (
            await db.execute(
                select(Invoice.total_amount).where(
                    Invoice.customer_id.isnot(None),
                    Invoice.status.in_(["UNPAID", "PARTIAL"]),
                )
            )
        ).scalars().all()

        ap_amounts = (
            await db.execute(
                select(Invoice.total_amount).where(
                    Invoice.supplier_id.isnot(None),
                    Invoice.status.in_(["UNPAID", "PARTIAL"]),
                )
            )
        ).scalars().all()

        total_ar = sum(ar_amounts)
        total_ap = sum(ap_amounts)
        net_balance = total_ar - total_ap
        liquidity_ratio = safe_divide(total_ar, total_ap, default=999.0)

        risk = "STABLE" if net_balance >= 0 else "LIQUIDITY_WARNING"
        if net_balance < -10000:
            risk = "CRITICAL"

        return {
            "prediction": (
                f"Expected 30-day net cash change: ${net_balance:+,.2f}. "
                f"AR: ${total_ar:,.2f} | AP: ${total_ap:,.2f}. "
                f"Liquidity Ratio: {liquidity_ratio:.2f}"
            ),
            "confidence_score": 0.82,
            "important_features": ["accounts_receivable", "accounts_payable", "payment_terms"],
            "business_impact": (
                "Cash shortfalls can interrupt supplier payments and halt operations. "
                "Surplus cash should be deployed into inventory or short-term growth."
            ),
            "suggested_action": (
                "Accelerate AR collection if net balance is negative. "
                "Consider invoice financing for immediate liquidity relief."
            ),
            "metadata": {
                "total_ar": round(total_ar, 2),
                "total_ap": round(total_ap, 2),
                "net_balance": round(net_balance, 2),
                "risk_level": risk,
                "liquidity_ratio": round(liquidity_ratio, 2),
            },
        }

    # ----------------------------------------------------------------
    # 3. Demand Forecast
    # ----------------------------------------------------------------

    @staticmethod
    async def predict_demand(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Per-product demand estimation with reorder quantity recommendation.
        """
        products = (await db.execute(select(Product))).scalars().all()
        predictions = []

        for product in products:
            # Estimate demand velocity from historical sales quantity
            sales_quantities = (
                await db.execute(
                    select(Sales.quantity).where(Sales.product_id == product.id)
                )
            ).scalars().all()

            if sales_quantities:
                avg_demand_per_period = float(np.mean(sales_quantities))
                est_30d_demand = int(avg_demand_per_period * 3)  # scale to ~30 days
            else:
                est_30d_demand = product.reorder_quantity  # default estimate

            shortfall = max(0, est_30d_demand - product.stock_level)
            urgency = "IMMEDIATE" if product.stock_level == 0 else (
                "HIGH" if product.stock_level <= product.reorder_point else "NORMAL"
            )
            confidence = clamp(0.5 + len(sales_quantities) * 0.02, 0.50, 0.90)

            predictions.append({
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "prediction": f"Estimated 30-day demand: {est_30d_demand} units (urgency: {urgency})",
                "confidence_score": round(confidence, 2),
                "important_features": ["historical_sales_velocity", "current_stock", "reorder_point"],
                "business_impact": (
                    "Stockouts cost an estimated 4-8% of revenue in lost sales. "
                    "Over-stocking ties up capital and increases holding costs."
                ),
                "suggested_action": f"Place order for {shortfall or product.reorder_quantity} units of {product.sku}.",
                "metadata": {
                    "current_stock": product.stock_level,
                    "reorder_point": product.reorder_point,
                    "estimated_30d_demand": est_30d_demand,
                    "suggested_order_qty": shortfall or product.reorder_quantity,
                    "urgency": urgency,
                },
            })

        return predictions

    # ----------------------------------------------------------------
    # 4. Customer Risk Model
    # ----------------------------------------------------------------

    @staticmethod
    async def predict_customer_risk(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Multi-factor customer risk assessment: churn probability + late payment risk + CLV.
        """
        from app.models.collections import PaymentHistory
        
        customers = (await db.execute(select(Customer))).scalars().all()
        results = []

        for customer in customers:
            # Churn model: low credit score + low CLV = high churn risk
            churn_prob = 0.10
            if customer.credit_score < 550:
                churn_prob += 0.45
            elif customer.credit_score < 650:
                churn_prob += 0.25
            elif customer.credit_score < 700:
                churn_prob += 0.10

            if customer.clv < 500:
                churn_prob += 0.15
            if customer.is_active == 0:
                churn_prob = 0.95  # Already churned

            churn_prob = clamp(churn_prob, 0.0, 1.0)
            late_payment_risk = "HIGH" if customer.credit_score < 620 else (
                "MEDIUM" if customer.credit_score < 700 else "LOW"
            )

            risk_label = "HIGH" if churn_prob > 0.50 else ("MEDIUM" if churn_prob > 0.25 else "LOW")

            # Calculate 1-100 Collections Risk Score
            base_credit_risk = clamp((850.0 - customer.credit_score) / 550.0 * 100.0, 0.0, 100.0)
            
            # Fetch payment history records
            inv_ids = (await db.execute(select(Invoice.id).where(Invoice.customer_id == customer.id))).scalars().all()
            if inv_ids:
                histories = (await db.execute(select(PaymentHistory).where(PaymentHistory.invoice_id.in_(inv_ids)))).scalars().all()
            else:
                histories = []
                
            if histories:
                late_payments = [h for h in histories if h.days_late > 0]
                late_frequency = len(late_payments) / len(histories)
                max_days_late = max(h.days_late for h in histories)
                avg_days_late = sum(h.days_late for h in histories) / len(histories)
                
                late_risk = (late_frequency * 40.0) + (clamp(avg_days_late / 30.0, 0.0, 1.0) * 40.0) + (clamp(max_days_late / 90.0, 0.0, 1.0) * 20.0)
                collections_score = (base_credit_risk * 0.4) + (late_risk * 0.6)
            else:
                collections_score = base_credit_risk
                
            collections_score = clamp(collections_score, 1.0, 100.0)

            results.append({
                "customer_id": customer.id,
                "name": customer.name,
                "prediction": (
                    f"Churn Probability: {churn_prob:.0%} | "
                    f"Late Payment Risk: {late_payment_risk} | "
                    f"Collections Risk Score: {collections_score:.0f}/100"
                ),
                "confidence_score": 0.85,
                "churn_probability": round(churn_prob, 3),
                "late_payment_risk": late_payment_risk,
                "collections_risk_score": round(collections_score, 1),
                "clv": customer.clv,
                "important_features": ["credit_score", "customer_lifetime_value", "activity_status"],
                "business_impact": (
                    "High churn customers represent lost recurring revenue. "
                    "Late payment risk increases DSO and cash flow pressure."
                ),
                "suggested_action": (
                    "Offer retention incentive for HIGH churn risk customers. "
                    "Require upfront payment from HIGH late-payment-risk accounts."
                    if churn_prob > 0.40 else
                    "Monitor quarterly. Introduce loyalty programme for mid-tier CLV customers."
                ),
                "metadata": {
                    "credit_score": customer.credit_score,
                    "credit_limit": customer.credit_limit,
                    "risk_level": risk_label,
                    "collections_risk_score": round(collections_score, 1),
                },
            })

        return results

    # ----------------------------------------------------------------
    # 5. Supplier Risk Model
    # ----------------------------------------------------------------

    @staticmethod
    async def predict_supplier_risk(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Supplier risk: delivery delay probability, reliability trend, price increase risk.
        """
        from datetime import datetime
        from app.models.supply_chain import PurchaseOrder, TransportationLog

        suppliers = (await db.execute(select(Supplier))).scalars().all()
        results = []

        for supplier in suppliers:
            delay_risk_prob = 1.0 - supplier.reliability_score
            delay_risk_label = "HIGH" if delay_risk_prob > 0.30 else (
                "MEDIUM" if delay_risk_prob > 0.15 else "LOW"
            )

            # Price increase risk: longer lead times + low reliability = higher risk
            price_risk = "HIGH" if (supplier.average_lead_days > 21 and supplier.reliability_score < 0.70) else (
                "MEDIUM" if supplier.average_lead_days > 14 else "LOW"
            )

            delay_ratio = safe_divide(supplier.total_delayed_orders, supplier.total_orders_placed, 0.0)

            # 1. Invoice Payment Delay Analysis
            ap_invoices = (await db.execute(
                select(Invoice).where(
                    Invoice.supplier_id == supplier.id,
                    Invoice.invoice_type == "AP",
                    Invoice.status.in_(["UNPAID", "PARTIAL", "OVERDUE"])
                )
            )).scalars().all()
            
            late_days = []
            now_dt = datetime.utcnow()
            for inv in ap_invoices:
                if inv.due_date < now_dt:
                    late_days.append((now_dt - inv.due_date).days)
            invoice_delay = sum(late_days) / len(late_days) if late_days else 0.0

            # 2. Transportation Margin Erosion Count
            pos = (await db.execute(
                select(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier.id)
            )).scalars().all()
            
            erosion_count = 0
            for po in pos:
                log = (await db.execute(
                    select(TransportationLog).where(TransportationLog.purchase_order_id == po.id)
                )).scalars().first()
                if log:
                    gross_margin = log.revenue_at_sale - (po.quantity * po.unit_cost)
                    if gross_margin > 0 and (log.shipping_cost / gross_margin) > 0.3:
                        erosion_count += 1

            results.append({
                "supplier_id": supplier.id,
                "name": supplier.name,
                "prediction": (
                    f"Delivery Delay Risk: {delay_risk_label} ({delay_risk_prob:.0%}) | "
                    f"Price Increase Risk: {price_risk} | "
                    f"Historical Delay Rate: {delay_ratio:.0%}"
                ),
                "confidence_score": 0.88,
                "delay_risk": delay_risk_label,
                "reliability_score": supplier.reliability_score,
                "important_features": ["reliability_score", "average_lead_days", "delay_history"],
                "business_impact": (
                    "Supplier delays cascade to stockouts, lost sales, and customer dissatisfaction. "
                    "Price increases directly compress operating margins."
                ),
                "suggested_action": (
                    f"{'Immediately source backup supplier — HIGH risk of disruption.' if delay_risk_label == 'HIGH' else 'Maintain dual-sourcing strategy for key SKUs.'} "
                    f"Negotiate fixed-price contracts to hedge against price increase risk."
                ),
                "metadata": {
                    "reliability_score": supplier.reliability_score,
                    "average_lead_days": supplier.average_lead_days,
                    "delay_rate": round(delay_ratio, 3),
                    "price_risk": price_risk,
                    "invoice_delay": round(invoice_delay, 1),
                    "margin_erosion_count": erosion_count,
                },
            })

        return results

    # ----------------------------------------------------------------
    # 6. Pricing Recommendation
    # ----------------------------------------------------------------

    @staticmethod
    async def pricing_recommendation(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Compute optimal pricing for each product based on cost, margin targets, and market position.
        """
        products = (await db.execute(select(Product))).scalars().all()
        results = []

        for product in products:
            current_margin = safe_divide(product.price - product.cost, product.price, 0.0)

            # Target: 35% gross margin minimum
            target_price = product.cost * 1.35
            if product.price >= target_price:
                # Already at or above target — can we push higher?
                optimal_price = round(product.price * 1.05, 2)  # +5% uplift test
                action = f"Test a 5% price increase to ${optimal_price:.2f} — current margin is healthy."
                revenue_uplift = (optimal_price - product.price) * max(product.stock_level, 10)
            else:
                # Price below margin target — recommend increase
                optimal_price = round(target_price, 2)
                action = (
                    f"Raise price from ${product.price:.2f} → ${optimal_price:.2f} "
                    f"to achieve 35% gross margin threshold."
                )
                revenue_uplift = (optimal_price - product.price) * max(product.stock_level, 10)

            profit_per_unit = optimal_price - product.cost
            demand_impact = "Minimal" if (optimal_price - product.price) / product.price < 0.10 else "Moderate"

            results.append({
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "current_price": product.price,
                "recommended_price": optimal_price,
                "expected_profit_per_unit": round(profit_per_unit, 2),
                "expected_revenue_uplift": round(revenue_uplift, 2),
                "demand_impact": demand_impact,
                "confidence_score": 0.78,
                "suggested_action": action,
                "metadata": {
                    "current_margin_pct": round(current_margin * 100, 2),
                    "cost": product.cost,
                    "target_margin_pct": 35.0,
                },
            })

        return results
