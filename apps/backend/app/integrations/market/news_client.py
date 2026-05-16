from app.core.config import settings


class NewsClient:
    def fetch_latest(self) -> list[dict]:
        if not settings.NEWS_API_KEY:
            return []
        return []
