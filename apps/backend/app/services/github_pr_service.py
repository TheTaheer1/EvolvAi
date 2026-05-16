from __future__ import annotations

import re
import time
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.github.pr_client import GitHubBranchExistsError, GitHubPRClient, GitHubPRClientError
from app.llm.validators import sanitize_branch_slug
from app.models.generated_artifact import GeneratedArtifact
from app.models.pull_request import PullRequestHistory
from app.realtime.events import PR_FAILED, PR_OPENED
from app.security.artifact_safety import (
    find_dangerous_content,
    find_external_write_instructions,
    find_production_deployment_instructions,
    find_prompt_injection,
    is_safe_relative_path,
)
from app.services.generated_artifact_service import GeneratedArtifactService
from app.services.pr_preview_service import PRPreviewService, pr_preview_payload
from app.services.realtime_service import RealtimeService
from app.services.verification_service import VerificationService
from app.services.workflow_service import WorkflowService
from app.utils.json import to_jsonable
from app.utils.time import utc_now


ALLOWED_PR_PREFIXES = (
    "evolvai/generated/",
    "docs/evolvai-generated/",
    "demo/evolvai-generated/",
)
BLOCKED_PR_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "dockerfile",
    "docker-compose.yml",
    "id_rsa",
    "id_dsa",
    "id_ed25519",
    "secrets.json",
}
BLOCKED_PR_PARTS = {".github", ".ssh", "src", "app", "node_modules", ".git"}


