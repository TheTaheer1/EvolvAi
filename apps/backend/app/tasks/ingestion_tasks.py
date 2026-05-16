from app.db.session import SessionLocal
from app.schemas.external_event import LiveEventIngestRequest
from app.services.external_event_service import GITHUB_SOURCE_KEY, ExternalEventService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.ingestion_tasks.ingest_github_signals", queue="scheduled")
def ingest_github_signals(query: str, max_results: int = 10) -> dict:
    """Lightweight scheduled hook; API ingestion remains the primary Step 3 path."""
    from app.ingestion.github_ingestion import GitHubIngestionService

    db = SessionLocal()
    service = ExternalEventService()
    run = service.start_ingestion_run(db, GITHUB_SOURCE_KEY)
    try:
        request = LiveEventIngestRequest(query=query, max_results=max_results)
        repos, warnings = GitHubIngestionService().ingest_github_search(
            request.query,
            request.max_results,
        )
        events, _raw, skipped = service.normalize_and_store_github_repositories(db, repos)
        run = service.complete_ingestion_run(
            db,
            run,
            status="completed",
            events_found=len(repos),
            events_created=len(events),
            events_skipped=skipped,
            raw_summary={"warnings": warnings},
        )
        return {"status": run.status, "events_created": run.events_created, "events_skipped": run.events_skipped}
    except Exception as exc:  # noqa: BLE001
        run = service.complete_ingestion_run(
            db,
            run,
            status="failed",
            events_found=0,
            events_created=0,
            events_skipped=0,
            error_message=str(exc),
        )
        return {"status": run.status, "error": run.error_message}
    finally:
        db.close()
