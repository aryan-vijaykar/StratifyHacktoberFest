# ADR-003: Architectural Design for Stratify Event Processing Engine

## Status
Accepted

## Date
2026-07-29

## Context
Stratify requires a unified Event Engine layer to process, store, and expose critical business events across all business pillars (Sales, Inventory, Supply Chain, Finance, Customer Management, Collections, and AI Decision Engine).
Prior to this enhancement, operational alerts and events were either ephemeral or handled disparately without a standardized payload format or explicit REST APIs for event evaluation and aggregation.

Key Requirements:
1. Every important business action (e.g. `InventoryLow`, `CashflowWarning`, `SupplierDelay`, `CustomerChurnRisk`, `RevenueIncrease`, `InvoiceOverdue`) must produce a structured business event.
2. Every event must guarantee five core attributes: `severity`, `timestamp`, `source`, `related_entities`, and `explanation`.
3. Events must be persisted in the relational database (`BusinessEvent` model).
4. Standardized REST APIs must expose endpoints to query, inspect, submit, and trigger automatic event evaluations.
5. Code modification must build upon existing SQLAlchemy models and FastAPI routing without rewriting existing code.

## Decision
We implemented a central **Event Processing Layer** comprising:

1. **Model Extension (`BusinessEvent`)**:
   - Extended `BusinessEvent` in [`backend/app/models/history.py`](file:///Users/vaibhav/Documents/Projects/Stratify/backend/app/models/history.py) with an explicit `explanation` column and helper properties for structured `related_entities`.
   - Added automatic non-destructive SQLite column migration on startup in `main.py`.

2. **Event Processing Service (`EventEngineService`)**:
   - Located at [`backend/app/services/event_engine.py`](file:///Users/vaibhav/Documents/Projects/Stratify/backend/app/services/event_engine.py).
   - Provides standardized helper Emitters for all major event types (`record_inventory_low`, `record_cashflow_warning`, `record_supplier_delay`, `record_customer_churn_risk`, `record_revenue_increase`, `record_invoice_overdue`).
   - Implements `evaluate_system_events(db)` to scan existing system state and emit missing operational events without duplication.

3. **Pydantic Schemas (`app/schemas/event.py`) & REST API (`app/routers/events.py`)**:
   - Exposes `/api/v1/events/` endpoints for CRUD, pagination, filtering, summary statistics, and manual evaluation triggers.

4. **Workflow Integrations**:
   - Integrated event creation into sales processing, inventory stock updates, supplier delay logs, customer churn score calculations, and periodic overdue invoice scanning.

## Consequences
- **Observability**: Complete visibility into system events and operational risks across all departments.
- **Backwards Compatibility**: Existing DB records continue to function seamlessly, with fallback serialization for legacy events.
- **Auditability**: Provides structured event history for AI agents to compile episodic memory and make informed recommendations.
