# Stratify (SME OS): Architectural & Operational Specification

Stratify (SME OS) is an enterprise-grade, local-AI-driven Business Operating System built to automate decision-making, transactional ledger flows (CRUD), document ingestion parsing, and predictive runway analytics for Small & Medium Enterprises.

---

## 1. System Topology & Workspace Structure

The project workspace is divided into a decoupled **FastAPI ASGI Backend** and a **Vite React Single Page Application (SPA) Frontend**:

```text
stratify/
â”œâ”€â”€ README.md                   # Complete architectural & operational specification
â”œâ”€â”€ design.md                   # Locked design system (tokens, CSS variables)
â”œâ”€â”€ package-lock.json           # Root lock file
â”œâ”€â”€ skills-lock.json            # Lock file for agent skills
â”œâ”€â”€ docs/                       # Project documentation
â”‚   â””â”€â”€ decisions/              # Architectural Decision Records (ADRs)
â”‚       â””â”€â”€ 0001-multi-agent-decision-engine.md
â”œâ”€â”€ backend/                    # FastAPI ASGI Python application
â”‚   â”œâ”€â”€ app/                    # Main source code package
â”‚   â”‚   â”œâ”€â”€ main.py             # App entrypoint, lifespan lifecycle, middleware, prefix registry
â”‚   â”‚   â”œâ”€â”€ config.py           # Environment variables configuration management (Pydantic settings)
â”‚   â”‚   â”œâ”€â”€ database.py         # SQLAlchemy connection engine & DB session dependencies
â”‚   â”‚   â”œâ”€â”€ models/             # Database ORM entity mapping classes
â”‚   â”‚   â”‚   â”œâ”€â”€ business.py     # Entities: Company, Customer, Supplier, Product, Invoice, Sales, Inventory
â”‚   â”‚   â”‚   â””â”€â”€ history.py      # Audits: BusinessEvent, RecommendationHistory, DecisionHistory
â”‚   â”‚   â”œâ”€â”€ schemas/            # Pydantic v2 validation data transfer objects DTOs
â”‚   â”‚   â”‚   â”œâ”€â”€ business.py     # Base, Create, Update, and Schema properties for business entities
â”‚   â”‚   â”‚   â”œâ”€â”€ predictive.py   # Forecast return formats (Prediction, Confidence, Feature weights)
â”‚   â”‚   â”‚   â””â”€â”€ decision.py     # Simulation input/outputs & recommendation summaries
â”‚   â”‚   â”œâ”€â”€ routers/            # Versioned API routes mapping controller actions
â”‚   â”‚   â”‚   â”œâ”€â”€ business.py     # CRUD controllers for customers, suppliers, products, invoices, sales
â”‚   â”‚   â”‚   â”œâ”€â”€ dashboard.py    # Analytics dashboards, alerts, business health scores, timeline events
â”‚   â”‚   â”‚   â”œâ”€â”€ ai.py           # Local LLM chat (Ollama status) and executive briefs
â”‚   â”‚   â”‚   â”œâ”€â”€ forecast.py     # Time-series regression forecasting models
â”‚   â”‚   â”‚   â”œâ”€â”€ risk.py         # Volatility, late-payment, and delivery delay risk estimators
â”‚   â”‚   â”‚   â”œâ”€â”€ decision.py     # Multi-Agent consensus, explanation audit, digital twin simulation
â”‚   â”‚   â”‚   â””â”€â”€ upload.py       # Async document ingestors
â”‚   â”‚   â”œâ”€â”€ services/           # Business domain processing engines
â”‚   â”‚   â”‚   â”œâ”€â”€ agent_engine.py # CEO orchestration of 6 domain expert agents
â”‚   â”‚   â”‚   â”œâ”€â”€ business_memory.py # Episodic contextual database retriever
â”‚   â”‚   â”‚   â”œâ”€â”€ doc_intelligence.py # Parser triggers mapping PDF/XLSX text to JSON DTOs
â”‚   â”‚   â”‚   â”œâ”€â”€ ollama_client.py # Local Ollama LLM integration client
â”‚   â”‚   â”‚   â”œâ”€â”€ prediction_engine.py # Regression analytics models (Revenue, Cash flow, Demand)
â”‚   â”‚   â”‚   â””â”€â”€ simulation_engine.py # Volatility Twin what-if math multipliers
â”‚   â”‚   â””â”€â”€ utils/              # Utility helpers
â”‚   â”‚       â”œâ”€â”€ helpers.py      # Common helper functions
â”‚   â”‚       â””â”€â”€ prompt_builder.py # Context-aware prompt template builder
â”‚   â”œâ”€â”€ requirements.txt        # Backend dependencies
â”‚   â”œâ”€â”€ sme_platform.db         # SQLite transactional database
â”‚   â””â”€â”€ docker-compose.yml      # Multi-service local launch (FastAPI, Ollama)
â””â”€â”€ frontend/                   # React 19 + Vite + TypeScript Single Page App
    â”œâ”€â”€ src/                    # App source code
    â”‚   â”œâ”€â”€ main.tsx            # Main App entrypoint
    â”‚   â”œâ”€â”€ App.tsx             # Interactive dashboard, view states, telemetry charts, Chat panels
    â”‚   â”œâ”€â”€ api.ts              # Axios api client integration
    â”‚   â”œâ”€â”€ index.css           # Global custom typography, glassmorphism, scrollbars
    â”‚   â””â”€â”€ App.css             # Specific layout styling
    â”œâ”€â”€ public/                 # Static assets directory
    â”œâ”€â”€ index.html              # Shell HTML template
    â”œâ”€â”€ package.json            # Frontend script actions & dependency list
    â”œâ”€â”€ tsconfig.json           # TypeScript configuration
    â””â”€â”€ vite.config.ts          # Vite build tool configuration
```

