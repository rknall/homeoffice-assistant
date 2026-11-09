"""add_paperless_custom_field_value_to_events

Revision ID: d3cd5fec2518
Revises: 5407cda97a67
Create Date: 2025-11-28 13:59:06.128975

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3cd5fec2518"
down_revision: str | None = "5407cda97a67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("paperless_custom_field_value", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "paperless_custom_field_value")
