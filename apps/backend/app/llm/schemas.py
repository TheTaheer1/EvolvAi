import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 2)


def bounded_text(value: str, limit: int = 1200) -> str:
    value = str(value or "").strip()
    return value[:limit]


def bounded_list(values: list[str], *, item_limit: int = 400, max_items: int = 8) -> list[str]:
    return [bounded_text(item, item_limit) for item in (values or []) if str(item or "").strip()][:max_items]


class EvidenceItem(BaseModel):
    source: str = "llm"
    title: str
    summary: str
    relevance: Literal["low", "medium", "high"] = "medium"
    url: str | None = None

    @field_validator("title", "summary")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return bounded_text(value, 600)


class ResearchLLMOutput(BaseModel):
    research_summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    relevance_score: float = Field(default=0, ge=0, le=1)
    competitor_relevance: float = Field(default=0, ge=0, le=1)
    confidence_score: float = Field(default=0, ge=0, le=1)
    key_market_signals: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("relevance_score", "competitor_relevance", "confidence_score", mode="before")
    @classmethod
    def clamp_scores(cls, value: float) -> float:
        return clamp(value)

    @field_validator("research_summary")
    @classmethod
    def trim_summary(cls, value: str) -> str:
        return bounded_text(value)

    @field_validator("evidence")
    @classmethod
    def limit_evidence(cls, value: list[EvidenceItem]) -> list[EvidenceItem]:
        return value[:6]

    @field_validator("key_market_signals", "risks", "assumptions")
    @classmethod
    def trim_lists(cls, value: list[str]) -> list[str]:
        return bounded_list(value)


ResearchAgentLLMOutput = ResearchLLMOutput


