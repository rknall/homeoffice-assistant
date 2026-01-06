# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event (trip) model."""

import uuid as uuid_lib
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.company import Company
    from src.models.contact import Contact
    from src.models.document_reference import DocumentReference
    from src.models.expense import Expense
    from src.models.expense_submission import ExpenseSubmission
    from src.models.note import Note
    from src.models.photo_reference import PhotoReference
    from src.models.todo import Todo
    from src.models.user import User


class Event(Base, TimestampMixin):
    """Event (trip) model."""

    __tablename__ = "events"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    user_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Note: status is computed from dates in response schemas (not stored)
    external_tag: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    # Custom field value stored in Paperless (the actual value, not field ID)
    paperless_custom_field_value: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # Location fields
    city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Cover image fields (from Unsplash)
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_photographer_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    cover_photographer_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    cover_image_position_y: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=50
    )  # 0-100, vertical position %

    # Report tracking
    report_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="events")
    company: Mapped[Company] = relationship("Company", back_populates="events")
    expenses: Mapped[list[Expense]] = relationship(
        "Expense",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    contacts: Mapped[list[Contact]] = relationship(
        "Contact",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    notes: Mapped[list[Note]] = relationship(
        "Note",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    todos: Mapped[list[Todo]] = relationship(
        "Todo",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    photo_references: Mapped[list[PhotoReference]] = relationship(
        "PhotoReference",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[list[ExpenseSubmission]] = relationship(
        "ExpenseSubmission",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    document_references: Mapped[list[DocumentReference]] = relationship(
        "DocumentReference",
        back_populates="event",
        cascade="all, delete-orphan",
    )
