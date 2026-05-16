import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    input_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workflow = relationship("Workflow", back_populates="agent_executions")
    logs = relationship("Log", back_populates="agent_execution", order_by="Log.created_at")
    traces = relationship("Trace", back_populates="agent_execution", order_by="Trace.created_at")
    explainability_records = relationship(
        "ExplainabilityRecord", back_populates="agent_execution", order_by="ExplainabilityRecord.created_at"
    )
    llm_invocations = relationship("LLMInvocation", back_populates="agent_execution", order_by="LLMInvocation.created_at")
