from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.decision import Decision
from app.schemas.decision import DecisionRead
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.get("/decisions", response_model=list[DecisionRead])
def list_decisions(db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=100)):
    return list(db.scalars(select(Decision).order_by(Decision.created_at.desc()).limit(limit)).all())


@router.get("/decisions/{decision_id}", response_model=DecisionRead)
def get_decision(decision_id: UUID, db: Session = Depends(get_db)):
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.get("/workflows/{workflow_id}/decisions", response_model=list[DecisionRead])
def workflow_decisions(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return list(
        db.scalars(select(Decision).where(Decision.workflow_id == workflow_id).order_by(Decision.created_at.desc())).all()
    )
