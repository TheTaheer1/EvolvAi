from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.ingestion.github_ingestion import GitHubIngestionService, GitHubIngestionError, GitHubRateLimitError
from app.ingestion.hacker_news_ingestion import (
    HackerNewsIngestionError,
    HackerNewsIngestionService,
    HackerNewsInvalidFeedError,
    parse_keywords,
)
from app.realtime.events import (
    LIVE_EVENT_INGESTION_COMPLETED,
    LIVE_EVENT_INGESTION_FAILED,
    LIVE_EVENT_INGESTION_STARTED,
)
from app.schemas.external_event import (
    ExternalEventIngestionRunRead,
    ExternalEventRawRead,
    ExternalEventSourceRead,
    HackerNewsIngestRequest,
    LiveEventIngestRequest,
    LiveEventIngestResponse,
)
from app.services.external_event_service import GITHUB_SOURCE_KEY, HACKER_NEWS_SOURCE_KEY, ExternalEventService
from app.services.live_event_workflow_service import LiveEventWorkflowService
from app.services.realtime_service import RealtimeService

router = APIRouter(prefix="/live-events")


@router.get("/sources", response_model=list[ExternalEventSourceRead])
def list_live_event_sources(db: Session = Depends(get_db)):
    return ExternalEventService().list_sources(db)


