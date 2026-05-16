from __future__ import annotations

import json
from typing import Any

from app.core.config import settings


GLOBAL_SYSTEM_PROMPT = """You are an agent inside EvolvAI, a safe autonomous SaaS evolution system. Return only valid JSON matching the required schema. Do not include markdown unless a schema content field explicitly asks for markdown artifact content. Do not reveal hidden chain-of-thought; provide concise user-visible reasoning summaries only. Do not suggest destructive shell commands, real production deployment, secret handling, direct external write actions, real GitHub PR creation, or bypassing verification. Do not create or expose API keys. Keep output practical for a SaaS evolution dashboard. If uncertain, say so in assumptions or risks. Use the provided company, scenario, event, and artifact data. Do not invent URLs."""

RESEARCH_SYSTEM_PROMPT = """You are the Research Agent inside EvolvAI. Evaluate a SaaS market signal for a B2B productivity company. Return concise, user-visible research only. Do not reveal hidden reasoning. Do not suggest shell commands, secret handling, production deployments, or external write actions. Return data matching the requested schema."""

SCHEMA_EXAMPLES: dict[str, dict[str, Any]] = {
    "WatcherLLMOutput": {
        "source": "controlled_demo",
        "event_type": "competitor_feature_launch",
        "title": "Short market signal title",
        "summary": "One concise sentence about the normalized signal.",
        "importance_score": 0.82,
        "tags": ["ai", "saas"],
        "company_name": "AcmeFlow",
        "why_it_matters": "Concise business reason.",
        "recommended_evolution": "Short safe product evolution.",
        "confidence_score": 0.8,
        "assumptions": ["One assumption"],
        "risks": ["One risk"],
    },
    "ResearchLLMOutput": {
        "research_summary": "Two concise sentences summarizing the market evidence.",
        "evidence": [
            {
                "source": "controlled_demo",
                "title": "Evidence title",
                "summary": "Short evidence summary.",
                "relevance": "high",
                "url": None,
            }
        ],
        "relevance_score": 0.84,
        "competitor_relevance": 0.78,
        "confidence_score": 0.8,
        "key_market_signals": ["Signal"],
        "risks": ["Risk"],
        "assumptions": ["Assumption"],
    },
    "StrategyAgentLLMOutput": {
        "should_act": True,
        "decision_type": "feature_recommendation",
        "title": "Short strategy title",
        "summary": "Short strategic summary.",
        "business_impact": 0.82,
        "technical_complexity": 0.55,
        "urgency": 0.76,
        "confidence_score": 0.8,
        "risk_score": 0.34,
        "recommended_action": "One safe recommended action.",
        "why_now": "Why timing matters.",
        "why_relevant": "Why it fits the company.",
        "expected_benefit": "Expected user or business benefit.",
        "risks": ["Risk"],
        "assumptions": ["Assumption"],
    },
    "PlannerAgentLLMOutput": {
        "objective": "Short implementation objective.",
        "affected_modules": ["dashboard", "docs"],
        "tasks": [
            {
                "title": "Create proposal",
                "description": "Draft preview-only feature proposal.",
                "type": "documentation",
                "complexity": "low",
                "risk": "low",
            }
        ],
        "files_to_generate": [
            {
                "file_path": "docs/features/example.md",
                "artifact_type": "documentation",
                "title": "Feature proposal",
                "description": "Preview-only document.",
                "language": "markdown",
            }
        ],
        "estimated_effort": "1-2 days",
        "estimated_complexity": "medium",
        "rollout_plan": ["Preview internally"],
        "risks": ["Risk"],
        "success_metrics": ["Metric"],
        "assumptions": ["Assumption"],
    },
    "ExecutionLLMOutput": {
        "artifacts": [
            {
                "file_path": "docs/features/example.md",
                "artifact_type": "documentation",
                "title": "Feature proposal",
                "description": "Preview-only artifact.",
                "language": "markdown",
                "content": "# Feature Proposal\n\nShort safe preview content.",
            }
        ],
        "execution_summary": "Generated preview-only artifact content.",
        "safety_notes": ["No code execution"],
        "assumptions": ["Preview workspace only"],
        "risks": ["Needs human review"],
    },
    "VerificationLLMOutput": {
        "summary": "Short explanation of deterministic safety checks.",
        "risk_interpretation": "Concise risk interpretation.",
        "suggested_remediations": ["Review generated files"],
        "reviewer_confidence": 0.82,
        "additional_risks": ["Risk"],
        "assumptions": ["Deterministic checks are authoritative"],
    },
    "PRAgentLLMOutput": {
        "title": "Demo PR: Short preview title",
        "branch_name_slug": "short-preview-title",
        "summary": "Short preview summary.",
        "problem": "Problem statement.",
        "solution": "Solution statement.",
        "proposed_changes": ["Preview artifact"],
        "generated_artifacts": ["docs/features/example.md"],
        "impact_summary": "Impact summary.",
        "verification_summary": "Verification summary.",
        "testing_checklist": ["Review preview artifacts"],
        "risks": ["Risk"],
        "rollback_plan": ["Close preview PR"],
        "demo_note": "Preview-only; no real PR was opened by the agent.",
    },
}


