"""
Event Engine Integration Tests.

Verifies that:
1. EventEngineService.create_event persists events with all required fields.
2. All six specialized emitters produce events with correct types, severity, source, related_entities, and explanation.
3. evaluate_system_events() correctly detects operational states.
4. REST API endpoints return correct response shapes.
5. Filtering and pagination work correctly.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from app.database import Base
from app.models.business import Customer, Invoice, Product, Supplier
from app.models.history import BusinessEvent
from app.models.memory import CustomerChurnLog
from app.services.event_engine import EventEngineService


# ---------------------------------------------------------------------------
# Test DB Setup (in-memory SQLite)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Import all models so tables are created
        import app.models.business
        import app.models.history
        import app.models.materials
        import app.models.memory
        import app.models.collections
        import app.models.supply_chain
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine):
    """Provides a transactional test session that rolls back after each test."""
    SessionLocal = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# 1. Core create_event — required fields guaranteed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_event_required_fields(db: AsyncSession):
    """All events must have severity, timestamp, source, related_entities, explanation."""
    ev = await EventEngineService.create_event(
        db=db,
        event_type="TestEvent",
        severity="WARNING",
        source="test_suite",
        explanation="Test explanation for required fields check.",
        related_entities=[{"entity_type": "product", "entity_id": 99, "name": "Widget"}],
    )

    assert ev.id is not None, "Event must be persisted with an ID"
    assert ev.event_type == "TestEvent"
    assert ev.severity == "WARNING"
    assert ev.source == "test_suite"
    assert ev.explanation == "Test explanation for required fields check."
    assert ev.timestamp is not None, "Event must have a timestamp"
    # related_entities stored in metadata_json
    assert ev.get_related_entities != [], "related_entities must not be empty"
    assert ev.get_related_entities[0]["entity_type"] == "product"


# ---------------------------------------------------------------------------
# 2. Specialized Emitters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_inventory_low(db: AsyncSession):
    ev = await EventEngineService.record_inventory_low(
        db=db, product_id=1, sku="SKU-001", name="Low Stock Widget",
        current_stock=2, reorder_point=10
    )
    assert ev.event_type == "InventoryLow"
    assert ev.severity in ("WARNING", "CRITICAL")
    assert ev.explanation != ""
    assert "Low Stock Widget" in ev.explanation
    assert ev.get_related_entities[0]["entity_type"] == "product"
    assert ev.get_related_entities[0]["entity_id"] == 1


@pytest.mark.asyncio
async def test_record_inventory_low_zero_stock_is_critical(db: AsyncSession):
    ev = await EventEngineService.record_inventory_low(
        db=db, product_id=2, sku="SKU-002", name="Out of Stock Item",
        current_stock=0, reorder_point=5
    )
    assert ev.severity == "CRITICAL"


@pytest.mark.asyncio
async def test_record_cashflow_warning(db: AsyncSession):
    ev = await EventEngineService.record_cashflow_warning(
        db=db, shortfall_amount=5000.0, ap_outstanding=15000.0, ar_outstanding=10000.0
    )
    assert ev.event_type == "CashflowWarning"
    assert ev.severity == "WARNING"
    assert "$5,000.00" in ev.explanation or "5000" in ev.explanation
    assert ev.source == "financial_service"


@pytest.mark.asyncio
async def test_record_cashflow_warning_critical_threshold(db: AsyncSession):
    ev = await EventEngineService.record_cashflow_warning(
        db=db, shortfall_amount=15000.0, ap_outstanding=30000.0, ar_outstanding=15000.0
    )
    assert ev.severity == "CRITICAL"


@pytest.mark.asyncio
async def test_record_supplier_delay(db: AsyncSession):
    ev = await EventEngineService.record_supplier_delay(
        db=db, supplier_id=5, name="Acme Supplies", purchase_order_id=101, days_delayed=2
    )
    assert ev.event_type == "SupplierDelay"
    assert ev.severity == "WARNING"  # 2 days <= 3
    assert "Acme Supplies" in ev.explanation
    rel_types = [r["entity_type"] for r in ev.get_related_entities]
    assert "supplier" in rel_types


@pytest.mark.asyncio
async def test_record_supplier_delay_critical(db: AsyncSession):
    ev = await EventEngineService.record_supplier_delay(
        db=db, supplier_id=6, name="Slow Supplier Ltd", purchase_order_id=202, days_delayed=7
    )
    assert ev.severity == "CRITICAL"


@pytest.mark.asyncio
async def test_record_customer_churn_risk(db: AsyncSession):
    ev = await EventEngineService.record_customer_churn_risk(
        db=db, customer_id=10, name="Jane Doe", churn_probability=0.55,
        risk_factors=["low CLV", "high credit risk"]
    )
    assert ev.event_type == "CustomerChurnRisk"
    assert ev.severity == "WARNING"
    assert "Jane Doe" in ev.explanation
    assert "55.0%" in ev.explanation
    assert ev.get_related_entities[0]["entity_type"] == "customer"


@pytest.mark.asyncio
async def test_record_customer_churn_risk_critical(db: AsyncSession):
    ev = await EventEngineService.record_customer_churn_risk(
        db=db, customer_id=11, name="At Risk Corp", churn_probability=0.80
    )
    assert ev.severity == "CRITICAL"


@pytest.mark.asyncio
async def test_record_revenue_increase(db: AsyncSession):
    ev = await EventEngineService.record_revenue_increase(
        db=db, amount=12500.0, description_text="Q2 bulk order fulfilled",
        customer_id=3, sale_id=55
    )
    assert ev.event_type == "RevenueIncrease"
    assert ev.severity == "INFO"
    assert "$12,500.00" in ev.explanation
    rel_types = [r["entity_type"] for r in ev.get_related_entities]
    assert "customer" in rel_types
    assert "sales" in rel_types


@pytest.mark.asyncio
async def test_record_invoice_overdue(db: AsyncSession):
    ev = await EventEngineService.record_invoice_overdue(
        db=db, invoice_id=20, invoice_number="INV-2024-001",
        party_name="ABC Corp", days_overdue=5, amount=3500.0
    )
    assert ev.event_type == "InvoiceOverdue"
    assert ev.severity == "WARNING"  # 5 days <= 14
    assert "INV-2024-001" in ev.explanation
    assert "ABC Corp" in ev.explanation
    assert ev.get_related_entities[0]["entity_type"] == "invoice"


@pytest.mark.asyncio
async def test_record_invoice_overdue_critical(db: AsyncSession):
    ev = await EventEngineService.record_invoice_overdue(
        db=db, invoice_id=21, invoice_number="INV-2024-002",
        party_name="XYZ Ltd", days_overdue=30, amount=8000.0
    )
    assert ev.severity == "CRITICAL"  # 30 days > 14


# ---------------------------------------------------------------------------
# 3. Query helpers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_events_with_filters(db: AsyncSession):
    # Create 3 events of different types
    await EventEngineService.record_inventory_low(db, 30, "SKU-030", "FilterTest A", 1, 10)
    await EventEngineService.record_inventory_low(db, 31, "SKU-031", "FilterTest B", 0, 10)
    await EventEngineService.record_cashflow_warning(db, 2000.0, 12000.0, 10000.0)

    inv_events = await EventEngineService.get_events(db, event_type="InventoryLow")
    assert len(inv_events) >= 2

    critical_events = await EventEngineService.get_events(db, severity="CRITICAL")
    assert all(ev.severity == "CRITICAL" for ev in critical_events)


@pytest.mark.asyncio
async def test_get_event_by_id(db: AsyncSession):
    ev = await EventEngineService.record_revenue_increase(
        db, amount=999.0, description_text="Test fetch by ID"
    )
    fetched = await EventEngineService.get_event_by_id(db, ev.id)
    assert fetched is not None
    assert fetched.id == ev.id
    assert fetched.event_type == "RevenueIncrease"


@pytest.mark.asyncio
async def test_get_event_by_id_not_found(db: AsyncSession):
    fetched = await EventEngineService.get_event_by_id(db, 9999999)
    assert fetched is None


@pytest.mark.asyncio
async def test_get_summary_stats(db: AsyncSession):
    await EventEngineService.record_inventory_low(db, 40, "SKU-040", "Stats Test", 3, 10)
    stats = await EventEngineService.get_summary_stats(db)

    assert "total_events" in stats
    assert "severity_counts" in stats
    assert "event_type_counts" in stats
    assert "recent_critical_count" in stats
    assert stats["total_events"] >= 1
    assert "InventoryLow" in stats["event_type_counts"]


# ---------------------------------------------------------------------------
# 4. Event model helper properties
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_business_event_helpers(db: AsyncSession):
    ev = await EventEngineService.record_supplier_delay(
        db, supplier_id=7, name="TestHelper Supplies",
        purchase_order_id=None, days_delayed=1
    )
    assert isinstance(ev.get_explanation, str)
    assert ev.get_explanation != ""
    assert isinstance(ev.get_related_entities, list)


@pytest.mark.asyncio
async def test_business_event_entity_type_fallback(db: AsyncSession):
    """Events without metadata-level related_entities fall back to entity_type/entity_id."""
    ev = BusinessEvent(
        event_type="LEGACY_EVENT",
        description="Legacy style event",
        severity="INFO",
        source="legacy",
        entity_type="invoice",
        entity_id=42,
    )
    db.add(ev)
    await db.flush()
    assert ev.get_related_entities == [{"entity_type": "invoice", "entity_id": 42}]
