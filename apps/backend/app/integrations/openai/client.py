from app.services.openai_service import OpenAIService


class OpenAIClient:
    def __init__(self) -> None:
        self.service = OpenAIService()

    def generate_text(self, prompt: str) -> str:
        return self.service.generate_text(prompt)
