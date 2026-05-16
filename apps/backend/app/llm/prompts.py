GLOBAL_SYSTEM_PROMPT = """You are an agent inside EvolvAI, a safe autonomous SaaS evolution system. Return only valid JSON matching the required schema. Do not include markdown unless a schema content field explicitly asks for markdown artifact content. Do not reveal hidden chain-of-thought; provide concise user-visible reasoning summaries only. Do not suggest destructive shell commands, real production deployment, secret handling, direct external write actions, real GitHub PR creation, or bypassing verification. Do not create or expose API keys. Keep output practical for a SaaS evolution dashboard. If uncertain, say so in assumptions or risks. Use the provided company, scenario, event, and artifact data. Do not invent URLs."""

RESEARCH_SYSTEM_PROMPT = """You are the Research Agent inside EvolvAI. Evaluate a SaaS market signal for a B2B productivity company. Return concise, user-visible research only. Do not reveal hidden reasoning. Do not suggest shell commands, secret handling, production deployments, or external write actions. Return data matching the requested schema."""


def build_watcher_prompt(company: dict, trigger_payload: dict, deterministic_event: dict) -> str:
    return f"""Normalize this incoming market signal for EvolvAI.

Company profile:
{company}

Trigger payload:
{trigger_payload}

Deterministic baseline event:
{deterministic_event}

Return source, event_type, title, summary, importance_score, tags, company_name, why_it_matters, recommended_evolution, confidence_score, assumptions, and risks.
Preserve the scenario_key if present in the baseline event by not contradicting the event identity. Do not invent URLs. Do not over-infer."""


def research_prompt(company: dict, market_event: dict, evidence: list[dict]) -> str:
    return build_research_prompt(company, market_event, evidence)


def build_research_prompt(company: dict, market_event: dict, evidence: list[dict]) -> str:
    return f"""Create a concise research output for EvolvAI.

Company profile:
{company}

Market event:
{market_event}

Known evidence:
{evidence}

Return:
- research_summary
- evidence
- relevance_score, competitor_relevance, confidence_score from 0 to 1
- key_market_signals
- risks
- assumptions

Summarize why the trend matters, list evidence, score relevance, and list assumptions/risks."""


def strategy_prompt(company: dict, market_event: dict, research: dict) -> str:
    return build_strategy_prompt(company, market_event, research)


def build_strategy_prompt(company: dict, market_event: dict, research: dict) -> str:
    return f"""Create a strategy decision for EvolvAI.

Company profile:
{company}

Market event:
{market_event}

Research output:
{research}

Decide if action is useful, score impact/complexity/urgency/confidence/risk, and return explainability-ready fields.
Backend scoring remains authoritative, so do not return a final priority. Keep recommendations incremental and safe."""


def planner_prompt(company: dict, decision: dict, impact: dict, codebase_context: dict | None = None) -> str:
    return build_planner_prompt(company, decision, impact, codebase_context)


def build_planner_prompt(company: dict, decision: dict, impact: dict, codebase_context: dict | None = None) -> str:
    return f"""Create a safe implementation plan for EvolvAI.

Company profile:
{company}

Strategic decision:
{decision}

Impact analysis:
{impact}

Read-only codebase context:
{codebase_context or {}}

Propose generated artifacts only. Use codebase context as suggested touchpoints when present, but do not suggest destructive commands, deployment, production writes, real source edits, package-manager changes, CI/CD changes, or files outside docs/features/*, demo/generated/*, and demo/reports/*."""


def build_execution_prompt(
    company: dict,
    market_event: dict,
    decision: dict,
    impact: dict,
    plan: dict,
    deterministic_artifacts: list[dict],
) -> str:
    return f"""Generate safe preview artifact content for EvolvAI only.

Company profile:
{company}

Market event:
{market_event}

Strategic decision:
{decision}

Impact analysis:
{impact}

Implementation plan:
{plan}

Deterministic artifact baseline:
{deterministic_artifacts}

Use only preview artifact content. Do not include executable shell steps, destructive commands, secrets, production deployment instructions, or external write instructions. The backend will write only inside generated_runs/{{workflow_id}} and will reject unsafe content."""


def build_verification_prompt(verification_result: dict, artifacts: list[dict]) -> str:
    return f"""Explain deterministic verification results for EvolvAI.

Deterministic verification result:
{verification_result}

Generated artifacts:
{artifacts}

Only provide advisory explanation, risk interpretation, suggested remediations, confidence, risks, and assumptions. Do not override passed/failed. Deterministic checks are authoritative."""


def pr_prompt(decision: dict, impact: dict, plan: dict, artifacts: list[dict], verification: dict | None) -> str:
    return build_pr_prompt(decision, impact, plan, artifacts, verification)


def build_pr_prompt(decision: dict, impact: dict, plan: dict, artifacts: list[dict], verification: dict | None) -> str:
    return f"""Create a safe PR preview for EvolvAI.

Decision:
{decision}

Impact analysis:
{impact}

Implementation plan:
{plan}

Generated artifacts:
{artifacts}

Verification report:
{verification}

No real PR was opened. Do not claim a branch, commit, merge, or real GitHub PR exists. Include preview-only wording, generated artifacts, risks, rollback, and a demo note."""