---

## 2. Decoupled Architecture Specifications

### A. Backend Architecture & API Routes

The backend uses **FastAPI** with async router endpoints. Database transactions are isolated per request using SQLAlchemy async sessions.

#### 1. Versioning Protocol
All api controllers are registered under the version prefix `/api/v1` in `app/main.py`:
- Prefix variable: `API_V1 = "/api/v1"`
- CORS settings are configured to allow access from local frontend clients (`http://localhost:5173` or specified origins).

#### 2. Complete Router Mappings
- **Business CRUD Router (`/business`)**:
  - `GET /business/company` & `POST /business/company` â€” Retrieve/setup company master details.
  - `GET /business/customers` & `POST /business/customers` â€” Manage customer directories.
  - `GET /business/suppliers` & `POST /business/suppliers` â€” Manage suppliers metadata.
  - `GET /business/products` & `POST /business/products` â€” Manage product catalogue items.
  - `GET /business/inventory` â€” Monitor warehouse stock levels.
  - `GET /business/invoices` & `POST /business/invoices` â€” Log ledger AR/AP invoices.
  - `GET /business/sales` & `POST /business/sales` â€” Log sales transactions (decrements inventory, increments customer CLV).
- **Dashboard & Analytics Router (no prefix)**:
  - `GET /dashboard` â€” High-level KPIs calculated from live transaction data (Revenue, Net Working Capital, AR, AP, Active Customers).
  - `GET /business-health` â€” Composite business health score derived from profitability, liquidity, and risk indicators.
  - `GET /alerts` â€” Active operational alerts.
  - `GET /timeline` â€” Chronological business event audit feed.
- **AI Intelligence Router (`/ai`)**:
  - `POST /ai/chat` â€” Context-aware chat matching prompt contexts dynamically built from recent business events and records.
  - `GET /ai/ollama-status` â€” Reports whether the local Ollama daemon is reachable and the configured model is available.
  - `GET /ai/executive-brief` â€” Structured morning briefs compiled from database states (returns morning summary text, alerts, opportunities, actions).
- **Forecasting Router (`/forecast`)**:
  - `GET /forecast/revenue` â€” 90-day revenue forecast using weighted historical sales velocity.
  - `GET /forecast/cashflow` â€” 30-day cash flow forecast based on outstanding AR/AP balances.
  - `GET /forecast/demand` â€” Per-product demand forecasting and reorder quantities.
- **Risk & Pricing Router (no prefix)**:
  - `GET /risk/customers` â€” Customer churn risk, late payment probability, and CLV forecasts.
  - `GET /risk/suppliers` â€” Delay probability and procurement price increase risk.
  - `GET /pricing` â€” Margin-optimised pricing advice per product.
- **Decision Engine Router (no prefix)**:
  - `GET /agents` â€” Executes 6 specialists (Finance, Logistics, Marketing, Supplier, Customer, Risk) and compiles individual reports.
  - `GET /recommendations` â€” Synthesizes domain reports into CEO strategic consensus suggestions.
  - `POST /simulate` â€” Digital twin simulation calculating simulated revenue, profit, cash, and risk indices from what-if sliders.
  - `GET /decision-history` & `POST /decision-history` â€” Log user responses (Approve/Decline) to recommendation cards.
  - `GET /explain/{recommendation_id}` â€” Resolves evidentiary details and affected departments for recommendations.
- **Upload Router (`/upload`)**:
  - `POST /upload/invoice`, `POST /upload/gst`, `POST /upload/bank`, `POST /upload/excel` â€” Multi-part form endpoints queuing background document parsing tasks.

---

### B. Frontend Architecture & Design Elements