class GitHubPRService:
    def __init__(
        self,
        client: GitHubPRClient | None = None,
        realtime: RealtimeService | None = None,
    ) -> None:
        self.client = client or GitHubPRClient()
        self.realtime = realtime or RealtimeService()

    def pr_safety_check(self, db: Session, workflow_id: UUID | str) -> dict[str, Any]:
        workflow = WorkflowService().require_workflow(db, workflow_id)
        verification = VerificationService().get_by_workflow(db, workflow.id)
        artifacts = GeneratedArtifactService().list_by_workflow(db, workflow.id)
        pr = PRPreviewService().get_pr_preview_by_workflow(db, workflow.id)
        prepared_files, artifact_errors = self._prepare_artifact_files(workflow.id, artifacts)

        checks: list[dict[str, Any]] = []

        def add(name: str, passed: bool, message: str) -> None:
            checks.append({"name": name, "passed": bool(passed), "message": message})

        add("real_pr_enabled", settings.ALLOW_REAL_GITHUB_PR, "ALLOW_REAL_GITHUB_PR must be true.")
        add(
            "external_writes_enabled",
            settings.ALLOW_EXTERNAL_WRITE_ACTIONS,
            "ALLOW_EXTERNAL_WRITE_ACTIONS must be true.",
        )
        add("code_execution_disabled", not settings.ALLOW_CODE_EXECUTION, "ALLOW_CODE_EXECUTION must remain false.")
        add("github_token_present", bool(settings.GITHUB_TOKEN), "GITHUB_TOKEN is required.")
        add(
            "target_repository_configured",
            bool(settings.GITHUB_TARGET_OWNER and settings.GITHUB_TARGET_REPO),
            "GITHUB_TARGET_OWNER and GITHUB_TARGET_REPO are required.",
        )
        add("verification_exists", verification is not None, "A verification report is required.")
        add(
            "verification_passed",
            bool(verification and verification.passed) if settings.GITHUB_PR_REQUIRE_VERIFICATION_PASS else True,
            "Verification must pass before opening a draft PR.",
        )
        add("pr_preview_exists", pr is not None, "A PR preview is required.")
        add("generated_artifacts_exist", bool(artifacts), "Generated artifacts are required.")
        add(
            "artifact_count_check",
            bool(artifacts) and len(artifacts) <= settings.GITHUB_PR_MAX_FILES,
            f"Artifact count must be 1-{settings.GITHUB_PR_MAX_FILES}.",
        )
        add(
            "artifact_type_check",
            all(artifact.artifact_type in self._allowed_artifact_types() for artifact in artifacts),
            "Only configured generated artifact types may be committed.",
        )
        add(
            "artifact_safety_check",
            not artifact_errors and bool(prepared_files),
            "; ".join(artifact_errors) if artifact_errors else "All artifacts map to safe draft PR paths and content.",
        )
        add(
            "draft_mode_check",
            settings.GITHUB_PR_DRAFT,
            "Step 6 only opens draft PRs.",
        )

        return {
            "can_open_pr": all(check["passed"] for check in checks),
            "checks": checks,
            "workflow_id": str(workflow.id),
            "pr_preview_id": str(pr.id) if pr else None,
            "existing_pr_url": pr.pr_url if pr and pr.status == "opened" else None,
            "prepared_files": [
                {"path": file["path"], "original_path": file["original_path"], "artifact_type": file["artifact_type"]}
                for file in prepared_files
            ],
        }

    def create_draft_pr_from_workflow(self, db: Session, workflow_id: UUID | str) -> PullRequestHistory:
        workflow = WorkflowService().require_workflow(db, workflow_id)
        if not settings.ALLOW_REAL_GITHUB_PR or not settings.ALLOW_EXTERNAL_WRITE_ACTIONS:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Real GitHub PR creation is disabled. Set ALLOW_REAL_GITHUB_PR=true and "
                    "ALLOW_EXTERNAL_WRITE_ACTIONS=true to enable."
                ),
            )

        safety = self.pr_safety_check(db, workflow.id)
        pr = PRPreviewService().get_pr_preview_by_workflow(db, workflow.id)
        if not pr:
            raise HTTPException(status_code=400, detail="PR preview is required before opening a draft PR.")
        if pr.status == "opened" and pr.pr_url:
            return pr
        if not safety["can_open_pr"]:
            raise HTTPException(
                status_code=400,
                detail={"message": "Draft PR safety checks failed.", "checks": safety["checks"]},
            )

        artifacts = GeneratedArtifactService().list_by_workflow(db, workflow.id)
        prepared_files, artifact_errors = self._prepare_artifact_files(workflow.id, artifacts)
        if artifact_errors or not prepared_files:
            raise HTTPException(
                status_code=400,
                detail={"message": "Artifact safety checks failed.", "errors": artifact_errors},
            )

        branch_name = self._branch_name(pr, workflow.id)
        try:
            result = self._create_with_unique_branch(pr, branch_name, prepared_files)
            pr.status = "opened"
            pr.repo_owner = settings.GITHUB_TARGET_OWNER
            pr.repo_name = settings.GITHUB_TARGET_REPO
            pr.branch_name = str(result.get("branch_name") or branch_name)
            pr.pr_number = int(result["number"]) if result.get("number") is not None else None
            pr.pr_url = result.get("url")
            pr.error_message = None
            pr.changed_files = to_jsonable(
                [
                    {
                        "path": file["path"],
                        "original_path": file["original_path"],
                        "type": file["artifact_type"],
                        "status": "opened",
                    }
                    for file in prepared_files
                ]
            )
            pr.updated_at = utc_now()
            db.commit()
            db.refresh(pr)
            self.realtime.emit_event(PR_OPENED, pr_preview_payload(pr), workflow_id=str(workflow.id))
            return pr
        except Exception as exc:  # noqa: BLE001
            pr.status = "failed"
            pr.error_message = self._sanitize_error(exc)
            pr.updated_at = utc_now()
            db.commit()
            db.refresh(pr)
            self.realtime.emit_event(PR_FAILED, pr_preview_payload(pr), workflow_id=str(workflow.id))
            return pr

    def _create_with_unique_branch(
        self,
        pr: PullRequestHistory,
        branch_name: str,
        files: list[dict[str, str]],
    ) -> dict[str, Any]:
        for attempt in range(2):
            candidate = branch_name if attempt == 0 else f"{branch_name}-{int(time.time())}"[:120]
            try:
                return self.client.create_draft_pr(
                    owner=settings.GITHUB_TARGET_OWNER,
                    repo=settings.GITHUB_TARGET_REPO,
                    base_branch=settings.GITHUB_BASE_BRANCH,
                    branch_name=candidate,
                    title=pr.title,
                    body=self._real_pr_body(pr),
                    files=files,
                    draft=settings.GITHUB_PR_DRAFT,
                )
            except GitHubBranchExistsError:
                if attempt == 1:
                    raise
        raise GitHubPRClientError("branch_already_exists")

    def _prepare_artifact_files(
        self,
        workflow_id: UUID | str,
        artifacts: list[GeneratedArtifact],
    ) -> tuple[list[dict[str, str]], list[str]]:
        errors: list[str] = []
        files: list[dict[str, str]] = []
        seen_paths: set[str] = set()
        if len(artifacts) > settings.GITHUB_PR_MAX_FILES:
            errors.append(f"too_many_files:{len(artifacts)}")
            return [], errors

        for artifact in artifacts:
            if artifact.artifact_type not in self._allowed_artifact_types():
                errors.append(f"artifact_type_not_allowed:{artifact.file_path}")
                continue
            try:
                target_path = self._safe_pr_path(workflow_id, artifact.file_path)
            except ValueError as exc:
                errors.append(f"unsafe_path:{artifact.file_path}:{exc}")
                continue
            if target_path in seen_paths:
                errors.append(f"duplicate_path:{target_path}")
                continue
            content = artifact.content or ""
            content_issues = self._content_issues(content)
            if content_issues:
                errors.append(f"unsafe_content:{artifact.file_path}:{','.join(content_issues[:3])}")
                continue
            if len(content.encode("utf-8")) > settings.MAX_ARTIFACT_SIZE_BYTES:
                errors.append(f"artifact_too_large:{artifact.file_path}")
                continue
            seen_paths.add(target_path)
            files.append(
                {
                    "path": target_path,
                    "content": content,
                    "original_path": artifact.file_path,
                    "artifact_type": artifact.artifact_type,
                }
            )
        return files, errors

    def _safe_pr_path(self, workflow_id: UUID | str, artifact_path: str) -> str:
        if not is_safe_relative_path(artifact_path):
            raise ValueError("path_must_be_relative")
        if self._is_blocked_path(artifact_path):
            raise ValueError("blocked_artifact_path")
        workflow_slug = re.sub(r"[^a-zA-Z0-9-]+", "-", str(workflow_id)).strip("-")
        parts = []
        for part in PurePosixPath(artifact_path).parts:
            cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", part).strip(".-")
            if not cleaned:
                raise ValueError("invalid_path_segment")
            parts.append(cleaned)
        target = f"evolvai/generated/{workflow_slug}/{'/'.join(parts)}"
        if not target.startswith(ALLOWED_PR_PREFIXES):
            raise ValueError("target_prefix_not_allowed")
        if self._is_blocked_path(target):
            raise ValueError("blocked_target_path")
        return target

    def _is_blocked_path(self, file_path: str) -> bool:
        lowered = file_path.lower().replace("\\", "/")
        parts = [part.lower() for part in PurePosixPath(lowered).parts]
        name = parts[-1] if parts else ""
        if name in BLOCKED_PR_FILE_NAMES:
            return True
        if any(part in BLOCKED_PR_PARTS for part in parts):
            return True
        if lowered.startswith(".github/workflows/"):
            return True
        if any(marker in lowered for marker in ["secret", "token", "private-key", "api-key"]):
            return True
        return False

    def _content_issues(self, content: str) -> list[str]:
        return [
            *find_dangerous_content(content),
            *find_prompt_injection(content),
            *find_external_write_instructions(content),
            *find_production_deployment_instructions(content),
        ]

    def _allowed_artifact_types(self) -> set[str]:
        return {
            item.strip()
            for item in str(settings.GITHUB_PR_ALLOWED_ARTIFACT_TYPES or "").split(",")
            if item.strip()
        }

    def _branch_name(self, pr: PullRequestHistory, workflow_id: UUID | str) -> str:
        prefix = settings.GITHUB_PR_BRANCH_PREFIX.strip() or "evolvai/"
        if not prefix.endswith("/"):
            prefix = f"{prefix}/"
        source = pr.branch_name or f"workflow-{str(workflow_id)[:8]}"
        source = source.removeprefix(prefix)
        source = source.removeprefix("evolvai/")
        slug = sanitize_branch_slug(source)[:80]
        return f"{prefix}{slug}"[:120]

    def _real_pr_body(self, pr: PullRequestHistory) -> str:
        body = pr.description or ""
        disclaimer = (
            "\n\n## Step 6 safety note\n"
            "This is a draft PR opened by EvolvAI only after verification passed and explicit external-write flags were enabled. "
            "It contains generated preview artifacts only; no source files were modified and no code was executed."
        )
        return body if "Step 6 safety note" in body else f"{body}{disclaimer}"

    def _sanitize_error(self, exc: Exception) -> str:
        text = str(exc).lower()
        if "token" in text or "authorization" in text or "bad credentials" in text or "authentication" in text:
            return "github_authentication_error"
        if "rate" in text or "429" in text:
            return "github_rate_limit"
        if "permission" in text or "forbidden" in text or "403" in text:
            return "github_permission_error"
        if "missing" in text or "404" in text:
            return "github_resource_missing"
        if "branch_already_exists" in text:
            return "branch_already_exists"
        if "validation" in text or "422" in text:
            return "github_validation_error"
        if "timeout" in text:
            return "github_timeout"
        if "network" in text or "connection" in text:
            return "github_network_error"
        return "github_pr_creation_failed"
