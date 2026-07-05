"""Move base currency from companies to global system setting

Revision ID: c4f2a91d7e30
Revises: 35c10b543937
Create Date: 2026-07-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f2a91d7e30"
down_revision: str | None = "35c10b543937"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Seed the global setting from the most common company base_currency so
    # existing non-EUR installs keep their conversion target
    result = conn.execute(
        sa.text(
            "SELECT base_currency, COUNT(*) AS cnt FROM companies "
            "GROUP BY base_currency ORDER BY cnt DESC LIMIT 1"
        )
    ).first()
    base_currency = result[0] if result and result[0] else "EUR"

    existing = conn.execute(
        sa.text("SELECT key FROM system_settings WHERE key = 'base_currency'")
    ).first()
    if not existing:
        conn.execute(
            sa.text(
                "INSERT INTO system_settings (key, value, is_encrypted) "
                "VALUES ('base_currency', :value, 0)"
            ),
            {"value": base_currency},
        )

    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("base_currency")


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT value FROM system_settings WHERE key = 'base_currency'")
    ).first()
    base_currency = result[0] if result and result[0] else "EUR"

    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "base_currency",
                sa.String(length=3),
                nullable=False,
                server_default=base_currency,
            )
        )

    conn.execute(sa.text("DELETE FROM system_settings WHERE key = 'base_currency'"))
