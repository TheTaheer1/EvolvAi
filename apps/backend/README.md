# EvolvAI Backend

FastAPI, SQLAlchemy, Celery, Socket.IO, and LangGraph skeleton for the Step 1 foundation.

Run locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.socket_app:app --host 0.0.0.0 --port 8000 --reload
```

Worker:

```bash
celery -A app.tasks.celery_app.celery_app worker -Q workflows,webhooks,scheduled,pr --loglevel=info
```
