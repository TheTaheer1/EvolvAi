import uuid

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_modules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    target_users: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    business_goals: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    technical_stack: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    competitors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    risk_tolerance: Mapped[str] = mapped_column(String(100), nullable=False, default="medium")
    engineering_capacity: Mapped[str] = mapped_column(String(100), nullable=False, default="small")
    raw_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
