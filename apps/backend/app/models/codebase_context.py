import uuid

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CodebaseContext(Base):
    __tablename__ = "codebase_contexts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relevant_files: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    architecture_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_hints: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    risks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis = relationship("RepositoryAnalysis", back_populates="codebase_contexts")
    workflow = relationship("Workflow", back_populates="codebase_contexts")
