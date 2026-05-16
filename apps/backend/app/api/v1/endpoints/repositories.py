from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.repository import (
    CodebaseContextRead,
    RepositoryAnalysisDetail,
    RepositoryAnalysisRead,
    RepositoryAnalyzeRequest,
)
from app.services.codebase_context_service import CodebaseContextService
from app.services.repository_analysis_service import RepositoryAnalysisService

router = APIRouter(prefix="/repositories")


@router.post("/analyze", response_model=RepositoryAnalysisDetail)
def analyze_repository(request: RepositoryAnalyzeRequest, db: Session = Depends(get_db)):
    return RepositoryAnalysisService().analyze_repository(
        db,
        owner=request.owner,
        repo=request.repo,
        branch=request.branch,
    )


@router.get("/analyses", response_model=list[RepositoryAnalysisRead])
def list_repository_analyses(
    db: Session = Depends(get_db),
    limit: int = Query(default=25, ge=1, le=100),
):
    return RepositoryAnalysisService().list_analyses(db, limit=limit)


@router.get("/analyses/{analysis_id}", response_model=RepositoryAnalysisDetail)
def get_repository_analysis(analysis_id: UUID, db: Session = Depends(get_db)):
    return RepositoryAnalysisService().require_analysis(db, analysis_id, detail=True)


@router.post("/analyses/{analysis_id}/attach-to-workflow/{workflow_id}", response_model=CodebaseContextRead)
def attach_repository_analysis_to_workflow(
    analysis_id: UUID,
    workflow_id: UUID,
    db: Session = Depends(get_db),
):
    return CodebaseContextService().attach_to_workflow(db, analysis_id=analysis_id, workflow_id=workflow_id)
