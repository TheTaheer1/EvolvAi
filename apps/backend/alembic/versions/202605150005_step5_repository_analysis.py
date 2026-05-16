"""step 5 repository analysis

Revision ID: 202605150005
Revises: 202605150004
Create Date: 2026-05-15 22:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202605150005"
down_revision = "202605150004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("repo", sa.String(length=255), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("repo_url", sa.Text(), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("detected_stack", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("analyzed_file_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repository_analyses_owner"), "repository_analyses", ["owner"], unique=False)
    op.create_index(op.f("ix_repository_analyses_repo"), "repository_analyses", ["repo"], unique=False)
    op.create_index(op.f("ix_repository_analyses_status"), "repository_analyses", ["status"], unique=False)

    op.create_table(
        "repository_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(length=1000), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha", sa.String(length=255), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["repository_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repository_files_analysis_id"), "repository_files", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_repository_files_path"), "repository_files", ["path"], unique=False)

    op.create_table(
        "codebase_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relevant_files", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("architecture_summary", sa.Text(), nullable=True),
        sa.Column("implementation_hints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["repository_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_codebase_contexts_analysis_id"), "codebase_contexts", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_codebase_contexts_workflow_id"), "codebase_contexts", ["workflow_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_codebase_contexts_workflow_id"), table_name="codebase_contexts")
    op.drop_index(op.f("ix_codebase_contexts_analysis_id"), table_name="codebase_contexts")
    op.drop_table("codebase_contexts")
    op.drop_index(op.f("ix_repository_files_path"), table_name="repository_files")
    op.drop_index(op.f("ix_repository_files_analysis_id"), table_name="repository_files")
    op.drop_table("repository_files")
    op.drop_index(op.f("ix_repository_analyses_status"), table_name="repository_analyses")
    op.drop_index(op.f("ix_repository_analyses_repo"), table_name="repository_analyses")
    op.drop_index(op.f("ix_repository_analyses_owner"), table_name="repository_analyses")
    op.drop_table("repository_analyses")
