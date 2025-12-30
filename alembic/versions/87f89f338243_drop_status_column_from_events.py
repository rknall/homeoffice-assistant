"""drop_status_column_from_events

Revision ID: 87f89f338243
Revises: e7aa98881c78
Create Date: 2025-12-30 10:29:49.246783

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '87f89f338243'
down_revision: str | None = 'e7aa98881c78'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the status column - status is now computed from dates
    op.drop_column("events", "status")


def downgrade() -> None:
    # Re-add the status column (with default UPCOMING)
    op.add_column(
        "events",
        sa.Column(
            "status",
            sa.Enum("UPCOMING", "ACTIVE", "PAST", name="eventstatus"),
            nullable=False,
            server_default="UPCOMING",
        ),
    )
