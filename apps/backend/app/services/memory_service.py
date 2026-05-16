import httpx

from app.core.config import settings


class MemoryService:
    def __init__(self) -> None:
        self.base_url = f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}"

    def check_health(self) -> dict[str, str]:
        for path in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            try:
                response = httpx.get(f"{self.base_url}{path}", timeout=1.5)
                if response.status_code < 500:
                    return {"status": "ok", "provider": "chroma", "url": self.base_url}
            except Exception:  # noqa: BLE001
                continue
        return {"status": "unavailable", "provider": "chroma", "url": self.base_url}

    def search_memory(self, query: str, limit: int = 5) -> list[dict]:
        return []

    def remember(self, content: str, metadata: dict | None = None) -> dict[str, str]:
        return {"status": "skipped", "reason": "Step 1 memory adapter skeleton only"}
