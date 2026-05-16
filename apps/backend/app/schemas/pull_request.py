from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PullRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    repo_owner: str | None = None
    repo_name: str | None = None
    branch_name: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    status: str
    title: str
    description: str | None = None
    changed_files: list[dict[str, Any]] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
