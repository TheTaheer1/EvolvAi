from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.market_event import MarketEventCreate, MarketEventRead
from app.schemas.workflow import WorkflowRead
from app.services.event_service import EventService
from app.services.live_event_workflow_service import LiveEventWorkflowService

router = APIRouter()


@router.get("", response_model=list[MarketEventRead])
def list_market_events(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    source: str | None = None,
    event_type: str | None = None,
):
    return EventService().list_market_events(db, limit=limit, source=source, event_type=event_type)


@router.post("", response_model=MarketEventRead)
def create_market_event(request: MarketEventCreate, db: Session = Depends(get_db)):
    return EventService().create_market_event(db, request.model_dump())


@router.get("/{event_id}", response_model=MarketEventRead)
def get_market_event(event_id: UUID, db: Session = Depends(get_db)):
    return EventService().get_market_event(db, event_id)


@router.post("/{event_id}/trigger-workflow", response_model=WorkflowRead)
def trigger_workflow_from_market_event(event_id: UUID, db: Session = Depends(get_db)):
    return LiveEventWorkflowService().trigger_from_market_event(db, event_id)
