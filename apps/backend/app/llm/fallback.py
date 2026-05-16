from typing import Any


def with_llm_metadata(payload: dict[str, Any], *, mode: str, fallback_used: bool, status: str, reason: str | None = None) -> dict[str, Any]:
    return {
        **payload,
        "llm_metadata": {
            "mode": mode,
            "status": status,
            "provider": "openai",
            "fallback_used": fallback_used,
            "structured_output_valid": False,
            "reason": reason,
        },
    }