def compact_schema_hint(schema_model: Any) -> str:
    """Return a small JSON example instead of a full JSON schema for quota-sensitive providers."""
    name = getattr(schema_model, "__name__", str(schema_model))
    example = SCHEMA_EXAMPLES.get(name)
    if example:
        return _dump(example)
    schema = schema_model.model_json_schema()
    return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))


def _short_text(value: Any, limit: int = 700) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _list(values: Any, max_items: int = 5, item_limit: int = 240) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_short_text(item, item_limit) for item in values if str(item or "").strip()][:max_items]


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str, separators=(",", ":"))


def _finalize_prompt(prompt: str) -> str:
    if not settings.LLM_COMPACT_PROMPTS:
        return prompt
    limit = max(1200, int(settings.LLM_MAX_PROMPT_CHARS or 5000))
    if len(prompt) <= limit:
        return prompt
    return (
        prompt[: limit - 120].rstrip()
        + "\n\n[compact_prompt_truncated: context was shortened to stay within EvolvAI demo token limits.]"
    )


def _company_summary(company: dict[str, Any]) -> dict[str, Any]:
    if not settings.LLM_COMPACT_PROMPTS:
        return company
    return {
        "name": company.get("name"),
        "description": _short_text(company.get("description"), 360),
        "industry": company.get("industry"),
        "product_modules": _list(company.get("product_modules"), 6, 80),
        "target_users": _list(company.get("target_users"), 4, 80),
        "business_goals": _list(company.get("business_goals"), 5, 100),
        "technical_stack": _list(company.get("technical_stack"), 8, 80),
        "competitors": _list(company.get("competitors"), 6, 80),
        "risk_tolerance": company.get("risk_tolerance"),
        "engineering_capacity": company.get("engineering_capacity"),
    }


def _event_summary(event: dict[str, Any]) -> dict[str, Any]:
    if not settings.LLM_COMPACT_PROMPTS:
        return event
    return {
        "source": event.get("source") or event.get("event_source"),
        "event_type": event.get("event_type"),
        "title": _short_text(event.get("title"), 180),
        "summary": _short_text(event.get("summary") or event.get("description"), 600),
        "importance_score": event.get("importance_score"),
        "tags": _list(event.get("tags"), 8, 60),
        "url": event.get("url"),
        "scenario_key": event.get("scenario_key"),
        "why_it_matters": _short_text(event.get("why_it_matters"), 450),
        "recommended_evolution": _short_text(event.get("recommended_evolution"), 360),
    }


