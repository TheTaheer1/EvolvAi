from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.generated_artifact import GeneratedArtifact
from app.models.verification_report import VerificationReport
from app.realtime.events import VERIFICATION_COMPLETED
from app.security.artifact_safety import (
    find_dangerous_content,
    find_external_write_instructions,
    find_production_deployment_instructions,
    find_prompt_injection,
    is_safe_relative_path,
)
from app.services.generated_artifact_service import GeneratedArtifactService
from app.services.realtime_service import RealtimeService
from app.utils.json import to_jsonable


def verification_report_payload(report: VerificationReport) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": report.id,
            "workflow_id": report.workflow_id,
            "status": report.status,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "summary": report.summary,
            "created_at": report.created_at,
        }
    )


class VerificationService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()

    def verify_artifacts(self, artifacts: list[GeneratedArtifact]) -> dict[str, Any]:
        checks: list[dict[str, str]] = []
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        if artifacts:
            checks.append(
                {
                    "name": "artifact_count_check",
                    "status": "passed",
                    "message": f"{len(artifacts)} generated artifacts are available.",
                }
            )
        else:
            checks.append({"name": "artifact_count_check", "status": "failed", "message": "No artifacts generated."})
            errors.append({"name": "artifact_count_check", "message": "At least one artifact is required."})

        for artifact in artifacts:
            if is_safe_relative_path(artifact.file_path):
                checks.append(
                    {
                        "name": "path_safety_check",
                        "status": "passed",
                        "message": f"{artifact.file_path} is a safe relative path.",
                    }
                )
            else:
                checks.append(
                    {
                        "name": "path_safety_check",
                        "status": "failed",
                        "message": f"{artifact.file_path} is unsafe.",
                    }
                )
                errors.append({"name": "path_safety_check", "file_path": artifact.file_path})

            if artifact.content.strip():
                checks.append(
                    {
                        "name": "content_non_empty_check",
                        "status": "passed",
                        "message": f"{artifact.file_path} has preview content.",
                    }
                )
            else:
                checks.append(
                    {
                        "name": "content_non_empty_check",
                        "status": "failed",
                        "message": f"{artifact.file_path} is empty.",
                    }
                )
                errors.append({"name": "content_non_empty_check", "file_path": artifact.file_path})

            dangerous = find_dangerous_content(artifact.content)
            if dangerous:
                checks.append(
                    {
                        "name": "no_dangerous_command_check",
                        "status": "failed",
                        "message": f"{artifact.file_path} matched dangerous content patterns.",
                    }
                )
                errors.append(
                    {"name": "no_dangerous_command_check", "file_path": artifact.file_path, "patterns": dangerous}
                )
            else:
                checks.append(
                    {
                        "name": "no_dangerous_command_check",
                        "status": "passed",
                        "message": f"{artifact.file_path} contains no blocked command patterns.",
                    }
                )

            prompt_injection = find_prompt_injection(artifact.content)
            if prompt_injection:
                checks.append(
                    {
                        "name": "no_prompt_injection_check",
                        "status": "failed",
                        "message": f"{artifact.file_path} includes prompt-injection-like text.",
                    }
                )
                errors.append(
                    {"name": "no_prompt_injection_check", "file_path": artifact.file_path, "patterns": prompt_injection}
                )
            else:
                checks.append(
                    {
                        "name": "no_prompt_injection_check",
                        "status": "passed",
                        "message": f"{artifact.file_path} contains no prompt injection indicators.",
                    }
                )

            external_write = find_external_write_instructions(artifact.content)
            if external_write:
                checks.append(
                    {
                        "name": "no_external_write_instruction_check",
                        "status": "failed",
                        "message": f"{artifact.file_path} suggests external write actions.",
                    }
                )
                errors.append(
                    {
                        "name": "no_external_write_instruction_check",
                        "file_path": artifact.file_path,
                        "patterns": external_write,
                    }
                )
            else:
                checks.append(
                    {
                        "name": "no_external_write_instruction_check",
                        "status": "passed",
                        "message": f"{artifact.file_path} does not instruct external writes.",
                    }
                )

            production_deploy = find_production_deployment_instructions(artifact.content)
            if production_deploy:
                checks.append(
                    {
                        "name": "no_production_deployment_instruction_check",
                        "status": "failed",
                        "message": f"{artifact.file_path} suggests production deployment.",
                    }
                )
                errors.append(
                    {
                        "name": "no_production_deployment_instruction_check",
                        "file_path": artifact.file_path,
                        "patterns": production_deploy,
                    }
                )
            else:
                checks.append(
                    {
                        "name": "no_production_deployment_instruction_check",
                        "status": "passed",
                        "message": f"{artifact.file_path} does not include production deployment instructions.",
                    }
                )

            if len((artifact.content or "").encode("utf-8")) <= settings.MAX_ARTIFACT_SIZE_BYTES:
                checks.append(
                    {
                        "name": "max_size_check",
                        "status": "passed",
                        "message": f"{artifact.file_path} is within the maximum artifact size.",
                    }
                )
            else:
                checks.append(
                    {
                        "name": "max_size_check",
                        "status": "failed",
                        "message": f"{artifact.file_path} exceeds the maximum artifact size.",
                    }
                )
                errors.append({"name": "max_size_check", "file_path": artifact.file_path})

        no_secret_errors = [error for error in errors if "key" in str(error).lower() or "token" in str(error).lower()]
        checks.append(
            {
                "name": "no_secret_leak_check",
                "status": "failed" if no_secret_errors else "passed",
                "message": "No generated artifact exposes blocked secret patterns."
                if not no_secret_errors
                else "Potential secret-like content found.",
            }
        )
        passed = not errors
        checks.append(
            {
                "name": "pr_ready_check",
                "status": "passed" if passed else "failed",
                "message": "Artifacts are safe for PR preview." if passed else "PR preview must be blocked.",
            }
        )
        return {
            "passed": passed,
            "status": "passed" if passed else "failed",
            "checks": checks,
            "warnings": warnings,
            "errors": errors,
            "summary": "All generated artifacts are safe for PR preview."
            if passed
            else "Generated artifacts failed safety verification.",
        }

    def create_verification_report(
        self,
        db: Session,
        workflow_id: UUID | str,
        report_data: dict[str, Any],
        emit: bool = True,
    ) -> VerificationReport:
        existing = self.get_by_workflow(db, workflow_id)
        if existing:
            return existing
        report = VerificationReport(
            workflow_id=workflow_id,
            status=report_data["status"],
            passed=report_data["passed"],
            checks=to_jsonable(report_data.get("checks") or []),
            warnings=to_jsonable(report_data.get("warnings") or []),
            errors=to_jsonable(report_data.get("errors") or []),
            summary=report_data.get("summary"),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        if report.passed:
            artifacts = GeneratedArtifactService().list_by_workflow(db, workflow_id)
            GeneratedArtifactService().mark_artifacts_verified(db, artifacts)
        if emit:
            self.realtime.emit_event(
                VERIFICATION_COMPLETED,
                verification_report_payload(report),
                workflow_id=str(report.workflow_id),
            )
        return report

    def get_by_workflow(self, db: Session, workflow_id: UUID | str) -> VerificationReport | None:
        return db.scalars(
            select(VerificationReport)
            .where(VerificationReport.workflow_id == workflow_id)
            .order_by(VerificationReport.created_at.desc())
        ).first()
