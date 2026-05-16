from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo.scenarios import DEMO_SCENARIOS
from app.models.demo_scenario import DemoScenario
from app.utils.json import to_jsonable
from app.utils.time import utc_now


def demo_scenario_payload(scenario: DemoScenario) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": scenario.id,
            "scenario_key": scenario.scenario_key,
            "title": scenario.title,
            "description": scenario.description,
            "event_source": scenario.event_source,
            "event_type": scenario.event_type,
            "market_event": scenario.market_event,
            "research_evidence": scenario.research_evidence,
            "expected_recommendation": scenario.expected_recommendation,
            "default_impact_score": scenario.default_impact_score,
            "default_complexity_score": scenario.default_complexity_score,
            "default_urgency_score": scenario.default_urgency_score,
            "tags": scenario.tags,
            "is_active": scenario.is_active,
            "created_at": scenario.created_at,
            "updated_at": scenario.updated_at,
        }
    )


class DemoScenarioService:
    def list_active_scenarios(self, db: Session) -> list[DemoScenario]:
        scenarios = list(
            db.scalars(
                select(DemoScenario).where(DemoScenario.is_active.is_(True)).order_by(DemoScenario.created_at.asc())
            ).all()
        )
        order = {scenario["scenario_key"]: index for index, scenario in enumerate(DEMO_SCENARIOS)}
        return sorted(scenarios, key=lambda scenario: order.get(scenario.scenario_key, 999))

    def get_scenario_by_key(self, db: Session, scenario_key: str) -> DemoScenario:
        scenario = db.scalars(select(DemoScenario).where(DemoScenario.scenario_key == scenario_key)).first()
        if not scenario:
            raise HTTPException(status_code=404, detail=f"Demo scenario not found: {scenario_key}")
        if not scenario.is_active:
            raise HTTPException(status_code=400, detail=f"Demo scenario is inactive: {scenario_key}")
        return scenario

    def get_scenario_by_id(self, db: Session, scenario_id: UUID | str) -> DemoScenario:
        scenario = db.get(DemoScenario, scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Demo scenario not found")
        return scenario

    def create_market_event_from_scenario(self, scenario: DemoScenario) -> dict[str, Any]:
        market_event = dict(scenario.market_event or {})
        return {
            "source": scenario.event_source,
            "event_type": scenario.event_type,
            "title": market_event.get("title", scenario.title),
            "summary": market_event.get("summary", scenario.description),
            "importance_score": market_event.get("importance_score", scenario.default_impact_score),
            "tags": scenario.tags,
            "scenario_key": scenario.scenario_key,
            "why_it_matters": market_event.get("why_it_matters"),
            "recommended_evolution": market_event.get("recommended_evolution", scenario.expected_recommendation),
        }

    def create_or_update_demo_scenarios(self, db: Session) -> list[DemoScenario]:
        scenarios: list[DemoScenario] = []
        for data in DEMO_SCENARIOS:
            scenario = db.scalars(
                select(DemoScenario).where(DemoScenario.scenario_key == data["scenario_key"])
            ).first()
            if not scenario:
                scenario = DemoScenario(scenario_key=data["scenario_key"])
                db.add(scenario)
            scenario.title = data["title"]
            scenario.description = data["description"]
            scenario.event_source = "controlled_demo"
            scenario.event_type = data["event_type"]
            scenario.market_event = to_jsonable(data["market_event"])
            scenario.research_evidence = to_jsonable(data["research_evidence"])
            scenario.expected_recommendation = data["expected_recommendation"]
            scenario.default_impact_score = data["scores"]["business_impact"]
            scenario.default_complexity_score = data["scores"]["technical_complexity"]
            scenario.default_urgency_score = data["scores"]["urgency"]
            scenario.tags = to_jsonable(data["tags"])
            scenario.is_active = True
            scenario.updated_at = utc_now()
            scenarios.append(scenario)
        db.commit()
        for scenario in scenarios:
            db.refresh(scenario)
        return scenarios

    def scenario_to_runtime_dict(self, scenario: DemoScenario) -> dict[str, Any]:
        runtime = demo_scenario_payload(scenario)
        fixture = next(
            (item for item in DEMO_SCENARIOS if item["scenario_key"] == scenario.scenario_key),
            None,
        )
        if fixture:
            runtime["scores"] = fixture["scores"]
            runtime["proposed_files"] = fixture["proposed_files"]
        return runtime
