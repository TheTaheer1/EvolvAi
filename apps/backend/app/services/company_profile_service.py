from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo.company_profile import DEMO_COMPANY_PROFILE
from app.models.company_profile import CompanyProfile
from app.utils.json import to_jsonable
from app.utils.time import utc_now


def company_profile_payload(profile: CompanyProfile) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": profile.id,
            "name": profile.name,
            "description": profile.description,
            "industry": profile.industry,
            "product_modules": profile.product_modules,
            "target_users": profile.target_users,
            "business_goals": profile.business_goals,
            "technical_stack": profile.technical_stack,
            "competitors": profile.competitors,
            "risk_tolerance": profile.risk_tolerance,
            "engineering_capacity": profile.engineering_capacity,
            "raw_profile": profile.raw_profile,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
    )


class CompanyProfileService:
    def list_company_profiles(self, db: Session) -> list[CompanyProfile]:
        return list(db.scalars(select(CompanyProfile).order_by(CompanyProfile.created_at.asc())).all())

    def get_default_company_profile(self, db: Session) -> CompanyProfile:
        profile = db.scalars(select(CompanyProfile).where(CompanyProfile.name == DEMO_COMPANY_PROFILE["name"])).first()
        if profile:
            return profile
        return self.create_or_update_demo_profile(db)

    def get_company_profile(self, db: Session, profile_id: UUID | str) -> CompanyProfile | None:
        return db.get(CompanyProfile, profile_id)

    def create_or_update_demo_profile(self, db: Session) -> CompanyProfile:
        data = dict(DEMO_COMPANY_PROFILE)
        profile = db.scalars(select(CompanyProfile).where(CompanyProfile.name == data["name"])).first()
        if not profile:
            profile = CompanyProfile(name=data["name"])
            db.add(profile)
        profile.description = data["description"]
        profile.industry = data["industry"]
        profile.product_modules = data["product_modules"]
        profile.target_users = data["target_users"]
        profile.business_goals = data["business_goals"]
        profile.technical_stack = data["technical_stack"]
        profile.competitors = data["competitors"]
        profile.risk_tolerance = data["risk_tolerance"]
        profile.engineering_capacity = data["engineering_capacity"]
        profile.raw_profile = to_jsonable(data)
        profile.updated_at = utc_now()
        db.commit()
        db.refresh(profile)
        return profile
