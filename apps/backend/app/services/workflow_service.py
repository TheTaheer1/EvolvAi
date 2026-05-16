from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import WORKFLOW_STATUSES
from app.models.agent_execution import AgentExecution
from app.models.decision import Decision
from app.models.log import Log
from app.models.pull_request import PullRequestHistory
from app.models.workflow import Workflow
from app.utils.json import to_jsonable
from app.utils.time import utc_now


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "no_action_needed"}


def workflow_payload(workflow: Workflow) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": workflow.id,
            "trigger_type": workflow.trigger_type,
            "trigger_source": workflow.trigger_source,
            "status": workflow.status,
            "current_agent": workflow.current_agent,
            "company_context": workflow.company_context,
            "input_payload": workflow.input_payload,
            "final_summary": workflow.final_summary,
            "error_message": workflow.error_message,
            "started_at": workflow.started_at,
            "completed_at": workflow.completed_at,
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
        }
    )


class WorkflowService:
    def create_workflow(
        self,
        db: Session,
        trigger_type: str,
        source: str,
        payload: dict[str, Any] | None = None,
        company_context: dict[str, Any] | None = None,
    ) -> Workflow:
        workflow = Workflow(
            trigger_type=trigger_type,
            trigger_source=source,
            status="queued",
            company_context=company_context,
            input_payload=to_jsonable(payload or {}),
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return workflow

    def get_workflow(self, db: Session, workflow_id: UUID | str, detail: bool = False) -> Workflow | None:
        stmt = select(Workflow).where(Workflow.id == workflow_id)
        if detail:
            stmt = stmt.options(
                selectinload(Workflow.agent_executions),
                selectinload(Workflow.logs),
                selectinload(Workflow.decisions),
                selectinload(Workflow.pull_requests),
            )
        return db.scalars(stmt).first()

    def require_workflow(self, db: Session, workflow_id: UUID | str, detail: bool = False) -> Workflow:
        workflow = self.get_workflow(db, workflow_id, detail=detail)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow

    def list_workflows(
        self, db: Session, status: str | None = None, limit: int = 20
    ) -> list[Workflow]:
        if status and status not in WORKFLOW_STATUSES:
            raise HTTPException(status_code=400, detail=f"Unknown workflow status: {status}")
        stmt = select(Workflow).order_by(Workflow.created_at.desc()).limit(min(limit, 100))
        if status:
            stmt = select(Workflow).where(Workflow.status == status).order_by(Workflow.created_at.desc()).limit(min(limit, 100))
        return list(db.scalars(stmt).all())

    def mark_queued(self, db: Session, workflow: Workflow) -> Workflow:
        workflow.status = "queued"
        workflow.updated_at = utc_now()
        db.commit()
        db.refresh(workflow)
        return workflow

    def mark_running(self, db: Session, workflow: Workflow) -> Workflow:
        workflow.status = "running"
        workflow.started_at = workflow.started_at or utc_now()
        workflow.updated_at = utc_now()
        db.commit()
        db.refresh(workflow)
        return workflow

    def update_current_agent(self, db: Session, workflow: Workflow, agent_name: str | None) -> Workflow:
        workflow.current_agent = agent_name
        workflow.updated_at = utc_now()
        db.commit()
        db.refresh(workflow)
        return workflow

    def mark_completed(self, db: Session, workflow: Workflow, summary: str | None = None) -> Workflow:
        workflow.status = "completed"
        workflow.current_agent = None
        workflow.final_summary = summary
        workflow.completed_at = utc_now()
        workflow.updated_at = utc_now()
        db.commit()
        db.refresh(workflow)
        return workflow

    def mark_no_action_needed(self, db: Session, workflow: Workflow, summary: str | None = None) -> Workflow:
        workflow.status = "no_action_needed"
        workflow.current_agent = None
        workflow.final_summary = summary
        workflow.completed_at = utc_now()
        workflow.updated_at = utc_now()
        db.commit()
        db.refresh(workflow)
        return workflow

    def mark_failed(self, db: Session, workflow: Workflow, error_message: str) -> Workflow:
        workflow.status = "failed"
        workflow.current_agent = None
        workflow.error_message = error_message
        workflow.completed_at = utc_now()
        workflow.updated_at = utc_now()
        db.commit()
        db.refresh(workflow)
        return workflow

    def mark_cancelled(self, db: Session, workflow: Workflow) -> Workflow:
        if workflow.status in {"completed", "failed"}:
            return workflow
        workflow.status = "cancelled"
        workflow.current_agent = None
        workflow.completed_at = utc_now()
        workflow.updated_at = utc_now()
        db.commit()
        db.refresh(workflow)
        return workflow

    def create_timeline(self, db: Session, workflow_id: UUID | str) -> list[dict[str, Any]]:
        workflow = self.require_workflow(db, workflow_id)
        items: list[dict[str, Any]] = [
            {
                "id": f"workflow:{workflow.id}:created",
                "type": "workflow",
                "title": "Workflow created",
                "status": workflow.status,
                "timestamp": workflow.created_at,
                "payload": workflow_payload(workflow),
            }
        ]
        agents = db.scalars(
            select(AgentExecution)
            .where(AgentExecution.workflow_id == workflow_id)
            .order_by(AgentExecution.created_at.asc())
        ).all()
        decisions = db.scalars(
            select(Decision).where(Decision.workflow_id == workflow_id).order_by(Decision.created_at.asc())
        ).all()
        prs = db.scalars(
            select(PullRequestHistory)
            .where(PullRequestHistory.workflow_id == workflow_id)
            .order_by(PullRequestHistory.created_at.asc())
        ).all()
        logs = db.scalars(
            select(Log).where(Log.workflow_id == workflow_id).order_by(Log.created_at.asc())
        ).all()
        for agent in agents:
            items.append(
                {
                    "id": f"agent:{agent.id}",
                    "type": "agent",
                    "title": agent.agent_name,
                    "status": agent.status,
                    "timestamp": agent.started_at or agent.created_at,
                    "payload": to_jsonable({"agent_execution_id": agent.id, "duration_ms": agent.duration_ms}),
                }
            )
        for decision in decisions:
            items.append(
                {
                    "id": f"decision:{decision.id}",
                    "type": "decision",
                    "title": decision.title,
                    "status": "created",
                    "timestamp": decision.created_at,
                    "payload": to_jsonable({"impact_score": decision.impact_score}),
                }
            )
        for pr in prs:
            items.append(
                {
                    "id": f"pr:{pr.id}",
                    "type": "pull_request",
                    "title": pr.title,
                    "status": pr.status,
                    "timestamp": pr.created_at,
                    "payload": to_jsonable({"pr_url": pr.pr_url, "changed_files": pr.changed_files}),
                }
            )
        for log in logs:
            items.append(
                {
                    "id": f"log:{log.id}",
                    "type": "log",
                    "title": log.message,
                    "status": log.level.lower(),
                    "timestamp": log.created_at,
                    "payload": to_jsonable(log.context or {}),
                }
            )
        return sorted(items, key=lambda item: item["timestamp"])
