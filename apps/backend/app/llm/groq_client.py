from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from app.core.config import settings


class GroqStructuredResult(BaseModel):
    output: dict[str, Any]
    usage: dict[str, int | None] = {}
    latency_ms: int


class GroqStructuredClient:
    def __init__(self) -> None:
        self.provider = "groq"

    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_model: Type[BaseModel],
    ) -> GroqStructuredResult:
        if not settings.GROQ_API_KEY:
            raise RuntimeError("missing_api_key")
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("groq_sdk_unavailable") from exc

        client = Groq(
            api_key=settings.GROQ_API_KEY,
            timeout=settings.GROQ_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
        )

        schema_hint = json.dumps(schema_model.model_json_schema(), indent=2)
        full_user_prompt = (
            f"{user_prompt}\n\n"
            "Return only valid JSON matching the required schema. Do not include markdown, comments, prose, "
            "hidden chain-of-thought, or surrounding text.\n"
            f"Required JSON shape:\n{schema_hint}"
        )

        started = perf_counter()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=settings.GROQ_MAX_OUTPUT_TOKENS,
            temperature=settings.GROQ_TEMPERATURE,
        )
        latency_ms = int((perf_counter() - started) * 1000)

        text = response.choices[0].message.content or ""
        if not text:
            raise RuntimeError("empty_response")

        try:
            output = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("malformed_output") from exc

        usage_obj = getattr(response, "usage", None)
        usage = {
            "input_tokens": getattr(usage_obj, "prompt_tokens", None),
            "output_tokens": getattr(usage_obj, "completion_tokens", None),
            "total_tokens": getattr(usage_obj, "total_tokens", None),
        }
        return GroqStructuredResult(output=output, usage=usage, latency_ms=latency_ms)
