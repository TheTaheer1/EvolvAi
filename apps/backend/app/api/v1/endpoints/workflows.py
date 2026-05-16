from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.realtime.events import WORKFLOW_CANCELLED, WORKFLOW_CREATED, WORKFLOW_QUEUED
from app.schemas.workflow import TimelineItem, WorkflowDetail, WorkflowRead, WorkflowTriggerRequest
from app.schemas.repository import CodebaseContextRead
from app.services.event_service import EventService
from app.schemas.explainability import ExplainabilityRecordRead
from app.schemas.generated_artifact import GeneratedArtifactRead
from app.schemas.impact_analysis import ImpactAnalysisRead
from app.schemas.pull_request import PullRequestRead
from app.schemas.verification_report import VerificationReportRead
from app.services.explainability_service import ExplainabilityService
from app.services.generated_artifact_service import GeneratedArtifactService
from app.services.impact_analysis_service import ImpactAnalysisService
from app.services.log_service import LogService
from app.services.pr_preview_service import PRPreviewService
from app.services.realtime_service import RealtimeService
from app.services.verification_service import VerificationService
from app.services.workflow_service import WorkflowService, workflow_payload
from app.services.codebase_context_service import CodebaseContextService
from app.tasks.workflow_tasks import run_workflow

router = APIRouter()


@router.post("/trigger", response_model=WorkflowRead)
def trigger_workflow(request: WorkflowTriggerRequest, db: Session = Depends(get_db)):
    workflow_service = WorkflowService()
    realtime = RealtimeService()
    log_service = LogService(realtime)
    payload = dict(request.payload or {})
    if payload.get("event"):
        market_event = EventService(realtime).create_market_event(
            db,
            {
                "source": request.source,
                "event_type": "manual_trigger",
                "title": str(payload.get("event")),
                "summary": "Competitor activity suggests increased demand for automated SaaS planning workflows.",
                "company_name": payload.get("company"),
                "importance_score": 0.82,
                "raw_payload": payload,
            },
        )
        payload["event_id"] = str(market_event.id)
    workflow = workflow_service.create_workflow(
        db,
        trigger_type=request.trigger_type,
        source=request.source,
        payload=payload,
        company_context={"company": payload.get("company", "Demo SaaS")},
    )
    log_service.create_log(db, "INFO", "Workflow queued", workflow_id=workflow.id, context=payload)
    realtime_payload = workflow_payload(workflow)
    realtime.emit_event(WORKFLOW_CREATED, realtime_payload, workflow_id=str(workflow.id))
    realtime.emit_event(WORKFLOW_QUEUED, realtime_payload, workflow_id=str(workflow.id))
    try:
        run_workflow.apply_async(args=[str(workflow.id)], queue="workflows")
    except Exception as exc:  # noqa: BLE001
        log_service.create_log(
            db,
            "ERROR",
            "Workflow queue unavailable",
            workflow_id=workflow.id,
            context={"error": str(exc)},
        )
    return workflow


@router.get("", response_model=list[WorkflowRead])
def list_workflows(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
):
    return WorkflowService().list_workflows(db, status=status, limit=limit)


@router.get("/{workflow_id}", response_model=WorkflowDetail)
def get_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    return WorkflowService().require_workflow(db, workflow_id, detail=True)


@router.post("/{workflow_id}/cancel", response_model=WorkflowRead)
def cancel_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    service = WorkflowService()
    workflow = service.require_workflow(db, workflow_id)
    workflow = service.mark_cancelled(db, workflow)
    LogService().create_log(db, "INFO", "Workflow cancelled", workflow_id=workflow.id)
    RealtimeService().emit_event(WORKFLOW_CANCELLED, workflow_payload(workflow), workflow_id=str(workflow.id))
    return workflow


@router.get("/{workflow_id}/timeline", response_model=list[TimelineItem])
def workflow_timeline(workflow_id: UUID, db: Session = Depends(get_db)):
    return WorkflowService().create_timeline(db, workflow_id)


@router.get("/{workflow_id}/codebase-context", response_model=CodebaseContextRead | None)
def workflow_codebase_context(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return CodebaseContextService().get_by_workflow(db, workflow_id)


@router.get("/{workflow_id}/explainability", response_model=list[ExplainabilityRecordRead])
def workflow_explainability(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return ExplainabilityService().list_by_workflow(db, workflow_id)


@router.get("/{workflow_id}/impact-analysis", response_model=ImpactAnalysisRead | None)
def workflow_impact_analysis(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return ImpactAnalysisService().get_by_workflow(db, workflow_id)


@router.get("/{workflow_id}/generated-artifacts", response_model=list[GeneratedArtifactRead])
def workflow_generated_artifacts(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return GeneratedArtifactService().list_by_workflow(db, workflow_id)


@router.get("/{workflow_id}/verification-report", response_model=VerificationReportRead | None)
def workflow_verification_report(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return VerificationService().get_by_workflow(db, workflow_id)


@router.get("/{workflow_id}/pr-preview", response_model=PullRequestRead | None)
def workflow_pr_preview(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return PRPreviewService().get_pr_preview_by_workflow(db, workflow_id)


@router.post("/{workflow_id}/pr-preview/regenerate", response_model=PullRequestRead)
def regenerate_workflow_pr_preview(workflow_id: UUID, db: Session = Depends(get_db)):
    workflow = WorkflowService().require_workflow(db, workflow_id)
    payload = workflow.input_payload or {}
    artifacts = GeneratedArtifactService().list_by_workflow(db, workflow_id)
    verification = VerificationService().get_by_workflow(db, workflow_id)
    impact = ImpactAnalysisService().get_by_workflow(db, workflow_id)
    return PRPreviewService().create_pr_preview(
        db,
        workflow_id,
        scenario=payload.get("scenario") or {},
        company=payload.get("company_profile") or {},
        artifacts=artifacts,
        verification=verification,
        impact=impact,
        plan={},
    )
