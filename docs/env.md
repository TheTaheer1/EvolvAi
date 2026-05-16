# Environment Variables

## Required for Local Demo

- `APP_ENV`
- `APP_NAME`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SOCKET_URL`

## Local Env Files

`.env.example` files are templates only. Real secrets belong in ignored local files such as `apps/backend/.env`; do not put real API keys in `apps/backend/.env.example`.

The placeholder value `<user-will-add-real-key-here>` is not a real OpenAI key. EvolvAI treats that value as unconfigured and will use deterministic fallback until it is replaced with a valid key from the OpenAI dashboard.

After changing `apps/backend/.env`, restart Docker containers so both the backend API and Celery worker receive the same LLM provider environment variables:

```bash
docker compose down
docker compose up --build
```

## Optional External Keys

- `OPENAI_API_KEY`: optional OpenAI provider key. OpenAI API access may require active paid credits; insufficient quota falls back deterministically.
- `GROQ_API_KEY`: optional Groq provider key. Set `LLM_PROVIDER=groq` to use `llama-3.3-70b-versatile`.
- `GEMINI_API_KEY`: optional Gemini provider key. Set `LLM_PROVIDER=gemini` to use Gemini 2.0 Flash.
- `XAI_API_KEY`: optional xAI Grok API key. Set `LLM_PROVIDER=xai` or `LLM_PROVIDER=grok` to use the OpenAI-compatible Grok API.
- `GITHUB_TOKEN`: optional for GitHub repository ingestion. Blank still allows unauthenticated read-only search with lower rate limits. It does not enable real PR creation.
- `GITHUB_WEBHOOK_SECRET`: blank skips strict signature checks in development.
- `OMIUM_API_KEY`: blank uses tracing stub.
- `NEWS_API_KEY`: blank disables real news ingestion.

## Safety Flags

- `ALLOW_REAL_GITHUB_PR=false`
- `ALLOW_CODE_EXECUTION=false`
- `ALLOW_EXTERNAL_WRITE_ACTIONS=false`
- `USE_LIVE_AI_OUTPUTS=false` for deterministic demo mode, or `true` for LLM-hybrid mode.
- `USE_LIVE_EXTERNAL_EVENTS=true` for Step 4 GitHub signal ingestion, or `false` for deterministic-only demos.
- `LLM_PROVIDER=groq`
- `LLM_FALLBACK_TO_DEMO=true`
- `ALLOW_LLM_ARTIFACT_CONTENT=true`
- `ALLOW_LLM_FILE_PATHS=false`
- `ALLOW_LLM_VERIFICATION_OVERRIDE=false`
- `GITHUB_INGESTION_ENABLED=true`
- `LIVE_EVENT_AUTO_TRIGGER=false`
- `REPO_ANALYSIS_ENABLED=true`
- `GITHUB_PR_DRAFT=true`

Dangerous writes are disabled by default and must remain disabled for the hackathon demo path.

## Reliable Demo Mode

The dashboard `Run Reliable Demo` button triggers the controlled `ai-meeting-summary` scenario with `demo_speed=fast`. It is the recommended judging path because it does not require working external APIs.

Reliable demo mode still uses the same FastAPI, PostgreSQL, Redis, Celery, Socket.IO, agent pipeline, generated artifact, verification, and PR preview architecture. If the active LLM provider fails, returns invalid JSON, or hits quota, EvolvAI records the fallback and uses deterministic safe output. If GitHub ingestion fails or is rate-limited, the controlled demo remains available.

Keep these safety defaults for the final demo:

```env
ALLOW_REAL_GITHUB_PR=false
ALLOW_CODE_EXECUTION=false
ALLOW_EXTERNAL_WRITE_ACTIONS=false
LLM_FALLBACK_TO_DEMO=true
LIVE_EVENT_AUTO_TRIGGER=false
```

Never put real secrets in `.env.example`, screenshots, or frontend-visible copy. Real keys belong only in ignored local files such as `apps/backend/.env`.

## Step 3 Optional Intelligence

```env
USE_OPENAI_STRUCTURED_OUTPUTS=true
OPENAI_MODEL=gpt-4.1-mini
OPENAI_REASONING_MODEL=gpt-5-mini
OPENAI_MAX_OUTPUT_TOKENS=1500
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_RETRIES=2
OPENAI_TEMPERATURE=0.2
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_API_BASE_URL=https://api.groq.com/openai/v1
GROQ_TIMEOUT_SECONDS=30
GROQ_MAX_OUTPUT_TOKENS=1800
GROQ_TEMPERATURE=0.2
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
GEMINI_TIMEOUT_SECONDS=30
GEMINI_MAX_OUTPUT_TOKENS=1500
GEMINI_TEMPERATURE=0.2
XAI_API_KEY=
XAI_API_BASE_URL=https://api.x.ai/v1
XAI_MODEL=grok-3-mini-latest
XAI_TIMEOUT_SECONDS=30
XAI_MAX_OUTPUT_TOKENS=1500
XAI_TEMPERATURE=0.2
LLM_PROVIDER=groq
LLM_LOG_PROMPTS=false
LLM_LOG_RESPONSES=false
LLM_CACHE_ENABLED=true
MAX_LLM_AGENTS_PER_WORKFLOW=7
LLM_AGENT_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=1
LLM_SEQUENTIAL_AGENT_CALLS=true
ALLOW_LLM_ARTIFACT_CONTENT=true
ALLOW_LLM_FILE_PATHS=false
ALLOW_LLM_VERIFICATION_OVERRIDE=false
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_INGESTION_ENABLED=true
GITHUB_SEARCH_QUERY=AI SaaS automation language:TypeScript stars:>500
GITHUB_SEARCH_MAX_RESULTS=10
GITHUB_RATE_LIMIT_SAFETY_ENABLED=true
GITHUB_REQUEST_TIMEOUT_SECONDS=20
GITHUB_MAX_RETRIES=2
GITHUB_PR_DRAFT=true
GITHUB_PR_BRANCH_PREFIX=evolvai/
GITHUB_PR_COMMIT_AUTHOR_NAME=EvolvAI Bot
GITHUB_PR_COMMIT_AUTHOR_EMAIL=evolvai-bot@example.com
GITHUB_PR_MAX_FILES=10
GITHUB_PR_REQUIRE_VERIFICATION_PASS=true
GITHUB_PR_ALLOWED_ARTIFACT_TYPES=documentation,component,schema,config,plan,report
LIVE_EVENT_MIN_IMPORTANCE_SCORE=0.65
REPO_ANALYSIS_ENABLED=true
REPO_ANALYSIS_MAX_FILES=80
REPO_ANALYSIS_MAX_FILE_SIZE_BYTES=120000
REPO_ANALYSIS_ALLOWED_EXTENSIONS=.ts,.tsx,.js,.jsx,.py,.md,.json,.yml,.yaml,.toml,.env.example
REPO_ANALYSIS_EXCLUDED_DIRS=node_modules,.next,dist,build,.git,__pycache__,.venv,venv,coverage
REPO_ANALYSIS_INCLUDE_CONTENT=false
REPO_ANALYSIS_SUMMARIZE_WITH_LLM=true
CHROMA_MEMORY_ENABLED=false
MEMORY_WRITE_ENABLED=false
```

## Step 4 GitHub Ingestion

GitHub ingestion is read-only. It searches public repositories, stores raw external event metadata with a source/content hash, normalizes each new repository signal into `market_events`, and lets a user manually trigger the existing seven-agent workflow from one selected event.

```env
USE_LIVE_EXTERNAL_EVENTS=true
GITHUB_INGESTION_ENABLED=true
GITHUB_TOKEN=
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_SEARCH_QUERY=AI SaaS automation stars:>500
GITHUB_SEARCH_MAX_RESULTS=10
GITHUB_RATE_LIMIT_SAFETY_ENABLED=true
GITHUB_REQUEST_TIMEOUT_SECONDS=20
GITHUB_MAX_RETRIES=2
LIVE_EVENT_AUTO_TRIGGER=false
LIVE_EVENT_MIN_IMPORTANCE_SCORE=0.65
ALLOW_REAL_GITHUB_PR=false
ALLOW_CODE_EXECUTION=false
ALLOW_EXTERNAL_WRITE_ACTIONS=false
```

`GITHUB_TOKEN` is optional. If it is missing, EvolvAI uses unauthenticated GitHub API requests and records a warning about lower rate limits. If GitHub returns rate limits, auth errors, malformed responses, or network failures, the ingestion run is marked failed or partial and the controlled demo remains available.

After changing `apps/backend/.env`, restart Docker so both the backend and worker receive the same values:

```bash
docker compose down
docker compose up --build
```

Smoke test:

```bash
curl http://localhost:8000/api/v1/live-events/sources
curl -X POST http://localhost:8000/api/v1/live-events/ingest/github \
  -H "Content-Type: application/json" \
  -d '{"query":"AI SaaS automation stars:>500","max_results":5,"trigger_workflows":false}'
