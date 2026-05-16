from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent_execution import AgentExecutionRead
from app.schemas.decision import DecisionRead
from app.schemas.log import LogRead
from app.schemas.pull_request import PullRequestRead


class WorkflowTriggerRequest(BaseModel):
    trigger_type: str = "manual"
    source: str = "dashboard"
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trigger_type: str
    trigger_source: str
    status: str
    current_agent: str | None = None
    company_context: dict[str, Any] | None = None
    input_payload: dict[str, Any]
    final_summary: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowDetail(WorkflowRead):
    agent_executions: list[AgentExecutionRead] = Field(default_factory=list)
    logs: list[LogRead] = Field(default_factory=list)
    decisions: list[DecisionRead] = Field(default_factory=list)
    pull_requests: list[PullRequestRead] = Field(default_factory=list)


class TimelineItem(BaseModel):
    id: str
    type: str
    title: str
    status: str | None = None
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
