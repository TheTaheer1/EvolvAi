from __future__ import annotations

import hashlib
from time import perf_counter
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.llm.gemini_service import GeminiService
from app.llm.groq_client import GroqStructuredClient
from app.llm.groq_service import GroqService
from app.llm.openai_client import OpenAIStructuredClient
from app.llm.prompts import (
    GLOBAL_SYSTEM_PROMPT,
    build_execution_prompt,
    build_planner_prompt,
    build_pr_prompt,
    build_research_prompt,
    build_strategy_prompt,
    build_verification_prompt,
    build_watcher_prompt,
)
from app.llm.schemas import (
    ExecutionLLMOutput,
    PlannerAgentLLMOutput,
    PRAgentLLMOutput,
    ResearchAgentLLMOutput,
    StrategyAgentLLMOutput,
    VerificationLLMOutput,
    WatcherLLMOutput,
)
from app.llm.xai_service import XAIService

SchemaT = TypeVar("SchemaT", bound=BaseModel)

PLACEHOLDER_KEYS = {
    "",
    "<user-will-add-real-key-here>",
    "your_openai_api_key_here",
    "your-openai-api-key",
    "your_groq_key_here",
    "your_xai_key_here",
    "your_grok_key_here",
    "replace-me",
    "changeme",
}


def _prompt_hash(system_prompt: str, user_prompt: str) -> str:
    return hashlib.sha256(f"{system_prompt}\n\n{user_prompt}".encode("utf-8")).hexdigest()


