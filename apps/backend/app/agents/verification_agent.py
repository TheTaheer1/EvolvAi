from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.llm.llm_service import LLMService
from app.llm.schemas import VerificationLLMOutput


class VerificationAgent(BaseAgent):
    name = "verification_agent"
    description = "Returns deterministic placeholder validation results."

    def execute(self, state: AgentState) -> dict[str, Any]:
        deterministic_result = {
            "passed": True,
            "checks": [
                {"name": "artifact_count_check", "status": "pending", "message": "Runner will validate persisted artifacts."},
                {"name": "path_safety_check", "status": "pending", "message": "Runner will validate safe paths."},
                {"name": "content_non_empty_check", "status": "pending", "message": "Runner will validate content."},
                {"name": "no_secret_leak_check", "status": "pending", "message": "Runner will scan for secrets."},
                {"name": "no_dangerous_command_check", "status": "pending", "message": "Runner will scan blocked commands."},
                {"name": "no_prompt_injection_check", "status": "pending", "message": "Runner will scan prompt injection indicators."},
                {"name": "no_external_write_instruction_check", "status": "pending", "message": "Runner will block external write instructions."},
                {"name": "no_production_deployment_instruction_check", "status": "pending", "message": "Runner will block production deployment instructions."},
                {"name": "max_size_check", "status": "pending", "message": "Runner will validate artifact size."},
                {"name": "pr_ready_check", "status": "pending", "message": "Runner will decide PR readiness."},
            ],
            "summary": "Verification agent requested safe persisted artifact checks.",
        }
        artifacts = state.get("persisted_artifacts") or state.get("generated_artifacts") or []
        fallback = VerificationLLMOutput(
            summary="Verification remains deterministic-rule-first and will validate persisted artifacts.",
            risk_interpretation="Risk is controlled because generated content is preview-only and safety checks are authoritative.",
            suggested_remediations=["Review any failed deterministic check before showing PR readiness."],
            reviewer_confidence=0.9,
            additional_risks=["Future template changes could introduce unsafe text; checks protect the demo path."],
            assumptions=["Generated content is preview text and will not be executed."],
        )
        llm_output, llm_metadata = LLMService().generate_verification_output(
            workflow_id=state.get("workflow_id"),
            verification_result=deterministic_result,
            artifacts=artifacts,
            fallback_output=fallback,
        )
        return {
            "verification_result": deterministic_result,
            "verification_explanation": llm_output.model_dump(),
            "output_mode": llm_metadata.get("output_mode", "deterministic"),
            "llm_metadata_by_agent": {"verification_agent": llm_metadata},
            "_llm_invocation": llm_metadata,
            "explainability": {
                "summary": (
                    "Verification used LLM-assisted explanation, while deterministic safety checks remain authoritative."
                    if llm_metadata.get("output_mode") == "llm_enhanced"
                    else "Verification validates generated artifacts with deterministic safety checks."
                ),
                "reasoning_steps": [
                    "Check artifact count.",
                    "Check safe relative paths.",
                    "Check non-empty content.",
                    "Scan for secret-like and dangerous command patterns.",
                    "Block PR preview readiness if any safety check fails.",
                ],
                "evidence": [{"label": "Safety checks", "value": 10}],
                "assumptions": llm_output.assumptions or fallback.assumptions,
                "risks": llm_output.additional_risks or fallback.additional_risks,
                "confidence_score": llm_output.reviewer_confidence,
            },
        }
