"""Add holiday_calendars table

Revision ID: 35c10b543937
Revises: b0d8b5f8e983
Create Date: 2026-01-10 11:42:31.400267

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "35c10b543937"
down_revision: str | None = "b0d8b5f8e983"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "holiday_calendars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("subdivision", sa.String(length=10), nullable=True),
        sa.Column("display_label", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_holiday_calendars_user_id"),
        "holiday_calendars",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_holiday_calendars_user_id"), table_name="holiday_calendars")
    op.drop_table("holiday_calendars")
