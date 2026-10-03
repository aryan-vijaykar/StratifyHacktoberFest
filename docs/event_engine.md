# Event Engine Specification & Documentation

## Overview

The **Event Engine** serves as the central Event Processing Layer for the Stratify SME Operating System. Every key business event—whether triggered by user actions, automated background scans, or predictive AI algorithms—is standardized, persisted, and made available for real-time querying, decision synthesis, and auditing.

---

## 1. Core Event Schema

Every business event captured by the Event Engine guarantees the following required fields:

| Field Name | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `id` | `int` | Unique auto-increment primary key | `101` |
| `event_type` | `str` | Type identifier for the business event | `"InventoryLow"`, `"CashflowWarning"` |
| `severity` | `str` | Event criticality (`INFO`, `WARNING`, `HIGH`, `CRITICAL`) | `"CRITICAL"` |
| `timestamp` | `datetime` | ISO-8601 UTC timestamp of occurrence | `"2026-07-29T05:50:00Z"` |
| `source` | `str` | System domain or agent source | `"inventory_service"`, `"financial_service"` |
| `related_entities`| `list[dict]`| List of associated business entity references | `[{"entity_type": "product", "entity_id": 5, "name": "Widget A"}]` |
| `explanation` | `str` | Detailed rationale and business context | `"Stock level (3) dropped below reorder point (10)."` |
| `metadata_json` | `dict` | Additional contextual data payload | `{"stock_level": 3, "reorder_point": 10}` |

---

## 2. Standard Business Event Types

The system natively produces and tracks the following core event types:

1. **`InventoryLow`**
   - **Trigger**: Product stock level falls below or equals its reorder threshold (`stock_level <= reorder_point`).
   - **Severity**: `WARNING` or `CRITICAL` (if stock level is 0).
   - **Source**: `inventory_service`
   - **Related Entities**: Product entity.

2. **`CashflowWarning`**
   - **Trigger**: Projected 30-day payables exceed receivables or net cash balance falls below safety threshold.
   - **Severity**: `WARNING` or `CRITICAL` (shortfall > $10,000).
   - **Source**: `financial_service`
   - **Related Entities**: Company / Financial Accounts.

3. **`SupplierDelay`**
   - **Trigger**: Supplier delivery exceeds expected lead time or delay log is recorded.
   - **Severity**: `WARNING` (delay <= 3 days) or `CRITICAL` (delay > 3 days).
   - **Source**: `supply_chain_service`
   - **Related Entities**: Supplier, Purchase Order.

4. **`CustomerChurnRisk`**
   - **Trigger**: Customer churn probability calculated by predictive risk model exceeds 40%.
   - **Severity**: `WARNING` (risk 40-70%) or `CRITICAL` (risk > 70%).
   - **Source**: `customer_service` / `ai_risk_agent`
   - **Related Entities**: Customer.

5. **`RevenueIncrease`**
   - **Trigger**: Major sales transaction recorded or revenue growth threshold surpassed.
   - **Severity**: `INFO`
   - **Source**: `sales_service`
   - **Related Entities**: Sales, Customer, Product.

6. **`InvoiceOverdue`**
   - **Trigger**: Unpaid accounts receivable or payables invoice passes its due date.
   - **Severity**: `WARNING` (overdue <= 14 days) or `CRITICAL` (overdue > 14 days).
   - **Source**: `collections_service`
   - **Related Entities**: Invoice, Customer, Supplier.

---

## 3. Architecture & Service Layer

The event processing layer is managed by `EventEngineService` in [`backend/app/services/event_engine.py`](file:///Users/vaibhav/Documents/Projects/Stratify/backend/app/services/event_engine.py).

```
                      +-----------------------------+
                      |   Workflow & Action Layer   |
                      |  (Sales, Inventory, POs,    |
                      |   Collections, AI Agents)   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |     Event Processing Layer  |
                      |    (EventEngineService)     |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |     SQLAlchemy ORM Model    |
                      |  (BusinessEvent / SQLite)   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |     REST API Controllers    |
                      |      (/api/v1/events)       |
                      +-----------------------------+
```

### Core Emitter API
- `EventEngineService.create_event(db, event_type, severity, source, explanation, related_entities, ...)`
- Emitter helpers:
  - `record_inventory_low(...)`
  - `record_cashflow_warning(...)`
  - `record_supplier_delay(...)`
  - `record_customer_churn_risk(...)`
  - `record_revenue_increase(...)`
  - `record_invoice_overdue(...)`
- `EventEngineService.evaluate_system_events(db)`: Periodic scanner inspecting database state to detect active operational events without duplicating existing alerts.

---

## 4. REST API Endpoint Reference

All endpoints are mounted under `/api/v1/events`:

- **`POST /api/v1/events/`**: Post a custom business event.
- **`GET /api/v1/events/`**: List and filter events with pagination. Supports `event_type`, `severity`, `source`, `entity_type`, `entity_id`, `start_date`, `end_date`, `limit`, and `offset`.
- **`GET /api/v1/events/{event_id}`**: Retrieve a single event details by ID.
- **`GET /api/v1/events/stats/summary`**: Get aggregate metrics (total events, count by severity, breakdown by type, recent critical events).
- **`POST /api/v1/events/evaluate`**: Trigger system-wide automated evaluation to check inventory, cashflow, supplier delays, churn risk, revenue, and overdue invoices.
