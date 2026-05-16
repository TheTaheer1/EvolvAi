from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.log import LogRead
from app.services.log_service import LogService
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.get("/logs", response_model=list[LogRead])
def list_logs(db: Session = Depends(get_db), limit: int = Query(default=100, ge=1, le=500)):
    return LogService().list_logs(db, limit=limit)


@router.get("/workflows/{workflow_id}/logs", response_model=list[LogRead])
def workflow_logs(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return LogService().list_logs(db, workflow_id=workflow_id, limit=500)
