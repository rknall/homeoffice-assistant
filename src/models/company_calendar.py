# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company calendar model for external calendar connections."""

import uuid as uuid_lib
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import CalendarType

if TYPE_CHECKING:
    from src.models.company import Company


class CompanyCalendar(Base, TimestampMixin):
    """External calendar connection for a company.

    Stores connection details for external calendars (Google, Outlook, iCal)
    that can be synced and displayed alongside HomeOffice events.
    """

    __tablename__ = "company_calendars"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    company_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    calendar_type: Mapped[CalendarType] = mapped_column(
        Enum(CalendarType),
        nullable=False,
    )
    # External calendar identifier (e.g., Google calendar ID, iCal URL)
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    # Display color for events from this calendar (hex format)
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Sync configuration
    sync_interval_minutes: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    company: Mapped[Company] = relationship(
        "Company",
        back_populates="calendars",
    )
