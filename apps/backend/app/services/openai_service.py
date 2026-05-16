from __future__ import annotations

import hashlib
import json
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.llm.prompts import RESEARCH_SYSTEM_PROMPT, research_prompt
from app.llm.schemas import ResearchLLMOutput


class OpenAIService:
    provider = "openai"
    placeholder_keys = {
        "",
        "<user-will-add-real-key-here>",
        "your_openai_api_key_here",
        "your-openai-api-key",
        "replace-me",
        "changeme",
    }

    def validate_config(self) -> bool:
        return self._api_key_state() == "configured"

    def status(self) -> dict[str, Any]:
        key_state = self._api_key_state()
        return {
            "live_ai_enabled": bool(settings.USE_LIVE_AI_OUTPUTS),
            "openai_key_present": key_state == "configured",
            "openai_key_usable": key_state == "configured",
            "openai_key_state": key_state,
            "model": settings.OPENAI_MODEL,
            "fallback_enabled": bool(settings.LLM_FALLBACK_TO_DEMO),
        }

    def generate_text(self, prompt: str) -> str:
        if not self.validate_config() or not settings.USE_LIVE_AI_OUTPUTS:
            return "OpenAI unavailable; deterministic fallback response used."
        return f"OpenAI adapter configured for {settings.OPENAI_MODEL}; use structured research generation."

    def generate_research_output(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        market_event: dict[str, Any],
        evidence: list[dict[str, Any]],
        fallback_output: ResearchLLMOutput,
    ) -> tuple[ResearchLLMOutput, dict[str, Any]]:
        user_prompt = research_prompt(company, market_event, evidence)
        metadata = self._base_metadata(workflow_id, user_prompt)
        if not settings.USE_LIVE_AI_OUTPUTS:
            metadata.update(
                {
                    "status": "fallback_used",
                    "mode": "deterministic",
                    "output_mode": "deterministic",
                    "fallback_used": True,
                    "error_message": "USE_LIVE_AI_OUTPUTS=false",
                }
            )
            return fallback_output, metadata
        if not self.validate_config():
            return fallback_output, self._fallback_metadata(metadata, self._api_key_error_reason())

        started = perf_counter()
        try:
            parsed, usage, structured_valid = self._call_openai_structured(user_prompt)
            metadata.update(
                {
                    "status": "success",
                    "mode": "llm_enhanced",
                    "output_mode": "llm_enhanced",
                    "fallback_used": False,
                    "structured_output_valid": structured_valid,
                    "latency_ms": int((perf_counter() - started) * 1000),
                    **usage,
                }
            )
            return parsed, metadata
        except Exception as exc:  # noqa: BLE001
            metadata["latency_ms"] = int((perf_counter() - started) * 1000)
            reason = self._classify_error(exc)
            if settings.LLM_FALLBACK_TO_DEMO:
                return fallback_output, self._fallback_metadata(metadata, reason)
            metadata.update(
                {
                    "status": "failed",
                    "mode": "fallback",
                    "output_mode": "fallback_used",
                    "fallback_used": False,
                    "structured_output_valid": False,
                    "error_message": reason,
                }
            )
            return fallback_output, metadata

    def _call_openai_structured(self, user_prompt: str) -> tuple[ResearchLLMOutput, dict[str, int | None], bool]:
        try:
            from openai import OpenAI
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("openai_sdk_unavailable") from exc

        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )

        try:
            completion = client.beta.chat.completions.parse(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=ResearchLLMOutput,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_OUTPUT_TOKENS,
            )
            message = completion.choices[0].message
            parsed = message.parsed
            if parsed is None:
                content = message.content or ""
                parsed = ResearchLLMOutput.model_validate_json(content)
            return parsed, self._usage_payload(getattr(completion, "usage", None)), True
        except (AttributeError, TypeError):
            return self._call_openai_json_mode(client, user_prompt)

    def _call_openai_json_mode(self, client: Any, user_prompt: str) -> tuple[ResearchLLMOutput, dict[str, int | None], bool]:
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"{user_prompt}\n\nReturn JSON only. Do not include Markdown fences.",
                },
            ],
            response_format={"type": "json_object"},
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_OUTPUT_TOKENS,
        )
        content = completion.choices[0].message.content or ""
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("invalid_json") from exc
        try:
            parsed = ResearchLLMOutput.model_validate(payload)
        except ValidationError as exc:
            raise RuntimeError("validation_error") from exc
        return parsed, self._usage_payload(getattr(completion, "usage", None)), True

    def _base_metadata(self, workflow_id: str | None, user_prompt: str) -> dict[str, Any]:
        return {
            "workflow_id": workflow_id,
            "agent_name": "research_agent",
            "provider": self.provider,
            "model": settings.OPENAI_MODEL,
            "mode": "deterministic",
            "output_mode": "deterministic",
            "prompt_hash": hashlib.sha256(user_prompt.encode("utf-8")).hexdigest(),
            "status": "fallback_used",
            "fallback_used": True,
            "structured_output_valid": False,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": None,
        }

    def _normalized_api_key(self) -> str:
        return (settings.OPENAI_API_KEY or "").strip()

    def _api_key_state(self) -> str:
        key = self._normalized_api_key()
        if not key:
            return "missing"
        if key.lower() in self.placeholder_keys or key.startswith("<"):
            return "placeholder"
        return "configured"

    def _api_key_error_reason(self) -> str:
        state = self._api_key_state()
        if state == "placeholder":
            return "placeholder_api_key"
        return "missing_api_key"

    def _fallback_metadata(self, metadata: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            **metadata,
            "status": "fallback_used",
            "mode": "fallback",
            "output_mode": "fallback_used",
            "fallback_used": True,
            "structured_output_valid": False,
            "error_message": reason[:500],
        }

    def _usage_payload(self, usage: Any) -> dict[str, int | None]:
        return {
            "input_tokens": getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    def _classify_error(self, exc: Exception) -> str:
        name = exc.__class__.__name__.lower()
        text = str(exc).lower()
        if "authentication" in name or "auth" in text or "api key" in text:
            return "authentication_error"
        if "insufficient_quota" in text or "exceeded your current quota" in text or "quota" in text:
            return "insufficient_quota"
        if "rate" in name or "rate limit" in text or "429" in text:
            return "rate_limit_error"
        if "timeout" in name or "timeout" in text or "timed out" in text:
            return "timeout_error"
        if "json" in text:
            return "invalid_json"
        if "validation" in text or isinstance(exc, ValidationError):
            return "validation_error"
        if "api" in name:
            return "sdk_error"
        return "openai_error"
