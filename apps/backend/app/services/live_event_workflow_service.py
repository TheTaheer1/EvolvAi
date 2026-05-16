import re
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.market_event import MarketEvent
from app.realtime.events import LIVE_EVENT_WORKFLOW_TRIGGERED, WORKFLOW_CREATED, WORKFLOW_QUEUED
from app.services.company_profile_service import CompanyProfileService, company_profile_payload
from app.services.event_service import EventService
from app.services.log_service import LogService
from app.services.realtime_service import RealtimeService
from app.services.workflow_service import WorkflowService, workflow_payload


class LiveEventWorkflowService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()
        self.events = EventService(self.realtime)
        self.workflows = WorkflowService()
        self.company_profiles = CompanyProfileService()
        self.logs = LogService(self.realtime)

    def trigger_from_market_event(
        self,
        db: Session,
        market_event_id: UUID | str,
        demo_speed: str = "fast",
    ):
        event = self.events.get_market_event(db, market_event_id)
        profile = self.company_profiles.get_default_company_profile(db)
        if not profile:
            profile = self.company_profiles.create_or_update_demo_profile(db)
        scenario = self._scenario_from_market_event(event)
        payload = {
            "demo_mode": False,
            "demo_speed": demo_speed,
            "live_event": True,
            "source": event.source,
            "market_event": {
                "id": str(event.id),
                "title": event.title,
                "source": event.source,
                "event_type": event.event_type,
                "summary": event.summary,
                "url": event.url,
                "importance_score": event.importance_score,
                "detected_at": str(event.detected_at),
                "raw_payload": event.raw_payload,
            },
            "scenario_key": scenario["scenario_key"],
            "scenario": scenario,
            "company_profile_id": str(profile.id),
            "company_profile": company_profile_payload(profile),
            "market_event_id": str(event.id),
            "safety": {
                "real_pr_enabled": settings.ALLOW_REAL_GITHUB_PR,
                "generated_files_scope": "apps/backend/generated_runs/{workflow_id}/",
                "external_apis_required": False,
                "live_ai_optional": True,
            },
        }
        workflow = self.workflows.create_workflow(
            db,
            trigger_type="live_market_event",
            source=f"{event.source}:{event.id}",
            payload=payload,
            company_context=company_profile_payload(profile),
        )
        raw_payload = dict(event.raw_payload or {})
        raw_payload["workflow_id"] = str(workflow.id)
        event.raw_payload = raw_payload
        db.commit()
        self.logs.create_log(
            db,
            "INFO",
            f"Workflow queued from live event: {event.title}",
            workflow_id=workflow.id,
            context={"market_event_id": str(event.id), "source": event.source},
        )
        realtime_payload = workflow_payload(workflow)
        self.realtime.emit_event(WORKFLOW_CREATED, realtime_payload, workflow_id=str(workflow.id))
        self.realtime.emit_event(WORKFLOW_QUEUED, realtime_payload, workflow_id=str(workflow.id))
        self.realtime.emit_event(
            LIVE_EVENT_WORKFLOW_TRIGGERED,
            {
                "id": str(event.id),
                "workflow_id": str(workflow.id),
                "source": event.source,
                "title": event.title,
                "message": "Triggered workflow from live market event",
            },
            workflow_id=str(workflow.id),
        )
        try:
            from app.tasks.workflow_tasks import run_workflow

            run_workflow.apply_async(args=[str(workflow.id)], queue="workflows")
        except Exception as exc:  # noqa: BLE001
            self.logs.create_log(
                db,
                "ERROR",
                "Workflow queue unavailable",
                workflow_id=workflow.id,
                context={"error": str(exc)},
            )
            raise HTTPException(status_code=503, detail="Workflow queue unavailable. Is Redis running?") from exc
        return workflow

    def _scenario_from_market_event(self, event: MarketEvent) -> dict[str, Any]:
        slug = self._slugify(event.title or event.event_type)
        importance = float(event.importance_score or 0.65)
        recommendation = self._recommendation_from_event(event)
        return {
            "scenario_key": f"live-{event.source}-{str(event.id)[:8]}",
            "title": event.title,
            "description": event.summary,
            "event_source": event.source,
            "event_type": event.event_type,
            "market_event": {
                "title": event.title,
                "source": event.source,
                "summary": event.summary,
                "importance_score": importance,
                "why_it_matters": "A real external signal suggests customer expectations and competitor capabilities may be moving.",
                "recommended_evolution": recommendation,
                "url": event.url,
            },
            "research_evidence": [
                {
                    "source": event.source,
                    "title": event.title,
                    "summary": event.summary or "External event detected by EvolvAI live ingestion.",
                    "relevance": "high" if importance >= settings.LIVE_EVENT_MIN_IMPORTANCE_SCORE else "medium",
                    "url": event.url,
                }
            ],
            "expected_recommendation": recommendation,
            "proposed_files": [
                {"file_path": f"docs/features/{slug}.md", "artifact_type": "documentation"},
                {"file_path": f"demo/generated/{slug}-plan.json", "artifact_type": "config"},
                {"file_path": f"demo/generated/{slug}-preview.tsx", "artifact_type": "component"},
            ],
            "scores": {
                "business_impact": min(0.95, 0.55 + importance * 0.35),
                "technical_complexity": 0.62,
                "urgency": importance,
                "confidence": 0.72,
                "risk_score": 0.42,
            },
            "tags": ["live-event", event.source, event.event_type],
            "live_event": True,
            "external_event_url": event.url,
        }

    def _recommendation_from_event(self, event: MarketEvent) -> str:
        title = (event.title or "").lower()
        if "rag" in title or "retrieval" in title:
            return "Evaluate a knowledge-aware AI assistant foundation"
        if "meeting" in title or "summary" in title:
            return "Evaluate AI meeting insight capabilities"
        if "audit" in title or "compliance" in title or "security" in title:
            return "Evaluate AI audit trail and compliance controls"
        if "automation" in title or "agent" in title:
            return "Evaluate autonomous workflow recommendations"
        return "Evaluate market-informed AI product evolution"

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
        slug = re.sub(r"-+", "-", slug)
        return (slug[:48] or "live-market-event").strip("-")
