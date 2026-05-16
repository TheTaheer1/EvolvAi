from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.ingestion.dedupe import external_content_hash
from app.ingestion.normalizer import normalize_github_repository_to_event
from app.ingestion.scoring import github_repository_importance


class GitHubIngestionError(RuntimeError):
    pass


class GitHubRateLimitError(GitHubIngestionError):
    pass


class GitHubIngestionService:
    def __init__(self) -> None:
        self.base_url = settings.GITHUB_API_BASE_URL.rstrip("/")

    def search_repositories(self, query: str, max_results: int = 10) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        if not settings.GITHUB_TOKEN:
            warnings.append("GITHUB_TOKEN is missing; using unauthenticated GitHub requests with lower rate limits.")
        payload = self.safe_request(
            "GET",
            f"{self.base_url}/search/repositories",
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max(1, min(max_results, 25)),
            },
        )
        items = payload.get("items") if isinstance(payload, dict) else []
        if not isinstance(items, list):
            raise GitHubIngestionError("malformed_response")
        return items[:max_results], warnings

    def fetch_repository_details(self, full_name: str) -> dict[str, Any]:
        return self.safe_request("GET", f"{self.base_url}/repos/{full_name}")

    def ingest_github_search(self, query: str, max_results: int = 10) -> tuple[list[dict[str, Any]], list[str]]:
        return self.search_repositories(query=query, max_results=max_results)

    def normalize_repository_to_market_event(self, repo: dict[str, Any]) -> dict[str, Any]:
        return normalize_github_repository_to_event(repo)

    def normalize_repository_to_event(self, repo: dict[str, Any]) -> dict[str, Any]:
        return self.normalize_repository_to_market_event(repo)

    def calculate_importance_score(self, repo: dict[str, Any]) -> float:
        return github_repository_importance(repo)

    def create_content_hash(self, repo: dict[str, Any]) -> str:
        return external_content_hash("github", repo)

    def handle_github_error(self, error: Exception) -> str:
        return self._classify_error(error)

    def safe_request(self, method: str, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "EvolvAI-Step3-Demo",
        }
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        last_error: Exception | None = None
        for attempt in range(settings.GITHUB_MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=settings.GITHUB_REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
                    response = client.request(method, url, params=params)
                if response.status_code == 401:
                    raise GitHubIngestionError(self._github_error_message(response, "github_authentication_error"))
                if response.status_code == 403:
                    self.handle_rate_limit(response)
                    raise GitHubIngestionError(self._github_error_message(response, "github_forbidden"))
                if response.status_code == 422:
                    raise GitHubIngestionError(self._github_error_message(response, "github_query_invalid"))
                if response.status_code == 404:
                    raise GitHubIngestionError(self._github_error_message(response, "github_resource_missing"))
                if response.status_code in {500, 502, 503, 504} and attempt < settings.GITHUB_MAX_RETRIES:
                    last_error = GitHubIngestionError(f"github_server_error_{response.status_code}")
                    continue
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError as exc:
                    raise GitHubIngestionError("malformed_json") from exc
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt >= settings.GITHUB_MAX_RETRIES:
                    raise GitHubIngestionError("github_timeout") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= settings.GITHUB_MAX_RETRIES:
                    raise GitHubIngestionError(self._classify_error(exc)) from exc
        raise GitHubIngestionError(str(last_error or "github_request_failed"))

    def handle_rate_limit(self, response: httpx.Response) -> None:
        if not settings.GITHUB_RATE_LIMIT_SAFETY_ENABLED:
            return
        remaining = response.headers.get("X-RateLimit-Remaining")
        body = response.text.lower()
        if remaining == "0" or "rate limit" in body or "secondary rate limit" in body:
            raise GitHubRateLimitError("github_rate_limit")

    def _github_error_message(self, response: httpx.Response, default: str) -> str:
        try:
            payload = response.json()
        except ValueError:
            return default
        message = payload.get("message") if isinstance(payload, dict) else None
        return f"{default}: {message}" if message else default

    def _classify_error(self, error: Exception) -> str:
        text = str(error).lower()
        if "rate limit" in text or "secondary rate limit" in text or "429" in text:
            return "github_rate_limit"
        if "401" in text or "bad credentials" in text or "authentication" in text:
            return "github_authentication_error"
        if "403" in text or "forbidden" in text:
            return "github_forbidden"
        if "422" in text or "validation failed" in text or "query_invalid" in text:
            return "github_query_invalid"
        if "404" in text:
            return "github_resource_missing"
        if "timeout" in text:
            return "github_timeout"
        if "network" in text or "connection" in text:
            return "github_network_error"
        if "malformed" in text or "json" in text:
            return "malformed_response"
        return "github_provider_error"
