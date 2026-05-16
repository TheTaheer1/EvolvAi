from time import perf_counter, sleep
from typing import Any

from sqlalchemy.orm import Session

from app.agents import build_agents
from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.core.config import settings
from app.models.decision import Decision
from app.models.workflow import Workflow
from app.orchestration.graph import build_runtime_graph
from app.realtime.events import (
    AGENT_COMPLETED,
    AGENT_FAILED,
    AGENT_STARTED,
    AGENT_UPDATED,
    DECISION_CREATED,
    AGENT_DETERMINISTIC_FALLBACK,
    AGENT_LLM_ENHANCED,
    LLM_COMPLETED,
    LLM_FALLBACK_USED,
    MARKET_EVENT_NORMALIZED,
    RESEARCH_COMPLETED,
    WORKFLOW_UPDATED,
)
from app.services.agent_service import AgentService, agent_payload
from app.services.codebase_context_service import CodebaseContextService, codebase_context_payload
from app.services.explainability_service import ExplainabilityService
from app.services.generated_artifact_service import GeneratedArtifactService, generated_artifact_payload
from app.services.impact_analysis_service import ImpactAnalysisService, impact_analysis_payload
from app.services.log_service import LogService
from app.services.llm_invocation_service import LLMInvocationService, llm_invocation_payload
from app.services.pr_preview_service import PRPreviewService, pr_preview_payload
from app.services.realtime_service import RealtimeService
from app.services.verification_service import VerificationService, verification_report_payload
from app.services.workflow_service import WorkflowService, workflow_payload
from app.utils.json import to_jsonable

DEMO_SPEED_DELAYS = {"fast": 100, "normal": 700, "slow": 1500}


