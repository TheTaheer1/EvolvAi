from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.llm_invocation import LLMInvocation
from app.utils.json import to_jsonable


def llm_invocation_payload(invocation: LLMInvocation) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": invocation.id,
            "workflow_id": invocation.workflow_id,
            "agent_execution_id": invocation.agent_execution_id,
            "agent_name": invocation.agent_name,
            "provider": invocation.provider,
            "model": invocation.model,
            "mode": invocation.mode,
            "prompt_hash": invocation.prompt_hash,
            "input_tokens": invocation.input_tokens,
            "output_tokens": invocation.output_tokens,
            "total_tokens": invocation.total_tokens,
            "status": invocation.status,
            "error_message": invocation.error_message,
            "latency_ms": invocation.latency_ms,
            "fallback_used": invocation.fallback_used,
            "structured_output_valid": invocation.structured_output_valid,
            "created_at": invocation.created_at,
        }
    )


class LLMInvocationService:
    def create_invocation(self, db: Session, data: dict[str, Any]) -> LLMInvocation:
        invocation = LLMInvocation(
            workflow_id=data.get("workflow_id"),
            agent_execution_id=data.get("agent_execution_id"),
            agent_name=data.get("agent_name"),
            provider=data.get("provider") or "openai",
            model=data.get("model") or "unknown",
            mode=data.get("mode") or "deterministic",
            prompt_hash=data.get("prompt_hash"),
            input_tokens=data.get("input_tokens"),
            output_tokens=data.get("output_tokens"),
            total_tokens=data.get("total_tokens"),
            status=data.get("status") or "skipped",
            error_message=(data.get("error_message") or None),
            latency_ms=data.get("latency_ms"),
            fallback_used=bool(data.get("fallback_used", False)),
            structured_output_valid=bool(data.get("structured_output_valid", False)),
        )
        db.add(invocation)
        db.commit()
        db.refresh(invocation)
        return invocation

    def list_invocations(
        self,
        db: Session,
        workflow_id: UUID | str | None = None,
        agent_name: str | None = None,
        limit: int = 50,
    ) -> list[LLMInvocation]:
        stmt = select(LLMInvocation).order_by(LLMInvocation.created_at.desc()).limit(min(limit, 200))
        if workflow_id:
            stmt = stmt.where(LLMInvocation.workflow_id == workflow_id)
        if agent_name:
            stmt = stmt.where(LLMInvocation.agent_name == agent_name)
        return list(db.scalars(stmt).all())
