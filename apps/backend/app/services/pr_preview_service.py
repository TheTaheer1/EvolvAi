from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.demo.pr_templates import build_branch_name, build_pr_title, format_pr_description
from app.llm.validators import sanitize_branch_slug
from app.models.pull_request import PullRequestHistory
from app.realtime.events import PR_CREATED, PR_PREVIEW_CREATED
from app.services.generated_artifact_service import generated_artifact_payload
from app.services.impact_analysis_service import impact_analysis_payload
from app.services.realtime_service import RealtimeService
from app.services.verification_service import verification_report_payload
from app.utils.json import to_jsonable


def pr_preview_payload(pr: PullRequestHistory) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": pr.id,
            "workflow_id": pr.workflow_id,
            "repo_owner": pr.repo_owner,
            "repo_name": pr.repo_name,
            "branch_name": pr.branch_name,
            "pr_number": pr.pr_number,
            "pr_url": pr.pr_url,
            "status": pr.status,
            "title": pr.title,
            "description": pr.description,
            "changed_files": pr.changed_files,
            "error_message": pr.error_message,
            "created_at": pr.created_at,
            "updated_at": pr.updated_at,
        }
    )


class PRPreviewService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()

    def get_pr_preview_by_workflow(self, db: Session, workflow_id: UUID | str) -> PullRequestHistory | None:
        return db.scalars(
            select(PullRequestHistory)
            .where(PullRequestHistory.workflow_id == workflow_id)
            .order_by(PullRequestHistory.created_at.desc())
        ).first()

    def format_pr_description(
        self,
        scenario: dict[str, Any],
        company: dict[str, Any],
        artifacts: list[dict[str, Any]],
        impact: dict[str, Any] | None,
        verification: dict[str, Any] | None,
        plan: dict[str, Any] | None,
    ) -> str:
        return format_pr_description(scenario, company, artifacts, impact, verification, plan)

    def create_pr_preview(
        self,
        db: Session,
        workflow_id: UUID | str,
        scenario: dict[str, Any],
        company: dict[str, Any],
        artifacts: list[Any],
        verification: Any | None,
        impact: Any | None,
        plan: dict[str, Any] | None,
        llm_pr_output: dict[str, Any] | None = None,
        emit: bool = True,
    ) -> PullRequestHistory:
        existing = self.get_pr_preview_by_workflow(db, workflow_id)
        artifact_payloads = [
            generated_artifact_payload(artifact) if hasattr(artifact, "id") else artifact for artifact in artifacts
        ]
        verification_payload = verification_report_payload(verification) if hasattr(verification, "id") else verification
        impact_payload = impact_analysis_payload(impact) if hasattr(impact, "id") else impact
        status = "planned" if verification_payload and verification_payload.get("passed") else "blocked"
        title = build_pr_title(scenario)
        description = self.format_pr_description(
            scenario=scenario,
            company=company,
            artifacts=artifact_payloads,
            impact=impact_payload,
            verification=verification_payload,
            plan=plan,
        )
        branch_slug = scenario.get("scenario_key", "controlled-demo")
        if llm_pr_output:
            title = str(llm_pr_output.get("title") or title)[:500]
            branch_slug = sanitize_branch_slug(str(llm_pr_output.get("branch_name_slug") or branch_slug))
            description = self._format_llm_pr_description(
                llm_pr_output,
                artifact_payloads,
                impact_payload,
                verification_payload,
                plan,
            )
        changed_files = [
            {
                "path": artifact.get("file_path"),
                "type": artifact.get("artifact_type"),
                "status": artifact.get("status", "generated"),
            }
            for artifact in artifact_payloads
        ]
        for file in (plan or {}).get("relevant_existing_files", [])[:12]:
            path = file.get("path") if isinstance(file, dict) else None
            if path:
                changed_files.append(
                    {
                        "path": path,
                        "type": "repository_context",
                        "status": "suggested_read_only",
                    }
                )
        pr = existing or PullRequestHistory(workflow_id=workflow_id, title=title)
        pr.status = status
        pr.title = title
        pr.description = description
        pr.branch_name = f"evolvai/demo-{branch_slug}-{str(workflow_id)[:8]}"[:80]
        pr.repo_owner = settings.GITHUB_TARGET_OWNER or None
        pr.repo_name = settings.GITHUB_TARGET_REPO or None
        pr.pr_url = None
        pr.error_message = None
        pr.changed_files = to_jsonable(changed_files)
        if not existing:
            db.add(pr)
        db.commit()
        db.refresh(pr)
        if emit:
            payload = pr_preview_payload(pr)
            self.realtime.emit_event(PR_CREATED, payload, workflow_id=str(pr.workflow_id))
            self.realtime.emit_event(PR_PREVIEW_CREATED, payload, workflow_id=str(pr.workflow_id))
        return pr

    def _format_llm_pr_description(
        self,
        llm_output: dict[str, Any],
        artifacts: list[dict[str, Any]],
        impact: dict[str, Any] | None,
        verification: dict[str, Any] | None,
        plan: dict[str, Any] | None,
    ) -> str:
        generated_files = "\n".join(
            f"- `{artifact.get('file_path')}` ({artifact.get('artifact_type')})" for artifact in artifacts
        ) or "- No generated files"
        proposed_changes = "\n".join(f"- {item}" for item in llm_output.get("proposed_changes", [])) or generated_files
        testing = "\n".join(f"- [ ] {item}" for item in llm_output.get("testing_checklist", [])) or "- [ ] Review verification report"
        risks = "\n".join(f"- {item}" for item in llm_output.get("risks", [])) or "- Preview-only artifacts require human review."
        rollback = "\n".join(f"- {item}" for item in llm_output.get("rollback_plan", [])) or "- Discard generated artifacts."
        impact = impact or {}
        verification = verification or {}
        plan = plan or {}
        tasks = "\n".join(f"- {task.get('title')}" for task in plan.get("tasks", [])) or proposed_changes
        return f"""## Summary
{llm_output.get("summary", "LLM-enhanced PR preview for EvolvAI.")}

## Problem
{llm_output.get("problem", "Market signals need a safe product response.")}

## Solution
{llm_output.get("solution", "Generate preview artifacts and keep real external writes disabled.")}

## Proposed changes
{proposed_changes}

## Implementation plan
{tasks}

## Generated artifacts
{generated_files}

## Impact analysis
- Business impact: {impact.get("business_impact", "pending")}
- Urgency: {impact.get("urgency", "pending")}
- Confidence: {impact.get("confidence", "pending")}
- Opportunity score: {impact.get("opportunity_score", "pending")}
- Priority: {impact.get("final_priority", "pending")}

## Verification
Status: {"passed" if verification.get("passed") else "blocked"}

{verification.get("summary", "Verification has not completed yet.")}

## Testing checklist
{testing}

## Risks
{risks}

## Rollback plan
{rollback}

## Demo note
{llm_output.get("demo_note", "This PR was generated in EvolvAI controlled demo mode.")}
"""
