from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.dashboard import DashboardActivity, DashboardLiveState, DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return DashboardService().get_summary(db)


@router.get("/activity", response_model=DashboardActivity)
def dashboard_activity(db: Session = Depends(get_db)):
    return DashboardService().get_activity(db)


@router.get("/live-state", response_model=DashboardLiveState)
def dashboard_live_state(db: Session = Depends(get_db)):
    return DashboardService().get_live_state(db)


@router.get("/demo-state")
def dashboard_demo_state(db: Session = Depends(get_db)):
    return DashboardService().get_demo_state(db)
