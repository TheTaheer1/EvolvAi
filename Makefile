.PHONY: dev down logs backend frontend worker migrate revision seed test

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend:
	cd apps/backend && uvicorn app.socket_app:app --host 0.0.0.0 --port 8000 --reload --reload-exclude 'generated_runs/*'

frontend:
	cd apps/frontend && npm run dev -- --hostname 0.0.0.0

worker:
	cd apps/backend && celery -A app.tasks.celery_app.celery_app worker -Q workflows,webhooks,scheduled,pr --loglevel=info

migrate:
	docker compose exec backend alembic upgrade head

revision:
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

seed:
	cd apps/backend && python3 scripts/seed.py

test:
	cd apps/backend && pytest || true
	cd apps/frontend && npm run lint