curl "http://localhost:8000/api/v1/market-events?source=github&event_type=github_repository_trend"
```

## Step 5 Read-only Repository Analysis

Repository analysis is read-only. EvolvAI reads GitHub repository metadata and the repository tree, filters unsafe paths and large files, detects the tech stack, stores important file metadata, and can attach selected relevant files as workflow context. It does not clone repositories, execute code, create branches, commit changes, or open PRs.

```env
GITHUB_TOKEN=
GITHUB_TARGET_OWNER=
GITHUB_TARGET_REPO=
GITHUB_BASE_BRANCH=main
REPO_ANALYSIS_ENABLED=true
REPO_ANALYSIS_MAX_FILES=80
REPO_ANALYSIS_MAX_FILE_SIZE_BYTES=120000
REPO_ANALYSIS_ALLOWED_EXTENSIONS=.ts,.tsx,.js,.jsx,.py,.md,.json,.yml,.yaml,.toml,.env.example
REPO_ANALYSIS_EXCLUDED_DIRS=node_modules,.next,dist,build,.git,__pycache__,.venv,venv,coverage
REPO_ANALYSIS_INCLUDE_CONTENT=false
REPO_ANALYSIS_SUMMARIZE_WITH_LLM=true
ALLOW_REAL_GITHUB_PR=false
ALLOW_CODE_EXECUTION=false
ALLOW_EXTERNAL_WRITE_ACTIONS=false
```

`GITHUB_TOKEN` remains optional for public repositories. Missing tokens use unauthenticated GitHub requests with lower rate limits. EvolvAI never exposes the token and never reads `.env`, `.ssh`, private keys, secret files, token files, excluded directories, or files above `REPO_ANALYSIS_MAX_FILE_SIZE_BYTES`.

Smoke test:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/analyze \
  -H "Content-Type: application/json" \
  -d '{"owner":"vercel","repo":"next.js","branch":"canary"}'
curl http://localhost:8000/api/v1/repositories/analyses
curl -X POST http://localhost:8000/api/v1/repositories/analyses/{analysis_id}/attach-to-workflow/{workflow_id}
curl http://localhost:8000/api/v1/workflows/{workflow_id}/codebase-context
```

