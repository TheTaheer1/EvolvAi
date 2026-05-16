import json
from typing import Any


def _feature_markdown(scenario: dict[str, Any], company: dict[str, Any], impact: dict[str, Any]) -> str:
    event = scenario.get("market_event", {})
    modules = ", ".join(company.get("product_modules") or [])
    users = ", ".join(company.get("target_users") or [])
    priority = impact.get("final_priority", "high")
    return f"""# {event.get("recommended_evolution", scenario.get("expected_recommendation"))}

## Feature overview
{company.get("name", "AcmeFlow")} should respond to **{scenario.get("title")}** with a focused, reviewable feature foundation. The first release should make the value visible inside existing product areas without introducing risky autonomous writes.

## User problem
Target users ({users}) increasingly expect AI-native productivity workflows. The current product modules ({modules}) already contain the raw workflow context, but customers still need manual effort to turn signals into decisions and follow-up work.

## Proposed solution
Ship a preview-safe module for: {event.get("recommended_evolution")}. Start with guided recommendations, transparent reasoning, and a compact dashboard surface before expanding into deeper automation.

## User stories
- As a product manager, I can see why this feature is recommended before committing roadmap capacity.
- As an operations lead, I can review the generated plan and artifacts without triggering external changes.
- As a customer success manager, I can connect the recommendation to retention and enterprise readiness goals.

## System impact
- Dashboard: add a concise preview card and impact visualization.
- Backend: persist explainability, impact scoring, generated artifacts, and verification results.
- Workflow: keep generated content inside the controlled demo workspace.

## Rollout plan
1. Launch as an internal preview with deterministic outputs.
2. Validate customer language and safety checks with product and CS teams.
3. Convert the strongest preview artifact into a scoped implementation ticket.
4. Add live AI enhancement only after safety review.

## Metrics
- Activation rate for previewed recommendations.
- Retention signal from teams using the related module.
- Reduction in manual follow-up effort.
- Verification pass rate before PR preview.

## Risks
- AI output quality must stay explainable and reviewable.
- Scope can expand beyond a small-team implementation window.
- UI must make demo mode and disabled real PR creation obvious.

## Recommendation
Priority: **{priority}**. Proceed with a safe foundation and keep real external writes disabled by default.
"""


def _component_template(scenario_key: str, scenario: dict[str, Any], impact: dict[str, Any]) -> str:
    title = scenario.get("expected_recommendation") or scenario.get("title")
    return f"""import React from "react";

type Insight = {{
  label: string;
  value: string;
}};

const insights: Insight[] = [
  {{ label: "Market signal", value: "{scenario.get("title")}" }},
  {{ label: "Priority", value: "{impact.get("final_priority", "high")}" }},
  {{ label: "Confidence", value: "{int(float(impact.get("confidence", 0.8)) * 100)}%" }}
];

export function DemoGeneratedPreview() {{
  return (
    <section aria-label="{title}" className="rounded-lg border border-slate-700 bg-slate-950 p-4 text-slate-100">
      <div className="text-xs uppercase tracking-wide text-cyan-300">Controlled demo artifact</div>
      <h3 className="mt-2 text-lg font-semibold">{title}</h3>
      <div className="mt-4 grid gap-3">
        {{insights.map((insight) => (
          <div key={{insight.label}} className="flex items-center justify-between rounded-md bg-slate-900 px-3 py-2">
            <span className="text-sm text-slate-400">{{insight.label}}</span>
            <span className="text-sm font-medium">{{insight.value}}</span>
          </div>
        ))}}
      </div>
    </section>
  );
}}
"""


