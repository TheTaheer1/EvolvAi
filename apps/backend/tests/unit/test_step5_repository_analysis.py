from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.integrations.github.repository_reader import RepositoryRateLimitError, RepositoryReader
from app.main import fastapi_app
from app.models.repository_analysis import RepositoryAnalysis
from app.models.repository_file import RepositoryFile
from app.models.workflow import Workflow
from app.services.codebase_context_service import CodebaseContextService
from app.services.repository_analysis_service import RepositoryAnalysisService


def _repo_tree() -> list[dict]:
    return [
        {"path": "package.json", "type": "blob", "size": 800, "sha": "pkg"},
        {"path": "src/app/dashboard/page.tsx", "type": "blob", "size": 4200, "sha": "page"},
        {"path": "src/components/dashboard/widget.tsx", "type": "blob", "size": 2600, "sha": "widget"},
        {"path": "app/main.py", "type": "blob", "size": 1800, "sha": "main"},
        {"path": "app/models/user.py", "type": "blob", "size": 900, "sha": "model"},
        {"path": "alembic/versions/0001_init.py", "type": "blob", "size": 1600, "sha": "migration"},
        {"path": ".env", "type": "blob", "size": 100, "sha": "secret"},
        {"path": "node_modules/react/index.js", "type": "blob", "size": 100, "sha": "vendor"},
    ]


def test_repo_file_filtering_excludes_unsafe_paths() -> None:
    reader = RepositoryReader()
    assert reader.should_include_file("src/app/page.tsx", 100)
    assert reader.should_include_file(".env.example", 100)
    assert not reader.should_include_file(".env", 100)
    assert not reader.should_include_file(".ssh/id_rsa", 100)
    assert not reader.should_include_file("../outside.ts", 100)
    assert not reader.should_include_file("node_modules/pkg/index.js", 100)
    assert not reader.should_include_file("src/large.ts", 999_999_999)


def test_language_detection_and_importance_scoring() -> None:
    reader = RepositoryReader()
    assert reader.detect_language("src/app/page.tsx") == "TypeScript React"
    assert reader.detect_language("app/main.py") == "Python"
    assert reader.score_file_importance("package.json") > reader.score_file_importance("docs/random.md")
    assert reader.classify_file("src/components/widget.tsx") == "frontend_component"


def test_tech_stack_detection_from_tree() -> None:
    reader = RepositoryReader()
    stack = reader.detect_tech_stack(_repo_tree())
    assert "React" in stack
    assert "Next.js" in stack
    assert "Python" in stack
    assert "FastAPI" in stack
    assert "PostgreSQL" in stack


def test_repository_reader_rate_limit_response_is_classified() -> None:
    response = httpx.Response(403, headers={"X-RateLimit-Remaining": "0"}, text="API rate limit exceeded")
    try:
        RepositoryReader().handle_rate_limit(response)
    except RepositoryRateLimitError as exc:
        assert "github_rate_limit" in str(exc)
    else:
        raise AssertionError("Expected RepositoryRateLimitError")


def test_repository_analysis_handles_missing_token_without_network(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.GITHUB_TOKEN", "")
    monkeypatch.setattr(
        RepositoryReader,
        "get_repo_metadata",
        lambda self, owner, repo: {
            "html_url": f"https://github.com/{owner}/{repo}",
            "default_branch": "main",
        },
    )
    monkeypatch.setattr(RepositoryReader, "get_repo_tree", lambda self, owner, repo, branch: _repo_tree())
    db = SessionLocal()
    try:
        analysis = RepositoryAnalysisService().analyze_repository(
            db,
            owner=f"example-{uuid4().hex[:8]}",
            repo="demo-repo",
            branch="main",
        )
        assert analysis.status == "completed"
        assert analysis.file_count == len(_repo_tree())
        assert analysis.analyzed_file_count > 0
        assert all(file.path != ".env" for file in analysis.files)
    finally:
        db.close()


def test_repositories_analyze_endpoint_returns_analysis(monkeypatch) -> None:
    monkeypatch.setattr(
        RepositoryReader,
        "get_repo_metadata",
        lambda self, owner, repo: {
            "html_url": f"https://github.com/{owner}/{repo}",
            "default_branch": "main",
        },
    )
    monkeypatch.setattr(RepositoryReader, "get_repo_tree", lambda self, owner, repo, branch: _repo_tree())
    response = TestClient(fastapi_app).post(
        "/api/v1/repositories/analyze",
        json={"owner": f"example-{uuid4().hex[:8]}", "repo": "demo-repo", "branch": "main"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["analyzed_file_count"] > 0
    assert any(file["path"] == "package.json" for file in payload["files"])


def test_codebase_context_attaches_to_workflow() -> None:
    db = SessionLocal()
    try:
        analysis = RepositoryAnalysis(
            owner=f"example-{uuid4().hex[:8]}",
            repo="demo-repo",
            branch="main",
            status="completed",
            detected_stack=["Next.js", "FastAPI"],
            file_count=2,
            analyzed_file_count=2,
        )
        db.add(analysis)
        db.flush()
        db.add_all(
            [
                RepositoryFile(
                    analysis_id=analysis.id,
                    path="src/app/dashboard/page.tsx",
                    file_type="frontend_route",
                    language="TypeScript React",
                    size_bytes=500,
                    importance_score=0.9,
                    summary="Dashboard route.",
                ),
                RepositoryFile(
                    analysis_id=analysis.id,
                    path="app/api/v1/endpoints/demo.py",
                    file_type="api",
                    language="Python",
                    size_bytes=500,
                    importance_score=0.85,
                    summary="Demo API endpoint.",
                ),
            ]
        )
        workflow = Workflow(
            trigger_type="demo_scenario",
            trigger_source="test",
            status="completed",
            input_payload={"recommended_evolution": "Add dashboard automation"},
        )
        db.add(workflow)
        db.commit()
        context = CodebaseContextService().attach_to_workflow(db, analysis.id, workflow.id)
        assert context.workflow_id == workflow.id
        assert context.relevant_files
        assert "read-only" in " ".join(context.risks).lower()
    finally:
        db.close()
