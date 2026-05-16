"""step 3 hybrid intelligence

Revision ID: 202605150003
Revises: 202605150002
Create Date: 2026-05-15 03:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202605150003"
down_revision: Union[str, None] = "202605150002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_event_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index(op.f("ix_external_event_sources_source_key"), "external_event_sources", ["source_key"])

    op.create_table(
        "external_event_ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("events_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("events_created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("events_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_external_event_ingestion_runs_source_key"),
        "external_event_ingestion_runs",
        ["source_key"],
    )

    op.create_table(
        "llm_invocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=100), server_default="openai", nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("mode", sa.String(length=100), nullable=False),
        sa.Column("prompt_hash", sa.String(length=128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("structured_output_valid", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_execution_id"], ["agent_executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_invocations_workflow_id"), "llm_invocations", ["workflow_id"])
    op.create_index(op.f("ix_llm_invocations_agent_execution_id"), "llm_invocations", ["agent_execution_id"])
    op.create_index(op.f("ix_llm_invocations_agent_name"), "llm_invocations", ["agent_name"])

    op.create_table(
        "external_event_raw",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized_market_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["normalized_market_event_id"], ["market_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "content_hash", name="uq_external_event_raw_source_hash"),
    )
    op.create_index(op.f("ix_external_event_raw_source"), "external_event_raw", ["source"])
    op.create_index(
        op.f("ix_external_event_raw_normalized_market_event_id"),
        "external_event_raw",
        ["normalized_market_event_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_external_event_raw_normalized_market_event_id"), table_name="external_event_raw")
    op.drop_index(op.f("ix_external_event_raw_source"), table_name="external_event_raw")
    op.drop_table("external_event_raw")
    op.drop_index(op.f("ix_llm_invocations_agent_name"), table_name="llm_invocations")
    op.drop_index(op.f("ix_llm_invocations_agent_execution_id"), table_name="llm_invocations")
    op.drop_index(op.f("ix_llm_invocations_workflow_id"), table_name="llm_invocations")
    op.drop_table("llm_invocations")
    op.drop_index(op.f("ix_external_event_ingestion_runs_source_key"), table_name="external_event_ingestion_runs")
    op.drop_table("external_event_ingestion_runs")
    op.drop_index(op.f("ix_external_event_sources_source_key"), table_name="external_event_sources")
    op.drop_table("external_event_sources")
