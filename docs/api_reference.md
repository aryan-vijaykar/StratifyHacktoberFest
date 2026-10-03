# SME Business Operating System (Stratify) — API Reference Guide

This document provides a detailed, comprehensive reference for all backend API endpoints implemented in the SME Business Operating System (Stratify). 

---

## Global API Configuration

- **Base URL**: `http://localhost:8000/api/v1` (for versioned endpoints) or `http://localhost:8000/` (for system/health root)
- **Content Type**: `application/json` (unless specified otherwise, e.g., multipart/form-data for uploads)
- **CORS**: Configured to allow all origins (`*`) during local development.
- **Interactive Documentation**:
  - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
  - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
  - OpenAPI Specification: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Table of Contents
1. [System & Health Check Endpoints](#1-system--health-check-endpoints)
2. [Core Business CRUD APIs (`/api/v1/business`)](#2-core-business-crud-apis-apiv1business)
   - [Company](#company)
   - [Customers](#customers)
   - [Suppliers](#suppliers)
   - [Products](#products)
   - [Inventory](#inventory)
   - [Sales](#sales)
   - [Invoices](#invoices)
   - [Employees](#employees)
   - [Events](#events)
3. [File Upload & Document Intelligence (`/api/v1/upload`)](#3-file-upload--document-intelligence-apiv1upload)
4. [Dashboard & Analytics APIs (`/api/v1`)](#4-dashboard--analytics-apis-apiv1)
5. [Ollama AI Intelligence APIs (`/api/v1/ai`)](#5-ollama-ai-intelligence-apis-apiv1ai)
6. [Predictive Forecasting APIs (`/api/v1`)](#6-predictive-forecasting-apis-apiv1)
7. [Decision Intelligence Engine APIs (`/api/v1`)](#7-decision-intelligence-engine-apis-apiv1)

---

## 1. System & Health Check Endpoints

### GET `/`
Confirms the service status, version, active environment, and lists the active platform phases.

- **Request**: `GET /`
- **Response** (200 OK):
  ```json
  {
    "service": "SME Business Operating System",
    "version": "1.0.0",
    "status": "operational",
    "environment": "development",
    "docs": "/docs",
    "api_base": "/api/v1",
    "phases_active": [
      "Phase 1: CRUD",
      "Phase 2: AI",
      "Phase 3: Predictive",
      "Phase 4: Decision"
    ]
  }
  ```

### GET `/health`
Lightweight health check endpoint for load balancers, Docker, or container orchestration systems.

- **Request**: `GET /health`
- **Response** (200 OK):
  ```json
  {
    "status": "healthy",
    "service": "sme-os-backend"
  }
  ```

---

## 2. Core Business CRUD APIs (`/api/v1/business`)

These endpoints provide complete CRUD capability for core transactional data and master records.

### Company

The platform is designed to represent a single company deployment.

#### GET `/business/company`
Retrieves the master record of the company.

- **Response** (200 OK):
  ```json
  {
    "id": 1,
    "name": "Acme Corp",
    "industry": "Manufacturing",
    "tax_id": "GSTIN-12345",
    "registration_number": "REG-889900",
    "address": "123 Business Rd, Bengaluru, India",
    "phone": "+91 98765 43210",
    "email": "finance@acme.corp",
    "cash_balance": 250000.00,
    "annual_revenue_target": 1200000.00,
    "founded_year": 2020,
    "created_at": "2026-07-18T10:00:00Z",
    "updated_at": "2026-07-18T10:00:00Z"
  }
  ```
- **Errors**:
  - `404 Not Found`: No company record has been initialized yet.

#### POST `/business/company`
Creates the company master record. Only one company record can exist.

- **Request Body** (JSON):
  ```json
  {
    "name": "Acme Corp",
    "industry": "Manufacturing",
    "tax_id": "GSTIN-12345",
    "registration_number": "REG-889900",
    "address": "123 Business Rd, Bengaluru, India",
    "phone": "+91 98765 43210",
    "email": "finance@acme.corp",
    "cash_balance": 250000.00,
    "annual_revenue_target": 1200000.00,
    "founded_year": 2020
  }
  ```
- **Response** (201 Created): Returns the created `CompanySchema` object.
- **Errors**:
  - `409 Conflict`: Company record already exists.

#### PATCH `/business/company`
Partially updates company metadata or parameters (such as cash balance or target revenue).

- **Request Body** (JSON): Any subset of updateable fields (`name`, `industry`, `cash_balance`, `annual_revenue_target`).
- **Response** (200 OK): Returns the updated `CompanySchema` object.

---

### Customers

#### GET `/business/customers`
Retrieves a list of customers. Supports pagination.

- **Query Parameters**:
  - `skip` (int, default: 0): Number of records to skip.
  - `limit` (int, default: 100, max: 500): Max number of records to return.
- **Response** (200 OK): Array of `CustomerSchema` objects.
  ```json
  [
    {
      "id": 1,
      "name": "Enterprise Solutions Ltd",
      "email": "procurement@entsol.com",
      "phone": "+1 555-0199",
      "address": "456 Enterprise Way, Austin, TX",
      "company_name": "Enterprise Solutions",
      "credit_score": 750,
      "credit_limit": 50000.00,
      "payment_terms_days": 30,
      "clv": 15200.50,
      "is_active": 1,
      "created_at": "2026-07-18T10:00:00Z",
      "updated_at": "2026-07-18T10:00:00Z"
    }
  ]
  ```

#### GET `/business/customers/{customer_id}`
Retrieves a specific customer record by ID.

- **Response** (200 OK): Single `CustomerSchema` object.
- **Errors**:
  - `404 Not Found`: Customer not found.

#### POST `/business/customers`
Creates a new customer. Email must be unique.

- **Request Body** (JSON):
  - `name` (string, required, length 1–255)
  - `email` (string/email, required)
  - `phone` (string, optional)
  - `address` (string, optional)
  - `company_name` (string, optional)
  - `credit_score` (int, default: 700, range: 300–850)
  - `credit_limit` (float, default: 10000.0, >= 0)
  - `payment_terms_days` (int, default: 30, >= 0)
- **Response** (201 Created): The created `CustomerSchema` object.
- **Errors**:
  - `409 Conflict`: Customer with email already exists.

#### PATCH `/business/customers/{customer_id}`
Updates details of an existing customer.

- **Request Body** (JSON): Any subset of updateable fields (`name`, `phone`, `credit_score`, `credit_limit`, `is_active`).
- **Response** (200 OK): The updated `CustomerSchema` object.

---

### Suppliers

#### GET `/business/suppliers`
Lists all suppliers. Supports pagination.

- **Query Parameters**: `skip` (default 0), `limit` (default 100).
- **Response** (200 OK): List of `SupplierSchema` objects.
  ```json
  [
    {
      "id": 1,
      "name": "Global Components Corp",
      "email": "sales@globalparts.com",
      "contact": "John Doe",
      "phone": "+1 555-0822",
      "address": "89 Industrial Ave, Detroit, MI",
      "payment_terms_days": 45,
      "reliability_score": 0.95,
      "average_lead_days": 5,
      "total_orders_placed": 42,
      "total_delayed_orders": 2,
      "created_at": "2026-07-18T10:00:00Z",
      "updated_at": "2026-07-18T10:00:00Z"
    }
  ]
  ```

#### GET `/business/suppliers/{supplier_id}`
Retrieves a supplier by ID.

- **Response** (200 OK): `SupplierSchema` object.

#### POST `/business/suppliers`
Registers a new supplier.

- **Request Body** (JSON):
  - `name` (string, required, length 1–255)
  - `email` (string/email, required)
  - `contact` (string, optional)
  - `phone` (string, optional)
  - `address` (string, optional)
  - `payment_terms_days` (int, default: 30, >= 0)
  - `reliability_score` (float, default: 1.0, range 0.0–1.0)
  - `average_lead_days` (int, default: 7, >= 0)
- **Response** (201 Created): `SupplierSchema` object.
- **Errors**:
  - `409 Conflict`: Supplier email already registered.

#### PATCH `/business/suppliers/{supplier_id}`
Updates an existing supplier's details or metrics.

- **Request Body** (JSON): Any subset of updateable fields (`name`, `reliability_score`, `average_lead_days`, `payment_terms_days`).
- **Response** (200 OK): Updated `SupplierSchema` object.

---

### Products

#### GET `/business/products`
Lists all products. Supports pagination and category filtering.

- **Query Parameters**:
  - `skip` (int, default: 0)
  - `limit` (int, default: 100)
  - `category` (string, optional): Filter by product category.
- **Response** (200 OK): Array of `ProductSchema` objects.
  ```json
  [
    {
      "id": 1,
      "sku": "PROD-A100",
      "name": "Industrial Widget A",
      "description": "High durability industrial grade widget",
      "category": "Components",
      "unit_of_measure": "unit",
      "price": 150.00,
      "cost": 85.00,
      "stock_level": 120,
      "reorder_point": 25,
      "reorder_quantity": 100,
      "supplier_id": 1,
      "is_active": 1,
      "created_at": "2026-07-18T10:00:00Z",
      "updated_at": "2026-07-18T10:00:00Z"
    }
  ]
  ```

#### GET `/business/products/{product_id}`
Retrieves a product by ID.

- **Response** (200 OK): `ProductSchema` object.

#### POST `/business/products`
Creates a product and automatically initializes a matching record in the [Inventory](#inventory) table. SKU must be unique.

- **Request Body** (JSON):
  - `sku` (string, required, length 1–50)
  - `name` (string, required, length 1–255)
  - `description` (string, optional)
  - `category` (string, optional)
  - `unit_of_measure` (string, default: "unit")
  - `price` (float, required, > 0)
  - `cost` (float, required, > 0)
  - `stock_level` (int, default: 0, >= 0)
  - `reorder_point` (int, default: 10, >= 0)
  - `reorder_quantity` (int, default: 50, >= 0)
  - `supplier_id` (int, optional)
- **Response** (201 Created): `ProductSchema` object.
- **Errors**:
  - `409 Conflict`: Product SKU already exists.

#### PATCH `/business/products/{product_id}`
Updates details of a product.

- **Request Body** (JSON): Any subset of updateable fields (`name`, `price`, `cost`, `stock_level`, `reorder_point`, `is_active`).
- **Response** (200 OK): Updated `ProductSchema` object.

---

### Inventory

#### GET `/business/inventory`
Lists inventory stock details for all products.

- **Response** (200 OK): Array of `InventorySchema` objects.
  ```json
  [
    {
      "id": 1,
      "product_id": 1,
      "current_stock": 120,
      "reserved_stock": 10,
      "warehouse_location": "Aisle 3, Row B",
      "last_updated": "2026-07-18T10:00:00Z"
    }
  ]
  ```

#### PATCH `/business/inventory/{product_id}`
Updates inventory specifications (location, current/reserved stock) for a specific product.
Updating the inventory `current_stock` will automatically update the `stock_level` in the [Products](#products) table to ensure synchronization.

- **Request Body** (JSON):
  - `current_stock` (int, optional, >= 0)
  - `reserved_stock` (int, optional, >= 0)
  - `warehouse_location` (string, optional)
- **Response** (200 OK): Updated `InventorySchema` object.

---

### Sales

#### GET `/business/sales`
Lists sales transactions in descending chronological order. Supports pagination and customer filtering.

- **Query Parameters**:
  - `skip` (int, default: 0)
  - `limit` (int, default: 100)
  - `customer_id` (int, optional): Filter by customer.
- **Response** (200 OK): Array of `SalesSchema` objects.
  ```json
  [
    {
      "id": 1,
      "product_id": 1,
      "customer_id": 1,
      "quantity": 10,
      "unit_price": 150.00,
      "discount_pct": 5.0,
      "total_price": 1425.00,
      "channel": "direct",
      "date": "2026-07-18T10:15:30Z"
    }
  ]
  ```

#### POST `/business/sales`
Records a sales transaction.
*Business Logic*:
1. Validates that the product exists and has sufficient stock (`stock_level >= quantity`).
2. Validates that the customer exists.
3. Computes the final `total_price` dynamically: `quantity * unit_price * (1 - discount_pct/100)`.
4. Decrements `stock_level` from both the product and its inventory record.
5. Adds the calculated `total_price` to the customer's customer lifetime value (`clv`).

- **Request Body** (JSON):
  - `product_id` (int, required)
  - `customer_id` (int, required)
  - `quantity` (int, required, > 0)
  - `unit_price` (float, required, > 0)
  - `discount_pct` (float, default: 0.0, range 0.0–100.0)
  - `channel` (string, default: "direct")
- **Response** (201 Created): `SalesSchema` object.
- **Errors**:
  - `404 Not Found`: Product or Customer not found.
  - `400 Bad Request`: Insufficient inventory level.

---

### Invoices

Invoices represent bills of two varieties: Accounts Receivable (`AR` from customers) and Accounts Payable (`AP` from suppliers).

#### GET `/business/invoices`
Lists invoices. Supports filtering by status and type.

- **Query Parameters**:
  - `skip` (int, default: 0)
  - `limit` (int, default: 100)
  - `status` (string, optional): `UNPAID` | `PARTIAL` | `PAID` | `OVERDUE`
  - `invoice_type` (string, optional): `AR` | `AP`
- **Response** (200 OK): Array of `InvoiceSchema` objects.
  ```json
  [
    {
      "id": 1,
      "invoice_number": "INV-2026-001",
      "invoice_type": "AR",
      "issue_date": "2026-07-18T10:00:00Z",
      "due_date": "2026-08-17T10:00:00Z",
      "total_amount": 1425.00,
      "tax_amount": 75.00,
      "discount_amount": 0.00,
      "paid_amount": 0.00,
      "status": "UNPAID",
      "notes": "Direct sales order",
      "customer_id": 1,
      "supplier_id": null
    }
  ]
  ```

#### GET `/business/invoices/{invoice_id}`
Retrieves a specific invoice by ID.

- **Response** (200 OK): `InvoiceSchema` object.

#### POST `/business/invoices`
Creates a new invoice. Must link to at least one party: customer or supplier.

- **Request Body** (JSON):
  - `invoice_number` (string, required, length 1–100)
  - `invoice_type` (string, default: "AR", pattern: `^(AR|AP)$`)
  - `due_date` (datetime, required)
  - `total_amount` (float, required, > 0)
  - `tax_amount` (float, default: 0.0, >= 0)
  - `discount_amount` (float, default: 0.0, >= 0)
  - `status` (string, default: "UNPAID", pattern: `^(UNPAID|PARTIAL|PAID|OVERDUE)$`)
  - `notes` (string, optional)
  - `customer_id` (int, optional)
  - `supplier_id` (int, optional)
- **Response** (201 Created): `InvoiceSchema` object.
- **Errors**:
  - `422 Unprocessable Entity`: Missing both `customer_id` and `supplier_id`.

#### PATCH `/business/invoices/{invoice_id}`
Updates partial parameters of an invoice (e.g. paying down balances or shifting status).

- **Request Body** (JSON):
  - `status` (string, optional): `UNPAID` | `PARTIAL` | `PAID` | `OVERDUE`
  - `paid_amount` (float, optional, >= 0)
  - `notes` (string, optional)
- **Response** (200 OK): Updated `InvoiceSchema` object.

---

### Employees

#### GET `/business/employees`
Lists all employees.

- **Response** (200 OK): Array of `EmployeeSchema` objects.
  ```json
  [
    {
      "id": 1,
      "name": "Jane Miller",
      "email": "jane@acme.corp",
      "role": "Sales Operations Specialist",
      "department": "Sales",
      "salary": 65000.00,
      "employment_type": "full_time",
      "is_active": 1,
      "hire_date": "2025-03-01T09:00:00Z"
    }
  ]
  ```

#### POST `/business/employees`
Creates a new employee record.

- **Request Body** (JSON):
  - `name` (string, required)
  - `email` (string/email, required)
  - `role` (string, required)
  - `department` (string, required)
  - `salary` (float, required, > 0)
  - `employment_type` (string, default: "full_time", pattern: `^(full_time|part_time|contractor)$`)
- **Response** (201 Created): `EmployeeSchema` object.

---

### Events

Used to manually or programmatically insert records into the platform's episodic "Business Memory".

#### GET `/business/events`
Lists chronological business events.

- **Query Parameters**:
  - `limit` (int, default: 50, range 1–500): Limit amount returned.
  - `event_type` (string, optional): Filter by type (e.g. `price_change`, `customer_complaint`, etc.).
- **Response** (200 OK): Array of `BusinessEventSchema` objects.
  ```json
  [
    {
      "id": 1,
      "event_type": "price_change",
      "description": "Product SKU PROD-A100 price adjusted to $150.00",
      "severity": "INFO",
      "source": "user",
      "entity_type": "product",
      "entity_id": 1,
      "metadata_json": {
        "old_price": 140.00,
        "new_price": 150.00
      },
      "timestamp": "2026-07-18T10:00:00Z"
    }
  ]
  ```

#### POST `/business/events`
Logs a business event manually in the platform database.

- **Request Body** (JSON):
  - `event_type` (string, required)
  - `description` (string, required)
  - `severity` (string, default: "INFO")
  - `source` (string, default: "user")
  - `entity_type` (string, optional)
  - `entity_id` (int, optional)
  - `metadata_json` (dict, optional)
- **Response** (201 Created): `BusinessEventSchema` object.

---

## 3. File Upload & Document Intelligence (`/api/v1/upload`)

These endpoints receive documents, save them to the server storage immediately, and queue background tasks for metadata extraction and parsing (powered by PyMuPDF, pdfplumber, pytesseract, etc.).

All upload endpoints accept file uploads using standard **`multipart/form-data`** containing a single parameter:
- **`file`**: Binary file contents.

### File Upload Routes Summary

| Endpoint | Subfolder Stored | Allowed Extensions | Purpose |
|---|---|---|---|
| `POST /upload/invoice` | `invoices/` | `.pdf`, `.png`, `.jpg`, `.jpeg` | Extracted vendor, GST details, amounts, line items |
| `POST /upload/gst` | `gst/` | `.pdf`, `.json`, `.xlsx` | Recon tax liabilities and return schedules |
| `POST /upload/bank` | `bank_statements/` | `.pdf`, `.csv`, `.xlsx`, `.xls` | Parses monthly statements to verify cash cycles |
| `POST /upload/excel` | `excel_imports/` | `.xls`, `.xlsx` | Bulk import product or inventory configurations |
| `POST /upload/supplier_notice`| `supplier_notices/`| `.pdf`, `.png`, `.jpg`, `.jpeg` | Monitors supplier price hikes or policy letters |
| `POST /upload/purchase_order` | `purchase_orders/` | `.pdf`, `.png`, `.jpg`, `.jpeg` | Parses buyer requirements to log pending orders |

- **Response Structure** (200 OK):
  ```json
  {
    "message": "Invoice processed successfully.",
    "filepath": "/Users/vaibhav/Documents/Projects/cashflow-ai/uploads/invoices/9a3c1e2f-524d-4876-b631-c0cf47e85c88.pdf",
    "original_filename": "supplier_bill_july.pdf"
  }
  ```
- **Errors**:
  - `400 Bad Request`: File extension is not in the allowed list for the target route.

### POST `/upload/sample`
Executes parsing and ingestion routines on a preloaded demonstration sample from the project's `sample_docs/` folder. This is useful for testing without importing external custom files.

- **Request Body** (JSON):
  - `sample_key` (string, required): One of:
    - `"invoice_001"` (invoice)
    - `"invoice_002"` (invoice)
    - `"overdue_invoice"` (invoice)
    - `"gst_return"` (gst)
    - `"bank_statement"` (bank CSV)
    - `"july_statement"` (bank Excel)
    - `"inventory"` (inventory Excel)
    - `"price_increase"` (supplier price notice)
    - `"po_2101"` (purchase order)
- **Response** (200 OK):
  ```json
  {
    "message": "Sample document 'invoice_001' processed successfully.",
    "filepath": "/Users/vaibhav/Documents/Projects/cashflow-ai/sample_docs/invoices/invoice_001.pdf",
    "category": "invoice"
  }
  ```
- **Errors**:
  - `400 Bad Request`: Invalid sample key.
  - `404 Not Found`: Preloaded file missing from workspace directories.

---

## 4. Dashboard & Analytics APIs (`/api/v1`)

Provides aggregated real-time financial health, stock trackers, alerts, and transaction histories compiled directly from database transactions.

### GET `/dashboard`
Computes key performance indicators (KPIs) based on live ledger balances, sales invoices, and customer indexes.

- **Response** (200 OK):
  ```json
  {
    "metrics": {
      "total_revenue": 145800.50,
      "monthly_revenue": 12400.00,
      "accounts_receivable": 45000.00,
      "accounts_payable": 18200.00,
      "net_working_capital": 26800.00,
      "low_stock_alerts": 3,
      "active_customers": 18,
      "monthly_orders": 24
    },
    "generated_at": "2026-07-18T10:30:00.000000"
  }
  ```

### GET `/business-health`
Calculates profitability ratios and health categorization, deducing risk points dynamically.
*Scoring Rules*: Starts at 100 points. Penalizes for operating ratio > 0.70 (-10) or > 0.85 (-25), loss periods (-20), high overdue invoices count (-10 to -20), or stock-outs (-5 to -15).

- **Response** (200 OK):
  ```json
  {
    "status": "Healthy",
    "health_score": 85,
    "gross_profit_margin_pct": 42.50,
    "operating_ratio": 0.5750,
    "overdue_invoices": 1,
    "low_stock_products": 2,
    "gross_profit": 61965.20,
    "generated_at": "2026-07-18T10:30:00.000000"
  }
  ```

### GET `/alerts`
Lists operational alerts (financial arrears, inventory shortages, upcoming payments) sorted by severity: `CRITICAL` -> `WARNING` -> `INFO`.

- **Response** (200 OK):
  ```json
  [
    {
      "severity": "CRITICAL",
      "category": "FINANCIAL",
      "title": "Overdue Invoices Require Immediate Action",
      "message": "1 invoice(s) are past due, totalling $2,500.00. Contact customers immediately.",
      "count": 1
    },
    {
      "severity": "WARNING",
      "category": "INVENTORY",
      "title": "Low Stock: Industrial Widget A",
      "message": "SKU PROD-A100 has 15 units remaining (reorder point: 25). Suggested reorder: 100 units.",
      "product_id": 1
    }
  ]
  ```

### GET `/timeline`
Aggregates and delivers chronological business event feed logs.

- **Query Parameters**:
  - `limit` (int, default: 20): Number of events.
- **Response** (200 OK): Array of logged episodic events.

---

## 5. Ollama AI Intelligence APIs (`/api/v1/ai`)

Leverages local LLM processes (such as Gemma) to conduct question-answering sessions and draft executive packages.

### POST `/ai/chat`
Answers business queries relative to the real-time company operational states compiled by the memory manager.
*Pipeline*: Compiles context metrics -> builds prompts using `PromptBuilder` -> forwards to local Gemma. If offline, switches to fallback state logging.

- **Request Body** (JSON):
  - `question` (string, required, minimum length: 1)
- **Response** (200 OK):
  ```json
  {
    "response": "Based on current data, your cash balance is $250,000.00, and there are 2 low stock alerts...",
    "model_used": "gemma2:9b",
    "context_summary": {
      "low_stock_count": 2,
      "recent_events_count": 5,
      "company": "Acme Corp"
    }
  }
  ```

### GET `/ai/ollama-status`
Confirms the local Ollama daemon's reachability and active model setups.

- **Response** (200 OK): Returns connection status and model details.

### GET `/ai/executive-brief`
Generates a structured morning executive review with summary items, action lines, and alert notifications.

- **Response** (200 OK):
  ```json
  {
    "morning_summary": "Good morning. Acme Corp is operating with a cash balance of $250,000.00...",
    "critical_alerts": [
      "2 products are below reorder threshold and require immediate restocking."
    ],
    "top_opportunities": [
      "Review top customer CLV data and implement a loyalty programme."
    ],
    "business_health_summary": "Business operations appear stable.",
    "top_actions": [
      "Reorder stock for 2 products at or below reorder point.",
      "Follow up on overdue customer invoices."
    ]
  }
  ```

---

## 6. Predictive Forecasting APIs (`/api/v1`)

Accesses predictive machine learning services to estimate future transaction directions without changing db tables directly.

### GET `/forecast/revenue`
Returns a 90-day revenue project based on sales velocity coefficients.

- **Response** (200 OK):
  ```json
  {
    "prediction": "Projected 90-day revenue: $45,000.00 (+5.2% vs previous period)",
    "confidence_score": 0.88,
    "important_features": ["prior_30d_velocity", "seasonality_index", "active_customers"],
    "business_impact": "Stabilised cash inflows; support for temporary operational hires",
    "suggested_action": "Maintain current pricing; initiate customer reactivation campaign",
    "metadata": { "growth_pct": 5.2 }
  }
  ```

### GET `/forecast/cashflow`
Projects outstanding invoice collections against payable dates over the next 30 days.

- **Response** (200 OK): `PredictionResponse` structure.

### GET `/forecast/demand`
Provides product-by-product stocking guidelines, listing urgency status.

- **Response** (200 OK): Array of `ProductPrediction` objects.
  ```json
  [
    {
      "product_id": 1,
      "sku": "PROD-A100",
      "name": "Industrial Widget A",
      "prediction": "Demand forecast: 85 units over next 30 days. Shortfall expected.",
      "confidence_score": 0.82,
      "important_features": ["sales_velocity_30d", "reorder_lead_time"],
      "business_impact": "Stock-out threat in 8 days if reorder delay occurs",
      "suggested_action": "Order 100 units from Supplier ID 1 immediately",
      "metadata": { "projected_sales": 85 }
    }
  ]
  ```

### GET `/risk/customers`
Assesses churn risk and customer late-payment likelihood.

- **Response** (200 OK): Array of `CustomerRiskPrediction` objects.
  ```json
  [
    {
      "customer_id": 1,
      "name": "Enterprise Solutions Ltd",
      "churn_probability": 0.12,
      "late_payment_risk": "MEDIUM",
      "clv": 15200.50,
      "prediction": "Customer is highly active; low churn threat but watch invoice delays",
      "confidence_score": 0.90,
      "important_features": ["days_past_due_avg", "interaction_frequency"],
      "business_impact": "Consistent CLV generation; minor liquidity drag",
      "suggested_action": "Offer a 2% early payment discount to secure AR timeline"
    }
  ]
  ```

### GET `/risk/suppliers`
Calculates fulfillment delay probabilities and potential supplier pricing issues.

- **Response** (200 OK): Array of `SupplierRiskPrediction` objects.

### GET `/pricing`
Suggests margin optimizations per catalog product.

- **Response** (200 OK): Array of `PricingRecommendation` objects.
  ```json
  [
    {
      "product_id": 1,
      "sku": "PROD-A100",
      "name": "Industrial Widget A",
      "current_price": 150.00,
      "recommended_price": 158.50,
      "expected_profit_per_unit": 73.50,
      "expected_revenue_uplift": 722.50,
      "demand_impact": "Slight demand softening (-1.5%) offset by higher margins (+5.6%)",
      "confidence_score": 0.85,
      "suggested_action": "Apply price change to SKU PROD-A100 in batches"
    }
  ]
  ```

---

## 7. Decision Intelligence Engine APIs (`/api/v1`)

The multi-agent system orchestrates reports from specialist agents to produce ranked strategic recommendations, simulate outcomes, and maintain decision logs.

### GET `/agents`
Runs the six specialist agents (Finance, Ops, Marketing, Supplier, Customer, Risk) independently and returns their reports. Does not run CEO synthesis.

- **Response** (200 OK):
  ```json
  {
    "agents": [
      {
        "agent_name": "Finance Agent",
        "analysis": "Liquid capital is healthy but AR cycles are rising.",
        "recommendations": ["Initiate early payment discounts."],
        "confidence": 0.85,
        "risk_level": "LOW",
        "supporting_evidence": ["Receivables average 38 days vs 30 term."]
      }
    ],
    "total_agents": 6,
    "context_snapshot": { ... }
  }
  ```

### GET `/recommendations`
Runs the complete multi-agent orchestration. The CEO agent synthesizes the individual reports into ranked items. The top 5 recommendations are stored in the database for tracking.

- **Response** (200 OK):
  ```json
  {
    "total": 3,
    "recommendations": [
      {
        "title": "Optimise Receivables Collection",
        "recommendation": "Deploy automated invoice follow-ups and early payment discounts.",
        "reasoning": "AR averages 38 days causing minor working capital friction.",
        "confidence": 0.90,
        "roi_estimate": 12.5,
        "risk_level": "LOW",
        "business_impact": "Reduces collection cycles to 29 days, boosting cash liquidity.",
        "affected_departments": ["Finance", "Customer Relations"],
        "supporting_evidence": ["Invoice #102 is overdue by 12 days"],
        "agent_source": "Finance Agent"
      }
    ]
  }
  ```

### POST `/simulate`
Digital Twin simulator: models what-if scenarios based on parameter shifts to project financial and operational impact without modifying the live database.

- **Request Body** (JSON):
  - `price_changes` (dict, optional): Map of product IDs to new prices. E.g. `{"1": 158.50}`
  - `new_hires` (int, default: 0): Employees to add.
  - `avg_new_hire_salary` (float, default: 50000.0)
  - `supplier_change` (string, optional): `"diversify"` | `"single_source"`
  - `inventory_investment` (float, default: 0.0)
  - `loan_amount` (float, default: 0.0)
  - `loan_interest_rate_pct` (float, default: 5.0)
  - `marketing_spend` (float, default: 0.0)
- **Response** (200 OK):
  ```json
  {
    "scenario_label": "Simulated What-If Scenario",
    "projected_revenue": 158000.00,
    "projected_profit": 64500.00,
    "projected_cash_flow": 28400.00,
    "risk_score": 0.32,
    "inventory_health": "HEALTHY",
    "business_health_score": 88,
    "key_insights": ["Marketing spend boosts demand by 8.5%"],
    "warnings": ["Price increase on SKU PROD-A100 will decrease conversion rate slightly"]
  }
  ```

### GET `/decision-history`
Lists user choices and outcome records on past AI recommendations to trace historical context.

- **Query Parameters**:
  - `limit` (int, default: 20, range 1–100)
- **Response** (200 OK): Array of `DecisionHistorySchema` records.

### POST `/decision-history`
Records the operator's decision (`APPROVED` | `REJECTED` | `MODIFIED`) and any subsequent real business outcomes. This updates the status of the related recommendation history record.

- **Request Body** (JSON):
  - `recommendation_id` (int, required)
  - `user_action` (string, required, pattern: `^(APPROVED|REJECTED|MODIFIED)$`)
  - `modification_notes` (string, optional)
  - `business_outcome` (string, optional)
  - `outcome_revenue_impact` (float, optional)
  - `feedback` (string, optional)
- **Response** (201 Created): Returns the generated `DecisionHistorySchema` record.

### GET `/explain/{recommendation_id}`
Retrieves explainability, logic factors, and evidence tracking reports for a specific recommendation ID.

- **Response** (200 OK):
  ```json
  {
    "recommendation_id": 1,
    "reason": "AR averages 38 days causing minor working capital friction.",
    "evidence": ["Invoice #102 is overdue by 12 days"],
    "confidence": 0.90,
    "business_impact": "Reduces collection cycles to 29 days, boosting cash liquidity.",
    "affected_departments": ["Finance", "Customer Relations"]
  }
  ```
- **Errors**:
  - `404 Not Found`: No recommendation record exists with that ID.
