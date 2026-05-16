"""step6 pr error message

Revision ID: 202605150006
Revises: 202605150005
Create Date: 2026-05-15 00:06:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605150006"
down_revision: Union[str, None] = "202605150005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pull_request_history", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pull_request_history", "error_message")
