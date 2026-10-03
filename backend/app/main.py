"""
SME Business Operating System — FastAPI Application Entrypoint

Phases implemented:
  Phase 1: Database foundation, CRUD APIs, Business Memory, File Uploads
  Phase 2: Document Intelligence (PDF/OCR/Excel) + Gemma AI Chat
  Phase 3: Predictive Intelligence (Revenue, Cashflow, Demand, Risk, Pricing)
  Phase 4: Multi-Agent Decision Engine (CEO Agent + 6 specialists + Digital Twin)

Architecture:
  - Async FastAPI with lifespan context (DB init on startup)
  - API versioned at /api/v1
  - CORS enabled for local development
  - Structured logging
  - All routers registered with descriptive tags
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine

# Import all models so SQLAlchemy registers them before create_all
import app.models.business  # noqa: F401
import app.models.history   # noqa: F401
import app.models.materials   # noqa: F401
import app.models.supply_chain   # noqa: F401
import app.models.collections   # noqa: F401
import app.models.memory   # noqa: F401

# Routers — Phase 1
from app.routers.business import router as business_router
from app.routers.upload import router as upload_router
from app.routers.dashboard import router as dashboard_router
from app.routers.materials import router as materials_router
from app.routers.supply_chain import router as supply_chain_router

# Routers — Phase 2
from app.routers.ai import router as ai_router

# Routers — Phase 3
from app.routers.forecast import router as forecast_router
from app.routers.risk import router as risk_router

# Routers — Phase 4
from app.routers.decision import router as decision_router
from app.routers.memory import router as memory_router

# Routers — Phase 5 (Event Engine)
from app.routers.events import router as events_router


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — DB initialisation + teardown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler.
    On startup: creates all SQLAlchemy tables if they don't exist.
    On shutdown: disposes the async engine connection pool.
    """
    logger.info("=== SME OS Starting Up (env=%s) ===", settings.ENVIRONMENT)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialised.")

        # Programmatic column addition for SQLite schemas updates
        from sqlalchemy import text
        try:
            cursor = await conn.execute(text("PRAGMA table_info(invoices)"))
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            if "purchase_order_id" not in col_names:
                logger.info("Migrating invoices table: adding purchase_order_id column")
                await conn.execute(text("ALTER TABLE invoices ADD COLUMN purchase_order_id INTEGER REFERENCES purchase_orders(id) ON DELETE SET NULL"))
                logger.info("invoices table migrated successfully.")

            cursor_cust = await conn.execute(text("PRAGMA table_info(customers)"))
            columns_cust = cursor_cust.fetchall()
            col_names_cust = [col[1] for col in columns_cust]
            if "region" not in col_names_cust:
                logger.info("Migrating customers table: adding region column")
                await conn.execute(text("ALTER TABLE customers ADD COLUMN region VARCHAR(100) DEFAULT 'East'"))
                logger.info("customers table migrated successfully.")
            # Add explanation column to business_events if missing
            cursor_be = await conn.execute(text("PRAGMA table_info(business_events)"))
            columns_be = cursor_be.fetchall()
            col_names_be = [col[1] for col in columns_be]
            if "explanation" not in col_names_be:
                logger.info("Migrating business_events table: adding explanation column")
                await conn.execute(text("ALTER TABLE business_events ADD COLUMN explanation VARCHAR(2000)"))
                logger.info("business_events table migrated successfully.")
        except Exception as e:
            logger.error("Lifespan database schema migration failed: %s", e)

    # Start daily open invoice scanner background task
    import asyncio
    from app.database import AsyncSessionLocal
    from app.services.collections_task import scan_open_invoices_periodically
    
    scanner_task = asyncio.create_task(
        scan_open_invoices_periodically(AsyncSessionLocal, interval_seconds=86400)
    )

    yield  # Application runs here

    logger.info("=== SME OS Shutting Down ===")
    
    # Cancel open invoice scanner task
    scanner_task.cancel()
    try:
        await scanner_task
    except asyncio.CancelledError:
        pass
        
    await engine.dispose()
    logger.info("Database connections closed.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SME Business Operating System API",
    description=(
        "Enterprise-grade AI-powered backend for SME business management. "
        "Covers CRUD operations, document intelligence, predictive analytics, "
        "multi-agent decision making, and digital twin simulation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API v1 Prefix
# ---------------------------------------------------------------------------

API_V1 = "/api/v1"

# Phase 1 — Core Business Operations
app.include_router(business_router, prefix=API_V1)
app.include_router(upload_router, prefix=API_V1)
app.include_router(dashboard_router, prefix=API_V1)
app.include_router(materials_router, prefix=API_V1)
app.include_router(supply_chain_router, prefix=API_V1)

# Phase 2 — AI Intelligence
app.include_router(ai_router, prefix=API_V1)

# Phase 3 — Predictive Intelligence
app.include_router(forecast_router, prefix=API_V1)
app.include_router(risk_router, prefix=API_V1)

# Phase 4 — Decision Intelligence & Memory Engine
app.include_router(decision_router, prefix=API_V1)
app.include_router(memory_router, prefix=API_V1)

# Phase 5 — Event Engine
app.include_router(events_router, prefix=API_V1)



# ---------------------------------------------------------------------------
# Root & Health Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["System"])
async def root():
    """API root — confirms the service is running."""
    return {
        "service": "SME Business Operating System",
        "version": "1.0.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "api_base": API_V1,
        "phases_active": ["Phase 1: CRUD", "Phase 2: AI", "Phase 3: Predictive", "Phase 4: Decision", "Phase 5: Event Engine"],
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Lightweight health check for load balancer / Docker healthcheck."""
    return {"status": "healthy", "service": "sme-os-backend"}
