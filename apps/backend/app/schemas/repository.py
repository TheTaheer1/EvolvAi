from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepositoryAnalyzeRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=255)
    repo: str = Field(min_length=1, max_length=255)
    branch: str = Field(default="main", min_length=1, max_length=255)


class RepositoryFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    path: str
    file_type: str | None = None
    language: str | None = None
    size_bytes: int | None = None
    sha: str | None = None
    importance_score: float
    summary: str | None = None
    raw_metadata: dict[str, Any] | None = None
    created_at: datetime


class RepositoryAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner: str
    repo: str
    branch: str
    status: str
    repo_url: str | None = None
    default_branch: str | None = None
    detected_stack: list[str] = Field(default_factory=list)
    file_count: int
    analyzed_file_count: int
    summary: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class RepositoryAnalysisDetail(RepositoryAnalysisRead):
    files: list[RepositoryFileRead] = Field(default_factory=list)


class CodebaseContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID | None = None
    analysis_id: UUID
    relevant_files: list[dict[str, Any]] = Field(default_factory=list)
    architecture_summary: str | None = None
    implementation_hints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    created_at: datetime
