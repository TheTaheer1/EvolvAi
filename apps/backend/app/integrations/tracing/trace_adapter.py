class TraceAdapter:
    def __init__(self, enabled: bool, provider: str) -> None:
        self.enabled = enabled
        self.provider = provider

    def start_span(self, name: str, metadata: dict | None = None) -> dict:
        if not self.enabled:
            return {"provider": self.provider, "span": name, "status": "disabled"}
        return {"provider": self.provider, "span": name, "status": "stubbed", "metadata": metadata or {}}
