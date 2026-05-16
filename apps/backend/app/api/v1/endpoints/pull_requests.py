from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.pull_request import PullRequestHistory
from app.schemas.pull_request import PullRequestRead
from app.services.github_pr_service import GitHubPRService
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.get("/prs", response_model=list[PullRequestRead])
def list_prs(db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=100)):
    return list(db.scalars(select(PullRequestHistory).order_by(PullRequestHistory.created_at.desc()).limit(limit)).all())


@router.get("/prs/{pr_id}", response_model=PullRequestRead)
def get_pr(pr_id: UUID, db: Session = Depends(get_db)):
    pr = db.get(PullRequestHistory, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="PR history item not found")
    return pr


@router.get("/workflows/{workflow_id}/prs", response_model=list[PullRequestRead])
def workflow_prs(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return list(
        db.scalars(
            select(PullRequestHistory)
            .where(PullRequestHistory.workflow_id == workflow_id)
            .order_by(PullRequestHistory.created_at.desc())
        ).all()
    )


@router.post("/prs/{pr_id}/open-real-pr")
def open_real_pr(pr_id: UUID, db: Session = Depends(get_db)):
    pr = db.get(PullRequestHistory, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="PR history item not found")
    return GitHubPRService().create_draft_pr_from_workflow(db, pr.workflow_id)


@router.get("/workflows/{workflow_id}/pr-safety-check")
def workflow_pr_safety_check(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return GitHubPRService().pr_safety_check(db, workflow_id)


@router.post("/workflows/{workflow_id}/open-draft-pr", response_model=PullRequestRead)
def open_workflow_draft_pr(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return GitHubPRService().create_draft_pr_from_workflow(db, workflow_id)
