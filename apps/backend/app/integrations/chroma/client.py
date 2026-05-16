from app.services.memory_service import MemoryService


class ChromaClient:
    def __init__(self) -> None:
        self.memory = MemoryService()

    def health(self) -> dict[str, str]:
        return self.memory.check_health()
