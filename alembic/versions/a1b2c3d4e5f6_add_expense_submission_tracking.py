# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""add_expense_submission_tracking

Revision ID: a1b2c3d4e5f6
Revises: 9546bc823832
Create Date: 2025-12-31 12:00:00.000000

Adds ExpenseSubmission and ExpenseSubmissionItem tables for tracking
incremental expense submissions. Also adds submitted_at and rejection_reason
fields to expenses, and migrates INCLUDED status to SUBMITTED.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9546bc823832"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create expense_submissions table
    op.create_table(
        "expense_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("submission_method", sa.String(length=50), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("expense_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_expense_submissions_event_id"),
        "expense_submissions",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expense_submissions_submitted_at"),
        "expense_submissions",
        ["submitted_at"],
        unique=False,
    )

    # Create expense_submission_items table
    op.create_table(
        "expense_submission_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("expense_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("converted_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["expense_id"],
            ["expenses.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["expense_submissions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_expense_submission_items_expense_id"),
        "expense_submission_items",
        ["expense_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expense_submission_items_submission_id"),
        "expense_submission_items",
        ["submission_id"],
        unique=False,
    )

    # Add submission tracking fields to expenses
    op.add_column(
        "expenses",
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "expenses",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )

    # Migrate INCLUDED status to SUBMITTED and set submitted_at
    # SQLite stores enums as text, so we can just update the string value
    op.execute(
        """
        UPDATE expenses
        SET status = 'submitted', submitted_at = updated_at
        WHERE status = 'included'
        """
    )


def downgrade() -> None:
    # Migrate SUBMITTED back to INCLUDED
    op.execute(
        """
        UPDATE expenses
        SET status = 'included'
        WHERE status = 'submitted'
        """
    )

    # Remove submission tracking fields from expenses
    op.drop_column("expenses", "rejection_reason")
    op.drop_column("expenses", "submitted_at")

    # Drop expense_submission_items table
    op.drop_index(
        op.f("ix_expense_submission_items_submission_id"),
        table_name="expense_submission_items",
    )
    op.drop_index(
        op.f("ix_expense_submission_items_expense_id"),
        table_name="expense_submission_items",
    )
    op.drop_table("expense_submission_items")

    # Drop expense_submissions table
    op.drop_index(
        op.f("ix_expense_submissions_submitted_at"),
        table_name="expense_submissions",
    )
    op.drop_index(
        op.f("ix_expense_submissions_event_id"),
        table_name="expense_submissions",
    )
    op.drop_table("expense_submissions")
