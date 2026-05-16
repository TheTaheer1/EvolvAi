from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.llm.llm_service import LLMService
from app.llm.schemas import PlannerAgentLLMOutput
from app.llm.validators import sanitize_file_plans


class PlannerAgent(BaseAgent):
    name = "planner_agent"
    description = "Creates a mocked implementation plan without modifying source code."

    def execute(self, state: AgentState) -> dict[str, Any]:
        payload = state.get("trigger_payload") or {}
        scenario = payload.get("scenario") or {}
        company = payload.get("company_profile") or {}
        codebase_context = state.get("codebase_context") or {}
        relevant_files = codebase_context.get("relevant_files") or []
        impact = state.get("impact_analysis") or {}
        recommendation = scenario.get("expected_recommendation", "Add controlled AI product evolution")
        files = scenario.get("proposed_files") or [
            {"file_path": "docs/features/controlled-demo.md", "artifact_type": "documentation"}
        ]
        fallback_files = [
            {
                **file,
                "title": file.get("title") or file.get("file_path", "Generated artifact").split("/")[-1],
                "description": file.get("description") or f"Preview-safe {file.get('artifact_type', 'artifact')} artifact.",
                "language": file.get("language")
                or ("markdown" if file.get("file_path", "").endswith(".md") else "json" if file.get("file_path", "").endswith(".json") else "tsx" if file.get("file_path", "").endswith(".tsx") else None),
            }
            for file in files
        ]
        if len(fallback_files) < 3:
            fallback_files.extend(
                [
                    {
                        "file_path": "demo/generated/controlled-impact-plan.json",
                        "artifact_type": "config",
                        "title": "controlled-impact-plan.json",
                        "description": "Machine-readable impact and rollout plan.",
                        "language": "json",
                    },
                    {
                        "file_path": "demo/generated/controlled-preview.tsx",
                        "artifact_type": "component",
                        "title": "controlled-preview.tsx",
                        "description": "Preview-only component artifact.",
                        "language": "tsx",
                    },
                ][: 3 - len(fallback_files)]
            )
        plan = {
            "objective": recommendation,
            "affected_modules": self._affected_modules(relevant_files) or ["dashboard", "docs", "backend"],
            "tasks": [
                {
                    "title": "Create feature proposal document",
                    "description": "Write a concise feature proposal that explains the market signal and product response.",
                    "type": "documentation",
                    "complexity": "low",
                    "risk": "low",
                },
                {
                    "title": "Generate preview artifact for judges",
                    "description": "Create a visible preview artifact that demonstrates the proposed product surface.",
                    "type": "component" if any(file["file_path"].endswith(".tsx") for file in files) else "plan",
                    "complexity": "medium",
                    "risk": "low",
                },
                {
                    "title": "Create structured impact or schema artifact",
                    "description": "Create a machine-readable plan or schema that downstream verification can inspect.",
                    "type": "config",
                    "complexity": "medium",
                    "risk": "medium",
                },
            ],
            "files_to_generate": fallback_files,
            "estimated_effort": "1-2 engineering days",
            "estimated_complexity": "medium-high" if impact.get("technical_complexity", 0) >= 0.7 else "medium",
            "rollout_plan": [
                "Review generated preview artifacts with product and engineering.",
                "Validate the UX with target users before touching production code.",
                "Promote to implementation only after human approval.",
            ],
            "risks": [
                "Keep generated artifacts in preview workspace only.",
                "Avoid production code writes until human approval.",
                "Validate the feature with target users before full roadmap commitment.",
            ],
            "success_metrics": ["User interest in the proposed feature", "Reduction in manual workflow effort"],
            "assumptions": ["A preview artifact is enough for hackathon judging and human review."],
            "technical_stack": company.get("technical_stack", []),
            "codebase_context": codebase_context,
            "relevant_existing_files": relevant_files,
        }
        if relevant_files:
            plan["tasks"].append(
                {
                    "title": "Review read-only codebase context",
                    "description": "Use selected repository files as reference touchpoints without modifying them.",
                    "type": "plan",
                    "complexity": "low",
                    "risk": "low",
                }
            )
            plan["risks"].extend(codebase_context.get("risks") or [])
            plan["assumptions"].append("Repository analysis is read-only and only informs preview artifacts.")
        fallback = PlannerAgentLLMOutput.model_validate(plan)
        decision = state.get("decision") or {"recommended_action": recommendation}
        llm_output, llm_metadata = LLMService().generate_planner_output(
            workflow_id=state.get("workflow_id"),
            company=company,
            decision=decision,
            impact=impact,
            codebase_context=codebase_context,
            fallback_output=fallback,
        )
        llm_files = [file.model_dump() for file in llm_output.files_to_generate]
        safe_files = sanitize_file_plans(llm_files, fallback_files)
        if len(safe_files) < 3 and llm_metadata.get("output_mode") == "llm_enhanced":
            safe_files = sanitize_file_plans(fallback_files, fallback_files)
            llm_metadata = {**llm_metadata, "status": "fallback_used", "output_mode": "fallback_used", "fallback_used": True, "structured_output_valid": False, "error_message": "planner_file_plan_incomplete"}
        tasks = [task.model_dump() for task in llm_output.tasks] or plan["tasks"]
        plan = {
            **plan,
            "objective": llm_output.objective,
            "affected_modules": llm_output.affected_modules or plan["affected_modules"],
            "tasks": tasks,
            "files_to_generate": safe_files,
            "estimated_effort": llm_output.estimated_effort,
            "estimated_complexity": llm_output.estimated_complexity,
            "rollout_plan": llm_output.rollout_plan or plan["rollout_plan"],
            "risks": llm_output.risks or plan["risks"],
            "success_metrics": llm_output.success_metrics or plan["success_metrics"],
            "assumptions": llm_output.assumptions or plan["assumptions"],
            "codebase_context": codebase_context,
            "relevant_existing_files": relevant_files,
        }
        return {
            "implementation_plan": plan,
            "artifact_plan": safe_files,
            "output_mode": llm_metadata.get("output_mode", "deterministic"),
            "llm_metadata_by_agent": {"planner_agent": llm_metadata},
            "_llm_invocation": llm_metadata,
            "explainability": {
                "summary": (
                    "Planning used LLM-enhanced reasoning and backend path sanitization."
                    if llm_metadata.get("output_mode") == "llm_enhanced"
                    else "Planning translated strategy into preview-safe deterministic artifacts."
                ),
                "reasoning_steps": [
                    "Selected docs plus generated demo/config artifacts for a visible 2-3 minute flow.",
                    "Scoped work to preview-only files so execution cannot alter source code.",
                    "Estimated effort for a small engineering team.",
                ],
                "evidence": [
                    {"label": "Files to generate", "value": len(safe_files)},
                    {"label": "Relevant repository files", "value": len(relevant_files)},
                ],
                "assumptions": plan["assumptions"],
                "risks": plan["risks"],
                "confidence_score": 0.84,
            },
        }

    def _affected_modules(self, relevant_files: list[dict[str, Any]]) -> list[str]:
        modules: list[str] = []
        for file in relevant_files[:8]:
            path = str(file.get("path") or "")
            if path.startswith("src/app") and "frontend" not in modules:
                modules.append("frontend")
            elif path.startswith("src/components") and "components" not in modules:
                modules.append("components")
            elif path.startswith("app/api") and "api" not in modules:
                modules.append("api")
            elif path.startswith("app/models") and "data-models" not in modules:
                modules.append("data-models")
            elif path.startswith(("alembic", "migrations")) and "database" not in modules:
                modules.append("database")
            elif path and "docs" not in modules:
                modules.append("docs")
        return modules
