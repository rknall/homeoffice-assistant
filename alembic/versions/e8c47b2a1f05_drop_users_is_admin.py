"""Drop users.is_admin

Administrator rights come only from the Global Admin role assignment; the
column was no longer read anywhere.

Revision ID: e8c47b2a1f05
Revises: 5b2d9f3e6a18
Create Date: 2026-11-08 23:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8c47b2a1f05"
down_revision: str | None = "5b2d9f3e6a18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen at this revision; migrations do not import application code.
GLOBAL_ADMIN_ROLE = "Global Admin"


def upgrade() -> None:
    """Drop the is_admin column."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_admin")


def downgrade() -> None:
    """Re-add is_admin, set for users holding Global Admin globally."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    op.execute(
        sa.text(
            "UPDATE users SET is_admin = true WHERE id IN ("
            "SELECT ur.user_id FROM user_roles ur JOIN roles r ON r.id = ur.role_id"
            " WHERE r.name = :role AND ur.company_id IS NULL)"
        ).bindparams(role=GLOBAL_ADMIN_ROLE)
    )
