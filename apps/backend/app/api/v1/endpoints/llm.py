from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.llm.llm_service import LLMService
from app.schemas.llm import LLMConfigRead, LLMInvocationRead, LLMTestResponse
from app.services.llm_invocation_service import LLMInvocationService

router = APIRouter(prefix="/llm")


@router.get("/config", response_model=LLMConfigRead)
def get_llm_config():
    return LLMService().config_status()


@router.get("/status")
def get_llm_status():
    return LLMService().status()


@router.get("/invocations", response_model=list[LLMInvocationRead])
def list_llm_invocations(
    db: Session = Depends(get_db),
    workflow_id: UUID | None = None,
    agent_name: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
):
    return LLMInvocationService().list_invocations(
        db,
        workflow_id=workflow_id,
        agent_name=agent_name,
        limit=limit,
    )


@router.get("/test", response_model=LLMTestResponse)
def get_test_llm_config():
    return LLMService().test_active_provider()


@router.post("/test", response_model=LLMTestResponse)
def test_llm_config():
    return LLMService().test_active_provider()
