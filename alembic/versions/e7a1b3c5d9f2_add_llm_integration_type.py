"""Add LLM (and missing UNSPLASH) values to the integrationtype enum

SQLite stores the enum as VARCHAR, so this is PostgreSQL-only. UNSPLASH was
added to the Python enum without a migration; it is included here so
PostgreSQL installations get both values.

Revision ID: e7a1b3c5d9f2
Revises: c4f2a91d7e30
Create Date: 2026-07-05 17:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a1b3c5d9f2"
down_revision: str | None = "c4f2a91d7e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE integrationtype ADD VALUE IF NOT EXISTS 'UNSPLASH'")
            op.execute("ALTER TYPE integrationtype ADD VALUE IF NOT EXISTS 'LLM'")


def downgrade() -> None:
    # PostgreSQL cannot remove enum values; leaving them in place is harmless.
    pass
