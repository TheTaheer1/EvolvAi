from typing import Any


def clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 2)


def calculate_opportunity_score(
    business_impact: float,
    urgency: float,
    confidence: float,
    risk_score: float,
) -> float:
    return clamp_score(
        business_impact * 0.4
        + urgency * 0.3
        + confidence * 0.2
        + (1 - risk_score) * 0.1
    )


def priority_from_score(opportunity_score: float) -> str:
    if opportunity_score >= 0.85:
        return "critical"
    if opportunity_score >= 0.70:
        return "high"
    if opportunity_score >= 0.50:
        return "medium"
    return "low"


def build_impact_breakdown(scores: dict[str, Any]) -> dict[str, float]:
    business_impact = clamp_score(scores.get("business_impact", 0))
    technical_complexity = clamp_score(scores.get("technical_complexity", 0))
    urgency = clamp_score(scores.get("urgency", 0))
    confidence = clamp_score(scores.get("confidence", 0))
    risk_score = clamp_score(scores.get("risk_score", 0))
    return {
        "customer_value": clamp_score((business_impact + confidence) / 2),
        "competitive_pressure": urgency,
        "revenue_potential": clamp_score((business_impact * 0.7) + (urgency * 0.3)),
        "retention_impact": business_impact,
        "engineering_effort": technical_complexity,
        "implementation_risk": risk_score,
        "time_sensitivity": urgency,
    }


def calculate_impact_from_scores(scores: dict[str, Any], recommendation: str | None = None) -> dict[str, Any]:
    business_impact = clamp_score(scores.get("business_impact", 0))
    technical_complexity = clamp_score(scores.get("technical_complexity", 0))
    urgency = clamp_score(scores.get("urgency", 0))
    confidence = clamp_score(scores.get("confidence", 0))
    risk_score = clamp_score(scores.get("risk_score", 0))
    opportunity_score = calculate_opportunity_score(business_impact, urgency, confidence, risk_score)
    return {
        "business_impact": business_impact,
        "technical_complexity": technical_complexity,
        "urgency": urgency,
        "confidence": confidence,
        "risk_score": risk_score,
        "opportunity_score": opportunity_score,
        "final_priority": priority_from_score(opportunity_score),
        "impact_breakdown": build_impact_breakdown(scores),
        "recommendation": recommendation,
    }
