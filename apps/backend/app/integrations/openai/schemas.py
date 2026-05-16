from pydantic import BaseModel


class TextGenerationRequest(BaseModel):
    prompt: str
    model: str | None = None


class TextGenerationResponse(BaseModel):
    text: str
    used_stub: bool = True
