from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.company_profile import CompanyProfile
from app.models.demo_scenario import DemoScenario
from app.realtime.events import SCENARIO_SELECTED, WORKFLOW_CREATED, WORKFLOW_QUEUED
from app.services.company_profile_service import CompanyProfileService, company_profile_payload
from app.services.demo_scenario_service import DemoScenarioService
from app.services.event_service import EventService
from app.services.log_service import LogService
from app.services.realtime_service import RealtimeService
from app.services.workflow_service import WorkflowService, workflow_payload


DEMO_SPEEDS = {"fast": 100, "normal": 700, "slow": 1500}


class DemoWorkflowService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()
        self.company_profiles = CompanyProfileService()
        self.scenarios = DemoScenarioService()
        self.workflows = WorkflowService()
        self.events = EventService(self.realtime)
        self.logs = LogService(self.realtime)

    def ensure_demo_data_exists(self, db: Session) -> tuple[CompanyProfile, list[DemoScenario]]:
        profile = self.company_profiles.create_or_update_demo_profile(db)
        scenarios = self.scenarios.create_or_update_demo_scenarios(db)
        return profile, scenarios

    def build_initial_workflow_payload(
        self,
        scenario: DemoScenario,
        profile: CompanyProfile,
        market_event_id: str,
        demo_speed: str,
    ) -> dict[str, Any]:
        runtime_scenario = self.scenarios.scenario_to_runtime_dict(scenario)
        return {
            "demo_mode": True,
            "demo_speed": demo_speed,
            "scenario_key": scenario.scenario_key,
            "scenario": runtime_scenario,
            "company_profile_id": str(profile.id),
            "company_profile": company_profile_payload(profile),
            "market_event_id": market_event_id,
            "safety": {
                "real_pr_enabled": False,
                "generated_files_scope": "apps/backend/generated_runs/{workflow_id}/",
                "external_apis_required": False,
            },
        }

    def trigger_demo_scenario(
        self,
        db: Session,
        scenario_key: str,
        company_profile_id: UUID | None = None,
        demo_speed: str = "normal",
    ):
        if demo_speed not in DEMO_SPEEDS:
            raise HTTPException(status_code=400, detail="demo_speed must be one of: fast, normal, slow")
        self.ensure_demo_data_exists(db)
        scenario = self.scenarios.get_scenario_by_key(db, scenario_key)
        profile = (
            self.company_profiles.get_company_profile(db, company_profile_id)
            if company_profile_id
            else self.company_profiles.get_default_company_profile(db)
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Company profile not found")

        normalized = self.scenarios.create_market_event_from_scenario(scenario)
        market_event = self.events.create_market_event(
            db,
            {
                **normalized,
                "company_name": profile.name,
                "raw_payload": {
                    "scenario_key": scenario.scenario_key,
                    "controlled_demo": True,
                    "tags": scenario.tags,
                    "market_event": scenario.market_event,
                },
            },
            emit=True,
        )
        payload = self.build_initial_workflow_payload(scenario, profile, str(market_event.id), demo_speed)
        workflow = self.workflows.create_workflow(
            db,
            trigger_type="controlled_demo_scenario",
            source=f"demo:{scenario.scenario_key}",
            payload=payload,
            company_context=company_profile_payload(profile),
        )
        market_event.raw_payload = {**(market_event.raw_payload or {}), "workflow_id": str(workflow.id)}
        db.commit()
        self.logs.create_log(
            db,
            "INFO",
            f"Workflow queued from scenario: {scenario.scenario_key}",
            workflow_id=workflow.id,
            context={"scenario_key": scenario.scenario_key, "demo_speed": demo_speed},
        )
        realtime_payload = workflow_payload(workflow)
        self.realtime.emit_event(
            SCENARIO_SELECTED,
            {
                "id": str(scenario.id),
                "workflow_id": str(workflow.id),
                "scenario_key": scenario.scenario_key,
                "title": scenario.title,
            },
            workflow_id=str(workflow.id),
        )
        self.realtime.emit_event(WORKFLOW_CREATED, realtime_payload, workflow_id=str(workflow.id))
        self.realtime.emit_event(WORKFLOW_QUEUED, realtime_payload, workflow_id=str(workflow.id))
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
