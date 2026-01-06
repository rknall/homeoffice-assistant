# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Add leave-related fields to time entries.

Revision ID: 005_add_leave_fields
Revises: 004_simplify_to_entries_only
Create Date: 2026-01-06

Adds support for:
- Multi-day leave entries (end_date field)
- Half-day vacation (is_half_day field)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_leave_fields"
down_revision: str | None = "004_simplify_to_entries_only"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add end_date and is_half_day columns to tt_time_entries."""
    # Add end_date column for multi-day leave entries
    op.add_column(
        "tt_time_entries",
        sa.Column("end_date", sa.Date(), nullable=True),
    )

    # Add is_half_day column for half-day vacation
    op.add_column(
        "tt_time_entries",
        sa.Column(
            "is_half_day",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    """Remove the added columns."""
    op.drop_column("tt_time_entries", "is_half_day")
    op.drop_column("tt_time_entries", "end_date")
