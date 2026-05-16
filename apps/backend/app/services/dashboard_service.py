from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.decision import Decision
from app.models.generated_artifact import GeneratedArtifact
from app.models.impact_analysis import ImpactAnalysis
from app.models.log import Log
from app.models.market_event import MarketEvent
from app.models.pull_request import PullRequestHistory
from app.models.verification_report import VerificationReport
from app.models.workflow import Workflow
from app.services.company_profile_service import company_profile_payload
from app.services.demo_scenario_service import demo_scenario_payload
from app.services.demo_workflow_service import DemoWorkflowService
from app.services.generated_artifact_service import generated_artifact_payload
from app.services.impact_analysis_service import impact_analysis_payload
from app.services.pr_preview_service import pr_preview_payload
from app.services.verification_service import verification_report_payload
from app.services.workflow_service import workflow_payload


class DashboardService:
    def get_summary(self, db: Session) -> dict[str, int]:
        active = db.scalar(select(func.count()).select_from(Workflow).where(Workflow.status.in_(["queued", "running"]))) or 0
        completed = db.scalar(select(func.count()).select_from(Workflow).where(Workflow.status == "completed")) or 0
        failed = db.scalar(select(func.count()).select_from(Workflow).where(Workflow.status == "failed")) or 0
        market_events = db.scalar(select(func.count()).select_from(MarketEvent)) or 0
        decisions = db.scalar(select(func.count()).select_from(Decision)) or 0
        prs = db.scalar(select(func.count()).select_from(PullRequestHistory)) or 0
        return {
            "active_workflows": active,
            "completed_workflows": completed,
            "failed_workflows": failed,
            "market_events": market_events,
            "decisions": decisions,
            "pull_requests": prs,
        }

    def get_activity(self, db: Session) -> dict[str, list]:
        return {
            "workflows": list(db.scalars(select(Workflow).order_by(Workflow.created_at.desc()).limit(10)).all()),
            "logs": list(db.scalars(select(Log).order_by(Log.created_at.desc()).limit(50)).all()),
            "decisions": list(db.scalars(select(Decision).order_by(Decision.created_at.desc()).limit(10)).all()),
            "pull_requests": list(
                db.scalars(select(PullRequestHistory).order_by(PullRequestHistory.created_at.desc()).limit(10)).all()
            ),
        }

    def get_live_state(self, db: Session) -> dict:
        activity = self.get_activity(db)
        return {
            **activity,
            "summary": self.get_summary(db),
            "market_events": list(db.scalars(select(MarketEvent).order_by(MarketEvent.created_at.desc()).limit(25)).all()),
            "environment": {
                "app_env": settings.APP_ENV,
                "demo_safe_mode": not settings.ALLOW_REAL_GITHUB_PR,
                "real_prs_enabled": settings.ALLOW_REAL_GITHUB_PR,
                "code_execution_enabled": settings.ALLOW_CODE_EXECUTION,
                "external_writes_enabled": settings.ALLOW_EXTERNAL_WRITE_ACTIONS,
                "openai_configured": bool(settings.OPENAI_API_KEY),
                "live_ai_outputs_enabled": settings.USE_LIVE_AI_OUTPUTS,
                "github_configured": bool(settings.GITHUB_TOKEN),
                "live_external_events_enabled": settings.USE_LIVE_EXTERNAL_EVENTS,
                "github_ingestion_enabled": settings.GITHUB_INGESTION_ENABLED,
                "hn_ingestion_enabled": settings.HN_INGESTION_ENABLED,
                "hn_api_key_required": False,
                "tracing_enabled": settings.TRACING_ENABLED,
            },
        }

    def get_demo_state(self, db: Session) -> dict:
        profile, scenarios = DemoWorkflowService().ensure_demo_data_exists(db)
        latest_workflows = list(db.scalars(select(Workflow).order_by(Workflow.created_at.desc()).limit(10)).all())
        latest_workflow = latest_workflows[0] if latest_workflows else None
        latest_workflow_id = latest_workflow.id if latest_workflow else None
        latest_impact = (
            db.scalars(
                select(ImpactAnalysis)
                .where(ImpactAnalysis.workflow_id == latest_workflow_id)
                .order_by(ImpactAnalysis.created_at.desc())
                .limit(1)
            ).first()
            if latest_workflow_id
            else None
        )
        latest_pr = (
            db.scalars(
                select(PullRequestHistory)
                .where(PullRequestHistory.workflow_id == latest_workflow_id)
                .order_by(PullRequestHistory.created_at.desc())
                .limit(1)
            ).first()
            if latest_workflow_id
            else None
        )
        latest_verification = (
            db.scalars(
                select(VerificationReport)
                .where(VerificationReport.workflow_id == latest_workflow_id)
                .order_by(VerificationReport.created_at.desc())
                .limit(1)
            ).first()
            if latest_workflow_id
            else None
        )
        latest_artifacts = (
            list(
                db.scalars(
                    select(GeneratedArtifact)
                    .where(GeneratedArtifact.workflow_id == latest_workflow_id)
                    .order_by(GeneratedArtifact.created_at.asc())
                ).all()
            )
            if latest_workflow_id
            else []
        )
        return {
            "company_profile": company_profile_payload(profile),
            "scenarios": [demo_scenario_payload(scenario) for scenario in scenarios],
            "latest_workflows": [workflow_payload(workflow) for workflow in latest_workflows],
            "latest_live_events": [
                {
                    "id": str(event.id),
                    "source": event.source,
                    "event_type": event.event_type,
                    "title": event.title,
                    "summary": event.summary,
                    "url": event.url,
                    "importance_score": event.importance_score,
                    "created_at": event.created_at,
                }
                for event in db.scalars(
                    select(MarketEvent)
                    .where(MarketEvent.source != "controlled_demo")
                    .order_by(MarketEvent.created_at.desc())
                    .limit(5)
                ).all()
            ],
            "metrics": self.get_summary(db),
            "latest_impact_analysis": impact_analysis_payload(latest_impact) if latest_impact else None,
            "latest_pr_preview": pr_preview_payload(latest_pr) if latest_pr else None,
            "latest_verification_report": verification_report_payload(latest_verification) if latest_verification else None,
            "latest_generated_artifacts": [generated_artifact_payload(artifact) for artifact in latest_artifacts],
            "environment": {
                "demo_mode": True,
                "real_prs_enabled": settings.ALLOW_REAL_GITHUB_PR,
                "generated_files_enabled": settings.ALLOW_GENERATED_FILES,
                "live_ai_outputs_enabled": settings.USE_LIVE_AI_OUTPUTS,
                "live_external_events_enabled": settings.USE_LIVE_EXTERNAL_EVENTS,
                "openai_configured": bool(settings.OPENAI_API_KEY),
                "github_configured": bool(settings.GITHUB_TOKEN),
                "github_ingestion_enabled": settings.GITHUB_INGESTION_ENABLED,
                "hn_ingestion_enabled": settings.HN_INGESTION_ENABLED,
                "hn_api_key_required": False,
            },
        }
