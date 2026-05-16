from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.llm.llm_service import LLMService
from app.llm.schemas import WatcherLLMOutput


class WatcherAgent(BaseAgent):
    name = "watcher_agent"
    description = "Normalizes incoming market signals into a workflow-ready event."

    def execute(self, state: AgentState) -> dict[str, Any]:
        payload = state.get("trigger_payload") or {}
        scenario = payload.get("scenario") or {}
        company = payload.get("company_profile") or {}
        scenario_event = scenario.get("market_event") or {}
        market_event = {
            "source": scenario.get("event_source", "controlled_demo"),
            "event_type": scenario.get("event_type", "competitor_update"),
            "title": scenario_event.get("title", payload.get("event", "Controlled market signal detected")),
            "summary": scenario_event.get("summary", scenario.get("description", "Deterministic demo event normalized.")),
            "importance_score": scenario_event.get("importance_score", scenario.get("default_impact_score", 0.8)),
            "tags": scenario.get("tags", ["controlled_demo"]),
            "scenario_key": scenario.get("scenario_key"),
            "company_name": company.get("name", "AcmeFlow"),
            "why_it_matters": scenario_event.get("why_it_matters"),
            "recommended_evolution": scenario_event.get("recommended_evolution", scenario.get("expected_recommendation")),
        }
        fallback = WatcherLLMOutput.model_validate(
            {
                **market_event,
                "why_it_matters": market_event.get("why_it_matters") or scenario.get("description") or market_event["summary"],
                "confidence_score": 0.86,
                "assumptions": [
                    "Controlled demo scenarios are trusted fixtures."
                    if not payload.get("live_event")
                    else "Live event ingestion stores raw source data before normalization.",
                    "Duplicate triggers are allowed and create independent workflows.",
                ],
                "risks": ["The signal still needs research and verification before any implementation work."],
            }
        )
        llm_output, llm_metadata = LLMService().generate_watcher_output(
            workflow_id=state.get("workflow_id"),
            company=company,
            trigger_payload=payload,
            deterministic_event=market_event,
            fallback_output=fallback,
        )
        normalized = llm_output.model_dump()
        normalized["scenario_key"] = market_event.get("scenario_key")
        normalized["company_name"] = normalized.get("company_name") or market_event.get("company_name")
        normalized["source"] = normalized.get("source") or market_event["source"]
        normalized["tags"] = (normalized.get("tags") or market_event.get("tags") or [])[:8]
        is_live_event = bool(payload.get("live_event") or scenario.get("live_event"))
        return {
            "market_events": [normalized],
            "normalized_market_event": normalized,
            "importance_score": normalized["importance_score"],
            "output_mode": llm_metadata.get("output_mode", "deterministic"),
            "llm_metadata_by_agent": {"watcher_agent": llm_metadata},
            "_llm_invocation": llm_metadata,
            "explainability": {
                "summary": (
                    f"Watcher used LLM-enhanced normalization for {company.get('name', 'AcmeFlow')}'s product context."
                    if llm_metadata.get("output_mode") == "llm_enhanced"
                    else f"Watcher normalized a live external signal for {company.get('name', 'AcmeFlow')}'s product context."
                    if is_live_event
                    else f"Watcher matched the controlled signal to {company.get('name', 'AcmeFlow')}'s product context."
                ),
                "reasoning_steps": [
                    "Loaded the selected deterministic scenario or normalized live event payload.",
                    "Normalized the market event into source, event type, summary, tags, and importance score.",
                    "Mapped the signal to the demo company profile so downstream agents can reason consistently.",
                ],
                "evidence": [
                    {"label": "Market signal", "value": normalized["title"]},
                    {"label": "Importance score", "value": normalized["importance_score"]},
                ],
                "assumptions": llm_output.assumptions or fallback.assumptions,
                "risks": llm_output.risks or fallback.risks,
                "confidence_score": llm_output.confidence_score,
            },
            "status": "running",
        }
