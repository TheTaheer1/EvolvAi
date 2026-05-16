from typing import Any


def build_pr_title(scenario: dict[str, Any]) -> str:
    recommendation = scenario.get("expected_recommendation") or scenario.get("title", "controlled demo foundation")
    return f"Demo PR: {recommendation.replace('.', '')}"


def build_branch_name(scenario_key: str, workflow_id: str) -> str:
    safe_key = "".join(char if char.isalnum() or char == "-" else "-" for char in scenario_key.lower())
    return f"evolvai/demo-{safe_key}-{workflow_id[:8]}"


def format_pr_description(
    scenario: dict[str, Any],
    company: dict[str, Any],
    artifacts: list[dict[str, Any]],
    impact: dict[str, Any] | None,
    verification: dict[str, Any] | None,
    plan: dict[str, Any] | None,
) -> str:
    event = scenario.get("market_event", {})
    impact = impact or {}
    verification = verification or {}
    plan = plan or {}
    generated_files = "\n".join(
        f"- `{artifact.get('file_path')}` ({artifact.get('artifact_type')})" for artifact in artifacts
    ) or "- No generated files"
    tasks = "\n".join(f"- {task.get('title')}" for task in plan.get("tasks", [])) or "- Review generated preview artifacts"
    return f"""## Summary
This preview proposes **{scenario.get("expected_recommendation")}** for {company.get("name", "AcmeFlow")}.

## Market signal
{event.get("summary", scenario.get("description"))}

## Why this matters
{event.get("why_it_matters")}

## Business impact
- Business impact: {impact.get("business_impact", "pending")}
- Urgency: {impact.get("urgency", "pending")}
- Confidence: {impact.get("confidence", "pending")}
- Opportunity score: {impact.get("opportunity_score", "pending")}
- Priority: {impact.get("final_priority", "pending")}

## Implementation plan
{tasks}

## Generated artifacts
{generated_files}

## Verification
Status: {"passed" if verification.get("passed") else "blocked"}

{verification.get("summary", "Verification has not completed yet.")}

## Risks
- Generated artifacts are preview-only and require human review before production implementation.
- Customer-facing AI features need quality evaluation and UX validation.
- Real GitHub PR creation remains disabled unless explicitly enabled.

## Rollback plan
No production files were changed. Remove the generated run directory and close this preview if the recommendation is rejected.

## Demo note
This PR was generated in EvolvAI controlled demo mode.
"""
