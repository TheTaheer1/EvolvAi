from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.core.config import settings
from app.demo.artifact_templates import build_artifacts
from app.llm.llm_service import LLMService
from app.llm.schemas import ExecutionLLMOutput
from app.llm.validators import is_safe_llm_file_path
from app.security.artifact_safety import (
    find_dangerous_content,
    find_external_write_instructions,
    find_production_deployment_instructions,
    find_prompt_injection,
)


class ExecutionAgent(BaseAgent):
    name = "execution_agent"
    description = "Produces a mock change plan and never edits repository code in Step 1."

    def execute(self, state: AgentState) -> dict[str, Any]:
        payload = state.get("trigger_payload") or {}
        scenario = payload.get("scenario") or {}
        company = payload.get("company_profile") or {}
        plan = state.get("implementation_plan") or {}
        impact = state.get("impact_analysis") or {}
        event = state.get("normalized_market_event") or {}
        decision = state.get("decision") or {}
        codebase_context = state.get("codebase_context") or {}
        artifacts = self._with_codebase_context(build_artifacts(scenario, company, plan, impact), codebase_context)
        fallback = ExecutionLLMOutput(
            artifacts=artifacts,
            execution_summary=f"Generated {len(artifacts)} safe preview artifacts.",
            safety_notes=[
                "Artifacts are preview-only and are never executed.",
                "File writes are delegated to the generated_runs safety service.",
            ],
            assumptions=["Generated artifacts should be reviewed as proposals, not executed."],
            risks=["Filesystem writes may fail; artifact content is still persisted in PostgreSQL."],
        )
        llm_output = fallback
        llm_metadata: dict[str, Any] = {
            "workflow_id": state.get("workflow_id"),
            "agent_name": self.name,
            "provider": "deterministic",
            "model": "deterministic-fallback",
            "mode": "deterministic",
            "output_mode": "deterministic",
            "prompt_hash": None,
            "status": "skipped",
            "fallback_used": False,
            "structured_output_valid": False,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": "ALLOW_LLM_ARTIFACT_CONTENT=false",
        }
        if settings.ALLOW_LLM_ARTIFACT_CONTENT:
            llm_output, llm_metadata = LLMService().generate_execution_output(
                workflow_id=state.get("workflow_id"),
                company=company,
                market_event=event,
                decision=decision,
                impact=impact,
                plan=plan,
                deterministic_artifacts=artifacts,
                fallback_output=fallback,
            )
        candidate_artifacts = [artifact.model_dump() for artifact in llm_output.artifacts]
        safe_artifacts = self._validated_artifacts(candidate_artifacts, artifacts)
        if not safe_artifacts:
            safe_artifacts = artifacts
            if llm_metadata.get("output_mode") == "llm_enhanced":
                llm_metadata = {
                    **llm_metadata,
                    "status": "fallback_used",
                    "output_mode": "fallback_used",
                    "fallback_used": True,
                    "structured_output_valid": False,
                    "error_message": "unsafe_llm_artifact_content",
                }
        return {
            "generated_artifacts": safe_artifacts,
            "generated_changes": [
                {
                    "file_path": artifact["file_path"],
                    "change_type": "preview_only",
                    "summary": artifact["description"],
                    "suggested_existing_files": [
                        file.get("path") for file in (codebase_context.get("relevant_files") or [])[:5]
                    ],
                }
                for artifact in safe_artifacts
            ],
            "execution_summary": llm_output.execution_summary,
            "output_mode": llm_metadata.get("output_mode", "deterministic"),
            "llm_metadata_by_agent": {"execution_agent": llm_metadata},
            "_llm_invocation": llm_metadata,
            "explainability": {
                "summary": (
                    "Execution used LLM-assisted artifact content after deterministic safety validation."
                    if llm_metadata.get("output_mode") == "llm_enhanced"
                    else "Execution produced preview artifacts without modifying application source files."
                ),
                "reasoning_steps": [
                    "Built deterministic artifacts first so fallback is always available.",
                    "Validated any LLM artifact content for safe paths, size, secrets, dangerous commands, and prompt injection.",
                    "Marked every artifact as preview-only.",
                    "Deferred file writing to the safe generated_runs workspace service.",
                ],
                "evidence": [
                    {"label": artifact["file_path"], "value": artifact["artifact_type"]} for artifact in safe_artifacts
                ],
                "assumptions": llm_output.assumptions or fallback.assumptions,
                "risks": llm_output.risks or fallback.risks,
                "confidence_score": 0.88,
            },
        }

    def _validated_artifacts(
        self,
        candidate_artifacts: list[dict[str, Any]],
        fallback_artifacts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        safe: list[dict[str, Any]] = []
        seen: set[str] = set()
        fallback_by_index = list(fallback_artifacts)
        for index, artifact in enumerate(candidate_artifacts[:5]):
            mapped_path = artifact.get("file_path")
            if not settings.ALLOW_LLM_FILE_PATHS and index < len(fallback_by_index):
                mapped_path = fallback_by_index[index]["file_path"]
            if not mapped_path or not is_safe_llm_file_path(str(mapped_path)):
                continue
            content = str(artifact.get("content") or "").strip()
            if not content or len(content.encode("utf-8")) > settings.MAX_ARTIFACT_SIZE_BYTES:
                continue
            unsafe_patterns = [
                *find_dangerous_content(content),
                *find_prompt_injection(content),
                *find_external_write_instructions(content),
                *find_production_deployment_instructions(content),
            ]
            if unsafe_patterns or str(mapped_path) in seen:
                continue
            seen.add(str(mapped_path))
            safe.append(
                {
                    **artifact,
                    "file_path": str(mapped_path),
                    "artifact_type": artifact.get("artifact_type") or fallback_by_index[min(index, len(fallback_by_index) - 1)].get("artifact_type"),
                    "title": artifact.get("title") or str(mapped_path).split("/")[-1],
                    "description": artifact.get("description") or "LLM-assisted safe preview artifact.",
                    "content": content,
                    "language": artifact.get("language"),
                    "status": "preview_only",
                    "metadata": {"origin": "llm_assisted"},
                }
            )
        return safe

    def _with_codebase_context(
        self,
        artifacts: list[dict[str, Any]],
        codebase_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        relevant_files = codebase_context.get("relevant_files") or []
        if not relevant_files:
            return artifacts
        file_lines = "\n".join(
            f"- {file.get('path')} ({file.get('file_type') or 'file'}, importance {file.get('importance_score')})"
            for file in relevant_files[:8]
        )
        suffix = (
            "\n\n## Read-only codebase context\n"
            "The following existing repository files informed this preview. EvolvAI did not modify them:\n"
            f"{file_lines}\n"
        )
        enhanced: list[dict[str, Any]] = []
        for artifact in artifacts:
            metadata = dict(artifact.get("metadata") or {})
            metadata["codebase_context_id"] = codebase_context.get("id")
            metadata["suggested_existing_files"] = [file.get("path") for file in relevant_files[:8]]
            content = str(artifact.get("content") or "")
            if artifact.get("language") in {"markdown", "md"} or artifact.get("file_path", "").endswith(".md"):
                content = f"{content}{suffix}"
            enhanced.append({**artifact, "content": content, "metadata": metadata})
        return enhanced
