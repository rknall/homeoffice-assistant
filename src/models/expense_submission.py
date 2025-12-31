# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense submission tracking models."""

import uuid as uuid_lib
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.event import Event
    from src.models.expense import Expense


class ExpenseSubmission(Base, TimestampMixin):
    """Record of an expense report submission.

    Tracks when expenses were submitted together as a batch, enabling
    incremental submission workflows where users can submit expenses
    in multiple rounds rather than all at once.
    """

    __tablename__ = "expense_submissions"

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

    # When/how submitted
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    submission_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # email, download, portal

    # Reference
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Content snapshot (totals at submission time)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    expense_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="submissions")
    items: Mapped[list[ExpenseSubmissionItem]] = relationship(
        "ExpenseSubmissionItem",
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class ExpenseSubmissionItem(Base):
    """Link between submission and individual expenses with amount snapshot.

    Captures the expense details at the time of submission, preserving
    the exact values that were submitted even if the expense is later
    edited (e.g., after rejection).
    """

    __tablename__ = "expense_submission_items"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    submission_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expense_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    expense_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expenses.id", ondelete="SET NULL"),
        nullable=True,  # Nullable in case expense is deleted
    )

    # Snapshot at submission time
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    converted_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    submission: Mapped[ExpenseSubmission] = relationship(
        "ExpenseSubmission", back_populates="items"
    )
    expense: Mapped[Expense | None] = relationship(
        "Expense", back_populates="submission_items"
    )
