# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Holiday calendar model for national holiday configuration."""

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class HolidayCalendar(Base, TimestampMixin):
    """User configuration for national holiday display.

    Stores the country and optional subdivision (state/region) for
    displaying national holidays in the calendar. Users can configure
    multiple countries/regions.
    """

    __tablename__ = "holiday_calendars"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    user_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # ISO 3166-1 alpha-2 country code (e.g., "AT", "DE", "US")
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    # ISO 3166-2 subdivision code without country prefix (e.g., "BY" for Bavaria)
    # Nullable - if not set, national holidays only
    subdivision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Display label shown in calendar (e.g., "AT", "DE-BY")
    display_label: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="holiday_calendars",
    )
