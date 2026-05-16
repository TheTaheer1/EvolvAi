from __future__ import annotations

import hashlib
import json
import re
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.llm.prompts import RESEARCH_SYSTEM_PROMPT, research_prompt
from app.llm.schemas import ResearchLLMOutput


class XAIService:
    provider = "xai"
    placeholder_keys = {
        "",
        "<user-will-add-real-key-here>",
        "your_xai_key_here",
        "your_grok_key_here",
        "replace-me",
        "changeme",
    }

    def validate_config(self) -> bool:
        return self._api_key_state() == "configured"

    def status(self) -> dict[str, Any]:
        key_state = self._api_key_state()
        return {
            "live_ai_enabled": bool(settings.USE_LIVE_AI_OUTPUTS),
            "provider": self.provider,
            "model": settings.XAI_MODEL,
            "fallback_enabled": bool(settings.LLM_FALLBACK_TO_DEMO),
            "xai_key_present": key_state == "configured",
            "xai_key_usable": key_state == "configured",
            "xai_key_state": key_state,
            "openai_key_present": self._foreign_key_present(settings.OPENAI_API_KEY),
            "openai_key_usable": self._foreign_key_present(settings.OPENAI_API_KEY),
        }

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
                    "status": "skipped",
                    "mode": "deterministic",
                    "output_mode": "deterministic",
                    "fallback_used": False,
                    "error_message": "USE_LIVE_AI_OUTPUTS=false",
                }
            )
            return fallback_output, metadata
        if not self.validate_config():
            return fallback_output, self._fallback_metadata(metadata, self._api_key_error_reason())

        started = perf_counter()
        try:
            parsed, usage, structured_valid = self._call_xai_research(user_prompt)
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
                    "mode": "llm_failed",
                    "output_mode": "fallback_used",
                    "fallback_used": False,
                    "structured_output_valid": False,
                    "error_message": reason,
                }
            )
            return fallback_output, metadata

    def test_connection(self) -> dict[str, Any]:
        status = self.status()
        if not status["live_ai_enabled"]:
            return {
                "success": False,
                "enabled": False,
                "fallback_used": False,
                "status": "skipped",
                "provider": self.provider,
                "model": settings.XAI_MODEL,
                "message": "USE_LIVE_AI_OUTPUTS=false; deterministic fallback is active.",
                "latency_ms": None,
            }
        if not self.validate_config():
            reason = self._api_key_error_reason()
            message = "XAI_API_KEY is missing; EvolvAI will use deterministic fallback."
            if reason == "placeholder_api_key":
                message = "XAI_API_KEY is still a placeholder; replace it with a valid xAI key to enable Grok output."
            return {
                "success": False,
                "enabled": False,
                "fallback_used": True,
                "status": "fallback_used",
                "provider": self.provider,
                "model": settings.XAI_MODEL,
                "message": message,
                "error_message": reason,
                "latency_ms": None,
            }
        started = perf_counter()
        try:
            payload, _usage = self._call_xai_json(
                "Return only this JSON object: {\"ok\": true}",
                schema_hint='{"ok": true}',
                max_tokens=64,
            )
            if payload.get("ok") is not True:
                raise RuntimeError("malformed_json")
            return {
                "success": True,
                "enabled": True,
                "fallback_used": False,
                "status": "success",
                "provider": self.provider,
                "model": settings.XAI_MODEL,
                "message": "xAI Grok provider test succeeded.",
                "latency_ms": int((perf_counter() - started) * 1000),
            }
        except Exception as exc:  # noqa: BLE001
            reason = self._classify_error(exc)
            return {
                "success": False,
                "enabled": False,
                "fallback_used": True,
                "status": "fallback_used",
                "provider": self.provider,
                "model": settings.XAI_MODEL,
                "message": f"xAI Grok unavailable; deterministic fallback will be used ({reason}).",
                "error_message": reason,
                "latency_ms": int((perf_counter() - started) * 1000),
            }

    def _call_xai_research(self, user_prompt: str) -> tuple[ResearchLLMOutput, dict[str, int | None], bool]:
        schema_hint = json.dumps(ResearchLLMOutput.model_json_schema(), indent=2)
        payload, usage = self._call_xai_json(user_prompt, schema_hint=schema_hint)
        try:
            parsed = ResearchLLMOutput.model_validate(payload)
        except ValidationError as exc:
            raise RuntimeError("schema_validation_error") from exc
        return parsed, usage, True

    def _call_xai_json(
        self,
        user_prompt: str,
        *,
        schema_hint: str,
        max_tokens: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, int | None]]:
        try:
            from openai import OpenAI
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("openai_sdk_unavailable") from exc

        client = OpenAI(
            api_key=settings.XAI_API_KEY,
            base_url=settings.XAI_API_BASE_URL,
            timeout=settings.XAI_TIMEOUT_SECONDS,
            max_retries=0,
        )
        prompt = (
            f"{user_prompt}\n\n"
            "Return only valid JSON matching the required schema. Do not include markdown, comments, prose, "
            "hidden chain-of-thought, invented URLs, destructive commands, or direct production changes.\n"
            "Use provided controlled evidence when live data is not available.\n"
            f"Required JSON shape:\n{schema_hint}"
        )
        completion = client.chat.completions.create(
            model=settings.XAI_MODEL,
            messages=[
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=settings.XAI_TEMPERATURE,
            max_tokens=max_tokens or settings.XAI_MAX_OUTPUT_TOKENS,
        )
        content = completion.choices[0].message.content or ""
        return self._parse_json(content), self._usage_payload(getattr(completion, "usage", None))

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError("malformed_json") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("malformed_json")
        return payload

    def _base_metadata(self, workflow_id: str | None, user_prompt: str) -> dict[str, Any]:
        return {
            "workflow_id": workflow_id,
            "agent_name": "research_agent",
            "provider": self.provider,
            "model": settings.XAI_MODEL,
            "mode": "deterministic",
            "output_mode": "deterministic",
            "prompt_hash": hashlib.sha256(user_prompt.encode("utf-8")).hexdigest(),
            "status": "skipped",
            "fallback_used": False,
            "structured_output_valid": False,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": None,
        }

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

    def _normalized_api_key(self) -> str:
        return (settings.XAI_API_KEY or "").strip()

    def _api_key_state(self) -> str:
        key = self._normalized_api_key()
        lowered = key.lower()
        if not key:
            return "missing"
        if (
            key.startswith("<")
            or key.endswith(">")
            or lowered in self.placeholder_keys
            or "placeholder" in lowered
            or "your_" in lowered
        ):
            return "placeholder"
        return "configured"

    def _api_key_error_reason(self) -> str:
        return "placeholder_api_key" if self._api_key_state() == "placeholder" else "missing_api_key"

    def _foreign_key_present(self, key: str | None) -> bool:
        value = (key or "").strip()
        lowered = value.lower()
        return bool(value and not value.startswith("<") and "placeholder" not in lowered and "your_" not in lowered)

    def _usage_payload(self, usage: Any) -> dict[str, int | None]:
        return {
            "input_tokens": getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    def _classify_error(self, exc: Exception) -> str:
        text = str(exc).lower()
        name = exc.__class__.__name__.lower()
        if "missing_api_key" in text:
            return "missing_api_key"
        if "placeholder_api_key" in text:
            return "placeholder_api_key"
        if "authentication" in name or "unauthorized" in text or "invalid api key" in text or "401" in text:
            return "authentication_error"
        if "quota" in text or "insufficient" in text or "billing" in text:
            return "insufficient_quota"
        if "rate" in name or "rate limit" in text or "too many requests" in text or "429" in text:
            return "rate_limit_error"
        if "timeout" in name or "timeout" in text or "timed out" in text:
            return "timeout_error"
        if "model" in text and ("not found" in text or "does not exist" in text or "404" in text):
            return "model_not_found"
        if "permission" in text or "forbidden" in text or "403" in text:
            return "permission_error"
        if "malformed_json" in text or "json" in text:
            return "malformed_json"
        if "schema_validation_error" in text or "validation" in text or isinstance(exc, ValidationError):
            return "schema_validation_error"
        if "api" in name or "provider" in text:
            return "provider_error"
        return "unknown_error"
