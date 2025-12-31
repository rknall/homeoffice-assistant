# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense model."""

import uuid as uuid_lib
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import ExpenseCategory, ExpenseStatus, PaymentType

if TYPE_CHECKING:
    from src.models.event import Event
    from src.models.expense_submission import ExpenseSubmissionItem


class Expense(Base, TimestampMixin):
    """Expense model for tracking trip expenses."""

    __tablename__ = "expenses"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    event_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    paperless_doc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType),
        nullable=False,
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ExpenseStatus] = mapped_column(
        Enum(ExpenseStatus),
        default=ExpenseStatus.PENDING,
        nullable=False,
    )
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Currency conversion fields
    converted_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    exchange_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), nullable=True
    )
    rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Submission tracking fields
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="expenses")
    submission_items: Mapped[list[ExpenseSubmissionItem]] = relationship(
        "ExpenseSubmissionItem",
        back_populates="expense",
    )
