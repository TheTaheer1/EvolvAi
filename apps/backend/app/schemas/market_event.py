from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MarketEventCreate(BaseModel):
    source: str = "manual"
    event_type: str = "competitor_update"
    title: str
    summary: str | None = None
    url: str | None = None
    company_name: str | None = None
    competitor_name: str | None = None
    importance_score: float = Field(default=0, ge=0, le=1)
    raw_payload: dict[str, Any] | None = None


class MarketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    event_type: str
    title: str
    summary: str | None = None
    url: str | None = None
    company_name: str | None = None
    competitor_name: str | None = None
    importance_score: float
    raw_payload: dict[str, Any] | None = None
    detected_at: datetime
    created_at: datetime
