"""Add plugin management tables

Revision ID: 5c9d4e8f3a2b
Revises: 4b7c3d8e2f1a
Create Date: 2025-12-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c9d4e8f3a2b"
down_revision: str | None = "4b7c3d8e2f1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create plugin_configs table
    op.create_table(
        "plugin_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plugin_id", sa.String(length=100), nullable=False),
        sa.Column("plugin_version", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("settings_encrypted", sa.Text(), nullable=True),
        sa.Column("migration_version", sa.String(length=100), nullable=True),
        sa.Column("permissions_granted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plugin_id"),
    )
    op.create_index(
        op.f("ix_plugin_configs_plugin_id"),
        "plugin_configs",
        ["plugin_id"],
        unique=True,
    )

    # Create plugin_migration_history table
    op.create_table(
        "plugin_migration_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plugin_id", sa.String(length=100), nullable=False),
        sa.Column("revision", sa.String(length=100), nullable=False),
        sa.Column("applied_at", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plugin_migration_history_plugin_id"),
        "plugin_migration_history",
        ["plugin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_plugin_migration_history_plugin_id"),
        table_name="plugin_migration_history",
    )
    op.drop_table("plugin_migration_history")

    op.drop_index(op.f("ix_plugin_configs_plugin_id"), table_name="plugin_configs")
    op.drop_table("plugin_configs")