def _plan_markdown(scenario: dict[str, Any], company: dict[str, Any], impact: dict[str, Any]) -> str:
    stack = ", ".join(company.get("technical_stack") or [])
    return f"""# Implementation Plan: {scenario.get("expected_recommendation")}

## Objective
Respond to {scenario.get("title")} with a controlled, preview-only implementation path.

## Stack alignment
Use the existing stack: {stack}. Keep persistence in PostgreSQL, asynchronous orchestration in Celery, realtime status through Socket.IO, and deterministic generated artifacts in the safe workspace.

## Tasks
- Create product-facing documentation for the recommended evolution.
- Add a demo preview artifact that illustrates the product surface.
- Store a machine-readable plan for verification and PR preview.
- Validate path safety, secret safety, and no dangerous commands before showing PR readiness.

## Complexity
Technical complexity score: {impact.get("technical_complexity")}

## Rollback
Because the workflow creates preview artifacts only, rollback is deleting the generated run directory and dismissing the PR preview.
"""


def _json_template(scenario_key: str, scenario: dict[str, Any], impact: dict[str, Any]) -> str:
    payload = {
        "scenario_key": scenario_key,
        "recommendation": scenario.get("expected_recommendation"),
        "priority": impact.get("final_priority"),
        "scores": {
            "business_impact": impact.get("business_impact"),
            "technical_complexity": impact.get("technical_complexity"),
            "urgency": impact.get("urgency"),
            "confidence": impact.get("confidence"),
            "risk_score": impact.get("risk_score"),
            "opportunity_score": impact.get("opportunity_score"),
        },
        "guardrails": [
            "preview_only",
            "no_source_file_modification",
            "no_shell_execution",
            "real_pr_disabled_by_default",
        ],
        "next_steps": [
            "Review generated artifacts",
            "Validate safety report",
            "Convert preview into implementation ticket",
        ],
    }
    if scenario_key == "github-rag-trend":
        payload["retrieval_plan"] = {
            "content_sources": ["knowledge base", "project docs", "meeting notes"],
            "memory_layers": ["document chunks", "citation metadata", "freshness score"],
            "evaluation": ["answer groundedness", "citation coverage", "latency"],
        }
    elif scenario_key == "security-compliance-shift":
        payload["audit_log_schema"] = {
            "actor": "string",
            "agent_name": "string",
            "decision_id": "uuid",
            "evidence": "array",
            "confidence_score": "number",
            "created_at": "datetime",
        }
    elif scenario_key == "competitor-automation":
        payload["workflow_template_schema"] = {
            "template_key": "string",
            "trigger": "market_event",
            "recommended_agents": ["watcher", "research", "strategy", "planning"],
            "approval_required": True,
        }
    return json.dumps(payload, indent=2)


def build_artifacts(
    scenario: dict[str, Any],
    company: dict[str, Any],
    plan: dict[str, Any],
    impact: dict[str, Any],
) -> list[dict[str, Any]]:
    scenario_key = scenario.get("scenario_key", "controlled-demo")
    artifacts: list[dict[str, Any]] = []
    for file_spec in plan.get("files_to_generate") or scenario.get("proposed_files") or []:
        file_path = file_spec["file_path"]
        artifact_type = file_spec.get("artifact_type", "documentation")
        if file_path.endswith(".tsx"):
            content = _component_template(scenario_key, scenario, impact)
            language = "tsx"
            title = "Generated demo component"
        elif file_path.endswith(".json"):
            content = _json_template(scenario_key, scenario, impact)
            language = "json"
            title = "Generated structured plan"
        else:
            content = _feature_markdown(scenario, company, impact) if artifact_type == "documentation" else _plan_markdown(scenario, company, impact)
            language = "markdown"
            title = "Generated feature proposal" if artifact_type == "documentation" else "Generated implementation plan"
        artifacts.append(
            {
                "artifact_type": artifact_type,
                "file_path": file_path,
                "title": title,
                "description": f"Deterministic {artifact_type} artifact for {scenario.get('title')}.",
                "content": content,
                "language": language,
                "metadata": {
                    "scenario_key": scenario_key,
                    "preview_only": True,
                    "safe_workspace": True,
                },
            }
        )
    return artifacts
