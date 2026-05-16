from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DemoScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scenario_key: str
    title: str
    description: str | None = None
    event_source: str
    event_type: str
    market_event: dict[str, Any]
    research_evidence: list[dict[str, Any]] = Field(default_factory=list)
    expected_recommendation: str | None = None
    default_impact_score: float
    default_complexity_score: float
    default_urgency_score: float
    tags: list[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DemoTriggerRequest(BaseModel):
    company_profile_id: UUID | None = None
    demo_speed: str = "normal"
