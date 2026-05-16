# EvolvAI

EvolvAI is an autonomous multi-agent SaaS evolution demo. Step 1 created the monorepo foundation. Step 2 added the deterministic controlled demo workflow. Step 3 added hybrid intelligence: all seven agents can use the active LLM provider with deterministic fallback. Step 4 adds real external event ingestion from GitHub repository/search signals. Step 5 adds read-only repository intelligence. Step 6 adds optional real GitHub draft PR creation behind explicit safety flags.

## Final Demo Path

Use `/dashboard` for the judge-ready walkthrough. The primary path is **Run Reliable Demo**:

1. Open `http://localhost:3000/dashboard`.
2. Click `Run Reliable Demo`.
3. EvolvAI triggers `ai-meeting-summary` with `demo_speed=fast`.
4. Open the workflow detail page and show the seven-agent pipeline: Watcher, Research, Strategy, Planner, Execution, Verification, and PR.
5. Show explainability, impact analysis, generated artifacts, verification, and the preview-only PR.

This path uses controlled data and deterministic fallback, so it remains demoable when Groq/OpenAI/GitHub are unavailable or rate-limited. If Socket.IO disconnects, the UI polls workflow status through REST. If the workflow stays queued, start the Celery worker.

The secondary path is **Run Live Signal Demo**:

1. Enter a GitHub query such as `AI SaaS automation stars:>500`.
2. Click `Ingest GitHub Signals`.
3. Pick a GitHub event and click `Run Workflow`.
4. EvolvAI runs the same seven-agent workflow on the real external signal.

Safety defaults stay visible in the UI: real PR creation, code execution, and external write actions are disabled unless explicitly opted in.

```mermaid
flowchart LR
  UI[Next.js Dashboard] --> API[FastAPI API]
  UI <-- Socket.IO --> SIO[Socket.IO ASGI]
  API --> PG[(PostgreSQL)]
  API --> Redis[(Redis)]
  API --> Celery[Celery Worker]
  Celery --> Graph[LangGraph Runner]
  Graph --> Watcher --> Research --> Strategy --> Planning --> Execution --> Verification --> PRPreview[PR Preview]
  Watcher -. optional structured JSON .-> LLM[LLMService]
  Research -. optional structured JSON .-> LLM
  Strategy -. optional structured JSON .-> LLM
  Planning -. optional structured JSON .-> LLM
  Execution -. safe artifact text only .-> LLM
  Verification -. advisory explanation only .-> LLM
  PRPreview -. optional preview wording .-> LLM
  GitHub[GitHub Search API] -. optional .-> API
  Repo[GitHub Repository Tree] -. read-only .-> API
  API -. optional gated draft PR .-> GitHubPR[GitHub Pull Requests]
  Execution --> SafeDir[apps/backend/generated_runs/{workflow_id}]
  Celery --> PG
```

## What Step 2 Adds

- AcmeFlow demo company profile stored in `company_profiles`.
- Four deterministic demo scenarios stored in `demo_scenarios`.
- Scenario selector and Run Demo Workflow button on `/dashboard`.
- Rich deterministic outputs from Watcher, Research, Strategy, Planning, Execution, Verification, and PR agents.
- Explainability records for every major agent step.
- Impact analysis scoring with priority calculation.
- Safe generated artifact storage in PostgreSQL and `apps/backend/generated_runs/{workflow_id}/`.
- Verification report with path, content, secret, and dangerous command checks.
- PR Center with planned or blocked preview PRs only.
- Workflow detail page with trigger event, evidence, impact, plan, artifacts, verification, PR preview, logs, and agent timeline.

## What Step 3 Adds

- `LLMService` routes structured calls through the active provider (`groq`, `openai`, `gemini`, or `xai`) behind `USE_LIVE_AI_OUTPUTS`.
- Strict Pydantic schemas for Watcher, Research, Strategy, Planner, Execution, Verification, and PR agent LLM outputs.
- All seven agents build deterministic fallback output first and record `llm_invocations` metadata for success, skipped, or fallback paths.
- Deterministic fallback for missing keys, malformed output, timeouts, rate limits, and API failures.
- `llm_invocations` metadata table with provider/model/status/latency/token metadata; prompts and responses are not stored by default.
- Dashboard, Market Events, Debug, and Workflow Detail UI badges for deterministic, LLM enhanced, fallback, live event, and controlled demo modes.

## What Step 4 Adds

- GitHub repository search ingestion behind `USE_LIVE_EXTERNAL_EVENTS` and `GITHUB_INGESTION_ENABLED`.
- `external_event_sources`, ingestion run, and raw event tables with source/content-hash dedupe.
- Live GitHub repository signals normalized into `market_events` with source, event type, URL, summary, raw payload, and importance score.
- `GET /market-events?source=github&event_type=github_repository_trend` filters live events.
- `POST /market-events/{event_id}/trigger-workflow` queues the existing seven-agent pipeline from a real ingested event.
- Dashboard and Market Events UI controls for ingesting GitHub signals and triggering workflows from live events.

