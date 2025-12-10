"""add_user_profile_fields

Revision ID: 22f34dad53ce
Revises: 1f81bbd6d0da
Create Date: 2025-11-29 12:31:43.762251

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '22f34dad53ce'
down_revision: str | None = '1f81bbd6d0da'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('full_name', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))
    op.add_column(
        'users',
        sa.Column('use_gravatar', sa.Boolean(), nullable=False, server_default='1'),
    )


def downgrade() -> None:
    op.drop_column('users', 'use_gravatar')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'full_name')
