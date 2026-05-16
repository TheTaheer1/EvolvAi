from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.ingestion.scoring import clamp_score


class HackerNewsIngestionError(RuntimeError):
    pass


class HackerNewsInvalidFeedError(HackerNewsIngestionError):
    pass


HN_SOURCE = "hacker_news"
HN_FEEDS = {
    "top": "topstories",
    "new": "newstories",
    "best": "beststories",
    "show": "showstories",
    "ask": "askstories",
    "jobs": "jobstories",
}
ALLOWED_TYPES = {"story", "job", "poll"}
TAG_KEYWORDS = {
    "ai": ["ai", "artificial intelligence"],
    "llm": ["llm", "large language model", "gpt"],
    "agent": ["agent", "agents"],
    "saas": ["saas"],
    "startup": ["startup", "startups"],
    "productivity": ["productivity"],
    "automation": ["automation", "workflow"],
    "security": ["security"],
    "compliance": ["compliance", "audit"],
    "developer-tools": ["developer tools", "devtool", "developer"],
    "rag": ["rag", "retrieval"],
    "github": ["github", "open source", "opensource"],
}


def hn_item_url(item_id: int | str | None) -> str:
    return f"https://news.ycombinator.com/item?id={item_id}"


def parse_keywords(raw_keywords: list[str] | None = None) -> list[str] | None:
    if raw_keywords is not None:
        return [keyword.strip().lower() for keyword in raw_keywords if keyword and keyword.strip()]
    return [keyword.strip().lower() for keyword in settings.HN_KEYWORDS.split(",") if keyword.strip()]


def strip_hn_text(value: Any, limit: int = 1000) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def story_search_text(story: dict[str, Any]) -> str:
    return " ".join(
        [
            str(story.get("title") or ""),
            strip_hn_text(story.get("text"), 2000),
            str(story.get("url") or ""),
        ]
    ).lower()


def keyword_matches_text(text: str, keyword: str) -> bool:
    normalized = keyword.strip().lower()
    if not normalized:
        return False
    if " " in normalized:
        return normalized in text
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text) is not None


def story_matches_keywords(story: dict[str, Any], keywords: list[str] | None) -> bool:
    if keywords == []:
        return True
    active_keywords = keywords if keywords is not None else parse_keywords(None)
    if not active_keywords:
        return True
    text = story_search_text(story)
    return any(keyword_matches_text(text, keyword) for keyword in active_keywords)


def extract_hn_tags(story: dict[str, Any], keywords: list[str] | None = None) -> list[str]:
    text = story_search_text(story)
    tags: list[str] = []
    for tag, aliases in TAG_KEYWORDS.items():
        if any(keyword_matches_text(text, alias) for alias in aliases):
            tags.append(tag)
    for keyword in keywords or []:
        normalized = keyword.strip().lower()
        if normalized and keyword_matches_text(text, normalized) and normalized not in tags:
            tags.append(normalized.replace(" ", "-"))
    return tags[:8]


