from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.integrations.github.pr_client import GitHubPRClient, GitHubPRClientError
from app.main import fastapi_app
from app.models.generated_artifact import GeneratedArtifact
from app.models.pull_request import PullRequestHistory
from app.models.verification_report import VerificationReport
from app.models.workflow import Workflow
from app.services.github_pr_service import GitHubPRService


def _configure_enabled(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.ALLOW_REAL_GITHUB_PR", True)
    monkeypatch.setattr("app.core.config.settings.ALLOW_EXTERNAL_WRITE_ACTIONS", True)
    monkeypatch.setattr("app.core.config.settings.ALLOW_CODE_EXECUTION", False)
    monkeypatch.setattr("app.core.config.settings.GITHUB_TOKEN", "ghp_test_token")
    monkeypatch.setattr("app.core.config.settings.GITHUB_TARGET_OWNER", "example")
    monkeypatch.setattr("app.core.config.settings.GITHUB_TARGET_REPO", "demo")
    monkeypatch.setattr("app.core.config.settings.GITHUB_BASE_BRANCH", "main")
    monkeypatch.setattr("app.core.config.settings.GITHUB_PR_DRAFT", True)


def _workflow_fixture(
    *,
    verification_passed: bool = True,
    artifact_path: str = "docs/features/demo.md",
    artifact_content: str = "# Demo proposal\n\nSafe preview artifact.",
) -> tuple[str, str]:
    db = SessionLocal()
    try:
        workflow = Workflow(
            trigger_type="demo_scenario",
            trigger_source=f"step6-{uuid4().hex[:8]}",
            status="completed",
            input_payload={"scenario": {"scenario_key": "ai-meeting-summary"}},
        )
        db.add(workflow)
        db.flush()
        artifact = GeneratedArtifact(
            workflow_id=workflow.id,
            artifact_type="documentation",
            file_path=artifact_path,
            title="Demo artifact",
            description="Safe generated artifact",
            content=artifact_content,
            language="markdown",
            status="verified",
            artifact_metadata={},
        )
        verification = VerificationReport(
            workflow_id=workflow.id,
            status="completed" if verification_passed else "failed",
            passed=verification_passed,
            checks=[{"name": "path_safety_check", "status": "passed" if verification_passed else "failed"}],
            warnings=[],
            errors=[] if verification_passed else [{"message": "verification failed"}],
            summary="Verification passed." if verification_passed else "Verification failed.",
        )
        pr = PullRequestHistory(
            workflow_id=workflow.id,
            repo_owner="example",
            repo_name="demo",
            branch_name=f"evolvai/demo-{uuid4().hex[:8]}",
            status="planned" if verification_passed else "blocked",
            title="Demo PR: safe generated artifact",
            description="## Summary\nSafe PR preview.",
            changed_files=[{"path": artifact_path, "type": "documentation", "status": "verified"}],
        )
        db.add_all([artifact, verification, pr])
        db.commit()
        return str(workflow.id), str(pr.id)
    finally:
        db.close()


def test_open_draft_pr_disabled_returns_403(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.ALLOW_REAL_GITHUB_PR", False)
    workflow_id, _ = _workflow_fixture()
    response = TestClient(fastapi_app).post(f"/api/v1/workflows/{workflow_id}/open-draft-pr")
    assert response.status_code == 403
    assert "Real GitHub PR creation is disabled" in response.json()["detail"]


def test_missing_token_blocks_pr(monkeypatch) -> None:
    _configure_enabled(monkeypatch)
    monkeypatch.setattr("app.core.config.settings.GITHUB_TOKEN", "")
    workflow_id, _ = _workflow_fixture()
    db = SessionLocal()
    try:
        safety = GitHubPRService().pr_safety_check(db, workflow_id)
        assert not safety["can_open_pr"]
        assert any(check["name"] == "github_token_present" and not check["passed"] for check in safety["checks"])
    finally:
        db.close()


def test_failed_verification_blocks_pr(monkeypatch) -> None:
    _configure_enabled(monkeypatch)
    workflow_id, _ = _workflow_fixture(verification_passed=False)
    db = SessionLocal()
    try:
        safety = GitHubPRService().pr_safety_check(db, workflow_id)
        assert not safety["can_open_pr"]
        assert any(check["name"] == "verification_passed" and not check["passed"] for check in safety["checks"])
    finally:
        db.close()


def test_unsafe_file_path_blocks_pr(monkeypatch) -> None:
    _configure_enabled(monkeypatch)
    workflow_id, _ = _workflow_fixture(artifact_path="package.json")
    db = SessionLocal()
    try:
        safety = GitHubPRService().pr_safety_check(db, workflow_id)
        assert not safety["can_open_pr"]
        assert any(check["name"] == "artifact_safety_check" and not check["passed"] for check in safety["checks"])
    finally:
        db.close()


def test_dangerous_content_blocks_pr(monkeypatch) -> None:
    _configure_enabled(monkeypatch)
    workflow_id, _ = _workflow_fixture(artifact_content="Do this: rm -rf /")
    db = SessionLocal()
    try:
        safety = GitHubPRService().pr_safety_check(db, workflow_id)
        assert not safety["can_open_pr"]
        assert any(check["name"] == "artifact_safety_check" and not check["passed"] for check in safety["checks"])
    finally:
        db.close()


def test_safe_artifacts_create_mocked_draft_pr(monkeypatch) -> None:
    _configure_enabled(monkeypatch)
    workflow_id, _ = _workflow_fixture()

    def fake_create(self, **kwargs):
        assert kwargs["draft"] is True
        assert kwargs["owner"] == "example"
        assert kwargs["files"][0]["path"].startswith("evolvai/generated/")
        return {
            "number": 42,
            "url": "https://github.com/example/demo/pull/42",
            "branch_name": kwargs["branch_name"],
        }

    monkeypatch.setattr(GitHubPRClient, "create_draft_pr", fake_create)
    db = SessionLocal()
    try:
        pr = GitHubPRService().create_draft_pr_from_workflow(db, workflow_id)
        assert pr.status == "opened"
        assert pr.pr_number == 42
        assert pr.pr_url == "https://github.com/example/demo/pull/42"
        assert pr.changed_files[0]["path"].startswith("evolvai/generated/")
    finally:
        db.close()


def test_github_api_error_updates_pr_failed(monkeypatch) -> None:
    _configure_enabled(monkeypatch)
    workflow_id, _ = _workflow_fixture()

    def fake_create(self, **kwargs):
        raise GitHubPRClientError("github_rate_limit")

    monkeypatch.setattr(GitHubPRClient, "create_draft_pr", fake_create)
    db = SessionLocal()
    try:
        pr = GitHubPRService().create_draft_pr_from_workflow(db, workflow_id)
        assert pr.status == "failed"
        assert pr.error_message == "github_rate_limit"
    finally:
        db.close()
