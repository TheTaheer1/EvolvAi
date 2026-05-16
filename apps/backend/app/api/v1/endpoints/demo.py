from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.demo_scenario import DemoScenarioRead, DemoTriggerRequest
from app.schemas.workflow import WorkflowRead
from app.services.demo_scenario_service import DemoScenarioService
from app.services.demo_workflow_service import DemoWorkflowService

router = APIRouter()


@router.get("/demo/scenarios", response_model=list[DemoScenarioRead])
def list_demo_scenarios(db: Session = Depends(get_db)):
    DemoWorkflowService().ensure_demo_data_exists(db)
    return DemoScenarioService().list_active_scenarios(db)


@router.get("/demo/scenarios/{scenario_key}", response_model=DemoScenarioRead)
def get_demo_scenario(scenario_key: str, db: Session = Depends(get_db)):
    DemoWorkflowService().ensure_demo_data_exists(db)
    return DemoScenarioService().get_scenario_by_key(db, scenario_key)


@router.post("/demo/scenarios/{scenario_key}/trigger", response_model=WorkflowRead)
def trigger_demo_scenario(
    scenario_key: str,
    request: DemoTriggerRequest | None = None,
    db: Session = Depends(get_db),
):
    request = request or DemoTriggerRequest()
    return DemoWorkflowService().trigger_demo_scenario(
        db,
        scenario_key=scenario_key,
        company_profile_id=request.company_profile_id,
        demo_speed=request.demo_speed,
    )
