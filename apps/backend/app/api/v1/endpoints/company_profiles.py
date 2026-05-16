from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.company_profile import CompanyProfileRead
from app.services.company_profile_service import CompanyProfileService

router = APIRouter()


@router.get("/company-profile/default", response_model=CompanyProfileRead)
def default_company_profile(db: Session = Depends(get_db)):
    return CompanyProfileService().get_default_company_profile(db)


@router.get("/company-profiles", response_model=list[CompanyProfileRead])
def list_company_profiles(db: Session = Depends(get_db)):
    service = CompanyProfileService()
    service.create_or_update_demo_profile(db)
    return service.list_company_profiles(db)
