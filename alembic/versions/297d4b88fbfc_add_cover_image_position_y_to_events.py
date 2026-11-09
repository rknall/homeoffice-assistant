"""Add cover_image_position_y to events

Revision ID: 297d4b88fbfc
Revises: 39501bd4d6c1
Create Date: 2025-12-08 14:23:59.820882

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "297d4b88fbfc"
down_revision: str | None = "39501bd4d6c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("cover_image_position_y", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "cover_image_position_y")
