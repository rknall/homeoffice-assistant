"""Expense model."""
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import ExpenseCategory, ExpenseStatus, PaymentType

if TYPE_CHECKING:
    from src.models.event import Event


class Expense(Base, TimestampMixin):
    """Expense model for tracking trip expenses."""

    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
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

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="expenses")
