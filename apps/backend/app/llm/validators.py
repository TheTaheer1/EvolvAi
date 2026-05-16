from pathlib import Path
import re
from typing import Any

from app.security.artifact_safety import find_dangerous_content, is_safe_relative_path

ALLOWED_LLM_FILE_PREFIXES = ("docs/features/", "demo/generated/", "demo/reports/")
BLOCKED_FILE_PARTS = {
    ".env",
    ".ssh",
    "id_rsa",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "secret",
    "secrets",
    "token",
    "key",
}


def sanitize_branch_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value).lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:64] or "controlled-demo"


def is_safe_llm_file_path(file_path: str) -> bool:
    if not is_safe_relative_path(file_path):
        return False
    lowered = file_path.lower()
    if lowered.startswith(".") or "/." in lowered:
        return False
    if any(part in lowered for part in BLOCKED_FILE_PARTS):
        return False
    if lowered.startswith(".github/workflows/"):
        return False
    return lowered.startswith(ALLOWED_LLM_FILE_PREFIXES)


def sanitize_file_plans(files: list[dict[str, Any]], fallback_files: list[dict[str, Any]], max_files: int = 5) -> list[dict[str, Any]]:
    safe: list[dict[str, Any]] = []
    seen: set[str] = set()
    for file_plan in files:
        file_path = str(file_plan.get("file_path") or "")
        if file_path in seen or not is_safe_llm_file_path(file_path):
            continue
        seen.add(file_path)
        safe.append(file_plan)
        if len(safe) >= max_files:
            break
    if not any(item.get("artifact_type") == "documentation" for item in safe):
        safe.extend([item for item in fallback_files if item.get("artifact_type") == "documentation"][:1])
    if not any(item.get("file_path", "").endswith((".json", ".md")) for item in safe):
        safe.extend([item for item in fallback_files if item.get("file_path", "").endswith((".json", ".md"))][:1])
    if not any(item.get("artifact_type") == "component" for item in safe):
        safe.extend([item for item in fallback_files if item.get("artifact_type") == "component"][:1])
    deduped: list[dict[str, Any]] = []
    seen.clear()
    for item in safe:
        if item["file_path"] not in seen and is_safe_relative_path(item["file_path"]):
            deduped.append(item)
            seen.add(item["file_path"])
    return deduped[:max_files]


def contains_unsafe_text(value: str) -> bool:
    return bool(find_dangerous_content(value))