## Step 6 Optional Draft PR Creation

Real GitHub draft PR creation is disabled by default and requires two explicit write flags. It is intended for reviewable proposal PRs only. EvolvAI commits generated preview artifacts under `evolvai/generated/{workflow_id}/...`; it does not commit source files, package files, CI/CD workflows, secrets, or production config.

```env
ALLOW_REAL_GITHUB_PR=false
ALLOW_EXTERNAL_WRITE_ACTIONS=false
ALLOW_CODE_EXECUTION=false
GITHUB_TOKEN=
GITHUB_TARGET_OWNER=
GITHUB_TARGET_REPO=
GITHUB_BASE_BRANCH=main
GITHUB_PR_DRAFT=true
GITHUB_PR_BRANCH_PREFIX=evolvai/
GITHUB_PR_COMMIT_AUTHOR_NAME=EvolvAI Bot
GITHUB_PR_COMMIT_AUTHOR_EMAIL=evolvai-bot@example.com
GITHUB_PR_MAX_FILES=10
GITHUB_PR_REQUIRE_VERIFICATION_PASS=true
GITHUB_PR_ALLOWED_ARTIFACT_TYPES=documentation,component,schema,config,plan,report
```

All safety gates must pass before a draft PR is opened: real PR flag, external write flag, GitHub token, target repository, passing verification report, PR preview, generated artifacts, safe paths, safe content, allowed artifact types, and max file count. If any gate fails, EvolvAI does not create a branch, commit, or PR.

