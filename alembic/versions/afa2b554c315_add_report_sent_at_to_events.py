"""add_report_sent_at_to_events

Revision ID: afa2b554c315
Revises: 7d8e9f0a1b2c
Create Date: 2025-12-29 23:56:06.797536

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'afa2b554c315'
down_revision: str | None = '7d8e9f0a1b2c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("report_sent_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "report_sent_at")