## What Step 5 Adds

- Read-only GitHub repository analysis behind `REPO_ANALYSIS_ENABLED`.
- `repository_analyses`, `repository_files`, and `codebase_contexts` tables for target repo metadata, important file detection, stack detection, and workflow-attached context.
- `/repositories` UI for owner/repo/branch analysis, detected stack, and important files.
- `POST /repositories/analyses/{analysis_id}/attach-to-workflow/{workflow_id}` to attach safe codebase context to an existing workflow.
- Planner, Execution, and PR agents use attached codebase context as suggested touchpoints only; generated artifacts still stay in `generated_runs/{workflow_id}`.

## What Step 6 Adds

- Optional real GitHub draft PR creation through `POST /workflows/{workflow_id}/open-draft-pr`.
- `GET /workflows/{workflow_id}/pr-safety-check` explains every gate before any external write.
- Real PR creation requires both `ALLOW_REAL_GITHUB_PR=true` and `ALLOW_EXTERNAL_WRITE_ACTIONS=true`.
- Draft PRs commit generated preview artifacts only under `evolvai/generated/{workflow_id}/...`.
- Verification must pass, artifacts must be safe, and code execution remains disabled.

## Run With Docker

```bash
cd evolvai
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env.local
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Dashboard: http://localhost:3000/dashboard
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

Migrations run automatically in the backend container. Manual commands:

```bash
make migrate
make seed
```

Docker seed alternative:

```bash
docker compose exec backend python scripts/seed_demo_data.py
```

## Demo Scenarios

1. `ai-meeting-summary`: Competitor launches AI meeting summarization.
2. `github-rag-trend`: RAG repositories are trending on GitHub.
3. `security-compliance-shift`: Market shift toward AI security compliance.
4. `competitor-automation`: Competitor releases autonomous workflow builder.

All scenarios are deterministic. Missing OpenAI, GitHub, Chroma, news, or tracing credentials do not break the demo.

## Runtime Modes

Deterministic demo mode:

```env
USE_LIVE_AI_OUTPUTS=false
USE_LIVE_EXTERNAL_EVENTS=false
```

Full LLM-hybrid mode with Groq:

```env
USE_LIVE_AI_OUTPUTS=true
LLM_PROVIDER=groq
GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.3-70b-versatile
LLM_FALLBACK_TO_DEMO=true
```

Live GitHub event mode:

```env
USE_LIVE_EXTERNAL_EVENTS=true
GITHUB_INGESTION_ENABLED=true
GITHUB_TOKEN=
```

`GITHUB_TOKEN` is optional. Without it, EvolvAI uses unauthenticated GitHub requests with lower rate limits. If Groq, OpenAI, Gemini, xAI, or GitHub is unavailable, EvolvAI falls back safely and keeps the controlled demo usable.

Read-only repository analysis:

```env
REPO_ANALYSIS_ENABLED=true
GITHUB_TARGET_OWNER=
GITHUB_TARGET_REPO=
GITHUB_BASE_BRANCH=main
REPO_ANALYSIS_MAX_FILES=80
REPO_ANALYSIS_INCLUDE_CONTENT=false
REPO_ANALYSIS_SUMMARIZE_WITH_LLM=true
```

Repository analysis reads public GitHub metadata and tree data. It filters secrets, large files, vendor/build folders, and unsafe paths; it does not create branches, commits, PRs, or execute code.

Optional draft PR mode:

```env
ALLOW_REAL_GITHUB_PR=false
ALLOW_EXTERNAL_WRITE_ACTIONS=false
ALLOW_CODE_EXECUTION=false
GITHUB_PR_DRAFT=true
GITHUB_PR_BRANCH_PREFIX=evolvai/
GITHUB_PR_MAX_FILES=10
```

Draft PR mode is disabled by default. To enable it for a controlled test, set both write flags to `true`, provide `GITHUB_TOKEN`, `GITHUB_TARGET_OWNER`, and `GITHUB_TARGET_REPO`, and use only a repository where opening a draft PR is acceptable.

## Curl Demo

Get scenarios:

```bash
curl http://localhost:8000/api/v1/demo/scenarios
```

Trigger the meeting summary scenario:

```bash
curl -X POST http://localhost:8000/api/v1/demo/scenarios/ai-meeting-summary/trigger \
  -H "Content-Type: application/json" \
  -d '{"demo_speed":"normal"}'
```

Get workflow details:

```bash
curl http://localhost:8000/api/v1/workflows/{workflow_id}
curl http://localhost:8000/api/v1/workflows/{workflow_id}/generated-artifacts
curl http://localhost:8000/api/v1/workflows/{workflow_id}/impact-analysis
curl http://localhost:8000/api/v1/workflows/{workflow_id}/pr-preview
```

Step 4 live event commands:

```bash
curl http://localhost:8000/api/v1/llm/status
curl http://localhost:8000/api/v1/llm/invocations
curl http://localhost:8000/api/v1/live-events/sources

