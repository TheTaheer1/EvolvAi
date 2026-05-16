from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.webhook_tasks.process_github_webhook", queue="webhooks")
def process_github_webhook(payload: dict) -> dict:
    return {"status": "accepted", "source": "github", "action": payload.get("action")}


@celery_app.task(name="app.tasks.webhook_tasks.process_market_event", queue="webhooks")
def process_market_event(payload: dict) -> dict:
    return {"status": "accepted", "source": "market", "title": payload.get("title")}