def _trigger_summary(trigger_payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.LLM_COMPACT_PROMPTS:
        return trigger_payload
    scenario = trigger_payload.get("scenario") or {}
    market_event = scenario.get("market_event") or trigger_payload.get("market_event") or {}
    return {
        "demo_mode": trigger_payload.get("demo_mode"),
        "live_event": trigger_payload.get("live_event"),
        "source": trigger_payload.get("source") or scenario.get("event_source"),
        "scenario_key": scenario.get("scenario_key"),
        "scenario_title": _short_text(scenario.get("title"), 180),
        "event": _event_summary(market_event),
    }


def _evidence_summary(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not settings.LLM_COMPACT_PROMPTS:
        return evidence
    items: list[dict[str, Any]] = []
    for item in (evidence or [])[: max(1, settings.LLM_MAX_EVIDENCE_ITEMS)]:
        items.append(
            {
                "source": item.get("source"),
                "title": _short_text(item.get("title"), 180),
                "summary": _short_text(item.get("summary"), 220),
                "relevance": item.get("relevance"),
                "url": item.get("url"),
            }
        )
    return items


def _research_summary(research: dict[str, Any]) -> dict[str, Any]:
    if not settings.LLM_COMPACT_PROMPTS:
        return research
    return {
        "research_summary": _short_text(research.get("research_summary") or research.get("summary"), 650),
        "trend_relevance": research.get("trend_relevance"),
        "competitor_relevance": research.get("competitor_relevance"),
        "confidence_score": research.get("confidence_score"),
        "evidence": _evidence_summary(research.get("research_evidence") or research.get("evidence") or []),
    }


def _decision_summary(decision: dict[str, Any]) -> dict[str, Any]:
    if not settings.LLM_COMPACT_PROMPTS:
        return decision
    reasoning = decision.get("reasoning") or {}
    return {
        "should_act": decision.get("should_act", True),
        "decision_type": decision.get("decision_type"),
        "title": _short_text(decision.get("title"), 180),
        "summary": _short_text(decision.get("summary"), 650),
        "impact_score": decision.get("impact_score"),
        "confidence_score": decision.get("confidence_score"),
        "recommended_action": _short_text(decision.get("recommended_action"), 450),
        "why_now": _short_text(reasoning.get("why_now") or decision.get("why_now"), 360),
        "why_relevant": _short_text(reasoning.get("why_relevant") or decision.get("why_relevant"), 360),
        "expected_benefit": _short_text(reasoning.get("expected_benefit") or decision.get("expected_benefit"), 360),
        "risks": _list(reasoning.get("risks") or decision.get("risks"), 4, 160),
    }


def _impact_summary(impact: dict[str, Any]) -> dict[str, Any]:
    if not settings.LLM_COMPACT_PROMPTS:
        return impact
    breakdown = impact.get("impact_breakdown") or {}
    return {
        "business_impact": impact.get("business_impact"),
        "technical_complexity": impact.get("technical_complexity"),
        "urgency": impact.get("urgency"),
        "confidence": impact.get("confidence"),
        "risk_score": impact.get("risk_score"),
        "opportunity_score": impact.get("opportunity_score"),
        "final_priority": impact.get("final_priority"),
        "recommendation": _short_text(impact.get("recommendation"), 360),
        "impact_breakdown": {
            key: breakdown.get(key)
            for key in (
                "customer_value",
                "competitive_pressure",
                "retention_impact",
                "engineering_effort",
                "implementation_risk",
                "time_sensitivity",
            )
            if key in breakdown
        },
    }


def _codebase_summary(codebase_context: dict[str, Any] | None) -> dict[str, Any]:
    if not codebase_context:
        return {}
    if not settings.LLM_COMPACT_PROMPTS:
        return codebase_context
    relevant_files = codebase_context.get("relevant_files") or []
    return {
        "architecture_summary": _short_text(codebase_context.get("architecture_summary"), 700),
        "relevant_files": [
            {
                "path": _short_text(item.get("path") or item.get("file_path"), 220),
                "language": item.get("language"),
                "importance_score": item.get("importance_score"),
                "summary": _short_text(item.get("summary"), 260),
            }
            for item in relevant_files[: max(1, settings.LLM_MAX_CODEBASE_FILES)]
            if isinstance(item, dict)
        ],
        "implementation_hints": _list(codebase_context.get("implementation_hints"), 5, 180),
        "risks": _list(codebase_context.get("risks"), 5, 180),
    }


def _plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    if not settings.LLM_COMPACT_PROMPTS:
        return plan
    return {
        "objective": _short_text(plan.get("objective"), 520),
        "affected_modules": _list(plan.get("affected_modules"), 6, 80),
        "tasks": [
            {
                "title": _short_text(item.get("title"), 180),
                "description": _short_text(item.get("description"), 240),
                "type": item.get("type"),
                "complexity": item.get("complexity"),
                "risk": item.get("risk"),
            }
            for item in (plan.get("tasks") or [])[:5]
            if isinstance(item, dict)
        ],
        "files_to_generate": [
            {
                "file_path": _short_text(item.get("file_path"), 220),
                "artifact_type": item.get("artifact_type"),
                "title": _short_text(item.get("title"), 160),
                "language": item.get("language"),
            }
            for item in (plan.get("files_to_generate") or [])[:5]
            if isinstance(item, dict)
        ],
        "estimated_effort": plan.get("estimated_effort"),
        "estimated_complexity": plan.get("estimated_complexity"),
        "risks": _list(plan.get("risks"), 5, 180),
        "success_metrics": _list(plan.get("success_metrics"), 5, 180),
    }


def _artifact_summary(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not settings.LLM_COMPACT_PROMPTS:
        return artifacts
    preview_limit = max(40, min(1500, settings.LLM_MAX_ARTIFACT_PREVIEW_CHARS))
    return [
        {
            "file_path": _short_text(item.get("file_path"), 220),
            "artifact_type": item.get("artifact_type"),
            "title": _short_text(item.get("title"), 160),
            "description": _short_text(item.get("description"), 260),
            "language": item.get("language"),
            "status": item.get("status"),
            "content_preview": _short_text(item.get("content"), preview_limit),
        }
        for item in (artifacts or [])[:5]
        if isinstance(item, dict)
    ]


def build_watcher_prompt(company: dict, trigger_payload: dict, deterministic_event: dict) -> str:
    prompt = f"""Normalize this incoming market signal for EvolvAI.

Company summary:
{_dump(_company_summary(company))}

Trigger summary:
{_dump(_trigger_summary(trigger_payload))}

Deterministic baseline event:
{_dump(_event_summary(deterministic_event))}

Return source, event_type, title, summary, importance_score, tags, company_name, why_it_matters, recommended_evolution, confidence_score, assumptions, and risks.
Preserve the scenario_key if present in the baseline event by not contradicting the event identity. Do not invent URLs. Do not over-infer."""
    return _finalize_prompt(prompt)


def research_prompt(company: dict, market_event: dict, evidence: list[dict]) -> str:
    return build_research_prompt(company, market_event, evidence)


def build_research_prompt(company: dict, market_event: dict, evidence: list[dict]) -> str:
    prompt = f"""Create a concise research output for EvolvAI.

Company summary:
{_dump(_company_summary(company))}

Market event summary:
{_dump(_event_summary(market_event))}

Top evidence:
{_dump(_evidence_summary(evidence))}

Return:
- research_summary
- evidence
- relevance_score, competitor_relevance, confidence_score from 0 to 1
- key_market_signals
- risks
- assumptions

Summarize why the trend matters, list evidence, score relevance, and list assumptions/risks."""
    return _finalize_prompt(prompt)


def strategy_prompt(company: dict, market_event: dict, research: dict) -> str:
    return build_strategy_prompt(company, market_event, research)


def build_strategy_prompt(company: dict, market_event: dict, research: dict) -> str:
    prompt = f"""Create a strategy decision for EvolvAI.

Company summary:
{_dump(_company_summary(company))}

Market event summary:
{_dump(_event_summary(market_event))}

Previous agent research summary:
{_dump(_research_summary(research))}

Decide if action is useful, score impact/complexity/urgency/confidence/risk, and return explainability-ready fields.
Backend scoring remains authoritative, so do not return a final priority. Keep recommendations incremental and safe."""
    return _finalize_prompt(prompt)


def planner_prompt(company: dict, decision: dict, impact: dict, codebase_context: dict | None = None) -> str:
    return build_planner_prompt(company, decision, impact, codebase_context)


def build_planner_prompt(company: dict, decision: dict, impact: dict, codebase_context: dict | None = None) -> str:
    prompt = f"""Create a safe implementation plan for EvolvAI.

Company summary:
{_dump(_company_summary(company))}

Previous agent decision summary:
{_dump(_decision_summary(decision))}

Impact analysis summary:
{_dump(_impact_summary(impact))}

Read-only codebase context:
{_dump(_codebase_summary(codebase_context))}

Propose generated artifacts only. Use codebase context as suggested touchpoints when present, but do not suggest destructive commands, deployment, production writes, real source edits, package-manager changes, CI/CD changes, or files outside docs/features/*, demo/generated/*, and demo/reports/*."""
    return _finalize_prompt(prompt)


def build_execution_prompt(
    company: dict,
    market_event: dict,
    decision: dict,
    impact: dict,
    plan: dict,
    deterministic_artifacts: list[dict],
) -> str:
    prompt = f"""Generate safe preview artifact content for EvolvAI only.

Company summary:
{_dump(_company_summary(company))}

Market event summary:
{_dump(_event_summary(market_event))}

Previous agent decision summary:
{_dump(_decision_summary(decision))}

Impact analysis summary:
{_dump(_impact_summary(impact))}

Implementation plan summary:
{_dump(_plan_summary(plan))}

Deterministic artifact baseline:
{_dump(_artifact_summary(deterministic_artifacts))}

Use only preview artifact content. Do not include executable shell steps, destructive commands, secrets, production deployment instructions, or external write instructions. The backend will write only inside generated_runs/{{workflow_id}} and will reject unsafe content."""
    return _finalize_prompt(prompt)


def build_verification_prompt(verification_result: dict, artifacts: list[dict]) -> str:
    prompt = f"""Explain deterministic verification results for EvolvAI.

Deterministic verification result:
{_dump(_impact_summary(verification_result) if "business_impact" in verification_result else verification_result)}

Generated artifacts:
{_dump(_artifact_summary(artifacts))}

Only provide advisory explanation, risk interpretation, suggested remediations, confidence, risks, and assumptions. Do not override passed/failed. Deterministic checks are authoritative."""
    return _finalize_prompt(prompt)


def pr_prompt(decision: dict, impact: dict, plan: dict, artifacts: list[dict], verification: dict | None) -> str:
    return build_pr_prompt(decision, impact, plan, artifacts, verification)


def build_pr_prompt(decision: dict, impact: dict, plan: dict, artifacts: list[dict], verification: dict | None) -> str:
    prompt = f"""Create a safe PR preview for EvolvAI.

Decision:
{_dump(_decision_summary(decision))}

Impact analysis:
{_dump(_impact_summary(impact))}

Implementation plan:
{_dump(_plan_summary(plan))}

Generated artifacts:
{_dump(_artifact_summary(artifacts))}

Verification report:
{_dump(verification or {})}

No real PR was opened. Do not claim a branch, commit, merge, or real GitHub PR exists. Include preview-only wording, generated artifacts, risks, rollback, and a demo note."""
    return _finalize_prompt(prompt)
