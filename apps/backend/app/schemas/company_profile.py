from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    industry: str | None = None
    product_modules: list[str] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    business_goals: list[str] = Field(default_factory=list)
    technical_stack: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    risk_tolerance: str
    engineering_capacity: str
    raw_profile: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
