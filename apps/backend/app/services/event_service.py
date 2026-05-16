from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_event import MarketEvent
from app.realtime.events import MARKET_EVENT_CREATED
from app.services.realtime_service import RealtimeService
from app.utils.json import to_jsonable


class EventService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()

    def create_market_event(self, db: Session, data: dict[str, Any], emit: bool = True) -> MarketEvent:
        event = MarketEvent(
            source=data.get("source", "manual"),
            event_type=data.get("event_type", "competitor_update"),
            title=data["title"],
            summary=data.get("summary"),
            url=data.get("url"),
            company_name=data.get("company_name"),
            competitor_name=data.get("competitor_name"),
            importance_score=data.get("importance_score", 0),
            raw_payload=to_jsonable(data.get("raw_payload") or data),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        if emit:
            self.realtime.emit_event(
                MARKET_EVENT_CREATED,
                {
                    "id": str(event.id),
                    "source": event.source,
                    "event_type": event.event_type,
                    "title": event.title,
                    "summary": event.summary,
                    "importance_score": event.importance_score,
                    "created_at": event.created_at,
                },
            )
        return event

    def list_market_events(
        self,
        db: Session,
        limit: int = 50,
        source: str | None = None,
        event_type: str | None = None,
    ) -> list[MarketEvent]:
        stmt = select(MarketEvent).order_by(MarketEvent.created_at.desc()).limit(min(limit, 100))
        if source:
            stmt = stmt.where(MarketEvent.source == source)
        if event_type:
            stmt = stmt.where(MarketEvent.event_type == event_type)
        return list(db.scalars(stmt).all())

    def get_market_event(self, db: Session, event_id: UUID | str) -> MarketEvent:
        event = db.get(MarketEvent, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Market event not found")
        return event