@router.post("/ingest/github", response_model=LiveEventIngestResponse)
def ingest_github_events(request: LiveEventIngestRequest, db: Session = Depends(get_db)):
    request.query = request.query.strip()
    if not request.query:
        raise HTTPException(status_code=400, detail="GitHub search query cannot be empty.")
    realtime = RealtimeService()
    service = ExternalEventService(realtime)
    sources = service.ensure_default_sources(db)
    source = sources[0] if sources else None
    run = service.start_ingestion_run(db, GITHUB_SOURCE_KEY)
    warnings: list[str] = []
    workflows_triggered = []
    realtime.emit_event(
        LIVE_EVENT_INGESTION_STARTED,
        {
            "id": str(run.id),
            "source_key": GITHUB_SOURCE_KEY,
            "message": "GitHub ingestion started",
            "payload": {"query": request.query, "max_results": request.max_results},
        },
    )
    if not (settings.USE_LIVE_EXTERNAL_EVENTS or settings.GITHUB_INGESTION_ENABLED):
        warnings.append("Live external event flags are disabled; manual ingestion request still ran in preview mode.")
    try:
        repositories, github_warnings = GitHubIngestionService().ingest_github_search(
            query=request.query,
            max_results=request.max_results,
        )
        warnings.extend(github_warnings)
        events, raw_events, skipped = service.normalize_and_store_github_repositories(db, repositories)
        if request.trigger_workflows:
            if settings.LIVE_EVENT_AUTO_TRIGGER:
                for event in events:
                    if event.importance_score >= settings.LIVE_EVENT_MIN_IMPORTANCE_SCORE:
                        workflow = LiveEventWorkflowService(realtime).trigger_from_market_event(db, event.id)
                        workflows_triggered.append(workflow.id)
            else:
                warnings.append("LIVE_EVENT_AUTO_TRIGGER=false; live events were ingested but workflows were not auto-triggered.")
        run = service.complete_ingestion_run(
            db,
            run,
            status="completed",
            events_found=len(repositories),
            events_created=len(events),
            events_skipped=skipped,
            raw_summary={
                "query": request.query,
                "max_results": request.max_results,
                "warnings": warnings,
            },
        )
        realtime.emit_event(
            LIVE_EVENT_INGESTION_COMPLETED,
            {
                "id": str(run.id),
                "source_key": GITHUB_SOURCE_KEY,
                "message": f"GitHub ingestion completed with {len(events)} new events",
                "payload": {
                    "events_found": run.events_found,
                    "events_created": run.events_created,
                    "events_skipped": run.events_skipped,
                },
            },
        )
        return {
            "run_id": run.id,
            "source": "github",
            "status": run.status,
            "events_found": run.events_found,
            "events_created": run.events_created,
            "events_skipped": run.events_skipped,
            "market_events": events,
            "run": run,
            "source_config": source,
            "events": events,
            "raw_events": raw_events,
            "warnings": warnings,
            "workflows_triggered": workflows_triggered,
        }
    except GitHubRateLimitError as exc:
        warnings.append("GitHub rate limit reached; try again later or configure GITHUB_TOKEN.")
        run = service.complete_ingestion_run(
            db,
            run,
            status="failed",
            events_found=0,
            events_created=0,
            events_skipped=0,
            raw_summary={"query": request.query, "warnings": warnings},
            error_message=str(exc),
        )
    except GitHubIngestionError as exc:
        warnings.append(str(exc))
        run = service.complete_ingestion_run(
            db,
            run,
            status="failed",
            events_found=0,
            events_created=0,
            events_skipped=0,
            raw_summary={"query": request.query, "warnings": warnings},
            error_message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append("Unexpected GitHub ingestion failure; controlled demo remains available.")
        run = service.complete_ingestion_run(
            db,
            run,
            status="failed",
            events_found=0,
            events_created=0,
            events_skipped=0,
            raw_summary={"query": request.query, "warnings": warnings},
            error_message=str(exc),
        )
    realtime.emit_event(
        LIVE_EVENT_INGESTION_FAILED,
        {
            "id": str(run.id),
            "source_key": GITHUB_SOURCE_KEY,
            "message": "GitHub ingestion failed safely",
            "payload": {"error_message": run.error_message, "warnings": warnings},
        },
    )
    return {
        "run_id": run.id,
        "source": "github",
        "status": run.status,
        "events_found": run.events_found,
        "events_created": run.events_created,
        "events_skipped": run.events_skipped,
        "market_events": [],
        "run": run,
        "source_config": source,
        "events": [],
        "raw_events": [],
        "warnings": warnings,
        "workflows_triggered": workflows_triggered,
    }


@router.post("/ingest/hacker-news", response_model=LiveEventIngestResponse)
def ingest_hacker_news_events(request: HackerNewsIngestRequest, db: Session = Depends(get_db)):
    realtime = RealtimeService()
    service = ExternalEventService(realtime)
    sources = service.ensure_default_sources(db)
    source = next((item for item in sources if item.source_key == HACKER_NEWS_SOURCE_KEY), None)
    run = service.start_ingestion_run(db, HACKER_NEWS_SOURCE_KEY)
    warnings: list[str] = []
    workflows_triggered = []
    feed = request.feed.strip().lower()
    max_results = min(max(1, request.max_results), settings.HN_MAX_STORIES)
    keywords = parse_keywords(request.keywords)
    min_score = settings.HN_MIN_SCORE if request.min_score is None else request.min_score
    realtime.emit_event(
        LIVE_EVENT_INGESTION_STARTED,
        {
            "id": str(run.id),
            "source_key": HACKER_NEWS_SOURCE_KEY,
            "display_name": "Hacker News",
            "message": "Hacker News ingestion started",
            "payload": {
                "feed": feed,
                "max_results": max_results,
                "keywords": keywords,
                "min_score": min_score,
            },
        },
    )
    if not (settings.USE_LIVE_EXTERNAL_EVENTS or settings.HN_INGESTION_ENABLED):
        warnings.append("Hacker News ingestion flags are disabled; manual request still ran in preview mode.")
    try:
        stories, hn_warnings = HackerNewsIngestionService().ingest_hacker_news(
            feed=feed,
            max_results=max_results,
            keywords=request.keywords,
            min_score=min_score,
        )
        warnings.extend(hn_warnings)
        events, raw_events, skipped = service.normalize_and_store_hacker_news_stories(
            db,
            stories,
            keywords=request.keywords,
        )
        if request.trigger_workflows:
            if settings.LIVE_EVENT_AUTO_TRIGGER:
                for event in events:
                    if event.importance_score >= settings.LIVE_EVENT_MIN_IMPORTANCE_SCORE:
                        workflow = LiveEventWorkflowService(realtime).trigger_from_market_event(db, event.id)
                        workflows_triggered.append(workflow.id)
            else:
                warnings.append("LIVE_EVENT_AUTO_TRIGGER=false; Hacker News events were ingested but workflows were not auto-triggered.")
        run = service.complete_ingestion_run(
            db,
            run,
            status="completed",
            events_found=max_results,
            events_created=len(events),
            events_skipped=skipped + max(0, max_results - len(stories)),
            raw_summary={
                "feed": feed,
                "max_results": max_results,
                "keywords": keywords,
                "min_score": min_score,
                "warnings": warnings,
            },
        )
        realtime.emit_event(
            LIVE_EVENT_INGESTION_COMPLETED,
            {
                "id": str(run.id),
                "source_key": HACKER_NEWS_SOURCE_KEY,
                "display_name": "Hacker News",
                "message": f"Hacker News ingestion completed with {len(events)} new events",
                "payload": {
                    "events_found": run.events_found,
                    "events_created": run.events_created,
                    "events_skipped": run.events_skipped,
                },
            },
        )
        return {
            "run_id": run.id,
            "source": "hacker_news",
            "status": run.status,
            "events_found": run.events_found,
            "events_created": run.events_created,
            "events_skipped": run.events_skipped,
            "market_events": events,
            "run": run,
            "source_config": source,
            "events": events,
            "raw_events": raw_events,
            "warnings": warnings,
            "workflows_triggered": workflows_triggered,
        }
    except HackerNewsInvalidFeedError as exc:
        run = service.complete_ingestion_run(
            db,
            run,
            status="failed",
            events_found=0,
            events_created=0,
            events_skipped=0,
            raw_summary={"feed": feed, "warnings": warnings},
            error_message="hn_invalid_feed",
        )
        realtime.emit_event(
            LIVE_EVENT_INGESTION_FAILED,
            {
                "id": str(run.id),
                "source_key": HACKER_NEWS_SOURCE_KEY,
                "display_name": "Hacker News",
                "message": "Hacker News ingestion failed safely",
                "payload": {"error_message": run.error_message, "warnings": warnings},
            },
        )
        raise HTTPException(status_code=400, detail="Invalid Hacker News feed. Use top, new, best, show, ask, or jobs.") from exc
    except HackerNewsIngestionError as exc:
        warnings.append(str(exc))
        run = service.complete_ingestion_run(
            db,
            run,
            status="failed",
            events_found=0,
            events_created=0,
            events_skipped=0,
            raw_summary={"feed": feed, "warnings": warnings},
            error_message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append("Unexpected Hacker News ingestion failure; controlled demo remains available.")
        run = service.complete_ingestion_run(
            db,
            run,
            status="failed",
            events_found=0,
            events_created=0,
            events_skipped=0,
            raw_summary={"feed": feed, "warnings": warnings},
            error_message=str(exc),
        )
    realtime.emit_event(
        LIVE_EVENT_INGESTION_FAILED,
        {
            "id": str(run.id),
            "source_key": HACKER_NEWS_SOURCE_KEY,
            "display_name": "Hacker News",
            "message": "Hacker News ingestion failed safely",
            "payload": {"error_message": run.error_message, "warnings": warnings},
        },
    )
    return {
        "run_id": run.id,
        "source": "hacker_news",
        "status": run.status,
        "events_found": run.events_found,
        "events_created": run.events_created,
        "events_skipped": run.events_skipped,
        "market_events": [],
        "run": run,
        "source_config": source,
        "events": [],
        "raw_events": [],
        "warnings": warnings,
        "workflows_triggered": workflows_triggered,
    }


@router.get("/ingestion-runs", response_model=list[ExternalEventIngestionRunRead])
def list_ingestion_runs(
    db: Session = Depends(get_db),
    limit: int = Query(default=25, ge=1, le=100),
    source: str | None = None,
):
    return ExternalEventService().list_ingestion_runs(db, limit=limit, source_key=source)


@router.get("/raw", response_model=list[ExternalEventRawRead])
def list_raw_live_events(
    db: Session = Depends(get_db),
    source: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
):
    return ExternalEventService().list_raw_events(db, limit=limit, source=source)
