import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.business import Invoice
from app.models.history import BusinessEvent
from app.services.event_engine import EventEngineService

logger = logging.getLogger(__name__)


async def scan_open_invoices(db_session_factory: async_sessionmaker):
    """
    Scans all open AR invoices, checks if they are due soon or overdue,
    and logs BusinessEvents accordingly.
    """
    logger.info("Scanning open invoices...")
    async with db_session_factory() as db:
        try:
            # Query all open AR invoices (customer_id not null)
            stmt = select(Invoice).where(
                Invoice.invoice_type == "AR",
                Invoice.status.in_(["UNPAID", "PARTIAL", "OVERDUE"]),
            )
            invoices = (await db.execute(stmt)).scalars().all()

            now_dt = datetime.utcnow()
            twenty_four_hours_ago = now_dt - timedelta(hours=24)

            for inv in invoices:
                # 1. Overdue Check
                if now_dt > inv.due_date:
                    if inv.status != "OVERDUE":
                        inv.status = "OVERDUE"

                    days_overdue = (now_dt - inv.due_date).days
                    # Check if already logged in the last 24h
                    check_stmt = select(BusinessEvent).where(
                        BusinessEvent.event_type == "PAYMENT_OVERDUE",
                        BusinessEvent.entity_type == "Invoice",
                        BusinessEvent.entity_id == inv.id,
                        BusinessEvent.timestamp >= twenty_four_hours_ago,
                    )
                    existing_event = (await db.execute(check_stmt)).scalars().first()

                    if not existing_event:
                        logger.info(
                            "Invoice %s is overdue by %d days. Logging event.",
                            inv.invoice_number,
                            days_overdue,
                        )
                        outstanding = inv.total_amount - (inv.paid_amount or 0.0)
                        party_name = f"Customer #{inv.customer_id}" if inv.customer_id else f"Supplier #{inv.supplier_id}"

                        # Emit structured InvoiceOverdue event via EventEngineService
                        await EventEngineService.record_invoice_overdue(
                            db=db,
                            invoice_id=inv.id,
                            invoice_number=inv.invoice_number,
                            party_name=party_name,
                            days_overdue=days_overdue,
                            amount=outstanding,
                            source="collections_service",
                        )

                # 2. Due Soon Check (due within 3 days)
                elif inv.due_date > now_dt and (inv.due_date - now_dt).days <= 3:
                    days_until_due = (inv.due_date - now_dt).days
                    # Check if already logged in the last 24h
                    check_stmt = select(BusinessEvent).where(
                        BusinessEvent.event_type == "PAYMENT_DUE_SOON",
                        BusinessEvent.entity_type == "Invoice",
                        BusinessEvent.entity_id == inv.id,
                        BusinessEvent.timestamp >= twenty_four_hours_ago,
                    )
                    existing_event = (await db.execute(check_stmt)).scalars().first()

                    if not existing_event:
                        logger.info(
                            "Invoice %s is due soon (%d days left). Logging event.",
                            inv.invoice_number,
                            days_until_due,
                        )
                        event = BusinessEvent(
                            event_type="PAYMENT_DUE_SOON",
                            description=(
                                f"Invoice {inv.invoice_number} is due soon "
                                f"(due in {days_until_due} days). Amount: ${inv.total_amount:.2f}."
                            ),
                            severity="WARNING",
                            source="system",
                            entity_type="Invoice",
                            entity_id=inv.id,
                            metadata_json={
                                "days_until_due": days_until_due,
                                "amount": inv.total_amount,
                            },
                        )
                        db.add(event)

            await db.commit()
            logger.info("Completed open invoices scan.")
        except Exception as e:
            logger.error("Error running open invoice scan: %s", e)
            await db.rollback()


async def scan_open_invoices_periodically(
    db_session_factory: async_sessionmaker, interval_seconds: int = 86400
):
    """Periodic task runner that executes the scan daily."""
    logger.info(
        "Starting periodic invoice scanner (interval: %d seconds)",
        interval_seconds,
    )
    # Wait 5 seconds on startup
    await asyncio.sleep(5)
    while True:
        await scan_open_invoices(db_session_factory)
        await asyncio.sleep(interval_seconds)
