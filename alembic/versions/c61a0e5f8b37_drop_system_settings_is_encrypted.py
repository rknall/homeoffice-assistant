"""Drop the unused system_settings.is_encrypted flag

The flag was written but never acted on: no setting value is encrypted.

Revision ID: c61a0e5f8b37
Revises: 9d4e7a15c0b2
Create Date: 2026-11-08 20:17:02.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c61a0e5f8b37"
down_revision: str | None = "9d4e7a15c0b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("system_settings", schema=None) as batch_op:
        batch_op.drop_column("is_encrypted")


def downgrade() -> None:
    with op.batch_alter_table("system_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_encrypted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
