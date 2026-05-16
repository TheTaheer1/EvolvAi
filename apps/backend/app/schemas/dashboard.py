from typing import Any

from pydantic import BaseModel, Field

from app.schemas.decision import DecisionRead
from app.schemas.log import LogRead
from app.schemas.market_event import MarketEventRead
from app.schemas.pull_request import PullRequestRead
from app.schemas.workflow import WorkflowRead


class DashboardSummary(BaseModel):
    active_workflows: int
    completed_workflows: int
    failed_workflows: int
    market_events: int
    decisions: int
    pull_requests: int


class DashboardActivity(BaseModel):
    workflows: list[WorkflowRead] = Field(default_factory=list)
    logs: list[LogRead] = Field(default_factory=list)
    decisions: list[DecisionRead] = Field(default_factory=list)
    pull_requests: list[PullRequestRead] = Field(default_factory=list)


class DashboardLiveState(DashboardActivity):
    summary: DashboardSummary
    market_events: list[MarketEventRead] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
