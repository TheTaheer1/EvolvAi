from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.realtime.events import NOTIFICATION_CREATED
from app.services.realtime_service import RealtimeService
from app.utils.json import to_jsonable


class NotificationService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()

    def create_notification(
        self,
        db: Session,
        type_: str,
        title: str,
        message: str,
        workflow_id: UUID | str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        notification = Notification(
            workflow_id=workflow_id,
            type=type_,
            title=title,
            message=message,
            payload=to_jsonable(payload or {}),
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        self.realtime.emit_event(
            NOTIFICATION_CREATED,
            {
                "id": str(notification.id),
                "workflow_id": str(notification.workflow_id) if notification.workflow_id else None,
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at,
            },
            workflow_id=str(notification.workflow_id) if notification.workflow_id else None,
        )
        return notification
