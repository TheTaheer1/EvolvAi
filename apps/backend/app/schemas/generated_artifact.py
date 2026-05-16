from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class GeneratedArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    artifact_type: str
    file_path: str
    title: str
    description: str | None = None
    content: str
    language: str | None = None
    status: str
    artifact_metadata: dict[str, Any] | None = Field(default=None, exclude=True)
    created_at: datetime

    @computed_field
    @property
    def metadata(self) -> dict[str, Any] | None:
        return self.artifact_metadata