curl -X POST http://localhost:8000/api/v1/live-events/ingest/github \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI SaaS automation stars:>500",
    "max_results": 10,
    "trigger_workflows": false
  }'

curl -X POST http://localhost:8000/api/v1/market-events/{event_id}/trigger-workflow
curl "http://localhost:8000/api/v1/market-events?source=github&event_type=github_repository_trend"
```

Step 5 repository analysis commands:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "vercel",
    "repo": "next.js",
    "branch": "canary"
  }'

curl http://localhost:8000/api/v1/repositories/analyses
curl http://localhost:8000/api/v1/repositories/analyses/{analysis_id}
curl -X POST http://localhost:8000/api/v1/repositories/analyses/{analysis_id}/attach-to-workflow/{workflow_id}
curl http://localhost:8000/api/v1/workflows/{workflow_id}/codebase-context
```

Step 6 draft PR safety commands:

```bash
curl http://localhost:8000/api/v1/workflows/{workflow_id}/pr-safety-check

curl -X POST http://localhost:8000/api/v1/workflows/{workflow_id}/open-draft-pr
```

With default flags, `open-draft-pr` returns `403` and does not create a branch, commit, or PR.

## Safety Flags

Dangerous actions are disabled by default:

```env
ALLOW_REAL_GITHUB_PR=false
ALLOW_CODE_EXECUTION=false
ALLOW_EXTERNAL_WRITE_ACTIONS=false
USE_LIVE_AI_OUTPUTS=false
USE_LIVE_EXTERNAL_EVENTS=true
USE_OPENAI_STRUCTURED_OUTPUTS=true
LLM_FALLBACK_TO_DEMO=true
GITHUB_INGESTION_ENABLED=true
LIVE_EVENT_AUTO_TRIGGER=false
ALLOW_GENERATED_FILES=true
GENERATED_RUNS_DIR=generated_runs
```

Real vs controlled:

- Real: FastAPI, PostgreSQL persistence, Redis/Celery async execution, Socket.IO realtime, Alembic migrations, Next.js dashboard.
- Controlled: market data, research evidence, agent outputs, generated artifacts, verification, and PR preview have deterministic fixtures/templates.
- Optional: the active LLM provider can enhance all seven agents with strict schema validation and fallback; GitHub can ingest public repository signals.
- Optional: read-only repository analysis can add stack and relevant-file context to workflow planning.
- Optional but disabled by default: real GitHub draft PR creation after verification passes.
- Disabled by default: real GitHub PR creation, code execution, shell command execution, external write actions, auto-merge, and automatic live-event workflow triggering.

## Local Development

Backend:

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python3 scripts/seed_demo_data.py
uvicorn app.socket_app:app --host 0.0.0.0 --port 8000 --reload
```

Worker:

```bash
cd apps/backend
celery -A app.tasks.celery_app.celery_app worker -Q workflows,webhooks,scheduled,pr --loglevel=info
```

Frontend:

```bash
cd apps/frontend
npm install
npm run dev -- --hostname 0.0.0.0
```

## Troubleshooting

- No scenarios visible: run `make seed` or call `GET /api/v1/dashboard/demo-state`.
- Workflow stuck queued: Celery worker is probably not running; start `docker compose up worker`.
- Socket disconnected: REST pages still work; check Redis and backend logs.
- No artifacts generated: check worker logs and ensure `ALLOW_GENERATED_FILES=true`; DB still stores artifact content if file writing fails.
- Database migration issue: run `docker compose exec backend alembic upgrade head`.
- Redis unavailable: trigger endpoint returns 503 because workflows cannot enqueue.
- Missing API keys: expected; deterministic fallbacks are used.
- GitHub rate limit: add `GITHUB_TOKEN` or rerun later; controlled demo remains available.
- LLM fallback badge: the active provider is disabled, rate-limited, invalid, or returned unusable JSON, so deterministic safe output was used.
- Live events empty: click `Ingest GitHub Signals` on `/dashboard` or `/market-events`, or enable `USE_LIVE_EXTERNAL_EVENTS=true`.
- Live source disabled: update `apps/backend/.env` with `USE_LIVE_EXTERNAL_EVENTS=true` and `GITHUB_INGESTION_ENABLED=true`, then restart Docker.
- Repository analysis failed: verify owner/repo/branch, add `GITHUB_TOKEN` for private or rate-limited repos, and keep `REPO_ANALYSIS_INCLUDE_CONTENT=false` for the safest demo path.
- Draft PR button blocked: inspect `/api/v1/workflows/{workflow_id}/pr-safety-check`; default flags intentionally block external writes.

## Verification

Useful checks:

```bash
docker compose config
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_demo_data.py
docker compose exec backend pytest
cd apps/frontend && npm run build
cd apps/frontend && npm run lint
```
