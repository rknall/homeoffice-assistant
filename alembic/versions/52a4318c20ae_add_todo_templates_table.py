"""add_todo_templates_table

Revision ID: 52a4318c20ae
Revises: 87f89f338243
Create Date: 2025-12-30 10:48:56.196268

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '52a4318c20ae'
down_revision: str | None = '87f89f338243'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the todo_templates table
    # Note: Using VARCHAR for enum columns for SQLite compatibility
    # SQLAlchemy's Enum type automatically handles this for SQLite
    op.create_table(
        "todo_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("days_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offset_reference", sa.String(20), nullable=False),
        sa.Column("template_set_name", sa.String(100), nullable=False),
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )

    # Create index for faster lookups by template_set_name
    op.create_index(
        "ix_todo_templates_template_set_name",
        "todo_templates",
        ["template_set_name"],
    )

    # Create index for user's templates
    op.create_index(
        "ix_todo_templates_user_id",
        "todo_templates",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_todo_templates_user_id", table_name="todo_templates")
    op.drop_index("ix_todo_templates_template_set_name", table_name="todo_templates")
    op.drop_table("todo_templates")
