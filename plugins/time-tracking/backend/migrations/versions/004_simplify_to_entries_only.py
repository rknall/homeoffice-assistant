# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Simplify schema to TimeEntry only.

Revision ID: 004_simplify_to_entries_only
Revises: 003_multi_company_per_day
Create Date: 2026-01-05

This migration removes the TimeRecord container model and makes TimeEntry
the primary (and only) time tracking table. This simplifies the architecture:
- No more two-layer TimeRecord -> TimeEntry hierarchy
- No more data duplication (check_in/out stored in both)
- No more synchronization of aggregated fields
- Multiple entries per day per company is natural (just multiple rows)

Tables removed:
- tt_time_records
- tt_time_record_audit
- tt_time_allocations

Tables modified:
- tt_time_entries: Now self-contained with all needed fields
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_simplify_to_entries_only"
down_revision: str | None = "003_multi_company_per_day"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Simplify to entries-only schema."""
    # Drop old tables that are no longer needed
    op.drop_table("tt_time_allocations")
    op.drop_table("tt_time_record_audit")

    # Drop the old time_entries table (we'll recreate it with new structure)
    op.drop_index("idx_tt_entry_record", table_name="tt_time_entries")
    op.drop_table("tt_time_entries")

    # Drop the time_records table
    op.drop_index("idx_tt_submission", table_name="tt_time_records")
    op.drop_index("idx_tt_company_date", table_name="tt_time_records")
    op.drop_index("idx_tt_user_date_range", table_name="tt_time_records")
    op.drop_table("tt_time_records")

    # Create the new simplified time_entries table
    op.create_table(
        "tt_time_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "company_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column("entry_type", sa.String(30), nullable=False),
        sa.Column("check_in", sa.Time(), nullable=True),
        sa.Column("check_out", sa.Time(), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True),
        sa.Column("work_location", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("submission_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["tt_timesheet_submissions.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "idx_tt_entry_user_date",
        "tt_time_entries",
        ["user_id", "date"],
    )
    op.create_index(
        "idx_tt_entry_company_date",
        "tt_time_entries",
        ["company_id", "date"],
    )
    op.create_index(
        "idx_tt_entry_submission",
        "tt_time_entries",
        ["submission_id"],
    )


def downgrade() -> None:
    """Restore original schema - not supported, data would be lost."""
    raise NotImplementedError(
        "Downgrade not supported for this migration. "
        "Restore from backup if needed."
    )
