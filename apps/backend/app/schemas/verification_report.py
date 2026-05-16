from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VerificationReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    status: str
    passed: bool
    checks: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any] | str] = Field(default_factory=list)
    errors: list[dict[str, Any] | str] = Field(default_factory=list)
    summary: str | None = None
    created_at: datetime
