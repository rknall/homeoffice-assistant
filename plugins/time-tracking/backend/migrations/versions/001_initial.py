# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Initial migration for time-tracking plugin.

Revision ID: 001_initial
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all time tracking tables."""
    # Create tt_timesheet_submissions first (referenced by tt_time_records)
    op.create_table(
        "tt_timesheet_submissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=False),
        sa.Column("sent_to_email", sa.String(254), nullable=False),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("record_ids", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
    )

    # Create tt_time_records
    op.create_table(
        "tt_time_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("day_type", sa.String(30), nullable=False, server_default="work"),
        sa.Column("check_in", sa.Time(), nullable=True),
        sa.Column("check_in_timezone", sa.String(50), nullable=True),
        sa.Column("check_out", sa.Time(), nullable=True),
        sa.Column("check_out_timezone", sa.String(50), nullable=True),
        sa.Column("partial_absence_type", sa.String(30), nullable=True),
        sa.Column("partial_absence_hours", sa.Float(), nullable=True),
        sa.Column("gross_hours", sa.Float(), nullable=True),
        sa.Column("break_minutes", sa.Integer(), nullable=True),
        sa.Column("net_hours", sa.Float(), nullable=True),
        sa.Column("work_location", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("compliance_warnings", sa.Text(), nullable=True),
        sa.Column("submission_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["tt_timesheet_submissions.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("user_id", "date", name="uq_tt_user_date"),
    )
    op.create_index(
        "idx_tt_user_date_range", "tt_time_records", ["user_id", "date"]
    )
    op.create_index(
        "idx_tt_company_date", "tt_time_records", ["company_id", "date"]
    )
    op.create_index(
        "idx_tt_submission", "tt_time_records", ["submission_id"]
    )

    # Create tt_time_allocations
    op.create_table(
        "tt_time_allocations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("time_record_id", sa.UUID(), nullable=False),
        sa.Column("hours", sa.Float(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("event_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["time_record_id"], ["tt_time_records.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="SET NULL"
        ),
    )

    # Create tt_leave_balances
    op.create_table(
        "tt_leave_balances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "vacation_entitled", sa.Float(), nullable=False, server_default="25.0"
        ),
        sa.Column(
            "vacation_carryover", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "vacation_taken", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "comp_time_balance", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column("sick_days_taken", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "user_id", "company_id", "year", name="uq_tt_user_company_year"
        ),
    )

    # Create tt_company_settings
    op.create_table(
        "tt_company_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column(
            "timezone", sa.String(50), nullable=False, server_default="Europe/Vienna"
        ),
        sa.Column(
            "country_code", sa.String(2), nullable=False, server_default="AT"
        ),
        sa.Column(
            "vacation_days_per_year",
            sa.Float(),
            nullable=False,
            server_default="25.0",
        ),
        sa.Column(
            "daily_overtime_threshold",
            sa.Float(),
            nullable=False,
            server_default="8.0",
        ),
        sa.Column(
            "weekly_overtime_threshold",
            sa.Float(),
            nullable=False,
            server_default="40.0",
        ),
        sa.Column(
            "overtime_threshold_hours",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "comp_time_warning_balance",
            sa.Float(),
            nullable=False,
            server_default="40.0",
        ),
        sa.Column("default_timesheet_contact_id", sa.UUID(), nullable=True),
        sa.Column("lock_period_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["default_timesheet_contact_id"],
            ["company_contacts.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("company_id"),
    )

    # Create tt_time_record_audit
    op.create_table(
        "tt_time_record_audit",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("time_record_id", sa.UUID(), nullable=False),
        sa.Column("changed_by", sa.UUID(), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("old_values", sa.Text(), nullable=True),
        sa.Column("new_values", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
    )

    # Create tt_custom_holidays
    op.create_table(
        "tt_custom_holidays",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
    )

    # Create tt_user_preferences
    op.create_table(
        "tt_user_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("last_company_id", sa.UUID(), nullable=True),
        sa.Column("last_work_location", sa.String(30), nullable=True),
        sa.Column("last_check_in", sa.Time(), nullable=True),
        sa.Column("last_check_out", sa.Time(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["last_company_id"], ["companies.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    """Drop all time tracking tables."""
    op.drop_table("tt_user_preferences")
    op.drop_table("tt_custom_holidays")
    op.drop_table("tt_time_record_audit")
    op.drop_table("tt_company_settings")
    op.drop_table("tt_leave_balances")
    op.drop_table("tt_time_allocations")
    op.drop_index("idx_tt_submission", table_name="tt_time_records")
    op.drop_index("idx_tt_company_date", table_name="tt_time_records")
    op.drop_index("idx_tt_user_date_range", table_name="tt_time_records")
    op.drop_table("tt_time_records")
    op.drop_table("tt_timesheet_submissions")