def hacker_news_content_hash(story: dict[str, Any]) -> str:
    stable = {
        "source": HN_SOURCE,
        "id": story.get("id"),
        "title": story.get("title"),
        "url": story.get("url"),
    }
    if not stable["id"]:
        stable["text"] = strip_hn_text(story.get("text"), 500)
    encoded = json.dumps(stable, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hacker_news_importance(story: dict[str, Any], keywords: list[str] | None = None) -> float:
    score = int(story.get("score") or 0)
    descendants = int(story.get("descendants") or 0)
    story_time = story.get("time")
    now = datetime.now(timezone.utc)
    try:
        created = datetime.fromtimestamp(int(story_time), timezone.utc) if story_time else None
    except (TypeError, ValueError, OSError):
        created = None
    keyword_hits = len(extract_hn_tags(story, keywords))
    return clamp_score(
        0.35
        + min(score / 500, 0.25)
        + min(descendants / 300, 0.20)
        + min(keyword_hits * 0.035, 0.15)
        + (0.05 if created and created >= now - timedelta(hours=48) else 0)
        + (0.05 if story.get("url") else 0)
    )


def normalize_hacker_news_story_to_event(
    story: dict[str, Any],
    *,
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    item_id = story.get("id")
    title = str(story.get("title") or "Hacker News story").strip()
    author = story.get("by") or "unknown"
    score = int(story.get("score") or 0)
    comments = int(story.get("descendants") or 0)
    tags = extract_hn_tags(story, keywords)
    story_type = str(story.get("type") or "story")
    url = story.get("url") or hn_item_url(item_id)
    if story_type == "job":
        event_type = "hacker_news_hiring_signal"
    elif title.lower().startswith("ask hn:"):
        event_type = "hacker_news_discussion"
    elif title.lower().startswith("show hn:"):
        event_type = "hacker_news_product_signal"
    else:
        event_type = "hacker_news_story"
    topic_text = ", ".join(tags) if tags else "technology and startup trends"
    summary = (
        f"Hacker News story '{title}' by {author} has {score} points and {comments} comments. "
        f"It may signal community interest in {topic_text}."
    )
    raw_payload = {
        **story,
        "hn_item_url": hn_item_url(item_id),
        "tags": tags,
        "keyword_matches": tags,
        "safe_text": strip_hn_text(story.get("text"), 1000),
    }
    return {
        "source": HN_SOURCE,
        "event_type": event_type,
        "title": title[:500],
        "summary": summary,
        "url": url,
        "importance_score": hacker_news_importance(story, keywords),
        "company_name": None,
        "competitor_name": None,
        "raw_payload": raw_payload,
    }


class HackerNewsIngestionService:
    def __init__(self) -> None:
        self.base_url = settings.HN_API_BASE_URL.rstrip("/")

    def fetch_story_ids(self, feed: str, limit: int) -> list[int]:
        feed_key = self._normalize_feed(feed)
        payload = self.safe_request(f"{self.base_url}/{HN_FEEDS[feed_key]}.json")
        if not isinstance(payload, list):
            raise HackerNewsIngestionError("hn_malformed_response")
        return [int(item_id) for item_id in payload[: max(1, min(limit, settings.HN_MAX_STORIES))]]

    def fetch_item(self, item_id: int) -> dict[str, Any]:
        payload = self.safe_request(f"{self.base_url}/item/{item_id}.json")
        if payload is None:
            raise HackerNewsIngestionError("hn_item_missing")
        if not isinstance(payload, dict):
            raise HackerNewsIngestionError("hn_malformed_response")
        return payload

    def fetch_stories(
        self,
        *,
        feed: str,
        limit: int,
        keywords: list[str] | None = None,
        min_score: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        story_ids = self.fetch_story_ids(feed, limit)
        warnings: list[str] = []
        stories: list[dict[str, Any]] = []
        active_min_score = settings.HN_MIN_SCORE if min_score is None else max(0, int(min_score))
        for item_id in story_ids:
            try:
                story = self.fetch_item(item_id)
            except HackerNewsIngestionError as exc:
                warnings.append(f"Skipped HN item {item_id}: {self.classify_error(exc)}")
                continue
            if self.should_skip_story(story, min_score=active_min_score, keywords=keywords):
                continue
            stories.append(story)
        if not stories:
            warnings.append("No Hacker News stories matched the selected feed, score, and keyword filters.")
        return stories, warnings

    def ingest_hacker_news(
        self,
        *,
        feed: str,
        max_results: int,
        keywords: list[str] | None = None,
        min_score: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        return self.fetch_stories(
            feed=feed,
            limit=max_results,
            keywords=parse_keywords(keywords),
            min_score=min_score,
        )

    def normalize_story_to_market_event(
        self,
        story: dict[str, Any],
        *,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        return normalize_hacker_news_story_to_event(story, keywords=parse_keywords(keywords))

    def calculate_importance_score(self, story: dict[str, Any]) -> float:
        return hacker_news_importance(story)

    def create_content_hash(self, story: dict[str, Any]) -> str:
        return hacker_news_content_hash(story)

    def should_skip_story(
        self,
        story: dict[str, Any],
        *,
        min_score: int,
        keywords: list[str] | None,
    ) -> bool:
        if story.get("deleted") or story.get("dead"):
            return True
        if not story.get("title"):
            return True
        if str(story.get("type") or "") not in ALLOWED_TYPES:
            return True
        if int(story.get("score") or 0) < min_score:
            return True
        if not story_matches_keywords(story, keywords):
            return True
        return False

    def safe_request(self, url: str) -> Any:
        last_error: Exception | None = None
        for attempt in range(settings.HN_MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=settings.HN_REQUEST_TIMEOUT_SECONDS) as client:
                    response = client.get(url)
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError as exc:
                    raise HackerNewsIngestionError("hn_malformed_response") from exc
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt >= settings.HN_MAX_RETRIES:
                    raise HackerNewsIngestionError("hn_timeout") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= settings.HN_MAX_RETRIES:
                    raise HackerNewsIngestionError(self.classify_error(exc)) from exc
        raise HackerNewsIngestionError(str(last_error or "hn_provider_error"))

    def classify_error(self, error: Exception) -> str:
        text = str(error).lower()
        if "invalid_hn_feed" in text:
            return "hn_invalid_feed"
        if "timeout" in text:
            return "hn_timeout"
        if "network" in text or "connect" in text:
            return "hn_network_error"
        if "malformed" in text or "json" in text:
            return "hn_malformed_response"
        return "hn_provider_error"

    def _normalize_feed(self, feed: str) -> str:
        feed_key = str(feed or settings.HN_DEFAULT_FEED or "top").strip().lower()
        if feed_key not in HN_FEEDS:
            raise HackerNewsInvalidFeedError("invalid_hn_feed")
        return feed_key
