from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID | None = None
    agent_execution_id: UUID | None = None
    level: str
    message: str
    context: dict[str, Any] | None = None
    created_at: datetime
