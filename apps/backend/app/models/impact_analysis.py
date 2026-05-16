import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ImpactAnalysis(Base):
    __tablename__ = "impact_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    technical_complexity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    urgency: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    final_priority: Mapped[str] = mapped_column(String(50), nullable=False)
    impact_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workflow = relationship("Workflow", back_populates="impact_analyses")
