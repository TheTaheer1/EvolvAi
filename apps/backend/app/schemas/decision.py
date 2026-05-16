from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    decision_type: str
    title: str
    summary: str | None = None
    impact_score: float
    confidence_score: float
    recommended_action: str | None = None
    reasoning: dict[str, Any] | None = None
    created_at: datetime