The user interface implements a premium, dark developer dashboard style using React 19 and Vite.

#### 1. Design System & CSS Rules (`src/index.css`)
- **Background Layer**: OKLCH deep midnight blue `oklch(14% 0.012 250)` combined with crisp cool white `oklch(95% 0.008 250)` text.
- **Glass Panel Blur**: `.glass-panel` and `.card` wrappers styled with `rgba(17, 17, 17, 0.7)` background, `backdrop-filter: blur(12px)` and subtle `border: 1px solid rgba(255, 255, 255, 0.08)`.
- **Developer Scrollbar**: Tailored scrollbars using `-webkit-scrollbar` with translucent thumbs (`rgba(255, 255, 255, 0.1)`) that expand on hover.
- **Microinteractions**: Active states show explicit `outline: 2px solid var(--color-focus); outline-offset: 2px;` borders. Subtle hover translations on cards and navigation buttons.

#### 2. Interactive SVG Analytics & Sparklines
- **Sparkline SVG**: Light inline SVG vectors charting historical trends next to metrics (e.g. Total Revenue, Net Working Capital, Active Customers).
- **Telemetry Charts**: Interactive SVG graphs with confidence bounds (upper confidence and lower risk margins) and dynamic crosshairs displaying data tooltips on hover.
- **Number Tickers**: Custom React `NumberTicker` component which smoothly counts up to target values using easing functions, conforming to accessibility standards with support for `prefers-reduced-motion`.

---

## 3. Real-Time Data Flow & State Synchronization

The frontend coordinates user action events and triggers state fetches to keep dashboards aligned with backend SQLite telemetry:

```mermaid
sequenceDiagram
    participant User
    participant UI as App View (App.tsx)
    participant API as Axios Client (api.ts)
    participant Server as FastAPI Server (Uvicorn)
    participant DB as SQLite Database

    User->>UI: View Tab Switch / Action (e.g. Chat Question)
    UI->>API: sendChat(question) / getDashboard()
    API->>Server: POST /api/v1/ai/chat / GET /api/v1/dashboard
    Server->>DB: Query current business metrics/context
    DB-->>Server: Result set
    Server-->>API: 200 OK Response (JSON Schema)
    API-->>UI: Update local state variables (useState)
    UI-->>User: Re-render UI with fresh values
```

### A. Navigation View States
The interface maintains state for the active view (`page` state):
- `dashboard`: Telemetry bento grid containing core KPIs, alerts, and recent business timeline events.
- `forecast`: Interactive trendlines showing projected revenue, cash flow runway, and demand.
- `risk`: Customer and supplier risk tables mapping late payment and delivery delay factors.
- `agents`: Consensus engine running individual specialist analyses.
- `simulate`: What-if simulation dashboard with sliders projecting corporate health index impact.
- `chat`: Multi-agent conversation panel interacting with the local Gemma model.
- `brief`: Unified structured morning brief checklist.
- `history`: Decisions logs showcasing past recommendation cards and approval audits.
- `upload`: File dropzone for uploading invoices, bank statements, and spreadsheets.

---

## 4. Operational Instructions & Stack Launch

### A. Backend Setup
1. Change directory: `cd backend`
2. Create the isolated virtual environment if it does not already exist: `python -m venv venv`
3. Activate it before running any backend commands:
   - PowerShell: `.\venv\Scripts\Activate.ps1`
   - Command Prompt: `.\venv\Scripts\activate.bat`
   - Git Bash / WSL shell on Windows: `source venv/bin/activate`
4. Upgrade packaging tools and install backend dependencies inside the venv: `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`
5. Run the API server from the activated venv: `python -m uvicorn app.main:app --reload --port 8000`

Backend environment variables live in `backend/.env`. The application reads settings like `DATABASE_URL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (default is `gemma4:latest` or similar), with safe defaults for local development.

Before starting the backend, make sure Ollama is running locally and the configured model is installed (e.g., `ollama run gemma4:latest`).

If you prefer a fully containerised local stack, start the backend from `backend/docker-compose.yml`; it includes an Ollama service and maps dependencies automatically.

### B. Frontend Setup
1. Change directory: `cd frontend`
2. Install packages: `npm install`
3. Launch development client: `npm run dev`

---

## 5. Automated Verification Skill

A workspace verifier agent skill is located in [SKILL.md](.agents/skills/sme_os_verifier/SKILL.md) inside the `.agents` customizations folder.

To perform a stack verify command:
```bash
./.agents/skills/sme_os_verifier/scripts/verify_stack.sh
```
This script audits:
- If the SQLite file `backend/sme_platform.db` exists.
- If the FastAPI server is online on port 8000 and responds to `/health`.
- If the frontend client is online on port 5173.

