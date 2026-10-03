"""
Events Router — REST API endpoints for the Event Engine.

All endpoints mounted at /api/v1/events.

Endpoints:
  POST   /api/v1/events/              — Create a custom business event
  GET    /api/v1/events/              — List/filter events with pagination
  GET    /api/v1/events/stats/summary — Aggregate summary metrics
  GET    /api/v1/events/{event_id}    — Retrieve single event by ID
  POST   /api/v1/events/evaluate      — Trigger system-wide automated evaluation
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.event import (
    EventCreate,
    EventEvaluationResult,
    EventSchema,
    EventSummaryStatsSchema,
)
from app.services.event_engine import EventEngineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Event Engine"])


def _serialize_event(event) -> Dict[str, Any]:
    """Serializes a BusinessEvent ORM instance into the EventSchema shape."""
    return {
        "id": event.id,
        "event_type": event.event_type,
        "severity": event.severity or "INFO",
        "timestamp": event.timestamp,
        "source": event.source or "system",
        "explanation": event.explanation or event.description or "",
        "description": event.description or event.explanation or "",
        "related_entities": event.get_related_entities,
        "metadata_json": event.metadata_json,
    }


# ---------------------------------------------------------------------------
# POST /events/ — Create custom business event
# ---------------------------------------------------------------------------

@router.post("/", response_model=EventSchema, status_code=201, summary="Create a business event")
async def create_event(payload: EventCreate, db: AsyncSession = Depends(get_db)):
    """
    Manually create a standardized business event.

    Every event requires: event_type, severity, source, explanation, and related_entities.
    """
    rel_entities = [e.model_dump() for e in payload.related_entities]
    event = await EventEngineService.create_event(
        db=db,
        event_type=payload.event_type,
        severity=payload.severity,
        source=payload.source,
        explanation=payload.explanation,
        description=payload.description,
        related_entities=rel_entities,
        metadata=payload.metadata_json,
    )
    return _serialize_event(event)


# ---------------------------------------------------------------------------
# GET /events/ — List events with filtering
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[EventSchema], summary="List business events")
async def list_events(
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g. InventoryLow)"),
    severity: Optional[str] = Query(None, description="Filter by severity: INFO, WARNING, HIGH, CRITICAL"),
    source: Optional[str] = Query(None, description="Filter by source domain or agent"),
    entity_type: Optional[str] = Query(None, description="Filter by related entity type (e.g. product, customer)"),
    entity_id: Optional[int] = Query(None, description="Filter by related entity ID"),
    start_date: Optional[datetime] = Query(None, description="Filter events at or after this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter events at or before this timestamp"),
    limit: int = Query(50, ge=1, le=500, description="Max events to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a paginated, filtered list of business events.
    All filters are optional and can be combined.
    """
    events = await EventEngineService.get_events(
        db=db,
        event_type=event_type,
        severity=severity,
        source=source,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return [_serialize_event(ev) for ev in events]


# ---------------------------------------------------------------------------
# GET /events/stats/summary — Aggregate stats
# IMPORTANT: This route must be declared BEFORE /events/{event_id} to avoid
# FastAPI matching "summary" as an integer event_id.
# ---------------------------------------------------------------------------

@router.get("/stats/summary", response_model=EventSummaryStatsSchema, summary="Aggregate event summary")
async def get_event_summary(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregate event metrics:
    - Total event count
    - Counts grouped by severity
    - Counts grouped by event type
    - Recent critical/high events in last 24 hours
    - Timestamp of most recent event
    """
    stats = await EventEngineService.get_summary_stats(db=db)
    return stats


# ---------------------------------------------------------------------------
# GET /events/{event_id} — Single event by ID
# ---------------------------------------------------------------------------

@router.get("/{event_id}", response_model=EventSchema, summary="Get single business event")
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve the full details of a specific business event by its ID."""
    event = await EventEngineService.get_event_by_id(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event #{event_id} not found.")
    return _serialize_event(event)


# ---------------------------------------------------------------------------
# POST /events/evaluate — Trigger system-wide automated evaluation
# ---------------------------------------------------------------------------

@router.post("/evaluate", response_model=EventEvaluationResult, summary="Run system-wide event evaluation")
async def evaluate_system_events(db: AsyncSession = Depends(get_db)):
    """
    Scans the current system state and auto-generates business events for:
    - InventoryLow (products below reorder threshold)
    - InvoiceOverdue (unpaid invoices past due date)
    - CustomerChurnRisk (customers with high churn probability)
    - CashflowWarning (AP exceeds AR)

    Deduplicates against events emitted within the last hour to avoid spam.
    """
    events = await EventEngineService.evaluate_system_events(db=db)
    return {
        "status": "completed",
        "events_generated": len(events),
        "generated_events": [_serialize_event(ev) for ev in events],
        "evaluated_at": datetime.utcnow(),
    }
