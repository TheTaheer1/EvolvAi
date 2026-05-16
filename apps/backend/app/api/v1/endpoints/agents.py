from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents import build_agents
from app.api.deps import get_db
from app.schemas.agent_execution import AgentDefinition, AgentExecutionRead
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.get("/agents", response_model=list[AgentDefinition])
def list_agents():
    return [{"name": agent.name, "description": agent.description} for agent in build_agents()]


@router.get("/workflows/{workflow_id}/agents", response_model=list[AgentExecutionRead])
def list_workflow_agents(workflow_id: UUID, db: Session = Depends(get_db)):
    WorkflowService().require_workflow(db, workflow_id)
    return AgentService().list_for_workflow(db, workflow_id)
