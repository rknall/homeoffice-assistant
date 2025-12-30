"""fix_planning_to_upcoming_status

Revision ID: e7aa98881c78
Revises: afa2b554c315
Create Date: 2025-12-30 10:21:16.966942

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e7aa98881c78'
down_revision: str | None = 'afa2b554c315'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Fix events that have PLANNING status from earlier migration
    # PLANNING was renamed to UPCOMING when status became computed from dates
    op.execute(
        "UPDATE events SET status = 'UPCOMING' "
        "WHERE status IN ('planning', 'PLANNING')"
    )


def downgrade() -> None:
    # No downgrade needed - UPCOMING is the correct value
    pass
