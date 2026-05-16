from __future__ import annotations

from time import perf_counter
from typing import Any, Type

from pydantic import BaseModel

from app.core.config import settings


class OpenAIStructuredResult(BaseModel):
    output: dict[str, Any]
    usage: dict[str, int | None] = {}
    latency_ms: int


class OpenAIStructuredClient:
    def __init__(self) -> None:
        self.provider = "openai"

    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_model: Type[BaseModel],
    ) -> OpenAIStructuredResult:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("missing_api_key")
        try:
            from openai import OpenAI
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"openai_client_unavailable: {exc}") from exc

        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )
        schema = schema_model.model_json_schema()
        started = perf_counter()
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_model.__name__,
                    "schema": schema,
                    "strict": False,
                }
            },
            max_output_tokens=settings.OPENAI_MAX_OUTPUT_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
        )
        latency_ms = int((perf_counter() - started) * 1000)
        text = getattr(response, "output_text", None) or self._extract_output_text(response)
        if not text:
            raise RuntimeError("empty_response")

        import json

        try:
            output = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("malformed_output") from exc
        usage_obj = getattr(response, "usage", None)
        usage = {
            "input_tokens": getattr(usage_obj, "input_tokens", None),
            "output_tokens": getattr(usage_obj, "output_tokens", None),
            "total_tokens": getattr(usage_obj, "total_tokens", None),
        }
        return OpenAIStructuredResult(output=output, usage=usage, latency_ms=latency_ms)

    def _extract_output_text(self, response: Any) -> str | None:
        try:
            chunks: list[str] = []
            for item in getattr(response, "output", []) or []:
                for content in getattr(item, "content", []) or []:
                    text = getattr(content, "text", None)
                    if text:
                        chunks.append(text)
            return "\n".join(chunks) if chunks else None
        except Exception:  # noqa: BLE001
            return None
