from typing import Any
import uuid

import socketio

from app.core.config import settings
from app.core.logging import logger
from app.realtime.rooms import workflow_room
from app.utils.json import to_jsonable
from app.utils.time import utc_now


class RealtimeService:
    def __init__(self) -> None:
        self._manager: socketio.RedisManager | None = None

    def _get_manager(self) -> socketio.RedisManager:
        if self._manager is None:
            self._manager = socketio.RedisManager(settings.REDIS_URL, write_only=True)
        return self._manager

    def emit_event(
        self, event_name: str, payload: dict[str, Any] | None = None, workflow_id: str | None = None
    ) -> None:
        safe_payload = dict(payload or {})
        safe_payload.setdefault("event_name", event_name)
        safe_payload.setdefault("event", event_name)
        timestamp = utc_now().isoformat()
        safe_payload.setdefault("id", str(uuid.uuid4()))
        safe_payload.setdefault("event_id", f"{event_name}:{safe_payload.get('id')}")
        safe_payload.setdefault("emitted_at", timestamp)
        safe_payload.setdefault("timestamp", timestamp)
        if workflow_id:
            safe_payload.setdefault("workflow_id", workflow_id)
        safe_payload = to_jsonable(safe_payload)
        try:
            manager = self._get_manager()
            manager.emit(event_name, safe_payload)
            if workflow_id:
                manager.emit(event_name, safe_payload, room=workflow_room(workflow_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning("realtime_emit_failed", event_name=event_name, error=str(exc))
