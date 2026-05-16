from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.core.config import settings
from app.demo.scoring import calculate_impact_from_scores
from app.llm.llm_service import LLMService
from app.llm.schemas import StrategyAgentLLMOutput


class StrategyAgent(BaseAgent):
    name = "strategy_agent"
    description = "Produces a deterministic strategic decision for the demo workflow."

    def execute(self, state: AgentState) -> dict[str, Any]:
        payload = state.get("trigger_payload") or {}
        scenario = payload.get("scenario") or {}
        company = payload.get("company_profile") or {}
        event = state.get("normalized_market_event") or {}
        baseline_scores = scenario.get("scores") or {
            "business_impact": 0.72,
            "technical_complexity": 0.55,
            "urgency": 0.66,
            "confidence": 0.7,
            "risk_score": 0.35,
        }
        impact = calculate_impact_from_scores(
            baseline_scores,
            recommendation=scenario.get("expected_recommendation"),
        )
        fallback = StrategyAgentLLMOutput(
            should_act=True,
            decision_type="feature_recommendation",
            title=scenario.get("expected_recommendation", "Add controlled AI product evolution"),
            summary=(
                f"{company.get('name', 'AcmeFlow')} should act because "
                f"{event.get('why_it_matters') or scenario.get('description')}"
            ),
            business_impact=impact["business_impact"],
            technical_complexity=impact["technical_complexity"],
            urgency=impact["urgency"],
            confidence_score=impact["confidence"],
            risk_score=impact["risk_score"],
            recommended_action=scenario.get("expected_recommendation") or "Create a safe product evolution proposal.",
            why_now=event.get("summary", scenario.get("description", "The market signal is relevant now.")),
            why_relevant=f"The signal maps to {', '.join((company.get('product_modules') or [])[:3])}.",
            expected_benefit="Higher retention, stronger AI-native positioning, and clearer enterprise readiness.",
            risks=[
                "Small engineering team must keep the rollout incremental.",
                "AI output quality must be explainable before production use.",
            ],
            assumptions=[
                "Retention and product stickiness are primary goals.",
                "Controlled demo scenarios should all produce should_act=true.",
            ],
        )
        research = {
            "summary": state.get("research_summary"),
            "evidence": state.get("research_evidence") or [],
            "trend_relevance": state.get("trend_relevance"),
            "competitor_relevance": state.get("competitor_relevance"),
            "confidence_score": state.get("confidence_score"),
        }
        llm_output, llm_metadata = LLMService().generate_strategy_output(
            workflow_id=state.get("workflow_id"),
            company=company,
            market_event=event,
            research=research,
            fallback_output=fallback,
        )
        controlled_demo = bool(payload.get("demo_mode") or scenario.get("scenario_key"))
        should_act = bool(llm_output.should_act)
        if not controlled_demo and (
            llm_output.confidence_score < settings.CONFIDENCE_ACTION_THRESHOLD
            or llm_output.business_impact < settings.IMPACT_ACTION_THRESHOLD
        ):
            should_act = False
        scores = {
            "business_impact": llm_output.business_impact,
            "technical_complexity": llm_output.technical_complexity,
            "urgency": llm_output.urgency,
            "confidence": llm_output.confidence_score,
            "risk_score": llm_output.risk_score,
        }
        impact = calculate_impact_from_scores(scores, recommendation=llm_output.recommended_action)
        decision = {
            "should_act": should_act,
            "decision_type": llm_output.decision_type,
            "title": llm_output.title,
            "summary": llm_output.summary,
            "impact_score": impact["business_impact"],
            "confidence_score": impact["confidence"],
            "recommended_action": llm_output.recommended_action,
            "reasoning": {
                "why_now": llm_output.why_now,
                "why_relevant": llm_output.why_relevant,
                "expected_benefit": llm_output.expected_benefit,
                "risks": llm_output.risks,
            },
        }
        return {
            "impact_score": impact["business_impact"],
            "impact_analysis": impact,
            "decision": decision,
            "output_mode": llm_metadata.get("output_mode", "deterministic"),
            "llm_metadata_by_agent": {"strategy_agent": llm_metadata},
            "_llm_invocation": llm_metadata,
            "explainability": {
                "summary": (
                    "Strategy used LLM-enhanced reasoning, then backend scoring recalculated priority."
                    if llm_metadata.get("output_mode") == "llm_enhanced"
                    else "Strategy converted the market signal into a deterministic should-act recommendation."
                ),
                "reasoning_steps": [
                    "Compared business impact, urgency, confidence, and risk.",
                    "Applied backend-owned action thresholds and priority scoring.",
                    "Selected a feature recommendation that fits AcmeFlow's goals and product modules.",
                ],
                "evidence": [
                    {"label": "Opportunity score", "value": impact["opportunity_score"]},
                    {"label": "Final priority", "value": impact["final_priority"]},
                ],
                "assumptions": llm_output.assumptions or fallback.assumptions,
                "risks": decision["reasoning"]["risks"],
                "confidence_score": impact["confidence"],
            },
        }
