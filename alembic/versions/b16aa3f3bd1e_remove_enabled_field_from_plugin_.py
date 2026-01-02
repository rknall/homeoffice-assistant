"""Remove enabled field from plugin registration model

Revision ID: b16aa3f3bd1e
Revises: 2a3b4c5d6e7f
Create Date: 2026-01-02 13:14:40.807697

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b16aa3f3bd1e"
down_revision: str | None = "2a3b4c5d6e7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("plugin_configs", "is_enabled")


def downgrade():
    op.add_column(
        "plugin_configs",
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default=sa.true_()
        ),
    )
