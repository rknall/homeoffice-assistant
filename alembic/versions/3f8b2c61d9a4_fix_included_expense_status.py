"""Fix expenses left in the removed INCLUDED status

a1b2c3d4e5f6 matched lowercase 'included', but Enum(ExpenseStatus) stores
member names, so 'INCLUDED' rows survived and fail to load. Map them to
SUBMITTED the way a1b2c3d4e5f6 intended.

Revision ID: 3f8b2c61d9a4
Revises: a9c8e2f4b1d6
Create Date: 2026-11-08 20:15:23.019812

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f8b2c61d9a4"
down_revision: str | None = "a9c8e2f4b1d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE expenses
        SET status = 'SUBMITTED',
            submitted_at = COALESCE(submitted_at, updated_at)
        WHERE status IN ('INCLUDED', 'included')
        """
    )


def downgrade() -> None:
    # No-op: the corrected rows cannot be told apart from rows that were
    # SUBMITTED already, and INCLUDED does not load in either schema version.
    pass
