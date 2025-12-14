# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""add plugin_id to permissions

Revision ID: 7d8e9f0a1b2c
Revises: 6bc1a7347a04
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d8e9f0a1b2c"
down_revision: str | None = "6bc1a7347a04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add plugin_id column to permissions table
    # NULL means it's a core permission, non-NULL means plugin-provided
    op.add_column(
        "permissions",
        sa.Column("plugin_id", sa.String(length=100), nullable=True),
    )
    # Create index for efficient lookup of plugin permissions
    op.create_index(
        "ix_permissions_plugin_id",
        "permissions",
        ["plugin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_permissions_plugin_id", table_name="permissions")
    op.drop_column("permissions", "plugin_id")
