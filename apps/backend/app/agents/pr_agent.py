from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.demo.pr_templates import build_pr_title
from app.llm.llm_service import LLMService
from app.llm.schemas import PRAgentLLMOutput


class PRAgent(BaseAgent):
    name = "pr_agent"
    description = "Creates a planned PR intent only; real PR creation is disabled by default."

    def execute(self, state: AgentState) -> dict[str, Any]:
        payload = state.get("trigger_payload") or {}
        scenario = payload.get("scenario") or {}
        verification = state.get("verification_result") or {}
        decision = state.get("decision") or {}
        impact = state.get("impact_analysis") or {}
        plan = state.get("implementation_plan") or {}
        artifacts = state.get("persisted_artifacts") or state.get("generated_artifacts") or []
        codebase_context = state.get("codebase_context") or plan.get("codebase_context") or {}
        relevant_paths = [file.get("path") for file in (codebase_context.get("relevant_files") or [])[:8]]
        status = "planned" if verification.get("passed", True) else "blocked"
        fallback = PRAgentLLMOutput(
            title=build_pr_title(scenario),
            branch_name_slug=scenario.get("scenario_key", "controlled-demo"),
            summary="Preview-only PR plan for generated EvolvAI artifacts.",
            problem=decision.get("summary") or "A market signal needs a safe product response.",
            solution=decision.get("recommended_action") or scenario.get("expected_recommendation") or "Create safe preview artifacts.",
            proposed_changes=[
                *[artifact.get("file_path", "Generated preview artifact") for artifact in artifacts],
                *[f"Suggested existing touchpoint: {path}" for path in relevant_paths if path],
            ],
            generated_artifacts=[artifact.get("file_path", "Generated preview artifact") for artifact in artifacts],
            impact_summary=f"Priority: {impact.get('final_priority', 'pending')}; opportunity score: {impact.get('opportunity_score', 'pending')}",
            verification_summary=verification.get("summary", "Verification pending."),
            testing_checklist=[
                "Review generated artifacts in the dashboard.",
                "Confirm deterministic verification checks pass.",
                "Keep real PR creation disabled until human approval.",
            ],
            risks=[
                "Preview artifacts require human review before implementation.",
                "Repository files listed in this preview were analyzed read-only and were not modified.",
            ],
            rollback_plan=["Discard the generated run directory and PR preview."],
            demo_note="This PR was generated in EvolvAI controlled demo mode. No real GitHub PR was opened.",
        )
        llm_output, llm_metadata = LLMService().generate_pr_output(
            workflow_id=state.get("workflow_id"),
            decision=decision,
            impact=impact,
            plan=plan,
            artifacts=artifacts,
            verification=verification,
            fallback_output=fallback,
        )
        if "preview" not in llm_output.demo_note.lower() and "no real" not in llm_output.demo_note.lower():
            llm_output.demo_note = f"{llm_output.demo_note} Preview-only: no real GitHub PR was opened."
        return {
            "pull_request": {
                "status": status,
                "title": llm_output.title,
                "url": None,
                "preview_only": True,
            },
            "pull_request_llm": llm_output.model_dump(),
            "output_mode": llm_metadata.get("output_mode", "deterministic"),
            "llm_metadata_by_agent": {"pr_agent": llm_metadata},
            "_llm_invocation": llm_metadata,
            "explainability": {
                "summary": (
                    "PR Agent used LLM-enhanced wording for a preview-only PR plan."
                    if llm_metadata.get("output_mode") == "llm_enhanced"
                    else "PR Agent created an intention preview only; no branch, commit, or GitHub PR was created."
                ),
                "reasoning_steps": [
                    "Read verification status before marking the preview planned or blocked.",
                    "Formatted a PR description that judges can inspect.",
                    "Kept ALLOW_REAL_GITHUB_PR disabled by default.",
                ],
                "evidence": [{"label": "Real PR creation", "value": "disabled"}],
                "codebase_context": codebase_context,
                "assumptions": ["Human approval is required before any external write action."],
                "risks": llm_output.risks or fallback.risks,
                "confidence_score": 0.92,
            },
            "status": "completed",
        }
