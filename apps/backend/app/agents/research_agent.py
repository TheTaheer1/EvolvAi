from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.llm.llm_service import LLMService
from app.llm.schemas import EvidenceItem, ResearchLLMOutput


class ResearchAgent(BaseAgent):
    name = "research_agent"
    description = "Summarizes market context with safe provider-based LLM fallback behavior."

    def execute(self, state: AgentState) -> dict[str, Any]:
        payload = state.get("trigger_payload") or {}
        scenario = payload.get("scenario") or {}
        company = payload.get("company_profile") or {}
        event = state.get("normalized_market_event") or (state.get("market_events") or [{}])[-1]
        evidence = scenario.get("research_evidence") or []
        if not evidence:
            evidence = [
                {
                    "source": "controlled_demo",
                    "title": f"{event.get('title', 'Market signal')} affects {company.get('name', 'AcmeFlow')}",
                    "summary": "Fallback deterministic evidence generated because the scenario had no evidence.",
                    "relevance": "medium",
                    "url": None,
                }
                for _ in range(3)
            ]
        competitors = company.get("competitors") or []
        modules = company.get("product_modules") or []
        summary = (
            f"Research found {len(evidence)} controlled evidence items. The signal is relevant to "
            f"{', '.join(modules[:3]) or 'core product modules'} and competitive against "
            f"{', '.join(competitors[:3]) or 'AI-native SaaS tools'}."
        )
        fallback = ResearchLLMOutput(
            research_summary=summary,
            evidence=[EvidenceItem.model_validate(item) for item in evidence],
            relevance_score=0.86 if event.get("importance_score", 0) >= 0.8 else 0.68,
            competitor_relevance=0.82 if competitors else 0.55,
            confidence_score=0.82,
            key_market_signals=[event.get("title") or scenario.get("title") or "Market signal"],
            risks=["Live market data could shift after the demo; controlled evidence remains stable."],
            assumptions=[
                "AcmeFlow users value workflow automation.",
                "Competitor relevance is higher when the signal touches existing modules.",
            ],
        )
        llm_output, llm_metadata = LLMService().generate_research_output(
            workflow_id=state.get("workflow_id"),
            company=company,
            market_event=event,
            evidence=evidence,
            fallback_output=fallback,
        )
        merged_evidence: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for item in [*llm_output.evidence, *fallback.evidence]:
            dumped = item.model_dump()
            title_key = dumped["title"].strip().lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            merged_evidence.append(dumped)
        return {
            "research_summary": llm_output.research_summary,
            "research_evidence": merged_evidence[:6],
            "trend_relevance": "high" if llm_output.relevance_score >= 0.75 else "medium",
            "competitor_relevance": "high" if llm_output.competitor_relevance >= 0.7 else "medium",
            "confidence_score": llm_output.confidence_score,
            "output_mode": llm_metadata.get("output_mode", "deterministic"),
            "llm_metadata_by_agent": {"research_agent": llm_metadata},
            "_llm_invocation": llm_metadata,
            "explainability": {
                "summary": (
                    "Research used LLM-enhanced reasoning with deterministic fallback."
                    if llm_metadata.get("output_mode") == "llm_enhanced"
                    else "Research used deterministic fallback after live AI was unavailable."
                    if llm_metadata.get("output_mode") == "fallback_used"
                    else "Research used deterministic evidence attached to the scenario."
                ),
                "reasoning_steps": [
                    "Collected evidence items for the selected market event.",
                    "Compared evidence against AcmeFlow's competitor set and product modules.",
                    "Kept URLs and live AI optional so missing external keys cannot break the demo.",
                ],
                "evidence": [{"label": item["title"], "value": item["summary"]} for item in merged_evidence[:3]],
                "assumptions": llm_output.assumptions or fallback.assumptions,
                "risks": llm_output.risks or fallback.risks,
                "confidence_score": llm_output.confidence_score,
            },
        }
