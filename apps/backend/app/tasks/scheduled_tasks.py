from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.scheduled_tasks.poll_market_sources", queue="scheduled")
def poll_market_sources() -> dict:
    return {"status": "skipped", "reason": "Step 1 scheduled polling skeleton only"}
