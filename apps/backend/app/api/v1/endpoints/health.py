import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.services.memory_service import MemoryService

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.APP_ENV}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "postgres"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "database": "postgres", "detail": str(exc)}


@router.get("/health/redis")
def health_redis() -> dict[str, str]:
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return {"status": "ok", "redis": settings.REDIS_URL.split("@")[0]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "redis": "redis", "detail": str(exc)}


@router.get("/health/chroma")
def health_chroma() -> dict[str, str]:
    return MemoryService().check_health()
