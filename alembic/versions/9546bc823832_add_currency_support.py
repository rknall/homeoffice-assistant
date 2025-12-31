# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""add_currency_support

Revision ID: 9546bc823832
Revises: 52a4318c20ae
Create Date: 2025-12-30 11:53:52.399121

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9546bc823832"
down_revision: str | None = "52a4318c20ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create currency_cache table
    op.create_table(
        "currency_cache",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("target_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "base_currency", "target_currency", "rate_date", name="uq_currency_rate"
        ),
    )
    op.create_index(
        op.f("ix_currency_cache_base_currency"),
        "currency_cache",
        ["base_currency"],
        unique=False,
    )
    op.create_index(
        op.f("ix_currency_cache_rate_date"),
        "currency_cache",
        ["rate_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_currency_cache_target_currency"),
        "currency_cache",
        ["target_currency"],
        unique=False,
    )

    # Add base_currency to companies (default EUR for existing)
    op.add_column(
        "companies",
        sa.Column(
            "base_currency", sa.String(length=3), nullable=False, server_default="EUR"
        ),
    )

    # Add conversion fields to expenses
    op.add_column(
        "expenses",
        sa.Column("converted_amount", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "expenses",
        sa.Column("exchange_rate", sa.Numeric(precision=12, scale=6), nullable=True),
    )
    op.add_column("expenses", sa.Column("rate_date", sa.Date(), nullable=True))


def downgrade() -> None:
    # Remove expense conversion fields
    op.drop_column("expenses", "rate_date")
    op.drop_column("expenses", "exchange_rate")
    op.drop_column("expenses", "converted_amount")

    # Remove company base_currency
    op.drop_column("companies", "base_currency")

    # Drop currency_cache table
    op.drop_index(
        op.f("ix_currency_cache_target_currency"), table_name="currency_cache"
    )
    op.drop_index(op.f("ix_currency_cache_rate_date"), table_name="currency_cache")
    op.drop_index(op.f("ix_currency_cache_base_currency"), table_name="currency_cache")
    op.drop_table("currency_cache")
