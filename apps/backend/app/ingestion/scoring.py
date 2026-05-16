from datetime import datetime, timedelta, timezone
from typing import Any


KEYWORDS = {
    "ai",
    "agent",
    "automation",
    "rag",
    "retrieval",
    "saas",
    "meeting",
    "summary",
    "compliance",
    "audit",
}


def clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 2)


def github_repository_importance(repo: dict[str, Any]) -> float:
    stars = int(repo.get("stargazers_count") or 0)
    forks = int(repo.get("forks_count") or 0)
    updated_at = _parse_github_datetime(repo.get("updated_at"))
    text = f"{repo.get('name', '')} {repo.get('full_name', '')} {repo.get('description', '')}".lower()
    keyword_hits = sum(1 for keyword in KEYWORDS if keyword in text)
    recent = bool(updated_at and updated_at >= datetime.now(timezone.utc) - timedelta(days=30))
    return clamp_score(
        0.4
        + min(stars / 10000, 0.3)
        + min(forks / 3000, 0.15)
        + (0.1 if recent else 0)
        + min(keyword_hits * 0.025, 0.15)
    )


def _parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
