"""Add company_calendars table

Revision ID: b0d8b5f8e983
Revises: b16aa3f3bd1e
Create Date: 2026-01-07 10:16:47.696149

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b0d8b5f8e983"
down_revision: str | None = "b16aa3f3bd1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_calendars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "calendar_type",
            sa.Enum("GOOGLE", "OUTLOOK", "ICAL", name="calendartype"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=500), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_company_calendars_company_id"),
        "company_calendars",
        ["company_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_company_calendars_company_id"), table_name="company_calendars"
    )
    op.drop_table("company_calendars")
    # Drop the enum type if using PostgreSQL
    op.execute("DROP TYPE IF EXISTS calendartype")
