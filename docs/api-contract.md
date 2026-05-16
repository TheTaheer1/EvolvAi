# API Contract

Base URL: `http://localhost:8000/api/v1`

## Health

- `GET /health`
- `GET /health/db`
- `GET /health/redis`
- `GET /health/chroma`

Example:

```json
{"status":"ok","app":"EvolvAI","environment":"development"}
```

## Workflows

- `POST /workflows/trigger`
- `GET /workflows?limit=20&status=running`
- `GET /workflows/{workflow_id}`
- `POST /workflows/{workflow_id}/cancel`
- `GET /workflows/{workflow_id}/timeline`

Trigger request:

```json
{
  "trigger_type": "manual",
  "source": "dashboard",
  "payload": {
    "company": "Demo SaaS",
    "event": "Competitor launched AI automation feature"
  }
}
```

## Agents

- `GET /agents`
- `GET /workflows/{workflow_id}/agents`

## Market Events

- `GET /market-events`
- `GET /market-events?source=github&event_type=github_repository_trend`
- `GET /market-events?source=hacker_news`
- `POST /market-events`
- `GET /market-events/{event_id}`
- `POST /market-events/{event_id}/trigger-workflow`

## Decisions

- `GET /decisions`
- `GET /decisions/{decision_id}`
- `GET /workflows/{workflow_id}/decisions`

## Pull Requests

- `GET /prs`
- `GET /prs/{pr_id}`
- `GET /workflows/{workflow_id}/prs`
- `GET /workflows/{workflow_id}/pr-safety-check`
- `POST /workflows/{workflow_id}/open-draft-pr`
- `POST /prs/{pr_id}/open-real-pr`

`open-real-pr` and `open-draft-pr` return `403` unless both `ALLOW_REAL_GITHUB_PR=true` and `ALLOW_EXTERNAL_WRITE_ACTIONS=true`.

Draft PR safety response:

```json
{
  "can_open_pr": false,
  "checks": [
    {"name": "real_pr_enabled", "passed": false, "message": "ALLOW_REAL_GITHUB_PR must be true."},
    {"name": "verification_passed", "passed": true, "message": "Verification must pass before opening a draft PR."}
  ],
  "prepared_files": []
}
```

When enabled and safe, `POST /workflows/{workflow_id}/open-draft-pr` opens a draft PR with generated preview artifacts only and updates `pull_request_history` to `status="opened"`. It never auto-merges.

## Logs

- `GET /logs`
- `GET /workflows/{workflow_id}/logs`

## Dashboard

- `GET /dashboard/summary`
- `GET /dashboard/activity`
- `GET /dashboard/live-state`

## Step 2 Demo

- `GET /company-profile/default`
- `GET /company-profiles`
- `GET /demo/scenarios`
- `GET /demo/scenarios/{scenario_key}`
- `POST /demo/scenarios/{scenario_key}/trigger`
- `GET /dashboard/demo-state`
- `GET /workflows/{workflow_id}/explainability`
- `GET /workflows/{workflow_id}/impact-analysis`
- `GET /workflows/{workflow_id}/generated-artifacts`
- `GET /workflows/{workflow_id}/verification-report`
- `GET /workflows/{workflow_id}/pr-preview`
- `POST /workflows/{workflow_id}/pr-preview/regenerate`

## Step 3 LLM

- `GET /llm/config`
- `GET /llm/status`
- `POST /llm/test`
- `GET /llm/invocations`
- `GET /llm/invocations?workflow_id={workflow_id}`

LLM endpoints expose only safe metadata: provider, model, agent name, status, latency, token counts, fallback flag, and structured-output flag. Raw prompts and responses are not exposed by default. In full LLM-hybrid mode the latest workflow should show invocation rows for `watcher_agent`, `research_agent`, `strategy_agent`, `planner_agent`, `execution_agent`, `verification_agent`, and `pr_agent`.

## Step 4 Live Events

- `GET /live-events/sources`
- `POST /live-events/ingest/github`
- `POST /live-events/ingest/hacker-news`
- `GET /live-events/ingestion-runs`
- `GET /live-events/ingestion-runs?source=hacker_news`
- `GET /live-events/raw`
- `GET /live-events/raw?source=hacker_news`
- `POST /market-events/{event_id}/trigger-workflow`

GitHub ingest request:

```json
{
  "query": "AI SaaS automation stars:>500",
  "max_results": 10,
  "trigger_workflows": false
}
```

GitHub ingestion is optional. Missing tokens use unauthenticated requests with lower rate limits. Rate limits and API failures produce a failed ingestion run, not an app crash.

GitHub ingest response:

```json
{
  "run_id": "uuid",
  "source": "github",
  "status": "completed",
  "events_found": 10,
  "events_created": 7,
  "events_skipped": 3,
  "market_events": []
}
```

`events_skipped` counts duplicate raw events based on `source + content_hash`. Triggering a workflow from a live event creates a `live_market_event` workflow with `demo_mode=false`, `live_event=true`, safe generated workspace metadata, and real PR creation disabled.

Hacker News ingest request:

```json
{
  "feed": "top",
  "max_results": 20,
  "keywords": ["ai", "saas", "agent"],
  "min_score": 20,
  "trigger_workflows": false
}
```

Hacker News ingest response:

```json
{
  "run_id": "uuid",
  "source": "hacker_news",
  "status": "completed",
  "events_found": 20,
  "events_created": 5,
  "events_skipped": 15,
  "market_events": [],
  "warnings": []
}
```

Supported Hacker News feeds are `top`, `new`, `best`, `show`, `ask`, and `jobs`. Hacker News requires no API key. EvolvAI fetches official story metadata only, does not scrape article bodies or comments, strips story HTML before display, dedupes by Hacker News item identity, and treats story text as untrusted market-signal data.

## Step 5 Repositories

- `POST /repositories/analyze`
- `GET /repositories/analyses`
- `GET /repositories/analyses/{analysis_id}`
- `POST /repositories/analyses/{analysis_id}/attach-to-workflow/{workflow_id}`
- `GET /workflows/{workflow_id}/codebase-context`

Repository analyze request:

```json
{
  "owner": "vercel",
  "repo": "next.js",
  "branch": "canary"
}
```

Repository analysis response includes safe metadata only:

```json
{
  "id": "uuid",
  "owner": "vercel",
  "repo": "next.js",
  "branch": "canary",
  "status": "completed",
  "detected_stack": ["Next.js", "React", "TypeScript"],
  "file_count": 12000,
  "analyzed_file_count": 80,
  "files": [
    {
      "path": "package.json",
      "file_type": "project_manifest",
      "language": "JSON",
      "importance_score": 0.75
    }
  ]
}
```

Repository analysis is read-only. It scans metadata/tree entries, filters secrets and large files, stores important file metadata, and can attach selected relevant files to a workflow as `codebase_context`. It does not clone repositories, execute code, create branches, commit, or open PRs.

## Step 6 Draft PRs

Draft PR creation is optional and disabled by default. The PR service validates all gates, maps generated artifacts into `evolvai/generated/{workflow_id}/...`, rejects dangerous content and unsafe paths, creates a branch from `GITHUB_BASE_BRANCH`, commits generated preview artifacts, and opens a draft PR. Failed GitHub calls update the PR preview to `status="failed"` with a sanitized `error_message`.

## Webhooks

- `POST /webhooks/github`
- `POST /webhooks/market-event`
- `POST /webhooks/demo-trigger`