Safety check:

```bash
curl http://localhost:8000/api/v1/workflows/{workflow_id}/pr-safety-check
curl -X POST http://localhost:8000/api/v1/workflows/{workflow_id}/open-draft-pr
```

With default flags, the second command returns `403` with a clear disabled message.

## Groq Provider

Groq is the recommended provider for the full seven-agent LLM-hybrid demo. Agents call the unified `LLMService`; each agent builds deterministic fallback output first, validates provider JSON with strict Pydantic schemas, and records metadata in `llm_invocations`.

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
USE_LIVE_AI_OUTPUTS=true
LLM_FALLBACK_TO_DEMO=true
ALLOW_REAL_GITHUB_PR=false
ALLOW_CODE_EXECUTION=false
ALLOW_EXTERNAL_WRITE_ACTIONS=false
ALLOW_LLM_ARTIFACT_CONTENT=true
ALLOW_LLM_FILE_PATHS=false
ALLOW_LLM_VERIFICATION_OVERRIDE=false
```

Execution remains safe: the LLM may generate artifact text only, generated paths are mapped or sanitized by the backend, files are written only inside `generated_runs/{workflow_id}`, and generated code is never executed. Verification remains deterministic-rule-first; LLM verification output is advisory and cannot override failed checks.

## xAI Grok Provider

xAI Grok uses an OpenAI-compatible API surface at `https://api.x.ai/v1`. It remains available as a provider, but `LLM_PROVIDER=groq` refers to Groq, while `LLM_PROVIDER=xai` or `LLM_PROVIDER=grok` refers to xAI Grok.

```env
LLM_PROVIDER=xai
XAI_API_KEY=your_xai_key_here
XAI_API_BASE_URL=https://api.x.ai/v1
XAI_MODEL=grok-3-mini-latest
USE_LIVE_AI_OUTPUTS=true
LLM_FALLBACK_TO_DEMO=true
ALLOW_REAL_GITHUB_PR=false
ALLOW_CODE_EXECUTION=false
ALLOW_EXTERNAL_WRITE_ACTIONS=false
```

Use `apps/backend/.env` for real provider keys. Keep `apps/backend/.env.example` blank for secrets. If Groq, OpenAI, Gemini, or xAI fails because of auth, quota, rate limits, model access, timeout, malformed JSON, or schema validation, EvolvAI records sanitized metadata and falls back to deterministic output. After changing `LLM_PROVIDER`, provider API keys, or model names, recreate the backend and worker containers:

```bash
docker compose up -d --force-recreate backend worker
```

Check the active provider without exposing secrets:

```bash
curl http://localhost:8000/api/v1/llm/status
curl http://localhost:8000/api/v1/llm/test
```

Frontend:

```env
NEXT_PUBLIC_LIVE_AI_ENABLED=false
NEXT_PUBLIC_LIVE_EXTERNAL_EVENTS_ENABLED=true
NEXT_PUBLIC_SHOW_LIVE_EVENT_BADGES=true
```

## CORS

`CORS_ORIGINS` supports comma-separated strings or JSON lists.

Examples:

```env
CORS_ORIGINS=http://localhost:3000
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```
