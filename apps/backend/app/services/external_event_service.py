from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingestion.dedupe import external_content_hash
from app.ingestion.hacker_news_ingestion import (
    HN_SOURCE,
    hacker_news_content_hash,
    normalize_hacker_news_story_to_event,
    parse_keywords,
)
from app.ingestion.normalizer import normalize_github_repository_to_event
from app.models.external_event_ingestion_run import ExternalEventIngestionRun
from app.models.external_event_raw import ExternalEventRaw
from app.models.external_event_source import ExternalEventSource
from app.models.market_event import MarketEvent
from app.realtime.events import LIVE_EVENT_CREATED, LIVE_EVENT_DEDUPED
from app.services.event_service import EventService
from app.services.realtime_service import RealtimeService
from app.utils.json import to_jsonable
from app.utils.time import utc_now


GITHUB_SOURCE_KEY = "github_repository_search"
HACKER_NEWS_SOURCE_KEY = "hacker_news"


class ExternalEventService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()
        self.events = EventService(self.realtime)

    def ensure_default_sources(self, db: Session) -> list[ExternalEventSource]:
        github_source = db.scalars(
            select(ExternalEventSource).where(ExternalEventSource.source_key == GITHUB_SOURCE_KEY)
        ).first()
        github_enabled = bool(settings.USE_LIVE_EXTERNAL_EVENTS or settings.GITHUB_INGESTION_ENABLED)
        github_config = {
            "query": settings.GITHUB_SEARCH_QUERY,
            "max_results": settings.GITHUB_SEARCH_MAX_RESULTS,
            "token_present": bool(settings.GITHUB_TOKEN),
            "api_base_url": settings.GITHUB_API_BASE_URL,
        }
        if github_source:
            github_source.enabled = github_enabled
            github_source.config = github_config
            github_source.updated_at = utc_now()
        else:
            github_source = ExternalEventSource(
                source_key=GITHUB_SOURCE_KEY,
                source_type="github",
                display_name="GitHub Repository Search",
                enabled=github_enabled,
                config=github_config,
            )
            db.add(github_source)

        hn_source = db.scalars(
            select(ExternalEventSource).where(ExternalEventSource.source_key == HACKER_NEWS_SOURCE_KEY)
        ).first()
        hn_enabled = bool(settings.USE_LIVE_EXTERNAL_EVENTS or settings.HN_INGESTION_ENABLED)
        hn_config = {
            "api_base_url": settings.HN_API_BASE_URL,
            "default_feed": settings.HN_DEFAULT_FEED,
            "max_stories": settings.HN_MAX_STORIES,
            "min_score": settings.HN_MIN_SCORE,
            "min_importance_score": settings.HN_MIN_IMPORTANCE_SCORE,
            "keywords": parse_keywords(None),
            "api_key_required": False,
        }
        if hn_source:
            hn_source.enabled = hn_enabled
            hn_source.config = hn_config
            hn_source.updated_at = utc_now()
        else:
            hn_source = ExternalEventSource(
                source_key=HACKER_NEWS_SOURCE_KEY,
                source_type="news",
                display_name="Hacker News",
                enabled=hn_enabled,
                config=hn_config,
            )
            db.add(hn_source)
        db.commit()
        db.refresh(github_source)
        db.refresh(hn_source)
        return [github_source, hn_source]

    def list_sources(self, db: Session) -> list[ExternalEventSource]:
        self.ensure_default_sources(db)
        return list(db.scalars(select(ExternalEventSource).order_by(ExternalEventSource.display_name.asc())).all())

    def start_ingestion_run(self, db: Session, source_key: str) -> ExternalEventIngestionRun:
        run = ExternalEventIngestionRun(
            source_key=source_key,
            status="running",
            started_at=utc_now(),
            raw_summary={},
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    def complete_ingestion_run(
        self,
        db: Session,
        run: ExternalEventIngestionRun,
        *,
        status: str,
        events_found: int,
        events_created: int,
        events_skipped: int,
        raw_summary: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> ExternalEventIngestionRun:
        run.status = status
        run.completed_at = utc_now()
        run.events_found = events_found
        run.events_created = events_created
        run.events_skipped = events_skipped
        run.raw_summary = to_jsonable(raw_summary or {})
        run.error_message = error_message
        source = db.scalars(
            select(ExternalEventSource).where(ExternalEventSource.source_key == run.source_key)
        ).first()
        if source:
            source.last_sync_at = run.completed_at if status in {"completed", "partial"} else source.last_sync_at
            source.last_error = error_message
        db.commit()
        db.refresh(run)
        return run

    def normalize_and_store_github_repositories(
        self,
        db: Session,
        repositories: list[dict[str, Any]],
    ) -> tuple[list[MarketEvent], list[ExternalEventRaw], int]:
        created_events: list[MarketEvent] = []
        raw_records: list[ExternalEventRaw] = []
        skipped = 0
        for repo in repositories:
            content_hash = external_content_hash("github", repo)
            existing = db.scalars(
                select(ExternalEventRaw).where(
                    ExternalEventRaw.source == "github",
                    ExternalEventRaw.content_hash == content_hash,
                )
            ).first()
            if existing:
                skipped += 1
                self.realtime.emit_event(
                    LIVE_EVENT_DEDUPED,
                    {
                        "id": str(existing.id),
                        "source": "github",
                        "message": f"Skipped duplicate GitHub event: {existing.title}",
                    },
                )
                continue
            normalized = normalize_github_repository_to_event(repo)
            market_event = self.events.create_market_event(db, normalized, emit=True)
            raw = ExternalEventRaw(
                source="github",
                external_id=str(repo.get("id") or repo.get("full_name") or ""),
                title=normalized["title"],
                url=normalized.get("url"),
                raw_payload=to_jsonable(repo),
                normalized_market_event_id=market_event.id,
                content_hash=content_hash,
            )
            db.add(raw)
            try:
                db.commit()
                db.refresh(raw)
            except IntegrityError:
                db.rollback()
                skipped += 1
                continue
            raw_records.append(raw)
            created_events.append(market_event)
            self.realtime.emit_event(
                LIVE_EVENT_CREATED,
                {
                    "id": str(market_event.id),
                    "source": market_event.source,
                    "event_type": market_event.event_type,
                    "title": market_event.title,
                    "summary": market_event.summary,
                    "url": market_event.url,
                    "importance_score": market_event.importance_score,
                    "raw_event_id": str(raw.id),
                    "message": f"Created live market event: {market_event.title}",
                },
            )
        return created_events, raw_records, skipped

    def normalize_and_store_hacker_news_stories(
        self,
        db: Session,
        stories: list[dict[str, Any]],
        *,
        keywords: list[str] | None = None,
    ) -> tuple[list[MarketEvent], list[ExternalEventRaw], int]:
        created_events: list[MarketEvent] = []
        raw_records: list[ExternalEventRaw] = []
        skipped = 0
        active_keywords = parse_keywords(keywords)
        for story in stories:
            content_hash = hacker_news_content_hash(story)
            existing = db.scalars(
                select(ExternalEventRaw).where(
                    ExternalEventRaw.source == HN_SOURCE,
                    ExternalEventRaw.content_hash == content_hash,
                )
            ).first()
            if existing:
                skipped += 1
                self.realtime.emit_event(
                    LIVE_EVENT_DEDUPED,
                    {
                        "id": str(existing.id),
                        "source": HN_SOURCE,
                        "source_key": HACKER_NEWS_SOURCE_KEY,
                        "display_name": "Hacker News",
                        "message": f"Skipped duplicate Hacker News event: {existing.title}",
                    },
                )
                continue
            normalized = normalize_hacker_news_story_to_event(story, keywords=active_keywords)
            market_event = self.events.create_market_event(db, normalized, emit=True)
            raw = ExternalEventRaw(
                source=HN_SOURCE,
                external_id=str(story.get("id") or ""),
                title=normalized["title"],
                url=normalized.get("url"),
                raw_payload=to_jsonable(normalized.get("raw_payload") or story),
                normalized_market_event_id=market_event.id,
                content_hash=content_hash,
            )
            db.add(raw)
            try:
                db.commit()
                db.refresh(raw)
            except IntegrityError:
                db.rollback()
                skipped += 1
                continue
            raw_records.append(raw)
            created_events.append(market_event)
            self.realtime.emit_event(
                LIVE_EVENT_CREATED,
                {
                    "id": str(market_event.id),
                    "source": market_event.source,
                    "source_key": HACKER_NEWS_SOURCE_KEY,
                    "display_name": "Hacker News",
                    "event_type": market_event.event_type,
                    "title": market_event.title,
                    "summary": market_event.summary,
                    "url": market_event.url,
                    "importance_score": market_event.importance_score,
                    "raw_event_id": str(raw.id),
                    "message": f"Created Hacker News market event: {market_event.title}",
                },
            )
        return created_events, raw_records, skipped

    def list_ingestion_runs(
        self,
        db: Session,
        limit: int = 25,
        source_key: str | None = None,
    ) -> list[ExternalEventIngestionRun]:
        stmt = (
            select(ExternalEventIngestionRun)
            .order_by(ExternalEventIngestionRun.created_at.desc())
            .limit(min(limit, 100))
        )
        if source_key:
            stmt = stmt.where(ExternalEventIngestionRun.source_key == source_key)
        return list(
            db.scalars(stmt).all()
        )

    def list_raw_events(self, db: Session, limit: int = 25, source: str | None = None) -> list[ExternalEventRaw]:
        stmt = select(ExternalEventRaw).order_by(ExternalEventRaw.created_at.desc()).limit(min(limit, 100))
        if source:
            stmt = stmt.where(ExternalEventRaw.source == source)
        return list(db.scalars(stmt).all())
