from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_execution import AgentExecution
from app.utils.json import to_jsonable
from app.utils.time import utc_now


def agent_payload(agent_execution: AgentExecution) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": agent_execution.id,
            "workflow_id": agent_execution.workflow_id,
            "agent_name": agent_execution.agent_name,
            "status": agent_execution.status,
            "input_state": agent_execution.input_state,
            "output_state": agent_execution.output_state,
            "error_message": agent_execution.error_message,
            "started_at": agent_execution.started_at,
            "completed_at": agent_execution.completed_at,
            "duration_ms": agent_execution.duration_ms,
            "created_at": agent_execution.created_at,
        }
    )


class AgentService:
    def create_agent_execution(
        self, db: Session, workflow_id: UUID | str, agent_name: str, input_state: dict[str, Any] | None
    ) -> AgentExecution:
        existing = self.get_agent_execution(db, workflow_id, agent_name)
        if existing:
            return existing
        execution = AgentExecution(
            workflow_id=workflow_id,
            agent_name=agent_name,
            status="pending",
            input_state=to_jsonable(input_state or {}),
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        return execution

    def get_agent_execution(
        self, db: Session, workflow_id: UUID | str, agent_name: str
    ) -> AgentExecution | None:
        return db.scalars(
            select(AgentExecution)
            .where(AgentExecution.workflow_id == workflow_id, AgentExecution.agent_name == agent_name)
            .order_by(AgentExecution.created_at.asc())
        ).first()

    def list_for_workflow(self, db: Session, workflow_id: UUID | str) -> list[AgentExecution]:
        return list(
            db.scalars(
                select(AgentExecution)
                .where(AgentExecution.workflow_id == workflow_id)
                .order_by(AgentExecution.created_at.asc())
            ).all()
        )

    def mark_agent_running(self, db: Session, execution: AgentExecution) -> AgentExecution:
        execution.status = "running"
        execution.started_at = execution.started_at or utc_now()
        db.commit()
        db.refresh(execution)
        return execution

    def mark_agent_completed(
        self, db: Session, execution: AgentExecution, output_state: dict[str, Any], duration_ms: int
    ) -> AgentExecution:
        execution.status = "completed"
        execution.output_state = to_jsonable(output_state)
        execution.duration_ms = duration_ms
        execution.completed_at = utc_now()
        db.commit()
        db.refresh(execution)
        return execution

    def mark_agent_failed(
        self, db: Session, execution: AgentExecution, error_message: str, duration_ms: int | None = None
    ) -> AgentExecution:
        execution.status = "failed"
        execution.error_message = error_message
        execution.duration_ms = duration_ms
        execution.completed_at = utc_now()
        db.commit()
        db.refresh(execution)
        return execution
