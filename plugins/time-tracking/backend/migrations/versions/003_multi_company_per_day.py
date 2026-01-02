# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Allow multiple time records per day for different companies.

Revision ID: 003_multi_company_per_day
Revises: 002_add_time_entries
Create Date: 2026-01-01 20:00:00.000000

This migration changes the unique constraint from (user_id, date) to
(user_id, date, company_id) to allow tracking time for multiple
companies on the same day.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_multi_company_per_day"
down_revision: str | None = "002_add_time_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change unique constraint to include company_id."""
    # SQLite doesn't support dropping constraints directly,
    # so we need to use batch mode to recreate the table
    with op.batch_alter_table("tt_time_records") as batch_op:
        # Drop the old constraint
        batch_op.drop_constraint("uq_tt_user_date", type_="unique")
        # Add new constraint including company_id
        batch_op.create_unique_constraint(
            "uq_tt_user_date_company",
            ["user_id", "date", "company_id"],
        )


def downgrade() -> None:
    """Revert to original unique constraint (user_id, date only)."""
    with op.batch_alter_table("tt_time_records") as batch_op:
        batch_op.drop_constraint("uq_tt_user_date_company", type_="unique")
        batch_op.create_unique_constraint(
            "uq_tt_user_date",
            ["user_id", "date"],
        )
