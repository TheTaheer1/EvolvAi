from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.codebase_context import CodebaseContext
from app.models.decision import Decision
from app.models.repository_analysis import RepositoryAnalysis
from app.models.repository_file import RepositoryFile
from app.models.workflow import Workflow
from app.utils.json import to_jsonable


def codebase_context_payload(context: CodebaseContext) -> dict[str, Any]:
    return to_jsonable(
        {
            "id": context.id,
            "workflow_id": context.workflow_id,
            "analysis_id": context.analysis_id,
            "relevant_files": context.relevant_files,
            "architecture_summary": context.architecture_summary,
            "implementation_hints": context.implementation_hints,
            "risks": context.risks,
            "created_at": context.created_at,
        }
    )


class CodebaseContextService:
    def get_by_workflow(self, db: Session, workflow_id: UUID | str) -> CodebaseContext | None:
        return db.scalars(
            select(CodebaseContext)
            .where(CodebaseContext.workflow_id == workflow_id)
            .order_by(CodebaseContext.created_at.desc())
        ).first()

    def require_by_workflow(self, db: Session, workflow_id: UUID | str) -> CodebaseContext:
        context = self.get_by_workflow(db, workflow_id)
        if not context:
            raise HTTPException(status_code=404, detail="Codebase context not found for workflow")
        return context

    def attach_to_workflow(
        self,
        db: Session,
        analysis_id: UUID | str,
        workflow_id: UUID | str,
    ) -> CodebaseContext:
        analysis = db.scalars(
            select(RepositoryAnalysis)
            .where(RepositoryAnalysis.id == analysis_id)
            .options(selectinload(RepositoryAnalysis.files))
        ).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="Repository analysis not found")
        if analysis.status != "completed":
            raise HTTPException(status_code=400, detail="Repository analysis is not completed")
        workflow = db.get(Workflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        files = self.select_relevant_files(db, analysis, workflow)
        context = CodebaseContext(
            workflow_id=workflow.id,
            analysis_id=analysis.id,
            relevant_files=[self._file_payload(file) for file in files],
            architecture_summary=self.build_architecture_summary(analysis, files),
            implementation_hints=self.build_hints(analysis, workflow, files),
            risks=[
                "Repository analysis is read-only; EvolvAI must not modify source repository files.",
                "Relevant files are suggested touchpoints only and require human review.",
                "Large files, secrets, and unsafe paths were excluded from analysis.",
            ],
        )
        db.add(context)
        db.commit()
        db.refresh(context)
        return context

    def select_relevant_files(
        self, db: Session, analysis: RepositoryAnalysis, workflow: Workflow, limit: int = 12
    ) -> list[RepositoryFile]:
        terms = self._workflow_terms(db, workflow)
        files = list(analysis.files or [])
        if not files:
            files = list(
                db.scalars(
                    select(RepositoryFile)
                    .where(RepositoryFile.analysis_id == analysis.id)
                    .order_by(RepositoryFile.importance_score.desc())
                ).all()
            )

        def score(file: RepositoryFile) -> float:
            path = file.path.lower()
            summary = (file.summary or "").lower()
            match_score = sum(0.08 for term in terms if term and (term in path or term in summary))
            return min(1.0, float(file.importance_score or 0) + match_score)

        return sorted(files, key=score, reverse=True)[:limit]

    def build_architecture_summary(self, analysis: RepositoryAnalysis, files: list[RepositoryFile]) -> str:
        stack = ", ".join(analysis.detected_stack or []) or "unknown stack"
        touchpoints = ", ".join(file.path for file in files[:6]) or "no relevant files selected"
        return (
            f"{analysis.owner}/{analysis.repo}@{analysis.branch} appears to use {stack}. "
            f"EvolvAI selected read-only implementation touchpoints: {touchpoints}."
        )

    def build_hints(
        self, analysis: RepositoryAnalysis, workflow: Workflow, files: list[RepositoryFile]
    ) -> list[str]:
        hints = [
            "Use these files as reference context for planning only; do not edit them automatically.",
            "Keep generated artifacts in the safe preview workspace until a human approves real implementation.",
        ]
        stack = set(analysis.detected_stack or [])
        if "Next.js" in stack or "React" in stack:
            hints.append("Frontend work should align with existing Next.js/React route and component patterns.")
        if "FastAPI" in stack or "Python" in stack:
            hints.append("Backend work should align with existing FastAPI service and schema boundaries.")
        if any(file.file_type == "migration" for file in files):
            hints.append("Database changes should use the repository's existing migration convention.")
        return hints

    def _workflow_terms(self, db: Session, workflow: Workflow) -> set[str]:
        blob = str(workflow.input_payload or {})
        decisions = db.scalars(select(Decision).where(Decision.workflow_id == workflow.id)).all()
        for decision in decisions:
            blob += " " + " ".join(
                str(value or "")
                for value in [decision.title, decision.summary, decision.recommended_action, decision.reasoning]
            )
        words = {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", blob)}
        stop = {"the", "and", "for", "with", "that", "this", "from", "workflow", "demo", "market", "event"}
        return {word for word in words if word not in stop}

    def _file_payload(self, file: RepositoryFile) -> dict[str, Any]:
        return {
            "id": str(file.id),
            "path": file.path,
            "file_type": file.file_type,
            "language": file.language,
            "size_bytes": file.size_bytes,
            "importance_score": file.importance_score,
            "summary": file.summary,
        }
