import uuid

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketEvent(Base):
    __tablename__ = "market_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    competitor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    detected_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
