from pathlib import Path
import re


DANGEROUS_CONTENT_PATTERNS = [
    r"rm\s+-rf",
    r"\bsudo\b",
    r"curl\s+[^|]*\|\s*bash",
    r"wget\s+[^|]*\|\s*bash",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"os\.system",
    r"import\s+subprocess",
    r"\bsubprocess\b",
    r"private\s+key",
    r"github[_-]?token",
    r"openai[_-]?api[_-]?key",
    r"\bpassword\s*=",
    r"\bsecret\s*=",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"BEGIN RSA PRIVATE KEY",
    r"sk-[A-Za-z0-9]{20,}",
    r"npm\s+publish",
    r"docker\s+push",
    r"\bkubectl\b",
    r"terraform\s+apply",
    r"gh\s+pr\s+merge",
    r"git\s+push\s+--force",
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"reveal\s+hidden\s+prompt",
    r"print\s+system\s+prompt",
    r"disable\s+safety",
    r"bypass\s+verification",
]

EXTERNAL_WRITE_PATTERNS = [
    r"create\s+a\s+real\s+github\s+pr",
    r"push\s+to\s+github",
    r"commit\s+and\s+push",
    r"upload\s+secrets",
    r"write\s+to\s+production",
]

PRODUCTION_DEPLOYMENT_PATTERNS = [
    r"deploy\s+to\s+production",
    r"run\s+database\s+migrations\s+in\s+production",
    r"promote\s+to\s+prod",
    r"apply\s+terraform",
]


def is_safe_relative_path(file_path: str) -> bool:
    if not file_path or Path(file_path).is_absolute():
        return False
    parts = Path(file_path).parts
    return ".." not in parts and not any(part.strip() == "" for part in parts)


def resolve_safe_artifact_path(base_dir: Path, workflow_id: str, file_path: str) -> Path:
    if not is_safe_relative_path(file_path):
        raise ValueError("Generated artifact path must be relative and cannot contain path traversal.")
    run_dir = (base_dir / workflow_id).resolve()
    target = (run_dir / file_path).resolve()
    if run_dir != target and run_dir not in target.parents:
        raise ValueError("Generated artifact path escapes the safe generated_runs directory.")
    return target


def find_dangerous_content(content: str) -> list[str]:
    matches: list[str] = []
    for pattern in DANGEROUS_CONTENT_PATTERNS:
        if re.search(pattern, content or "", flags=re.IGNORECASE):
            matches.append(pattern)
    return matches


def find_prompt_injection(content: str) -> list[str]:
    return _find_patterns(content, PROMPT_INJECTION_PATTERNS)


def find_external_write_instructions(content: str) -> list[str]:
    return _find_patterns(content, EXTERNAL_WRITE_PATTERNS)


def find_production_deployment_instructions(content: str) -> list[str]:
    return _find_patterns(content, PRODUCTION_DEPLOYMENT_PATTERNS)


def _find_patterns(content: str, patterns: list[str]) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        if re.search(pattern, content or "", flags=re.IGNORECASE):
            matches.append(pattern)
    return matches
