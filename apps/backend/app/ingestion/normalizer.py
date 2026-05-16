from typing import Any

from app.ingestion.scoring import github_repository_importance


def normalize_github_repository_to_event(repo: dict[str, Any]) -> dict[str, Any]:
    full_name = repo.get("full_name") or repo.get("name") or "GitHub repository"
    description = repo.get("description") or "No repository description was provided."
    stars = int(repo.get("stargazers_count") or 0)
    forks = int(repo.get("forks_count") or 0)
    language = repo.get("language") or "unknown"
    topics = repo.get("topics") or []
    summary = f"{description} Stars: {stars}. Forks: {forks}. Primary language: {language}."
    if topics:
        summary = f"{summary} Topics: {', '.join(topics[:6])}."
    return {
        "source": "github",
        "event_type": "github_repository_trend",
        "title": full_name,
        "summary": summary,
        "url": repo.get("html_url"),
        "importance_score": github_repository_importance(repo),
        "raw_payload": repo,
    }
