from __future__ import annotations

import base64
from pathlib import PurePosixPath
from typing import Any

import httpx

from app.core.config import settings


class RepositoryReaderError(RuntimeError):
    pass


class RepositoryRateLimitError(RepositoryReaderError):
    pass


SECRET_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_dsa",
    "id_ed25519",
    "known_hosts",
    "secrets.json",
}

SECRET_PATH_MARKERS = ("/.ssh/", "/secrets/", "/secret/", "/tokens/", "/keys/")

LANGUAGE_BY_EXTENSION = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".js": "JavaScript",
    ".jsx": "React JSX",
    ".py": "Python",
    ".md": "Markdown",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
    ".env.example": "Environment template",
}


class RepositoryReader:
    """Read-only GitHub repository metadata and tree scanner."""

    def __init__(self) -> None:
        self.base_url = settings.GITHUB_API_BASE_URL.rstrip("/")

    def get_repo_metadata(self, owner: str, repo: str) -> dict[str, Any]:
        return self.safe_request("GET", f"{self.base_url}/repos/{owner}/{repo}")

    def get_repo_tree(self, owner: str, repo: str, branch: str) -> list[dict[str, Any]]:
        payload = self.safe_request(
            "GET",
            f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
        )
        tree = payload.get("tree") if isinstance(payload, dict) else None
        if not isinstance(tree, list):
            raise RepositoryReaderError("malformed_repository_tree")
        return tree

    def get_file_content(self, owner: str, repo: str, path: str, branch: str) -> str | None:
        if not self.should_include_file(path, 0):
            return None
        payload = self.safe_request(
            "GET",
            f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch},
        )
        if not isinstance(payload, dict) or payload.get("type") != "file":
            return None
        size = int(payload.get("size") or 0)
        if size > settings.REPO_ANALYSIS_MAX_FILE_SIZE_BYTES:
            return None
        content = payload.get("content")
        encoding = payload.get("encoding")
        if not isinstance(content, str) or encoding != "base64":
            return None
        try:
            decoded = base64.b64decode(content, validate=False)
            return decoded.decode("utf-8", errors="ignore")
        except Exception as exc:  # noqa: BLE001
            raise RepositoryReaderError("file_content_decode_failed") from exc

    def classify_file(self, path: str) -> str:
        lowered = path.lower()
        name = PurePosixPath(path).name.lower()
        if name in {"package.json", "requirements.txt", "pyproject.toml", "dockerfile", "docker-compose.yml"}:
            return "project_manifest"
        if name.startswith("readme"):
            return "documentation"
        if "/app/api/" in f"/{lowered}" or lowered.startswith("app/api/"):
            return "api"
        if "/app/models/" in f"/{lowered}" or lowered.startswith("app/models/"):
            return "data_model"
        if lowered.startswith("src/app/"):
            return "frontend_route"
        if lowered.startswith("src/components/"):
            return "frontend_component"
        if lowered.startswith("src/lib/"):
            return "frontend_library"
        if "alembic/" in lowered or lowered.startswith("migrations/"):
            return "migration"
        if name.endswith((".yml", ".yaml", ".toml", ".json", ".env.example")):
            return "configuration"
        if name.endswith(".md"):
            return "documentation"
        return "source"

    def detect_language(self, path: str) -> str | None:
        lowered = path.lower()
        for extension, language in LANGUAGE_BY_EXTENSION.items():
            if lowered.endswith(extension):
                return language
        if PurePosixPath(path).name.lower() == "dockerfile":
            return "Dockerfile"
        return None

    def should_include_file(self, path: str, size: int | None) -> bool:
        normalized = path.strip().replace("\\", "/")
        lowered = normalized.lower()
        if not normalized or normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
            return False
        parts = [part.lower() for part in PurePosixPath(normalized).parts]
        excluded_dirs = self._csv(settings.REPO_ANALYSIS_EXCLUDED_DIRS)
        if any(part in excluded_dirs for part in parts[:-1]):
            return False
        name = parts[-1] if parts else ""
        if name in SECRET_FILE_NAMES or any(marker in f"/{lowered}/" for marker in SECRET_PATH_MARKERS):
            return False
        if "private_key" in lowered or "github_token" in lowered or "api_key" in lowered:
            return False
        if size is not None and size > settings.REPO_ANALYSIS_MAX_FILE_SIZE_BYTES:
            return False
        allowed = self._csv(settings.REPO_ANALYSIS_ALLOWED_EXTENSIONS)
        if PurePosixPath(normalized).name == "Dockerfile":
            return True
        return any(lowered.endswith(extension) for extension in allowed)

    def score_file_importance(self, path: str) -> float:
        lowered = path.lower()
        name = PurePosixPath(path).name.lower()
        score = 0.2
        if name in {"package.json", "requirements.txt", "pyproject.toml", "dockerfile", "docker-compose.yml"}:
            score += 0.55
            if "/" not in lowered:
                score += 0.2
        if name.startswith("readme"):
            score += 0.45
            if "/" not in lowered:
                score += 0.15
        if lowered.startswith(("app/api/", "app/models/", "src/app/", "src/components/", "src/lib/")):
            score += 0.4
        if lowered.startswith(("packages/next/src/", "packages/next/package.json")):
            score += 0.25
        if "alembic/" in lowered or lowered.startswith("migrations/") or "prisma/schema.prisma" in lowered:
            score += 0.35
        if lowered.endswith((".tsx", ".ts", ".py")):
            score += 0.15
        if lowered.startswith("examples/"):
            score -= 0.12
        if "/compiled/" in lowered or lowered.startswith(".github/"):
            score -= 0.2
        if "test" in lowered or "__tests__" in lowered:
            score -= 0.08
        return max(0.0, min(score, 1.0))

    def detect_tech_stack(self, files: list[dict[str, Any]]) -> list[str]:
        paths = {str(file.get("path", "")).lower() for file in files}
        stack: set[str] = set()
        if "package.json" in paths or any(path.endswith((".tsx", ".jsx")) for path in paths):
            stack.update({"React", "TypeScript"})
        if any(path.startswith("src/app/") or path.startswith("app/") and path.endswith("page.tsx") for path in paths):
            stack.add("Next.js")
        if any("packages/next/" in path or "next.config" in path for path in paths):
            stack.add("Next.js")
        if any(path.endswith("tailwind.config.js") or path.endswith("tailwind.config.ts") for path in paths):
            stack.add("Tailwind")
        if "requirements.txt" in paths or "pyproject.toml" in paths or any(path.endswith(".py") for path in paths):
            stack.add("Python")
        if any(path.endswith("main.py") or "fastapi" in path for path in paths):
            stack.add("FastAPI")
        if any("models/" in path or "sqlalchemy" in path for path in paths):
            stack.add("SQLAlchemy")
        if any("alembic/" in path or "migrations/" in path for path in paths):
            stack.add("PostgreSQL")
        if any("celery" in path for path in paths):
            stack.add("Celery")
        if any("redis" in path for path in paths):
            stack.add("Redis")
        if any(path.endswith("docker-compose.yml") or PurePosixPath(path).name.lower() == "dockerfile" for path in paths):
            stack.add("Docker")
        if any("langgraph" in path for path in paths):
            stack.add("LangGraph")
        return sorted(stack)

    def safe_request(self, method: str, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "EvolvAI-Step5-Repo-Analyzer",
        }
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        last_error: Exception | None = None
        for attempt in range(settings.GITHUB_MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=settings.GITHUB_REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
                    response = client.request(method, url, params=params)
                if response.status_code == 401:
                    raise RepositoryReaderError(self._github_error_message(response, "github_authentication_error"))
                if response.status_code == 403:
                    self.handle_rate_limit(response)
                    raise RepositoryReaderError(self._github_error_message(response, "github_forbidden"))
                if response.status_code == 404:
                    raise RepositoryReaderError(self._github_error_message(response, "github_resource_missing"))
                if response.status_code == 422:
                    raise RepositoryReaderError(self._github_error_message(response, "github_branch_or_query_invalid"))
                if response.status_code in {500, 502, 503, 504} and attempt < settings.GITHUB_MAX_RETRIES:
                    last_error = RepositoryReaderError(f"github_server_error_{response.status_code}")
                    continue
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError as exc:
                    raise RepositoryReaderError("malformed_json") from exc
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt >= settings.GITHUB_MAX_RETRIES:
                    raise RepositoryReaderError("github_timeout") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= settings.GITHUB_MAX_RETRIES:
                    raise RepositoryReaderError(self.classify_error(exc)) from exc
        raise RepositoryReaderError(str(last_error or "github_request_failed"))

    def handle_rate_limit(self, response: httpx.Response) -> None:
        if not settings.GITHUB_RATE_LIMIT_SAFETY_ENABLED:
            return
        remaining = response.headers.get("X-RateLimit-Remaining")
        body = response.text.lower()
        if remaining == "0" or "rate limit" in body or "secondary rate limit" in body:
            raise RepositoryRateLimitError("github_rate_limit")

    def classify_error(self, error: Exception) -> str:
        text = str(error).lower()
        if "rate limit" in text or "429" in text:
            return "github_rate_limit"
        if "401" in text or "bad credentials" in text or "authentication" in text:
            return "github_authentication_error"
        if "403" in text or "forbidden" in text:
            return "github_forbidden"
        if "404" in text:
            return "github_resource_missing"
        if "422" in text or "branch" in text:
            return "github_branch_or_query_invalid"
        if "timeout" in text:
            return "github_timeout"
        if "network" in text or "connection" in text:
            return "github_network_error"
        if "malformed" in text or "json" in text:
            return "malformed_response"
        return "github_provider_error"

    def _github_error_message(self, response: httpx.Response, default: str) -> str:
        try:
            payload = response.json()
        except ValueError:
            return default
        message = payload.get("message") if isinstance(payload, dict) else None
        return f"{default}: {message}" if message else default

    def _csv(self, value: str) -> set[str]:
        return {item.strip().lower() for item in str(value or "").split(",") if item.strip()}
