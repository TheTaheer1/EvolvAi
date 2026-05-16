import uuid

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    current_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    final_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    agent_executions = relationship(
        "AgentExecution", back_populates="workflow", order_by="AgentExecution.created_at"
    )
    logs = relationship("Log", back_populates="workflow", order_by="Log.created_at")
    decisions = relationship("Decision", back_populates="workflow", order_by="Decision.created_at")
    pull_requests = relationship(
        "PullRequestHistory", back_populates="workflow", order_by="PullRequestHistory.created_at"
    )
    explainability_records = relationship(
        "ExplainabilityRecord", back_populates="workflow", order_by="ExplainabilityRecord.created_at"
    )
    impact_analyses = relationship("ImpactAnalysis", back_populates="workflow", order_by="ImpactAnalysis.created_at")
    generated_artifacts = relationship(
        "GeneratedArtifact", back_populates="workflow", order_by="GeneratedArtifact.created_at"
    )
    verification_reports = relationship(
        "VerificationReport", back_populates="workflow", order_by="VerificationReport.created_at"
    )
    llm_invocations = relationship("LLMInvocation", back_populates="workflow", order_by="LLMInvocation.created_at")
    codebase_contexts = relationship("CodebaseContext", back_populates="workflow", order_by="CodebaseContext.created_at")
