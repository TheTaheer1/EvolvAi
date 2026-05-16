from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import SessionLocal
from app.ingestion.dedupe import external_content_hash
from app.ingestion.github_ingestion import GitHubIngestionService, GitHubRateLimitError
from app.ingestion.hacker_news_ingestion import (
    HackerNewsIngestionService,
    hacker_news_importance,
    normalize_hacker_news_story_to_event,
    story_matches_keywords,
)
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


def _hn_story(**overrides):
    payload = {
        "id": int(uuid4().int % 1_000_000_000),
        "type": "story",
        "title": "Show HN: AI workflow automation for SaaS teams",
        "url": "https://example.com/ai-workflow",
        "by": "founder42",
        "score": 180,
        "descendants": 54,
        "time": 1778880000,
        "kids": [1, 2, 3],
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


def test_hacker_news_story_normalizes_to_market_event() -> None:
    event = normalize_hacker_news_story_to_event(_hn_story(), keywords=["ai", "saas"])
    assert event["source"] == "hacker_news"
    assert event["event_type"] == "hacker_news_product_signal"
    assert "Hacker News story" in event["summary"]
    assert event["raw_payload"]["tags"]


def test_hacker_news_importance_score_clamps() -> None:
    assert 0 <= hacker_news_importance(_hn_story(score=999999, descendants=999999), ["ai"]) <= 1


def test_hacker_news_keyword_filtering_and_empty_keyword_list() -> None:
    story = _hn_story(title="Database internals discussion", url="https://example.com/database")
    assert not story_matches_keywords(story, ["ai"])
    assert story_matches_keywords(story, [])


def test_hacker_news_deleted_dead_and_missing_url_behavior() -> None:
    service = HackerNewsIngestionService()
    assert service.should_skip_story(_hn_story(deleted=True), min_score=0, keywords=[])
    assert service.should_skip_story(_hn_story(dead=True), min_score=0, keywords=[])
    event = normalize_hacker_news_story_to_event(_hn_story(url=None), keywords=[])
    assert event["url"].startswith("https://news.ycombinator.com/item?id=")


def test_hacker_news_duplicate_story_is_skipped() -> None:
    db = SessionLocal()
    try:
        story = _hn_story()
        service = ExternalEventService()
        first_events, _first_raw, first_skipped = service.normalize_and_store_hacker_news_stories(db, [story], keywords=["ai"])
        second_events, _second_raw, second_skipped = service.normalize_and_store_hacker_news_stories(db, [story], keywords=["ai"])
        assert len(first_events) == 1
        assert first_skipped == 0
        assert len(second_events) == 0
        assert second_skipped == 1
    finally:
        db.close()


def test_live_event_sources_include_hacker_news() -> None:
    response = TestClient(fastapi_app).get("/api/v1/live-events/sources")
    assert response.status_code == 200
    sources = response.json()
    assert any(source["source_key"] == "hacker_news" and source["source_type"] == "news" for source in sources)


def test_live_events_ingest_hacker_news_endpoint_returns_summary(monkeypatch) -> None:
    story = _hn_story()

    def fake_ingest(self, feed, max_results, keywords=None, min_score=None):
        return [story], ["mocked Hacker News response"]

    monkeypatch.setattr(HackerNewsIngestionService, "ingest_hacker_news", fake_ingest)
    response = TestClient(fastapi_app).post(
        "/api/v1/live-events/ingest/hacker-news",
        json={
            "feed": "top",
            "max_results": 1,
            "keywords": ["ai", "saas"],
            "min_score": 20,
            "trigger_workflows": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "hacker_news"
    assert payload["status"] == "completed"
    assert payload["events_found"] == 1
    assert "market_events" in payload


def test_live_events_ingest_hacker_news_invalid_feed_returns_400() -> None:
    response = TestClient(fastapi_app).post(
        "/api/v1/live-events/ingest/hacker-news",
        json={"feed": "invalid", "max_results": 1, "keywords": [], "min_score": 0},
    )
    assert response.status_code == 400


def test_market_events_source_filter_hacker_news() -> None:
    db = SessionLocal()
    try:
        event = EventService().create_market_event(
            db,
            {
                "source": "hacker_news",
                "event_type": "hacker_news_story",
                "title": f"HN test event {uuid4().hex[:8]}",
                "summary": "A Hacker News event for source filtering.",
                "url": "https://news.ycombinator.com/item?id=1",
                "importance_score": 0.74,
            },
            emit=False,
        )
    finally:
        db.close()
    response = TestClient(fastapi_app).get("/api/v1/market-events?source=hacker_news")
    assert response.status_code == 200
    assert any(item["id"] == str(event.id) for item in response.json())
