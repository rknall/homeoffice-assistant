"""add_email_templates

Revision ID: 1f81bbd6d0da
Revises: a28421a30ffa
Create Date: 2025-11-29 11:10:03.472943

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1f81bbd6d0da'
down_revision: str | None = 'a28421a30ffa'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('email_templates',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('reason', sa.String(length=50), nullable=False),
    sa.Column('company_id', sa.String(length=36), nullable=True),
    sa.Column('subject', sa.String(length=500), nullable=False),
    sa.Column('body_html', sa.Text(), nullable=False),
    sa.Column('body_text', sa.Text(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_email_templates_company_id'),
        'email_templates',
        ['company_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_email_templates_reason'),
        'email_templates',
        ['reason'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_email_templates_reason'), table_name='email_templates')
    op.drop_index(op.f('ix_email_templates_company_id'), table_name='email_templates')
    op.drop_table('email_templates')
