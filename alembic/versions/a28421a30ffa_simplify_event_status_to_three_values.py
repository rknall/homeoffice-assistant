"""simplify_event_status_to_three_values

Revision ID: a28421a30ffa
Revises: d3cd5fec2518
Create Date: 2025-11-28 14:28:14.190496

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a28421a30ffa'
down_revision: str | None = 'd3cd5fec2518'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Convert old status values to new simplified statuses:
    # SQLAlchemy stores enum member NAMES (uppercase): PLANNING, ACTIVE, PAST
    # draft/DRAFT -> PLANNING
    # preparation/PREPARATION -> PLANNING
    # active/ACTIVE -> ACTIVE
    # completed/COMPLETED -> PAST
    # archived/ARCHIVED -> PAST
    op.execute(
        "UPDATE events SET status = 'PLANNING' "
        "WHERE status IN ('draft', 'DRAFT')"
    )
    op.execute(
        "UPDATE events SET status = 'PLANNING' "
        "WHERE status IN ('preparation', 'PREPARATION')"
    )
    op.execute(
        "UPDATE events SET status = 'ACTIVE' "
        "WHERE status IN ('active', 'ACTIVE')"
    )
    op.execute(
        "UPDATE events SET status = 'PAST' "
        "WHERE status IN ('completed', 'COMPLETED')"
    )
    op.execute(
        "UPDATE events SET status = 'PAST' "
        "WHERE status IN ('archived', 'ARCHIVED')"
    )


def downgrade() -> None:
    # Convert new status values back to old format
    # Note: This is a lossy conversion as we can't restore the original distinction
    # PLANNING -> DRAFT (default choice)
    # ACTIVE -> ACTIVE (no change)
    # PAST -> COMPLETED (default choice)
    op.execute("UPDATE events SET status = 'DRAFT' WHERE status = 'PLANNING'")
    op.execute("UPDATE events SET status = 'COMPLETED' WHERE status = 'PAST'")
