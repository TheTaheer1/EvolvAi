from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import verify_github_signature
from app.realtime.events import WORKFLOW_CREATED, WORKFLOW_QUEUED
from app.services.event_service import EventService
from app.services.log_service import LogService
from app.services.realtime_service import RealtimeService
from app.services.workflow_service import WorkflowService, workflow_payload
from app.tasks.webhook_tasks import process_github_webhook, process_market_event
from app.tasks.workflow_tasks import run_workflow

router = APIRouter()


def enqueue_workflow(workflow_id: str) -> None:
    run_workflow.apply_async(args=[workflow_id], queue="workflows")


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    body = await request.body()
    if not verify_github_signature(settings.GITHUB_WEBHOOK_SECRET, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid GitHub signature")
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="GitHub webhook payload must be an object")
    LogService().create_log(db, "INFO", "GitHub webhook received", context={"action": payload.get("action")})
    try:
        process_github_webhook.apply_async(args=[payload], queue="webhooks")
    except Exception as exc:  # noqa: BLE001
        LogService().create_log(db, "ERROR", "GitHub webhook queue unavailable", context={"error": str(exc)})
    return {"status": "accepted"}


@router.post("/market-event")
def market_event_webhook(payload: dict, db: Session = Depends(get_db)):
    title = payload.get("title") or "Competitor launched AI-powered roadmap automation"
    event = EventService().create_market_event(
        db,
        {
            "source": payload.get("source", "webhook"),
            "event_type": payload.get("event_type", "competitor_update"),
            "title": title,
            "summary": payload.get("summary", "Market event accepted by EvolvAI webhook."),
            "importance_score": payload.get("importance_score", 0.82),
            "raw_payload": payload,
        },
    )
    workflow = WorkflowService().create_workflow(
        db,
        trigger_type="market_event",
        source="webhook",
        payload={"event_id": str(event.id), "event": event.title, "company": payload.get("company", "Demo SaaS")},
    )
    LogService().create_log(db, "INFO", "Workflow queued from market webhook", workflow_id=workflow.id)
    realtime = RealtimeService()
    realtime.emit_event(WORKFLOW_CREATED, workflow_payload(workflow), workflow_id=str(workflow.id))
    realtime.emit_event(WORKFLOW_QUEUED, workflow_payload(workflow), workflow_id=str(workflow.id))
    try:
        process_market_event.apply_async(args=[payload], queue="webhooks")
        enqueue_workflow(str(workflow.id))
    except Exception as exc:  # noqa: BLE001
        LogService().create_log(db, "ERROR", "Market webhook queue unavailable", workflow_id=workflow.id, context={"error": str(exc)})
    return {"status": "accepted", "market_event_id": str(event.id), "workflow_id": str(workflow.id)}


@router.post("/demo-trigger")
def demo_trigger(db: Session = Depends(get_db)):
    payload = {
        "source": "demo",
        "event_type": "competitor_update",
        "title": "Competitor launched AI-powered roadmap automation",
        "summary": "Competitor activity suggests increased demand for automated SaaS planning workflows.",
        "company": "Demo SaaS",
        "importance_score": 0.82,
    }
    event = EventService().create_market_event(db, payload)
    workflow = WorkflowService().create_workflow(
        db,
        trigger_type="manual",
        source="demo-trigger",
        payload={
            "company": "Demo SaaS",
            "event": event.title,
            "event_id": str(event.id),
        },
    )
    LogService().create_log(db, "INFO", "Demo workflow queued", workflow_id=workflow.id, context=payload)
    realtime = RealtimeService()
    realtime.emit_event(WORKFLOW_CREATED, workflow_payload(workflow), workflow_id=str(workflow.id))
    realtime.emit_event(WORKFLOW_QUEUED, workflow_payload(workflow), workflow_id=str(workflow.id))
    try:
        enqueue_workflow(str(workflow.id))
    except Exception as exc:  # noqa: BLE001
        LogService().create_log(db, "ERROR", "Demo workflow queue unavailable", workflow_id=workflow.id, context={"error": str(exc)})
    return {"status": "queued", "market_event_id": str(event.id), "workflow_id": str(workflow.id)}
