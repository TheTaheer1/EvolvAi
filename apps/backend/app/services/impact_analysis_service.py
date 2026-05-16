from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo.scoring import calculate_impact_from_scores
from app.models.impact_analysis import ImpactAnalysis
from app.realtime.events import IMPACT_CREATED
from app.services.realtime_service import RealtimeService
from app.utils.json import to_jsonable


def impact_analysis_payload(impact: ImpactAnalysis) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": impact.id,
            "workflow_id": impact.workflow_id,
            "business_impact": impact.business_impact,
            "technical_complexity": impact.technical_complexity,
            "urgency": impact.urgency,
            "confidence": impact.confidence,
            "risk_score": impact.risk_score,
            "opportunity_score": impact.opportunity_score,
            "final_priority": impact.final_priority,
            "impact_breakdown": impact.impact_breakdown,
            "recommendation": impact.recommendation,
            "created_at": impact.created_at,
        }
    )


class ImpactAnalysisService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()

    def calculate_impact(self, scenario: dict[str, Any]) -> dict[str, Any]:
        return calculate_impact_from_scores(
            scenario.get("scores", {}),
            recommendation=scenario.get("expected_recommendation"),
        )

    def create_impact_analysis(
        self,
        db: Session,
        workflow_id: UUID | str,
        impact_data: dict[str, Any],
        emit: bool = True,
    ) -> ImpactAnalysis:
        existing = self.get_by_workflow(db, workflow_id)
        if existing:
            return existing
        impact = ImpactAnalysis(
            workflow_id=workflow_id,
            business_impact=impact_data["business_impact"],
            technical_complexity=impact_data["technical_complexity"],
            urgency=impact_data["urgency"],
            confidence=impact_data["confidence"],
            risk_score=impact_data["risk_score"],
            opportunity_score=impact_data["opportunity_score"],
            final_priority=impact_data["final_priority"],
            impact_breakdown=to_jsonable(impact_data.get("impact_breakdown") or {}),
            recommendation=impact_data.get("recommendation"),
        )
        db.add(impact)
        db.commit()
        db.refresh(impact)
        if emit:
            self.realtime.emit_event(IMPACT_CREATED, impact_analysis_payload(impact), workflow_id=str(impact.workflow_id))
        return impact

    def get_by_workflow(self, db: Session, workflow_id: UUID | str) -> ImpactAnalysis | None:
        return db.scalars(
            select(ImpactAnalysis)
            .where(ImpactAnalysis.workflow_id == workflow_id)
            .order_by(ImpactAnalysis.created_at.desc())
        ).first()
