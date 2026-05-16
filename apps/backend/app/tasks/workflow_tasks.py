from sqlalchemy.exc import OperationalError

from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.orchestration.runner import WorkflowRunner
from app.realtime.events import DEMO_COMPLETED, WORKFLOW_COMPLETED, WORKFLOW_FAILED, WORKFLOW_STARTED
from app.services.log_service import LogService
from app.services.realtime_service import RealtimeService
from app.services.workflow_service import TERMINAL_STATUSES, WorkflowService, workflow_payload
from app.tasks.celery_app import celery_app


@celery_app.task(
    name="app.tasks.workflow_tasks.run_workflow",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
    queue="workflows",
)
def run_workflow(self, workflow_id: str) -> dict:
    db = SessionLocal()
    workflow_service = WorkflowService()
    log_service = LogService()
    realtime = RealtimeService()
    try:
        workflow = db.get(Workflow, workflow_id)
        if not workflow:
            return {"status": "missing", "workflow_id": workflow_id}
        if workflow.status in TERMINAL_STATUSES:
            return {"status": "skipped", "workflow_id": workflow_id, "reason": workflow.status}

        workflow = workflow_service.mark_running(db, workflow)
        log_service.create_log(db, "INFO", "Workflow started", workflow_id=workflow.id)
        realtime.emit_event(WORKFLOW_STARTED, workflow_payload(workflow), workflow_id=str(workflow.id))

        state = WorkflowRunner().run(db, workflow)

        decision_data = state.get("decision") or {}
        if not decision_data.get("should_act", True):
            workflow = workflow_service.mark_no_action_needed(db, workflow, "Strategy decided no action is needed.")
            realtime.emit_event(WORKFLOW_COMPLETED, workflow_payload(workflow), workflow_id=str(workflow.id))
            return {"status": workflow.status, "workflow_id": str(workflow.id)}

        is_live_event = bool((workflow.input_payload or {}).get("live_event"))
        summary = (
            "Live event workflow completed with explainability, impact analysis, safe artifacts, verification, and PR preview."
            if is_live_event
            else "Controlled demo workflow completed with explainability, impact analysis, safe artifacts, verification, and PR preview."
        )
        workflow = workflow_service.mark_completed(db, workflow, summary)
        log_service.create_log(db, "INFO", "Workflow completed", workflow_id=workflow.id)
        realtime.emit_event(WORKFLOW_COMPLETED, workflow_payload(workflow), workflow_id=str(workflow.id))
        if not is_live_event:
            realtime.emit_event(
                DEMO_COMPLETED,
                {
                    **workflow_payload(workflow),
                    "message": "Controlled demo workflow completed successfully",
                },
                workflow_id=str(workflow.id),
            )
        return {"status": workflow.status, "workflow_id": str(workflow.id)}
    except OperationalError as exc:
        db.rollback()
        raise self.retry(exc=exc)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        workflow = db.get(Workflow, workflow_id)
        if workflow:
            workflow_service.mark_failed(db, workflow, str(exc))
            log_service.create_log(db, "ERROR", "Workflow failed", workflow_id=workflow.id, context={"error": str(exc)})
            realtime.emit_event(WORKFLOW_FAILED, workflow_payload(workflow), workflow_id=str(workflow.id))
        raise
    finally:
        db.close()