class LLMService:
    """Provider-routed structured LLM calls with deterministic fallback metadata."""

    def provider_name(self) -> str:
        return (settings.LLM_PROVIDER or "openai").strip().lower()

    def is_enabled(self) -> bool:
        status = self.status()
        provider = status.get("provider") or self.provider_name()
        return bool(status.get("live_ai_enabled") and status.get(f"{provider}_key_usable"))

    def status(self) -> dict[str, Any]:
        provider = self.provider_name()
        if provider == "gemini":
            return GeminiService().status()
        if provider == "groq":
            return GroqService().status()
        if provider in {"xai", "grok"}:
            return XAIService().status()
        if provider == "openai":
            from app.services.openai_service import OpenAIService

            return {**OpenAIService().status(), "provider": "openai"}
        return {
            "live_ai_enabled": bool(settings.USE_LIVE_AI_OUTPUTS),
            "provider": provider or "unknown",
            "model": "deterministic-fallback",
            "fallback_enabled": bool(settings.LLM_FALLBACK_TO_DEMO),
            "provider_valid": False,
            "error_message": "invalid_llm_provider",
        }

    def config_status(self) -> dict[str, Any]:
        status = self.status()
        provider = status.get("provider") or self.provider_name()
        key_state = (
            status.get(f"{provider}_key_state")
            or status.get("openai_key_state")
            or status.get("api_key_state")
            or "unknown"
        )
        key_present = bool(status.get(f"{provider}_key_present") or status.get("openai_key_present"))
        key_usable = bool(status.get(f"{provider}_key_usable") or status.get("openai_key_usable"))
        return {
            "live_ai_enabled": bool(settings.USE_LIVE_AI_OUTPUTS),
            "api_key_present": key_present,
            "api_key_usable": key_usable,
            "api_key_state": key_state,
            "provider": provider,
            "model": status.get("model") or self._active_model(),
            "reasoning_model": settings.OPENAI_REASONING_MODEL,
            "structured_outputs_enabled": settings.USE_OPENAI_STRUCTURED_OUTPUTS,
            "fallback_to_demo": settings.LLM_FALLBACK_TO_DEMO,
            "cache_enabled": settings.LLM_CACHE_ENABLED,
            "prompt_logging_enabled": settings.LLM_LOG_PROMPTS,
            "response_logging_enabled": settings.LLM_LOG_RESPONSES,
        }

    def test_active_provider(self) -> dict[str, Any]:
        provider = self.provider_name()
        if provider == "gemini":
            return GeminiService().test_connection()
        if provider == "groq":
            return GroqService().test_connection()
        if provider in {"xai", "grok"}:
            return XAIService().test_connection()
        status = self.config_status()
        if provider != "openai":
            return {
                "success": False,
                "enabled": False,
                "fallback_used": True,
                "status": "fallback_used",
                "provider": provider or "unknown",
                "model": "deterministic-fallback",
                "message": "Invalid LLM_PROVIDER; EvolvAI will use deterministic fallback.",
                "error_message": "unsupported_provider",
                "latency_ms": None,
            }
        if not status["live_ai_enabled"]:
            return {
                "success": False,
                "enabled": False,
                "fallback_used": False,
                "status": "skipped",
                "provider": status["provider"],
                "model": status["model"],
                "message": "USE_LIVE_AI_OUTPUTS=false; deterministic fallback is active.",
                "latency_ms": None,
            }
        if not status["api_key_usable"]:
            reason = "placeholder_api_key" if status.get("api_key_state") == "placeholder" else "missing_api_key"
            return {
                "success": False,
                "enabled": False,
                "fallback_used": True,
                "status": "fallback_used",
                "provider": status["provider"],
                "model": status["model"],
                "message": "OPENAI_API_KEY is not configured; EvolvAI will use deterministic fallback.",
                "error_message": reason,
                "latency_ms": None,
            }
        return {
            "success": True,
            "enabled": True,
            "fallback_used": False,
            "status": "configured",
            "provider": status["provider"],
            "model": status["model"],
            "message": "LLM mode is configured. Agent calls will be made inside workflow execution.",
            "latency_ms": None,
        }

    def generate_watcher_output(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        trigger_payload: dict[str, Any],
        deterministic_event: dict[str, Any],
        fallback_output: WatcherLLMOutput,
    ) -> tuple[WatcherLLMOutput, dict[str, Any]]:
        return self.safe_generate_structured(
            workflow_id=workflow_id,
            agent_name="watcher_agent",
            schema_model=WatcherLLMOutput,
            user_prompt=build_watcher_prompt(company, trigger_payload, deterministic_event),
            fallback_output=fallback_output,
        )

    def generate_research_summary(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        market_event: dict[str, Any],
        evidence: list[dict[str, Any]],
        fallback_output: ResearchAgentLLMOutput,
    ) -> tuple[ResearchAgentLLMOutput, dict[str, Any]]:
        return self.generate_research_output(
            workflow_id=workflow_id,
            company=company,
            market_event=market_event,
            evidence=evidence,
            fallback_output=fallback_output,
        )

    def generate_research_output(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        market_event: dict[str, Any],
        evidence: list[dict[str, Any]],
        fallback_output: ResearchAgentLLMOutput,
    ) -> tuple[ResearchAgentLLMOutput, dict[str, Any]]:
        provider = self.provider_name()
        if provider == "gemini":
            return GeminiService().generate_research_output(
                workflow_id=workflow_id,
                company=company,
                market_event=market_event,
                evidence=evidence,
                fallback_output=fallback_output,
            )
        if provider == "groq":
            return GroqService().generate_research_output(
                workflow_id=workflow_id,
                company=company,
                market_event=market_event,
                evidence=evidence,
                fallback_output=fallback_output,
            )
        if provider in {"xai", "grok"}:
            return XAIService().generate_research_output(
                workflow_id=workflow_id,
                company=company,
                market_event=market_event,
                evidence=evidence,
                fallback_output=fallback_output,
            )
        if provider == "openai":
            from app.services.openai_service import OpenAIService

            return OpenAIService().generate_research_output(
                workflow_id=workflow_id,
                company=company,
                market_event=market_event,
                evidence=evidence,
                fallback_output=fallback_output,
            )
        user_prompt = build_research_prompt(company, market_event, evidence)
        metadata = self._base_metadata(workflow_id, "research_agent", _prompt_hash(GLOBAL_SYSTEM_PROMPT, user_prompt))
        metadata.update(
            {
                "provider": provider or "unknown",
                "model": "deterministic-fallback",
                "mode": "fallback",
                "output_mode": "fallback_used",
                "status": "fallback_used",
                "fallback_used": True,
                "error_message": "unsupported_provider",
            }
        )
        return fallback_output, metadata

    def generate_strategy_output(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        market_event: dict[str, Any],
        research: dict[str, Any],
        fallback_output: StrategyAgentLLMOutput,
    ) -> tuple[StrategyAgentLLMOutput, dict[str, Any]]:
        return self.safe_generate_structured(
            workflow_id=workflow_id,
            agent_name="strategy_agent",
            schema_model=StrategyAgentLLMOutput,
            user_prompt=build_strategy_prompt(company, market_event, research),
            fallback_output=fallback_output,
        )

    def generate_strategy_decision(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        market_event: dict[str, Any],
        research: dict[str, Any],
        fallback_output: StrategyAgentLLMOutput,
    ) -> tuple[StrategyAgentLLMOutput, dict[str, Any]]:
        return self.generate_strategy_output(
            workflow_id=workflow_id,
            company=company,
            market_event=market_event,
            research=research,
            fallback_output=fallback_output,
        )

    def generate_planner_output(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        decision: dict[str, Any],
        impact: dict[str, Any],
        codebase_context: dict[str, Any] | None = None,
        fallback_output: PlannerAgentLLMOutput,
    ) -> tuple[PlannerAgentLLMOutput, dict[str, Any]]:
        return self.safe_generate_structured(
            workflow_id=workflow_id,
            agent_name="planner_agent",
            schema_model=PlannerAgentLLMOutput,
            user_prompt=build_planner_prompt(company, decision, impact, codebase_context),
            fallback_output=fallback_output,
        )

    def generate_implementation_plan(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        decision: dict[str, Any],
        impact: dict[str, Any],
        codebase_context: dict[str, Any] | None = None,
        fallback_output: PlannerAgentLLMOutput,
    ) -> tuple[PlannerAgentLLMOutput, dict[str, Any]]:
        return self.generate_planner_output(
            workflow_id=workflow_id,
            company=company,
            decision=decision,
            impact=impact,
            codebase_context=codebase_context,
            fallback_output=fallback_output,
        )

    def generate_execution_output(
        self,
        *,
        workflow_id: str | None,
        company: dict[str, Any],
        market_event: dict[str, Any],
        decision: dict[str, Any],
        impact: dict[str, Any],
        plan: dict[str, Any],
        deterministic_artifacts: list[dict[str, Any]],
        fallback_output: ExecutionLLMOutput,
    ) -> tuple[ExecutionLLMOutput, dict[str, Any]]:
        return self.safe_generate_structured(
            workflow_id=workflow_id,
            agent_name="execution_agent",
            schema_model=ExecutionLLMOutput,
            user_prompt=build_execution_prompt(company, market_event, decision, impact, plan, deterministic_artifacts),
            fallback_output=fallback_output,
        )

    def generate_verification_output(
        self,
        *,
        workflow_id: str | None,
        verification_result: dict[str, Any],
        artifacts: list[dict[str, Any]],
        fallback_output: VerificationLLMOutput,
    ) -> tuple[VerificationLLMOutput, dict[str, Any]]:
        return self.safe_generate_structured(
            workflow_id=workflow_id,
            agent_name="verification_agent",
            schema_model=VerificationLLMOutput,
            user_prompt=build_verification_prompt(verification_result, artifacts),
            fallback_output=fallback_output,
        )

    def generate_pr_output(
        self,
        *,
        workflow_id: str | None,
        decision: dict[str, Any],
        impact: dict[str, Any],
        plan: dict[str, Any],
        artifacts: list[dict[str, Any]],
        verification: dict[str, Any] | None,
        fallback_output: PRAgentLLMOutput,
    ) -> tuple[PRAgentLLMOutput, dict[str, Any]]:
        return self.safe_generate_structured(
            workflow_id=workflow_id,
            agent_name="pr_agent",
            schema_model=PRAgentLLMOutput,
            user_prompt=build_pr_prompt(decision, impact, plan, artifacts, verification),
            fallback_output=fallback_output,
        )

    def generate_pr_description(
        self,
        *,
        workflow_id: str | None,
        decision: dict[str, Any],
        impact: dict[str, Any],
        plan: dict[str, Any],
        artifacts: list[dict[str, Any]],
        verification: dict[str, Any] | None,
        fallback_output: PRAgentLLMOutput,
    ) -> tuple[PRAgentLLMOutput, dict[str, Any]]:
        return self.generate_pr_output(
            workflow_id=workflow_id,
            decision=decision,
            impact=impact,
            plan=plan,
            artifacts=artifacts,
            verification=verification,
            fallback_output=fallback_output,
        )

    def safe_generate_structured(
        self,
        *,
        workflow_id: str | None,
        agent_name: str,
        schema_model: Type[SchemaT],
        user_prompt: str,
        fallback_output: SchemaT,
    ) -> tuple[SchemaT, dict[str, Any]]:
        prompt_hash = _prompt_hash(GLOBAL_SYSTEM_PROMPT, user_prompt)
        metadata = self._base_metadata(workflow_id, agent_name, prompt_hash)
        provider = self.provider_name()
        if provider not in {"openai", "groq"}:
            return self._fallback(fallback_output, metadata, "unsupported_provider_for_agent", "fallback_used")
        if not settings.USE_LIVE_AI_OUTPUTS:
            metadata.update(
                {
                    "mode": "deterministic",
                    "output_mode": "deterministic",
                    "status": "skipped",
                    "fallback_used": False,
                    "error_message": "USE_LIVE_AI_OUTPUTS=false",
                }
            )
            return fallback_output, metadata
        key_state = self._provider_key_state(provider)
        if key_state != "configured":
            return self._fallback(
                fallback_output,
                metadata,
                "placeholder_api_key" if key_state == "placeholder" else "missing_api_key",
                "fallback_used",
            )

        started = perf_counter()
        try:
            result = self._structured_client(provider).generate_structured(
                model=self._active_model(),
                system_prompt=GLOBAL_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema_model=schema_model,
            )
            validated = schema_model.model_validate(result.output)
            metadata.update(
                {
                    "mode": "llm_enhanced",
                    "output_mode": "llm_enhanced",
                    "status": "success",
                    "fallback_used": False,
                    "structured_output_valid": True,
                    "latency_ms": result.latency_ms,
                    **result.usage,
                }
            )
            return validated, metadata
        except ValidationError as exc:
            metadata["latency_ms"] = int((perf_counter() - started) * 1000)
            return self._fallback(fallback_output, metadata, "schema_validation_error", "fallback_used", exc)
        except Exception as exc:  # noqa: BLE001
            metadata["latency_ms"] = int((perf_counter() - started) * 1000)
            error_type = self.classify_error(exc)
            if settings.LLM_FALLBACK_TO_DEMO:
                return self._fallback(fallback_output, metadata, error_type, "fallback_used", exc)
            metadata.update(
                {
                    "mode": "llm_failed",
                    "output_mode": "fallback_used",
                    "status": "failed",
                    "fallback_used": False,
                    "structured_output_valid": False,
                    "error_message": error_type,
                }
            )
            raise RuntimeError(f"LLM generation failed: {error_type}") from exc

    def _structured_client(self, provider: str) -> Any:
        if provider == "groq":
            return GroqStructuredClient()
        return OpenAIStructuredClient()

    def _active_model(self) -> str:
        provider = self.provider_name()
        if provider == "gemini":
            return settings.GEMINI_MODEL
        if provider == "groq":
            return settings.GROQ_MODEL
        if provider in {"xai", "grok"}:
            return settings.XAI_MODEL
        return settings.OPENAI_MODEL

    def _provider_key_state(self, provider: str) -> str:
        if provider == "groq":
            key = (settings.GROQ_API_KEY or "").strip()
        else:
            key = (settings.OPENAI_API_KEY or "").strip()
        lowered = key.lower()
        if not key:
            return "missing"
        if key.startswith("<") or key.endswith(">") or lowered in PLACEHOLDER_KEYS or "placeholder" in lowered or "your_" in lowered:
            return "placeholder"
        return "configured"

    def _fallback(
        self,
        fallback_output: SchemaT,
        metadata: dict[str, Any],
        reason: str,
        status: str,
        exc: Exception | None = None,
    ) -> tuple[SchemaT, dict[str, Any]]:
        metadata.update(
            {
                "mode": "fallback",
                "output_mode": "fallback_used",
                "status": status,
                "fallback_used": True,
                "structured_output_valid": False,
                "error_message": reason,
            }
        )
        if exc and settings.LLM_LOG_RESPONSES:
            metadata["sanitized_error_detail"] = str(exc)[:500]
        return fallback_output, metadata

    def _base_metadata(self, workflow_id: str | None, agent_name: str, prompt_hash: str) -> dict[str, Any]:
        return {
            "workflow_id": workflow_id,
            "agent_name": agent_name,
            "provider": self.provider_name(),
            "model": self._active_model(),
            "mode": "deterministic",
            "output_mode": "deterministic",
            "prompt_hash": prompt_hash,
            "status": "skipped",
            "fallback_used": False,
            "structured_output_valid": False,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": None,
        }

    def classify_error(self, exc: Exception) -> str:
        text = str(exc).lower()
        name = exc.__class__.__name__.lower()
        if "missing_api_key" in text:
            return "missing_api_key"
        if "placeholder_api_key" in text:
            return "placeholder_api_key"
        if "auth" in text or "unauthorized" in text or "incorrect api key" in text or "invalid api key" in text or "401" in text:
            return "authentication_error"
        if "permission" in text or "forbidden" in text or "403" in text:
            return "permission_error"
        if "insufficient_quota" in text or "exceeded your current quota" in text or "quota" in text or "billing" in text:
            return "insufficient_quota"
        if "rate" in name or "rate limit" in text or "too many requests" in text or "429" in text:
            return "rate_limit_error"
        if "timeout" in name or "timeout" in text or "timed out" in text:
            return "timeout_error"
        if "model" in text and ("not found" in text or "does not exist" in text or "404" in text):
            return "model_not_found"
        if "malformed" in text or "json" in text:
            return "malformed_json"
        if "schema_validation_error" in text or "validation" in text or isinstance(exc, ValidationError):
            return "schema_validation_error"
        if "empty_response" in text:
            return "empty_response"
        if "refusal" in text or "content filter" in text:
            return "content_filter_or_refusal"
        if "network" in text or "connection" in text:
            return "network_error"
        if "api" in name or "provider" in text:
            return "provider_error"
        return "unknown_error"
