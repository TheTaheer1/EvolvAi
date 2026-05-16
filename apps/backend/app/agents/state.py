from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    workflow_id: str
    company_id: str | None
    trigger_type: str
    trigger_payload: dict[str, Any]
    codebase_context: dict[str, Any] | None
    market_events: list[dict[str, Any]]
    normalized_market_event: dict[str, Any]
    research_summary: str
    research_evidence: list[dict[str, Any]]
    trend_relevance: str
    competitor_relevance: str
    confidence_score: float
    impact_score: float
    impact_analysis: dict[str, Any]
    decision: dict[str, Any]
    implementation_plan: dict[str, Any]
    artifact_plan: list[dict[str, Any]]
    generated_artifacts: list[dict[str, Any]]
    persisted_artifacts: list[dict[str, Any]]
    artifact_warnings: list[dict[str, Any]]
    generated_changes: list[dict[str, Any]]
    verification_result: dict[str, Any]
    verification_explanation: dict[str, Any]
    pull_request: dict[str, Any]
    pull_request_llm: dict[str, Any]
    execution_summary: str
    output_mode: str
    llm_metadata_by_agent: dict[str, dict[str, Any]]
    explainability: dict[str, Any]
    current_agent: str
    status: str
    errors: list[str]
    logs: list[str]
    trace_id: str | None
