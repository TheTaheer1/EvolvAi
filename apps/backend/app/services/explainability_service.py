from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.explainability import ExplainabilityRecord
from app.realtime.events import EXPLAINABILITY_CREATED
from app.services.realtime_service import RealtimeService
from app.utils.json import to_jsonable


def explainability_payload(record: ExplainabilityRecord) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": record.id,
            "workflow_id": record.workflow_id,
            "agent_execution_id": record.agent_execution_id,
            "title": record.title,
            "summary": record.summary,
            "reasoning_steps": record.reasoning_steps,
            "evidence": record.evidence,
            "assumptions": record.assumptions,
            "risks": record.risks,
            "confidence_score": record.confidence_score,
            "created_at": record.created_at,
        }
    )


class ExplainabilityService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()

    def create_explainability_record(
        self,
        db: Session,
        workflow_id: UUID | str,
        title: str,
        summary: str,
        reasoning_steps: list[str] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        assumptions: list[str] | None = None,
        risks: list[str] | None = None,
        confidence_score: float = 0,
        agent_execution_id: UUID | str | None = None,
        emit: bool = True,
    ) -> ExplainabilityRecord:
        record = ExplainabilityRecord(
            workflow_id=workflow_id,
            agent_execution_id=agent_execution_id,
            title=title,
            summary=summary,
            reasoning_steps=to_jsonable(reasoning_steps or []),
            evidence=to_jsonable(evidence or []),
            assumptions=to_jsonable(assumptions or []),
            risks=to_jsonable(risks or []),
            confidence_score=float(confidence_score or 0),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        if emit:
            self.realtime.emit_event(
                EXPLAINABILITY_CREATED,
                explainability_payload(record),
                workflow_id=str(record.workflow_id),
            )
        return record

    def list_by_workflow(self, db: Session, workflow_id: UUID | str) -> list[ExplainabilityRecord]:
        return list(
            db.scalars(
                select(ExplainabilityRecord)
                .where(ExplainabilityRecord.workflow_id == workflow_id)
                .order_by(ExplainabilityRecord.created_at.asc())
            ).all()
        )

    def build_agent_explanation(
        self,
        agent_name: str,
        output: dict[str, Any],
        scenario: dict[str, Any],
        company: dict[str, Any],
    ) -> dict[str, Any]:
        title_map = {
            "watcher_agent": "Why the market event matters",
            "research_agent": "Why the research evidence is relevant",
            "strategy_agent": "Why EvolvAI recommends action",
            "planner_agent": "Why this implementation plan is scoped safely",
            "execution_agent": "Why generated artifacts are preview-only",
            "verification_agent": "Why the artifacts are safe to preview",
            "pr_agent": "Why the PR remains a controlled preview",
        }
        return {
            "title": title_map.get(agent_name, f"{agent_name} explanation"),
            "summary": output.get("explainability", {}).get("summary")
            or f"{agent_name} used deterministic demo context for {company.get('name', 'AcmeFlow')}.",
            "reasoning_steps": output.get("explainability", {}).get("reasoning_steps")
            or [
                f"Read controlled scenario: {scenario.get('title')}.",
                f"Mapped the signal to {company.get('name', 'AcmeFlow')}'s product and business goals.",
                "Kept outputs deterministic for demo reliability.",
            ],
            "evidence": output.get("explainability", {}).get("evidence") or [],
            "assumptions": output.get("explainability", {}).get("assumptions")
            or [
                "AcmeFlow users value workflow automation.",
                "A small engineering team prefers incremental, reviewable releases.",
            ],
            "risks": output.get("explainability", {}).get("risks") or ["Human review is still required before production work."],
            "confidence_score": output.get("explainability", {}).get("confidence_score")
            or output.get("confidence_score")
            or 0.8,
        }
