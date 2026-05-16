from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.generated_artifact import GeneratedArtifact
from app.realtime.events import ARTIFACT_GENERATED
from app.security.artifact_safety import resolve_safe_artifact_path
from app.services.realtime_service import RealtimeService
from app.utils.json import to_jsonable


VALID_ARTIFACT_TYPES = {"documentation", "component", "config", "schema", "plan", "report"}
VALID_ARTIFACT_STATUSES = {"generated", "verified", "rejected", "preview_only"}


def generated_artifact_payload(artifact: GeneratedArtifact) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": artifact.id,
            "workflow_id": artifact.workflow_id,
            "artifact_type": artifact.artifact_type,
            "file_path": artifact.file_path,
            "title": artifact.title,
            "description": artifact.description,
            "content": artifact.content,
            "language": artifact.language,
            "status": artifact.status,
            "metadata": artifact.artifact_metadata,
            "created_at": artifact.created_at,
        }
    )


class GeneratedArtifactService:
    def __init__(self, realtime: RealtimeService | None = None) -> None:
        self.realtime = realtime or RealtimeService()

    def _base_dir(self) -> Path:
        configured = Path(settings.GENERATED_RUNS_DIR)
        if configured.is_absolute():
            return configured
        return Path.cwd() / configured

    def verify_safe_path(self, workflow_id: UUID | str, file_path: str) -> Path:
        return resolve_safe_artifact_path(self._base_dir(), str(workflow_id), file_path)

    def create_artifact(
        self,
        db: Session,
        workflow_id: UUID | str,
        artifact_data: dict[str, Any],
        status: str = "generated",
        emit: bool = True,
    ) -> GeneratedArtifact:
        artifact_type = artifact_data.get("artifact_type", "documentation")
        if artifact_type not in VALID_ARTIFACT_TYPES:
            artifact_type = "report"
        if status not in VALID_ARTIFACT_STATUSES:
            status = "generated"
        content = artifact_data.get("content") or ""
        if len(content.encode("utf-8")) > settings.MAX_ARTIFACT_SIZE_BYTES:
            content = content.encode("utf-8")[: settings.MAX_ARTIFACT_SIZE_BYTES].decode("utf-8", errors="ignore")
        artifact = GeneratedArtifact(
            workflow_id=workflow_id,
            artifact_type=artifact_type,
            file_path=artifact_data["file_path"],
            title=artifact_data.get("title") or artifact_data["file_path"],
            description=artifact_data.get("description"),
            content=content,
            language=artifact_data.get("language"),
            status=status,
            artifact_metadata=to_jsonable(artifact_data.get("metadata") or {}),
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        if emit:
            self.realtime.emit_event(
                ARTIFACT_GENERATED,
                generated_artifact_payload(artifact),
                workflow_id=str(artifact.workflow_id),
            )
        return artifact

    def list_by_workflow(self, db: Session, workflow_id: UUID | str) -> list[GeneratedArtifact]:
        return list(
            db.scalars(
                select(GeneratedArtifact)
                .where(GeneratedArtifact.workflow_id == workflow_id)
                .order_by(GeneratedArtifact.created_at.asc())
            ).all()
        )

    def get_artifact(self, db: Session, artifact_id: UUID | str) -> GeneratedArtifact:
        artifact = db.get(GeneratedArtifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Generated artifact not found")
        return artifact

    def read_artifact_content(self, db: Session, artifact_id: UUID | str) -> str:
        return self.get_artifact(db, artifact_id).content

    def write_artifacts_to_safe_directory(
        self,
        db: Session,
        workflow_id: UUID | str,
        artifacts: list[dict[str, Any]],
    ) -> tuple[list[GeneratedArtifact], list[dict[str, Any]]]:
        created: list[GeneratedArtifact] = []
        warnings: list[dict[str, Any]] = []
        for artifact_data in artifacts:
            try:
                self.verify_safe_path(workflow_id, artifact_data["file_path"])
            except ValueError as exc:
                warnings.append({"file_path": artifact_data.get("file_path"), "warning": str(exc)})
                continue
            artifact = self.create_artifact(db, workflow_id, artifact_data)
            created.append(artifact)
            if settings.ALLOW_GENERATED_FILES:
                try:
                    target = self.verify_safe_path(workflow_id, artifact.file_path)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(artifact.content, encoding="utf-8")
                except Exception as exc:  # noqa: BLE001
                    warnings.append({"file_path": artifact.file_path, "warning": f"DB stored; file write failed: {exc}"})
        return created, warnings

    def mark_artifacts_verified(self, db: Session, artifacts: list[GeneratedArtifact]) -> None:
        for artifact in artifacts:
            artifact.status = "verified"
        db.commit()
