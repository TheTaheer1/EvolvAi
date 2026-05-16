from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import SessionLocal
from app.ingestion.dedupe import external_content_hash
from app.ingestion.github_ingestion import GitHubIngestionService, GitHubRateLimitError
from app.ingestion.normalizer import normalize_github_repository_to_event
from app.ingestion.scoring import github_repository_importance
from app.main import fastapi_app
from app.services.event_service import EventService
from app.services.external_event_service import ExternalEventService


def _repo_payload(**overrides):
    payload = {
        "id": 987654321,
        "full_name": "example/ai-saas-automation",
        "name": "ai-saas-automation",
        "description": "AI SaaS automation toolkit with agents and workflow recommendations",
        "stargazers_count": 2400,
        "forks_count": 300,
        "language": "TypeScript",
        "updated_at": "2026-05-01T00:00:00Z",
        "html_url": "https://github.com/example/ai-saas-automation",
        "topics": ["ai", "saas", "automation"],
    }
    payload.update(overrides)
    return payload


def test_github_repo_payload_normalizes_to_market_event() -> None:
    event = normalize_github_repository_to_event(_repo_payload())
    assert event["source"] == "github"
    assert event["event_type"] == "github_repository_trend"
    assert event["title"] == "example/ai-saas-automation"
    assert "Stars: 2400" in event["summary"]
    assert event["url"] == "https://github.com/example/ai-saas-automation"


def test_github_importance_score_clamps() -> None:
    assert 0 <= github_repository_importance(_repo_payload(stargazers_count=999999999, forks_count=999999999)) <= 1


def test_github_content_hash_uses_repo_identity_and_updated_at() -> None:
    repo = _repo_payload()
    assert external_content_hash("github", repo) == external_content_hash("github", dict(repo))
    changed = dict(repo, updated_at="2026-05-02T00:00:00Z")
    assert external_content_hash("github", repo) != external_content_hash("github", changed)


def test_missing_github_token_warns_but_does_not_crash(monkeypatch) -> None:
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")

    def fake_request(self, method, url, params=None):
        return {"items": [_repo_payload()]}

    monkeypatch.setattr(GitHubIngestionService, "safe_request", fake_request)
    repos, warnings = GitHubIngestionService().search_repositories("AI SaaS automation", 1)
    assert len(repos) == 1
    assert any("GITHUB_TOKEN is missing" in warning for warning in warnings)


def test_rate_limit_response_is_classified() -> None:
    response = httpx.Response(403, headers={"X-RateLimit-Remaining": "0"}, text="API rate limit exceeded")
    try:
        GitHubIngestionService().handle_rate_limit(response)
    except GitHubRateLimitError as exc:
        assert "rate_limit" in str(exc)
    else:
        raise AssertionError("Expected GitHubRateLimitError")


def test_external_event_service_skips_duplicate_repo() -> None:
    db = SessionLocal()
    try:
        repo = _repo_payload(id=int(uuid4().int % 1_000_000_000), updated_at="2026-05-03T00:00:00Z")
        service = ExternalEventService()
        first_events, _first_raw, first_skipped = service.normalize_and_store_github_repositories(db, [repo])
        second_events, _second_raw, second_skipped = service.normalize_and_store_github_repositories(db, [repo])
        assert len(first_events) == 1
        assert first_skipped == 0
        assert len(second_events) == 0
        assert second_skipped == 1
    finally:
        db.close()


def test_live_events_ingest_github_endpoint_returns_summary(monkeypatch) -> None:
    repo = _repo_payload(id=int(uuid4().int % 1_000_000_000), updated_at="2026-05-04T00:00:00Z")

    def fake_ingest(self, query, max_results):
        return [repo], ["mocked GitHub response"]

    monkeypatch.setattr(GitHubIngestionService, "ingest_github_search", fake_ingest)
    response = TestClient(fastapi_app).post(
        "/api/v1/live-events/ingest/github",
        json={"query": "AI SaaS automation stars:>500", "max_results": 1, "trigger_workflows": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "github"
    assert payload["status"] == "completed"
    assert payload["events_found"] == 1
    assert payload["events_created"] in {0, 1}
    assert "market_events" in payload


def test_trigger_workflow_from_market_event_creates_queued_workflow(monkeypatch) -> None:
    from app.tasks.workflow_tasks import run_workflow

    monkeypatch.setattr(run_workflow, "apply_async", lambda *args, **kwargs: None)
    db = SessionLocal()
    try:
        event = EventService().create_market_event(
            db,
            {
                "source": "github",
                "event_type": "github_repository_trend",
                "title": f"example/live-event-{uuid4().hex[:8]}",
                "summary": "A live GitHub event for workflow trigger testing.",
                "url": "https://github.com/example/live-event",
                "importance_score": 0.74,
            },
            emit=False,
        )
    finally:
        db.close()
    response = TestClient(fastapi_app).post(f"/api/v1/market-events/{event.id}/trigger-workflow")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["trigger_type"] == "live_market_event"
