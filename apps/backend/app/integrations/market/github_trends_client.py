from app.core.config import settings


class GitHubTrendsClient:
    def fetch_trends(self) -> list[dict]:
        if not settings.GITHUB_TRENDS_ENABLED:
            return []
        return []
