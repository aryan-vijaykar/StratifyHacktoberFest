"""
Event Engine Schemas — Pydantic V2 models for event processing and REST API validation.

Every event contains:
  - severity
  - timestamp
  - source
  - related_entities
  - explanation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RelatedEntitySchema(BaseModel):
    entity_type: str = Field(..., description="Entity type, e.g. customer, product, supplier, invoice")
    entity_id: Optional[int] = Field(None, description="Entity primary key ID")
    name: Optional[str] = Field(None, description="Optional entity display name or reference")


class EventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=100, description="Business event type (e.g. InventoryLow, CashflowWarning)")
    severity: str = Field(default="INFO", description="Severity level: INFO, WARNING, HIGH, CRITICAL")
    source: str = Field(default="system", description="Event generator source domain/agent")
    explanation: str = Field(..., min_length=1, max_length=2000, description="Detailed explanation of the event trigger and business context")
    description: Optional[str] = Field(None, max_length=2000, description="Brief summary description (defaults to explanation)")
    related_entities: List[RelatedEntitySchema] = Field(default_factory=list, description="List of related business entities")
    metadata_json: Optional[Dict[str, Any]] = Field(default=None, description="Additional contextual JSON metadata")


class EventSchema(BaseModel):
    id: int
    event_type: str
    severity: str
    timestamp: datetime
    source: str
    explanation: str
    description: str
    related_entities: List[Dict[str, Any]]
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class EventFilterParams(BaseModel):
    event_type: Optional[str] = None
    severity: Optional[str] = None
    source: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class EventSummaryStatsSchema(BaseModel):
    total_events: int
    severity_counts: Dict[str, int]
    event_type_counts: Dict[str, int]
    recent_critical_count: int
    last_event_timestamp: Optional[datetime] = None


class EventEvaluationResult(BaseModel):
    status: str
    events_generated: int
    generated_events: List[EventSchema]
    evaluated_at: datetime