class WatcherLLMOutput(BaseModel):
    source: str = "controlled_demo"
    event_type: str = "competitor_update"
    title: str
    summary: str
    importance_score: float = Field(default=0, ge=0, le=1)
    tags: list[str] = Field(default_factory=list)
    company_name: str | None = None
    why_it_matters: str
    recommended_evolution: str | None = None
    confidence_score: float = Field(default=0, ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    @field_validator("importance_score", "confidence_score", mode="before")
    @classmethod
    def clamp_scores(cls, value: float) -> float:
        return clamp(value)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        return bounded_text(value, 160)

    @field_validator("summary")
    @classmethod
    def trim_summary(cls, value: str) -> str:
        return bounded_text(value, 700)

    @field_validator("why_it_matters", "recommended_evolution")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return bounded_text(value, 700) if value is not None else None

    @field_validator("tags")
    @classmethod
    def limit_tags(cls, value: list[str]) -> list[str]:
        return bounded_list(value, item_limit=48, max_items=8)

    @field_validator("assumptions", "risks")
    @classmethod
    def trim_lists(cls, value: list[str]) -> list[str]:
        return bounded_list(value)


class StrategyAgentLLMOutput(BaseModel):
    should_act: bool = True
    decision_type: str = "feature_recommendation"
    title: str
    summary: str
    business_impact: float = Field(default=0, ge=0, le=1)
    technical_complexity: float = Field(default=0, ge=0, le=1)
    urgency: float = Field(default=0, ge=0, le=1)
    confidence_score: float = Field(default=0, ge=0, le=1)
    risk_score: float = Field(default=0, ge=0, le=1)
    recommended_action: str
    why_now: str
    why_relevant: str
    expected_benefit: str
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("business_impact", "technical_complexity", "urgency", "confidence_score", "risk_score", mode="before")
    @classmethod
    def clamp_scores(cls, value: float) -> float:
        return clamp(value)

    @field_validator("title", "summary", "recommended_action", "why_now", "why_relevant", "expected_benefit")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return bounded_text(value)

    @field_validator("risks", "assumptions")
    @classmethod
    def trim_lists(cls, value: list[str]) -> list[str]:
        return bounded_list(value)


class ImplementationTask(BaseModel):
    title: str
    description: str
    type: Literal["documentation", "component", "schema", "config", "test", "plan", "report"]
    complexity: Literal["low", "medium", "high"]
    risk: Literal["low", "medium", "high"]

    @field_validator("title", "description")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return bounded_text(value, 500)


class GeneratedFilePlan(BaseModel):
    file_path: str
    artifact_type: Literal["documentation", "component", "schema", "config", "plan", "report"]
    title: str
    description: str
    language: str | None = None

    @field_validator("file_path", "title", "description", "language")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return bounded_text(value, 500) if value is not None else None


class PlannerAgentLLMOutput(BaseModel):
    objective: str
    affected_modules: list[str] = Field(default_factory=list)
    tasks: list[ImplementationTask] = Field(default_factory=list)
    files_to_generate: list[GeneratedFilePlan] = Field(default_factory=list)
    estimated_effort: str
    estimated_complexity: str = "medium"
    rollout_plan: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("objective", "estimated_effort", "estimated_complexity")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return bounded_text(value)

    @field_validator("files_to_generate")
    @classmethod
    def limit_files(cls, value: list[GeneratedFilePlan]) -> list[GeneratedFilePlan]:
        return value[:5]

    @field_validator("affected_modules", "rollout_plan", "risks", "success_metrics", "assumptions")
    @classmethod
    def trim_lists(cls, value: list[str]) -> list[str]:
        return bounded_list(value)


class ArtifactContent(BaseModel):
    file_path: str
    artifact_type: Literal["documentation", "component", "schema", "config", "plan", "report"]
    title: str
    description: str
    language: str | None = None
    content: str

    @field_validator("file_path", "title", "description", "language")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return bounded_text(value, 500) if value is not None else None

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        return bounded_text(value, 100000)


class ExecutionLLMOutput(BaseModel):
    artifacts: list[ArtifactContent] = Field(default_factory=list)
    execution_summary: str
    safety_notes: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    @field_validator("execution_summary")
    @classmethod
    def trim_summary(cls, value: str) -> str:
        return bounded_text(value)

    @field_validator("artifacts")
    @classmethod
    def limit_artifacts(cls, value: list[ArtifactContent]) -> list[ArtifactContent]:
        return value[:5]

    @field_validator("safety_notes", "assumptions", "risks")
    @classmethod
    def trim_lists(cls, value: list[str]) -> list[str]:
        return bounded_list(value)


class VerificationLLMOutput(BaseModel):
    summary: str
    risk_interpretation: str
    suggested_remediations: list[str] = Field(default_factory=list)
    reviewer_confidence: float = Field(default=0, ge=0, le=1)
    additional_risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("reviewer_confidence", mode="before")
    @classmethod
    def clamp_score(cls, value: float) -> float:
        return clamp(value)

    @field_validator("summary", "risk_interpretation")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return bounded_text(value)

    @field_validator("suggested_remediations", "additional_risks", "assumptions")
    @classmethod
    def trim_lists(cls, value: list[str]) -> list[str]:
        return bounded_list(value)


class PRAgentLLMOutput(BaseModel):
    title: str
    branch_name_slug: str
    summary: str
    problem: str
    solution: str
    proposed_changes: list[str] = Field(default_factory=list)
    generated_artifacts: list[str] = Field(default_factory=list)
    impact_summary: str = ""
    verification_summary: str = ""
    testing_checklist: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    rollback_plan: list[str] = Field(default_factory=list)
    demo_note: str

    @field_validator("branch_name_slug")
    @classmethod
    def safe_branch_slug(cls, value: str) -> str:
        slug = re.sub(r"[^a-z0-9-]+", "-", str(value).lower()).strip("-")
        slug = re.sub(r"-+", "-", slug)
        return slug[:64] or "controlled-demo"

    @field_validator("title", "summary", "problem", "solution", "impact_summary", "verification_summary", "demo_note")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return bounded_text(value)

    @field_validator("proposed_changes", "generated_artifacts", "testing_checklist", "risks", "rollback_plan")
    @classmethod
    def trim_lists(cls, value: list[str]) -> list[str]:
        return bounded_list(value)


StrategyLLMOutput = StrategyAgentLLMOutput
PlannerLLMOutput = PlannerAgentLLMOutput
PRLLMOutput = PRAgentLLMOutput
