"""Reset stored expense conversions

Conversions written before the global-currency change (or while the
Frankfurter API URL was broken) may carry wrong 1:1 rates. Null them out;
they are lazily recomputed with correct daily rates on next access.

Revision ID: a9c8e2f4b1d6
Revises: e7a1b3c5d9f2
Create Date: 2026-07-05 21:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9c8e2f4b1d6"
down_revision: str | None = "e7a1b3c5d9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE expenses SET converted_amount = NULL, "
            "exchange_rate = NULL, rate_date = NULL"
        )
    )
    # Drop cached rates as well; they may stem from the broken API era
    op.get_bind().execute(sa.text("DELETE FROM currency_cache"))


def downgrade() -> None:
    # Nothing to restore; conversions are recomputed lazily.
    pass
