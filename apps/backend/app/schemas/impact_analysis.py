from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImpactAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    business_impact: float
    technical_complexity: float
    urgency: float
    confidence: float
    risk_score: float
    opportunity_score: float
    final_priority: str
    impact_breakdown: dict[str, Any] = Field(default_factory=dict)
    recommendation: str | None = None
    created_at: datetime
