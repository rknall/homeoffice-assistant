# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Currency cache model for storing exchange rates."""

import uuid as uuid_lib
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class CurrencyCache(Base):
    """Cache for exchange rates from external API."""

    __tablename__ = "currency_cache"
    __table_args__ = (
        UniqueConstraint(
            "base_currency", "target_currency", "rate_date", name="uq_currency_rate"
        ),
    )

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
