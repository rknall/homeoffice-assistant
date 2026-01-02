# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Add time entries table for multi-entry support.

Revision ID: 002_add_time_entries
Revises: 001_initial
Create Date: 2026-01-01 00:00:00.000000

This migration adds support for multiple check-in/check-out pairs per day.
The TimeEntry table stores individual clock punches, while TimeRecord
continues to hold daily aggregates for backward compatibility.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_time_entries"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create time entries table and migrate existing data."""
    # Create tt_time_entries table
    op.create_table(
        "tt_time_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("time_record_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("check_in", sa.Time(), nullable=False),
        sa.Column("check_in_timezone", sa.String(50), nullable=True),
        sa.Column("check_out", sa.Time(), nullable=True),
        sa.Column("check_out_timezone", sa.String(50), nullable=True),
        sa.Column("gross_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["time_record_id"],
            ["tt_time_records.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("time_record_id", "sequence", name="uq_tt_entry_seq"),
    )
    op.create_index(
        "idx_tt_entry_record", "tt_time_entries", ["time_record_id"]
    )

    # Migrate existing TimeRecord check_in/check_out data to TimeEntry
    # This creates one entry per existing record that has check_in
    connection = op.get_bind()

    # Get all existing records with check_in times
    records = connection.execute(
        sa.text("""
            SELECT id, check_in, check_in_timezone, check_out, check_out_timezone,
                   created_at, updated_at
            FROM tt_time_records
            WHERE check_in IS NOT NULL
        """)
    ).fetchall()

    # Insert corresponding time entries
    if records:
        for record in records:
            record_id = record[0]
            check_in = record[1]
            check_in_tz = record[2]
            check_out = record[3]
            check_out_tz = record[4]
            created_at = record[5]
            updated_at = record[6]

            # Calculate gross minutes if both times exist
            gross_minutes = None
            if check_in and check_out:
                # Handle both time objects and strings (SQLite returns strings)
                if isinstance(check_in, str):
                    # Parse time string "HH:MM:SS" or "HH:MM"
                    parts = check_in.split(":")
                    in_minutes = int(parts[0]) * 60 + int(parts[1])
                else:
                    in_minutes = check_in.hour * 60 + check_in.minute

                if isinstance(check_out, str):
                    parts = check_out.split(":")
                    out_minutes = int(parts[0]) * 60 + int(parts[1])
                else:
                    out_minutes = check_out.hour * 60 + check_out.minute

                gross_minutes = out_minutes - in_minutes

            # Insert the entry
            entry_id = str(uuid.uuid4())
            connection.execute(
                sa.text("""
                    INSERT INTO tt_time_entries (
                        id, time_record_id, sequence,
                        check_in, check_in_timezone,
                        check_out, check_out_timezone,
                        gross_minutes, created_at, updated_at
                    ) VALUES (
                        :id, :record_id, 1,
                        :check_in, :check_in_tz,
                        :check_out, :check_out_tz,
                        :gross_minutes, :created_at, :updated_at
                    )
                """),
                {
                    "id": entry_id,
                    "record_id": str(record_id),
                    "check_in": check_in,
                    "check_in_tz": check_in_tz,
                    "check_out": check_out,
                    "check_out_tz": check_out_tz,
                    "gross_minutes": gross_minutes,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )


def downgrade() -> None:
    """Remove time entries table."""
    op.drop_index("idx_tt_entry_record", table_name="tt_time_entries")
    op.drop_table("tt_time_entries")