class WorkflowRunner:
    def __init__(self) -> None:
        self.agent_service = AgentService()
        self.workflow_service = WorkflowService()
        self.log_service = LogService()
        self.realtime = RealtimeService()
        self.agents = build_agents()
        self.explainability = ExplainabilityService(self.realtime)
        self.impact_analysis = ImpactAnalysisService(self.realtime)
        self.generated_artifacts = GeneratedArtifactService(self.realtime)
        self.verification = VerificationService(self.realtime)
        self.pr_preview = PRPreviewService(self.realtime)
        self.llm_invocations = LLMInvocationService()
        self.codebase_contexts = CodebaseContextService()

    def run(self, db: Session, workflow: Workflow) -> AgentState:
        codebase_context = self.codebase_contexts.get_by_workflow(db, workflow.id)
        state: AgentState = {
            "workflow_id": str(workflow.id),
            "company_id": (workflow.input_payload or {}).get("company_profile_id"),
            "trigger_type": workflow.trigger_type,
            "trigger_payload": workflow.input_payload or {},
            "codebase_context": codebase_context_payload(codebase_context) if codebase_context else None,
            "market_events": [],
            "status": "running",
            "errors": [],
            "logs": [],
            "trace_id": None,
        }
        handlers = {agent.name: self._handler(db, workflow, agent) for agent in self.agents}
        graph = build_runtime_graph(handlers)
        if graph is not None:
            try:
                return graph.invoke(state)
            except Exception as exc:  # noqa: BLE001
                self.log_service.create_log(
                    db,
                    "WARNING",
                    "LangGraph execution failed; using sequential fallback",
                    workflow_id=workflow.id,
                    context={"error": str(exc)},
                )
        return self._fallback_sequential(state, handlers)

    def _fallback_sequential(
        self, state: AgentState, handlers: dict[str, Any]
    ) -> AgentState:
        current = state
        for name in [agent.name for agent in self.agents]:
            current = handlers[name](current)
            if name == "strategy_agent" and not (current.get("decision") or {}).get("should_act", True):
                current["status"] = "no_action_needed"
                break
        return current

    def _handler(self, db: Session, workflow: Workflow, agent: BaseAgent):
        def run_agent(state: AgentState) -> AgentState:
            db.refresh(workflow)
            if workflow.status == "cancelled":
                raise RuntimeError("Workflow was cancelled")
            existing = self.agent_service.get_agent_execution(db, workflow.id, agent.name)
            if existing and existing.status == "completed" and existing.output_state:
                next_state = {**state, **existing.output_state}
                return next_state

            execution = self.agent_service.create_agent_execution(db, workflow.id, agent.name, state)
            self.agent_service.mark_agent_running(db, execution)
            self.workflow_service.update_current_agent(db, workflow, agent.name)
            self.realtime.emit_event(AGENT_STARTED, agent_payload(execution), workflow_id=str(workflow.id))
            self.realtime.emit_event(WORKFLOW_UPDATED, workflow_payload(workflow), workflow_id=str(workflow.id))

            started = perf_counter()
            try:
                output_state = agent.run(state)
                if output_state.get("status") == "failed":
                    raise RuntimeError("; ".join(output_state.get("errors", [])) or f"{agent.name} failed")
                output_state = self._persist_agent_outputs(db, workflow, execution, agent.name, output_state)
                duration_ms = int((perf_counter() - started) * 1000)
                execution = self.agent_service.mark_agent_completed(
                    db, execution, to_jsonable(output_state), duration_ms
                )
                self.log_service.create_log(
                    db,
                    "INFO",
                    f"{agent.name} completed",
                    workflow_id=workflow.id,
                    agent_execution_id=execution.id,
                    context={"duration_ms": duration_ms},
                )
                self.realtime.emit_event(AGENT_COMPLETED, agent_payload(execution), workflow_id=str(workflow.id))
                self._demo_sleep(workflow)
                return output_state
            except Exception as exc:  # noqa: BLE001
                duration_ms = int((perf_counter() - started) * 1000)
                execution = self.agent_service.mark_agent_failed(db, execution, str(exc), duration_ms)
                self.log_service.create_log(
                    db,
                    "ERROR",
                    f"{agent.name} failed",
                    workflow_id=workflow.id,
                    agent_execution_id=execution.id,
                    context={"error": str(exc)},
                )
                self.realtime.emit_event(AGENT_FAILED, agent_payload(execution), workflow_id=str(workflow.id))
                raise

        return run_agent

    def _demo_sleep(self, workflow: Workflow) -> None:
        payload = workflow.input_payload or {}
        if not payload.get("demo_mode"):
            return
        speed = payload.get("demo_speed") or settings.DEMO_SPEED
        delay_ms = DEMO_SPEED_DELAYS.get(str(speed), settings.DEMO_AGENT_DELAY_MS)
        try:
            sleep(max(0, int(delay_ms)) / 1000)
        except Exception:  # noqa: BLE001
            return

    def _base_explainability(
        self,
        db: Session,
        workflow: Workflow,
        execution,
        agent_name: str,
        output_state: AgentState,
    ) -> None:
        payload = workflow.input_payload or {}
        scenario = payload.get("scenario") or {}
        company = payload.get("company_profile") or {}
        explanation = self.explainability.build_agent_explanation(agent_name, output_state, scenario, company)
        self.explainability.create_explainability_record(
            db,
            workflow.id,
            agent_execution_id=execution.id,
            **explanation,
        )

    def _persist_agent_outputs(
        self,
        db: Session,
        workflow: Workflow,
        execution,
        agent_name: str,
        output_state: AgentState,
    ) -> AgentState:
        self._base_explainability(db, workflow, execution, agent_name, output_state)
        self._persist_llm_invocation(db, workflow, execution, agent_name, output_state)
        payload = workflow.input_payload or {}
        scenario = payload.get("scenario") or {}
        company = payload.get("company_profile") or {}

        if agent_name == "watcher_agent":
            event = output_state.get("normalized_market_event") or (output_state.get("market_events") or [{}])[-1]
            event["market_event_id"] = payload.get("market_event_id")
            self.log_service.create_log(
                db,
                "INFO",
                "Watcher Agent normalized market event",
                workflow_id=workflow.id,
                agent_execution_id=execution.id,
                context=event,
            )
            self.realtime.emit_event(
                MARKET_EVENT_NORMALIZED,
                {
                    **to_jsonable(event),
                    "agent_name": agent_name,
                    "message": "Watcher Agent normalized market event",
                },
                workflow_id=str(workflow.id),
            )

        if agent_name == "research_agent":
            evidence = output_state.get("research_evidence") or []
            self.log_service.create_log(
                db,
                "INFO",
                f"Research Agent collected {len(evidence)} evidence items",
                workflow_id=workflow.id,
                agent_execution_id=execution.id,
                context={"evidence_count": len(evidence), "trend_relevance": output_state.get("trend_relevance")},
            )
            self.realtime.emit_event(
                RESEARCH_COMPLETED,
                {
                    "id": str(execution.id),
                    "agent_name": agent_name,
                    "message": f"Research Agent collected {len(evidence)} evidence items",
                    "research_summary": output_state.get("research_summary"),
                    "research_evidence": to_jsonable(evidence),
                },
                workflow_id=str(workflow.id),
            )

        if agent_name == "strategy_agent":
            decision_data = output_state.get("decision") or {}
            existing_decision = db.query(Decision).filter(Decision.workflow_id == workflow.id).first()
            if not existing_decision:
                decision = Decision(
                    workflow_id=workflow.id,
                    decision_type=decision_data.get("decision_type", "feature_recommendation"),
                    title=decision_data.get("title", scenario.get("expected_recommendation", "Controlled demo recommendation")),
                    summary=decision_data.get("summary"),
                    impact_score=float(decision_data.get("impact_score", 0)),
                    confidence_score=float(decision_data.get("confidence_score", 0)),
                    recommended_action=decision_data.get("recommended_action"),
                    reasoning=to_jsonable(decision_data.get("reasoning") or {}),
                )
                db.add(decision)
                db.commit()
                db.refresh(decision)
                self.realtime.emit_event(
                    DECISION_CREATED,
                    to_jsonable(
                        {
                            "id": decision.id,
                            "workflow_id": decision.workflow_id,
                            "title": decision.title,
                            "summary": decision.summary,
                            "impact_score": decision.impact_score,
                            "confidence_score": decision.confidence_score,
                            "recommended_action": decision.recommended_action,
                            "reasoning": decision.reasoning,
                            "created_at": decision.created_at,
                        }
                    ),
                    workflow_id=str(workflow.id),
                )
            impact_data = output_state.get("impact_analysis") or self.impact_analysis.calculate_impact(scenario)
            impact = self.impact_analysis.create_impact_analysis(db, workflow.id, impact_data)
            output_state["impact_analysis"] = impact_analysis_payload(impact)
            self.log_service.create_log(
                db,
                "INFO",
                f"Strategy Agent calculated {impact.final_priority} priority impact score",
                workflow_id=workflow.id,
                agent_execution_id=execution.id,
                context=impact_analysis_payload(impact),
            )

        if agent_name == "planner_agent":
            plan = output_state.get("implementation_plan") or {}
            tasks = plan.get("tasks") or []
            self.log_service.create_log(
                db,
                "INFO",
                f"Planning Agent created {len(tasks)} implementation tasks",
                workflow_id=workflow.id,
                agent_execution_id=execution.id,
                context={"tasks": tasks, "files_to_generate": plan.get("files_to_generate") or []},
            )

        if agent_name == "execution_agent":
            artifact_specs = output_state.get("generated_artifacts") or []
            artifacts, warnings = self.generated_artifacts.write_artifacts_to_safe_directory(
                db,
                workflow.id,
                artifact_specs,
            )
            artifact_payloads = [generated_artifact_payload(artifact) for artifact in artifacts]
            output_state["persisted_artifacts"] = artifact_payloads
            output_state["artifact_warnings"] = warnings
            for artifact in artifact_payloads:
                self.realtime.emit_event(
                    AGENT_UPDATED,
                    {
                        "id": str(execution.id),
                        "workflow_id": str(workflow.id),
                        "agent_name": agent_name,
                        "status": "running",
                        "message": f"Generated artifact: {artifact['file_path']}",
                        "payload": artifact,
                    },
                    workflow_id=str(workflow.id),
                )
            self.log_service.create_log(
                db,
                "INFO",
                f"Execution Agent generated {len(artifacts)} safe artifacts",
                workflow_id=workflow.id,
                agent_execution_id=execution.id,
                context={"artifact_count": len(artifacts), "warnings": warnings},
            )

        if agent_name == "verification_agent":
            artifacts = self.generated_artifacts.list_by_workflow(db, workflow.id)
            report_data = self.verification.verify_artifacts(artifacts)
            report = self.verification.create_verification_report(db, workflow.id, report_data)
            output_state["verification_result"] = verification_report_payload(report)
            self.log_service.create_log(
                db,
                "INFO" if report.passed else "WARNING",
                f"Verification Agent {'passed' if report.passed else 'failed'} {len(report.checks)} safety checks",
                workflow_id=workflow.id,
                agent_execution_id=execution.id,
                context=verification_report_payload(report),
            )

        if agent_name == "pr_agent":
            artifacts = self.generated_artifacts.list_by_workflow(db, workflow.id)
            report = self.verification.get_by_workflow(db, workflow.id)
            impact = self.impact_analysis.get_by_workflow(db, workflow.id)
            plan = output_state.get("implementation_plan") or {}
            if not plan:
                previous_plan = self.agent_service.get_agent_execution(db, workflow.id, "planner_agent")
                plan = (previous_plan.output_state or {}).get("implementation_plan", {}) if previous_plan else {}
            pr = self.pr_preview.create_pr_preview(
                db,
                workflow.id,
                scenario=scenario,
                company=company,
                artifacts=artifacts,
                verification=report,
                impact=impact,
                plan=plan,
                llm_pr_output=output_state.get("pull_request_llm"),
            )
            output_state["pull_request"] = pr_preview_payload(pr)
            self.log_service.create_log(
                db,
                "INFO",
                "PR Agent created preview PR plan",
                workflow_id=workflow.id,
                agent_execution_id=execution.id,
                context=pr_preview_payload(pr),
            )

        return output_state

    def _persist_llm_invocation(
        self,
        db: Session,
        workflow: Workflow,
        execution,
        agent_name: str,
        output_state: AgentState,
    ) -> None:
        metadata = output_state.get("_llm_invocation")
        if not metadata or metadata.get("agent_name") != agent_name:
            return
        data = {
            **metadata,
            "workflow_id": str(workflow.id),
            "agent_execution_id": str(execution.id),
            "agent_name": agent_name,
        }
        try:
            invocation = self.llm_invocations.create_invocation(db, data)
            payload = llm_invocation_payload(invocation)
            by_agent = dict(output_state.get("llm_metadata_by_agent") or {})
            by_agent[agent_name] = payload
            output_state["llm_metadata_by_agent"] = by_agent
            output_state.pop("_llm_invocation", None)
            if invocation.status == "success":
                self.realtime.emit_event(LLM_COMPLETED, payload, workflow_id=str(workflow.id))
                self.realtime.emit_event(
                    AGENT_LLM_ENHANCED,
                    {
                        **payload,
                        "message": f"{agent_name} used LLM-enhanced reasoning",
                    },
                    workflow_id=str(workflow.id),
                )
            elif invocation.fallback_used:
                self.realtime.emit_event(LLM_FALLBACK_USED, payload, workflow_id=str(workflow.id))
                self.realtime.emit_event(
                    AGENT_DETERMINISTIC_FALLBACK,
                    {
                        **payload,
                        "message": f"{agent_name} used deterministic fallback",
                    },
                    workflow_id=str(workflow.id),
                )
        except Exception as exc:  # noqa: BLE001
            self.log_service.create_log(
                db,
                "WARNING",
                "Failed to record LLM invocation metadata",
                workflow_id=workflow.id,
                agent_execution_id=execution.id,
                context={"agent_name": agent_name, "error": str(exc)},
            )
