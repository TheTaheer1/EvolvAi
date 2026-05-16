from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.log import Log
from app.realtime.events import LOG_CREATED
from app.services.realtime_service import RealtimeService
from app.utils.json import to_jsonable


class LogService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()

    def create_log(
        self,
        db: Session,
        level: str,
        message: str,
        workflow_id: UUID | str | None = None,
        agent_execution_id: UUID | str | None = None,
        context: dict[str, Any] | None = None,
        emit: bool = True,
    ) -> Log:
        log = Log(
            workflow_id=workflow_id,
            agent_execution_id=agent_execution_id,
            level=level.upper(),
            message=message,
            context=to_jsonable(context or {}),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        if emit:
            self.realtime.emit_event(
                LOG_CREATED,
                {
                    "id": str(log.id),
                    "workflow_id": str(log.workflow_id) if log.workflow_id else None,
                    "agent_execution_id": str(log.agent_execution_id) if log.agent_execution_id else None,
                    "level": log.level,
                    "message": log.message,
                    "context": log.context,
                    "created_at": log.created_at,
                },
                workflow_id=str(log.workflow_id) if log.workflow_id else None,
            )
        return log

    def list_logs(
        self, db: Session, workflow_id: UUID | str | None = None, limit: int = 100
    ) -> list[Log]:
        stmt = select(Log).order_by(Log.created_at.desc()).limit(min(limit, 500))
        if workflow_id:
            stmt = select(Log).where(Log.workflow_id == workflow_id).order_by(Log.created_at.asc()).limit(min(limit, 500))
        return list(db.scalars(stmt).all())
