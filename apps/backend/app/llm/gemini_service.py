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


class GeminiService:
    provider = "gemini"
    placeholder_keys = {
        "",
        "<user-will-add-gemini-api-key-here>",
        "<user-will-add-real-key-here>",
        "your_gemini_api_key_here",
        "your-gemini-api-key",
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
            "gemini_key_present": key_state == "configured",
            "gemini_key_usable": key_state == "configured",
            "gemini_key_state": key_state,
            "model": settings.GEMINI_MODEL,
            "fallback_enabled": bool(settings.LLM_FALLBACK_TO_DEMO),
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
            parsed, usage, structured_valid = self._call_gemini_research(user_prompt)
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
                "enabled": False,
                "fallback_used": False,
                "status": "skipped",
                "provider": self.provider,
                "model": settings.GEMINI_MODEL,
                "message": "USE_LIVE_AI_OUTPUTS=false; deterministic fallback is active.",
                "latency_ms": None,
            }
        if not self.validate_config():
            reason = self._api_key_error_reason()
            message = "GEMINI_API_KEY is missing; EvolvAI will use deterministic fallback."
            if reason == "placeholder_gemini_api_key":
                message = "GEMINI_API_KEY is still a placeholder; replace it with a valid key to enable Gemini output."
            return {
                "enabled": False,
                "fallback_used": True,
                "status": "fallback_used",
                "provider": self.provider,
                "model": settings.GEMINI_MODEL,
                "message": message,
                "latency_ms": None,
            }
        started = perf_counter()
        try:
            payload, _usage = self._call_gemini_json(
                "Return only this JSON object: {\"ok\": true}",
                schema_hint='{"ok": true}',
            )
            if payload.get("ok") is not True:
                raise RuntimeError("invalid_json")
            return {
                "enabled": True,
                "fallback_used": False,
                "status": "success",
                "provider": self.provider,
                "model": settings.GEMINI_MODEL,
                "message": "Gemini provider responded successfully.",
                "latency_ms": int((perf_counter() - started) * 1000),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "enabled": False,
                "fallback_used": True,
                "status": "fallback_used",
                "provider": self.provider,
                "model": settings.GEMINI_MODEL,
                "message": f"Gemini unavailable; deterministic fallback will be used ({self._classify_error(exc)}).",
                "latency_ms": int((perf_counter() - started) * 1000),
            }

    def _call_gemini_research(self, user_prompt: str) -> tuple[ResearchLLMOutput, dict[str, int | None], bool]:
        schema_hint = json.dumps(ResearchLLMOutput.model_json_schema(), indent=2)
        payload, usage = self._call_gemini_json(user_prompt, schema_hint=schema_hint)
        try:
            parsed = ResearchLLMOutput.model_validate(payload)
        except ValidationError as exc:
            raise RuntimeError("validation_error") from exc
        return parsed, usage, True

    def _call_gemini_json(self, user_prompt: str, *, schema_hint: str) -> tuple[dict[str, Any], dict[str, int | None]]:
        try:
            from google import genai
            from google.genai import types
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("gemini_sdk_unavailable") from exc

        try:
            http_options = types.HttpOptions(timeout=int(settings.GEMINI_TIMEOUT_SECONDS * 1000))
            client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=http_options)
        except TypeError:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = (
            f"{RESEARCH_SYSTEM_PROMPT}\n\n"
            f"{user_prompt}\n\n"
            "Return only valid JSON. Do not include Markdown fences, comments, prose, or hidden reasoning.\n"
            f"JSON schema or expected shape:\n{schema_hint}"
        )
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=settings.GEMINI_TEMPERATURE,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        text = self._extract_response_text(response)
        if not text:
            raise RuntimeError("empty_response")
        return self._parse_json(text), self._usage_payload(getattr(response, "usage_metadata", None))

    def _extract_response_text(self, response: Any) -> str:
        try:
            text = getattr(response, "text", None)
            if text:
                return str(text)
        except Exception:  # noqa: BLE001
            pass
        chunks: list[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                text = getattr(part, "text", None)
                if text:
                    chunks.append(str(text))
        return "\n".join(chunks)

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError("invalid_json") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("invalid_json")
        return payload

    def _base_metadata(self, workflow_id: str | None, user_prompt: str) -> dict[str, Any]:
        return {
            "workflow_id": workflow_id,
            "agent_name": "research_agent",
            "provider": self.provider,
            "model": settings.GEMINI_MODEL,
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
        return (settings.GEMINI_API_KEY or "").strip()

    def _api_key_state(self) -> str:
        key = self._normalized_api_key()
        if not key:
            return "missing"
        if key.lower() in self.placeholder_keys or key.startswith("<"):
            return "placeholder"
        return "configured"

    def _api_key_error_reason(self) -> str:
        return "placeholder_gemini_api_key" if self._api_key_state() == "placeholder" else "missing_gemini_api_key"

    def _usage_payload(self, usage: Any) -> dict[str, int | None]:
        return {
            "input_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
        }

    def _classify_error(self, exc: Exception) -> str:
        text = str(exc).lower()
        name = exc.__class__.__name__.lower()
        if "missing_gemini_api_key" in text:
            return "missing_gemini_api_key"
        if "placeholder_gemini_api_key" in text:
            return "placeholder_gemini_api_key"
        if "api_key_invalid" in text or "api key not valid" in text or "permission_denied" in text or "401" in text:
            return "authentication_error"
        if "quota" in text or "resource_exhausted" in text or "insufficient" in text:
            return "insufficient_quota"
        if "rate" in text or "429" in text:
            return "rate_limit_error"
        if "timeout" in text or "deadline" in text or "timed out" in text:
            return "timeout_error"
        if "json" in text:
            return "invalid_json"
        if "validation" in text or isinstance(exc, ValidationError):
            return "validation_error"
        if "sdk" in text or "google" in name:
            return "sdk_error"
        return "gemini_error"
