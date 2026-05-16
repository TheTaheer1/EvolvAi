from app.core.config import settings


class OmiumClient:
    def enabled(self) -> bool:
        return bool(settings.OMIUM_API_KEY and settings.TRACING_ENABLED)

    def start_span(self, name: str, metadata: dict | None = None) -> dict:
        if not self.enabled():
            return {"status": "stubbed", "span_name": name, "metadata": metadata or {}}
        return {"status": "configured", "span_name": name, "metadata": metadata or {}}
