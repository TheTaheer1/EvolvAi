from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.integrations.github.repository_reader import RepositoryReader, RepositoryReaderError
from app.models.repository_analysis import RepositoryAnalysis
from app.models.repository_file import RepositoryFile
from app.utils.json import to_jsonable
from app.utils.time import utc_now


class RepositoryAnalysisService:
    def __init__(self, reader: RepositoryReader | None = None) -> None:
        self.reader = reader or RepositoryReader()

    def analyze_repository(self, db: Session, owner: str, repo: str, branch: str | None = None) -> RepositoryAnalysis:
        if not settings.REPO_ANALYSIS_ENABLED:
            raise HTTPException(status_code=400, detail="Repository analysis is disabled.")
        branch = (branch or settings.GITHUB_BASE_BRANCH or "main").strip()
        analysis = RepositoryAnalysis(
            owner=owner.strip(),
            repo=repo.strip(),
            branch=branch,
            status="running",
            detected_stack=[],
            file_count=0,
            analyzed_file_count=0,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        try:
            metadata = self.reader.get_repo_metadata(owner, repo)
            tree = self.reader.get_repo_tree(owner, repo, branch)
            blobs = [item for item in tree if item.get("type") == "blob" and item.get("path")]
            included = [
                item for item in blobs if self.reader.should_include_file(str(item["path"]), item.get("size"))
            ]
            included.sort(
                key=lambda item: (
                    self.reader.score_file_importance(str(item["path"])),
                    -(int(item.get("size") or 0)),
                ),
                reverse=True,
            )
            selected = included[: max(1, settings.REPO_ANALYSIS_MAX_FILES)]
            stack = self.reader.detect_tech_stack(included)
            analysis.repo_url = metadata.get("html_url")
            analysis.default_branch = metadata.get("default_branch")
            analysis.file_count = len(blobs)
            analysis.analyzed_file_count = len(selected)
            analysis.detected_stack = stack
            analysis.summary = self.build_summary(owner, repo, branch, stack, selected, len(blobs))
            analysis.status = "completed"
            analysis.error_message = None
            analysis.updated_at = utc_now()
            db.flush()
            for item in selected:
                path = str(item["path"])
                file = RepositoryFile(
                    analysis_id=analysis.id,
                    path=path,
                    file_type=self.reader.classify_file(path),
                    language=self.reader.detect_language(path),
                    size_bytes=item.get("size"),
                    sha=item.get("sha"),
                    importance_score=self.reader.score_file_importance(path),
                    summary=self.summarize_file(path, item),
                    raw_metadata=to_jsonable(
                        {
                            "mode": item.get("mode"),
                            "type": item.get("type"),
                            "url": item.get("url"),
                            "content_included": False,
                        }
                    ),
                )
                db.add(file)
            db.commit()
            return self.get_analysis(db, analysis.id, detail=True) or analysis
        except RepositoryReaderError as exc:
            analysis.status = "failed"
            analysis.error_message = str(exc)
            analysis.updated_at = utc_now()
            db.commit()
            db.refresh(analysis)
            return analysis
        except Exception as exc:  # noqa: BLE001
            analysis.status = "failed"
            analysis.error_message = "repository_analysis_failed"
            analysis.updated_at = utc_now()
            db.commit()
            db.refresh(analysis)
            return analysis

    def get_analysis(
        self, db: Session, analysis_id: UUID | str, detail: bool = False
    ) -> RepositoryAnalysis | None:
        stmt = select(RepositoryAnalysis).where(RepositoryAnalysis.id == analysis_id)
        if detail:
            stmt = stmt.options(selectinload(RepositoryAnalysis.files))
        return db.scalars(stmt).first()

    def require_analysis(
        self, db: Session, analysis_id: UUID | str, detail: bool = False
    ) -> RepositoryAnalysis:
        analysis = self.get_analysis(db, analysis_id, detail=detail)
        if not analysis:
            raise HTTPException(status_code=404, detail="Repository analysis not found")
        return analysis

    def list_analyses(self, db: Session, limit: int = 25) -> list[RepositoryAnalysis]:
        return list(
            db.scalars(
                select(RepositoryAnalysis)
                .order_by(RepositoryAnalysis.created_at.desc())
                .limit(min(max(limit, 1), 100))
            ).all()
        )

    def build_summary(
        self,
        owner: str,
        repo: str,
        branch: str,
        stack: list[str],
        files: list[dict[str, Any]],
        total_files: int,
    ) -> str:
        stack_text = ", ".join(stack) if stack else "unknown stack"
        top_paths = ", ".join(str(file.get("path")) for file in files[:5])
        return (
            f"Read-only analysis of {owner}/{repo}@{branch} found {total_files} repository files "
            f"and selected {len(files)} important safe files. Detected stack: {stack_text}. "
            f"Highest-signal files: {top_paths or 'none'}."
        )

    def summarize_file(self, path: str, item: dict[str, Any]) -> str:
        file_type = self.reader.classify_file(path).replace("_", " ")
        language = self.reader.detect_language(path) or "unknown language"
        size = item.get("size")
        return f"{file_type.title()} file in {language}; size {size if size is not None else 'unknown'} bytes."
