from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.market_event import MarketEventRead


class ExternalEventSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_key: str
    source_type: str
    display_name: str
    enabled: bool
    config: dict[str, Any] | None = None
    last_sync_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class ExternalEventIngestionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_key: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    events_found: int
    events_created: int
    events_skipped: int
    error_message: str | None = None
    raw_summary: dict[str, Any] | None = None
    created_at: datetime


class ExternalEventRawRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    external_id: str | None = None
    title: str
    url: str | None = None
    raw_payload: dict[str, Any]
    normalized_market_event_id: UUID | None = None
    content_hash: str
    created_at: datetime


class LiveEventIngestRequest(BaseModel):
    query: str = "AI SaaS automation stars:>500"
    max_results: int = Field(default=10, ge=1, le=25)
    trigger_workflows: bool = False


class LiveEventIngestResponse(BaseModel):
    run_id: UUID
    source: str = "github"
    status: str
    events_found: int
    events_created: int
    events_skipped: int
    market_events: list[MarketEventRead] = Field(default_factory=list)
    run: ExternalEventIngestionRunRead
    source_config: ExternalEventSourceRead | None = None
    events: list[MarketEventRead] = Field(default_factory=list)
    raw_events: list[ExternalEventRawRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    workflows_triggered: list[UUID] = Field(default_factory=list)
