from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LLMInvocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID | None = None
    agent_execution_id: UUID | None = None
    agent_name: str | None = None
    provider: str
    model: str
    mode: str
    prompt_hash: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    status: str
    error_message: str | None = None
    latency_ms: int | None = None
    fallback_used: bool
    structured_output_valid: bool
    created_at: datetime


class LLMConfigRead(BaseModel):
    live_ai_enabled: bool
    api_key_present: bool
    api_key_usable: bool | None = None
    api_key_state: str | None = None
    provider: str
    model: str
    reasoning_model: str
    structured_outputs_enabled: bool
    fallback_to_demo: bool
    cache_enabled: bool
    prompt_logging_enabled: bool
    response_logging_enabled: bool


class LLMTestResponse(BaseModel):
    success: bool | None = None
    enabled: bool
    fallback_used: bool
    status: str
    provider: str
    model: str
    message: str
    error_message: str | None = None
    latency_ms: int | None = None
