# Demo Script

## 2-3 Minute Judge Walkthrough

1. Open `http://localhost:3000/dashboard`.
2. Say: "This is EvolvAI, an autonomous SaaS evolution platform."
3. Point to the safety badges: real PR creation, code execution, and external write actions are disabled by default.
4. Say: "We can run a reliable controlled demo or ingest real GitHub signals."
5. Click `Run Reliable Demo`.
6. Open the active workflow detail page.
7. Explain the seven-agent story:
   - Watcher detects and normalizes the signal.
   - Research validates market context.
   - Strategy scores business impact and urgency.
   - Planner creates a safe implementation plan.
   - Execution generates preview artifacts only.
   - Verification checks paths, secrets, dangerous commands, and PR readiness.
   - PR Agent prepares a preview-only pull request.
8. Show explainability, impact analysis, generated artifacts, verification passed, and PR preview.
9. Optional: return to the dashboard, ingest GitHub signals, and trigger the same workflow from a real GitHub event.
10. Close with: "Everything is autonomous, but safety-gated. Real PR creation and code execution are disabled by default, and deterministic fallback keeps the demo reliable."

If live LLM or GitHub calls rate-limit, point to `Fallback Used`: that means EvolvAI safely used deterministic output and the workflow continued.

## Path A: Controlled Demo

1. Open `http://localhost:3000/dashboard`.
2. Point to the badges: `Controlled Demo Mode`, `Real PR creation disabled`, and `Generated safely in preview workspace`.
3. Show the AcmeFlow company profile: B2B SaaS productivity platform, modules, target users, goals, competitors, and small-team engineering capacity.
4. Select `Competitor launches AI meeting summarization`.
5. Click `Run Demo Workflow`.
6. Explain the live sequence:
   - Watcher Agent normalizes the market event.
   - Research Agent validates the signal with controlled evidence.
   - Strategy Agent calculates business impact, urgency, confidence, risk, and priority.
   - Planning Agent creates implementation tasks and artifact plan.
   - Execution Agent generates safe preview artifacts only.
   - Verification Agent checks path safety, content, secrets, dangerous commands, and PR readiness.
   - PR Agent creates a PR preview/intention without touching GitHub.
7. Open the workflow detail page for the latest workflow.
8. Show explainability cards: reasoning, evidence, assumptions, risks, and confidence.
9. Show impact analysis chart and priority.
10. Show generated artifacts and code/markdown/JSON previews.
11. Show verification report.
12. Show PR preview in PR Center.

## Path B: LLM Enhanced Demo

1. Keep Path A ready as the reliable fallback.
2. Set `USE_LIVE_AI_OUTPUTS=true`, `LLM_PROVIDER=groq`, and configure `GROQ_API_KEY`.
3. Trigger the same AI meeting summary scenario.
4. Open the workflow detail page and point to `LLM Enhanced` badges plus LLM invocation metadata.
5. Explain that all seven agents are LLM-hybrid, but Execution only accepts safe preview artifact text and Verification remains deterministic-rule-first.
6. If Groq fails or rate-limits, show `Fallback Used` and emphasize the workflow still completes.

## Path C: Live GitHub Event Ingestion

1. Open `/market-events`.
2. Select `Live External Events`.
3. Click `Ingest GitHub Signals`.
4. Show GitHub events with source badge, importance score, source URL, and dedupe behavior. If no token is configured, explain that unauthenticated GitHub search still works but has lower rate limits.
5. Click `Trigger Workflow` on one live event.
6. Open the workflow detail page and show the same seven-agent pipeline, explainability, impact, artifacts, verification, and PR preview.

## Path D: Read-only Repository Intelligence

1. Open `/repositories`.
2. Enter a public repository such as `vercel/next.js` on branch `canary`.
3. Click `Analyze Repository`.
4. Show detected stack, analyzed file count, and important files. Emphasize that EvolvAI scanned metadata/tree entries only, excluded secrets/large files, and made no repo changes.
5. Attach the analysis to a workflow from the workflow detail or curl path.
6. Open the workflow detail page and show the Codebase Context panel with relevant files, architecture summary, hints, and risks.
7. Point out that Planner, Execution, and PR agents use this context as suggested touchpoints while generated artifacts still remain preview-only.

## Path E: Optional Draft PR Gate

1. Open a completed workflow detail page.
2. Scroll to `PR preview`.
3. Show the Draft PR safety checklist.
4. With default flags, point out the blocked checks: real PR creation and external writes are disabled.
5. Explain that enabling draft PR creation requires `ALLOW_REAL_GITHUB_PR=true`, `ALLOW_EXTERNAL_WRITE_ACTIONS=true`, a valid `GITHUB_TOKEN`, target owner/repo, passing verification, and safe generated artifacts.
6. Emphasize that Step 6 opens draft PRs only, never auto-merges, never executes code, and commits generated preview artifacts only.

Judge recommendation: run Path A first because it is deterministic. Then show Path B or C if internet/API keys are available.

## What To Emphasize

- FastAPI API with PostgreSQL persistence.
- Redis queue and Celery worker executing asynchronously.
- Socket.IO realtime updates.
- LangGraph-compatible seven-agent orchestration.
- Deterministic demo data for reliability.
- Optional LLM reasoning with deterministic fallback.
- Optional GitHub ingestion normalized into the same MarketEvent pipeline.
- Optional read-only repository intelligence improves planning without touching the source repo.
- Optional draft PR creation exists, but is explicitly gated and disabled by default.
- Missing GitHub token or rate limits do not break the product; ingestion reports the failure and the controlled demo remains ready.
- Safe autonomous execution: generated files stay inside `apps/backend/generated_runs/{workflow_id}/`.
- Real GitHub PR creation is disabled unless `ALLOW_REAL_GITHUB_PR=true`.

## Curl Fallback

```bash
curl http://localhost:8000/api/v1/demo/scenarios

curl -X POST http://localhost:8000/api/v1/demo/scenarios/ai-meeting-summary/trigger \
  -H "Content-Type: application/json" \
  -d '{"demo_speed":"normal"}'

curl -X POST http://localhost:8000/api/v1/live-events/ingest/github \
  -H "Content-Type: application/json" \
  -d '{"query":"AI SaaS automation stars:>500","max_results":5,"trigger_workflows":false}'

curl "http://localhost:8000/api/v1/market-events?source=github&event_type=github_repository_trend"

curl -X POST http://localhost:8000/api/v1/market-events/{event_id}/trigger-workflow

curl -X POST http://localhost:8000/api/v1/repositories/analyze \
  -H "Content-Type: application/json" \
  -d '{"owner":"vercel","repo":"next.js","branch":"canary"}'

curl -X POST http://localhost:8000/api/v1/repositories/analyses/{analysis_id}/attach-to-workflow/{workflow_id}

curl http://localhost:8000/api/v1/workflows/{workflow_id}/codebase-context

curl http://localhost:8000/api/v1/workflows/{workflow_id}/pr-safety-check

curl -X POST http://localhost:8000/api/v1/workflows/{workflow_id}/open-draft-pr
```
