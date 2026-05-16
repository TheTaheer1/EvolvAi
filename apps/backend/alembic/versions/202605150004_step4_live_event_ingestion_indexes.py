"""step 4 live event ingestion indexes

Revision ID: 202605150004
Revises: 202605150003
Create Date: 2026-05-15 04:00:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "202605150004"
down_revision: Union[str, None] = "202605150003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_market_events_event_type", "market_events", ["event_type"], unique=False)
    op.create_index("ix_market_events_source_event_type", "market_events", ["source", "event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_market_events_source_event_type", table_name="market_events")
    op.drop_index("ix_market_events_event_type", table_name="market_events")
