import uuid

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemoScenario(Base):
    __tablename__ = "demo_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_source: Mapped[str] = mapped_column(String(100), nullable=False, default="controlled_demo")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    market_event: Mapped[dict] = mapped_column(JSONB, nullable=False)
    research_evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    expected_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    default_complexity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    default_urgency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
