# Development

## Docker

```bash
docker compose up --build
docker compose logs -f backend worker frontend
```

## Backend

```bash
cd apps/backend
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.socket_app:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend

```bash
cd apps/frontend
npm install
npm run dev -- --hostname 0.0.0.0
```

## Worker

```bash
cd apps/backend
celery -A app.tasks.celery_app.celery_app worker -Q workflows,webhooks,scheduled,pr --loglevel=info
```

## Testing

```bash
cd apps/backend && pytest
cd apps/frontend && npm run lint
```

## Git Workflow

Keep Step 1 focused on architecture, reliability, and safe stubs. Do not add production auth, billing, multi-tenancy, or real external write behavior without explicit Step 2 scope.
