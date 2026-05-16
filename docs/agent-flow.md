# Agent Flow

EvolvAI uses seven agents sharing an `AgentState` typed dictionary. Step 3 keeps the deterministic path intact and makes every agent LLM-hybrid through `LLMService`.

## Agents

- `watcher_agent`: deterministic normalization first, optional LLM normalization with backend validation.
- `research_agent`: deterministic research first, optional LLM-enhanced research summary and evidence.
- `strategy_agent`: deterministic impact baseline, optional LLM decision blended with backend-owned scoring.
- `planner_agent`: deterministic plan first, optional LLM implementation plan with path sanitization.
- `execution_agent`: deterministic artifacts first, optional LLM artifact content only; no source edits and no code execution.
- `verification_agent`: rule-based safety verification remains authoritative; optional LLM explanation is advisory only.
- `pr_agent`: planned/blocked PR preview only, optional LLM wording for the preview body.

## Flow

```text
watcher -> research -> strategy -> planner -> execution -> verification -> pr
```

If strategy returns `should_act=false`, the runner skips later nodes and marks the workflow `no_action_needed`. The default demo path returns `true`.

LangGraph `StateGraph` is attempted at runtime. If the installed LangGraph API is incompatible, the runner falls back to the same sequential flow so the demo remains reliable.

## Fallback Rules

- Missing provider key: agents use deterministic outputs and record `llm_invocations.status=fallback_used` when live AI was requested.
- Invalid LLM JSON or schema validation error: deterministic fallback.
- Low impact or low confidence: backend thresholds decide whether to continue.
- Unsafe file paths from LLM planner output: removed and replaced with safe fallback files.
- Unsafe artifact content from LLM execution output: rejected and replaced with deterministic template artifacts.
- Verification LLM output cannot override deterministic safety failures.
- Suspicious generated content: verification fails and PR preview is blocked.
