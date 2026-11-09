# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Holiday service."""

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.services.holiday_calendar_service import get_public_holidays

from ..models import (
    CustomHoliday,
)
from .config import TimeTrackingConfig


class HolidayService:
    """Service for managing holidays."""

    def __init__(self, db: Session, config: TimeTrackingConfig | None = None) -> None:
        """Initialize the service.

        Args:
            db: Database session.
            config: Plugin settings; the built-in defaults when omitted.
        """
        self.db = db
        self.config = config or TimeTrackingConfig()
        self.validator = self.config.validator()

    def get_public_holidays(
        self,
        year: int,
        region: str | None = None,
    ) -> dict[date, str]:
        """Get public holidays of the configured country for a year.

        Args:
            year: The year.
            region: Optional region/state code.

        Returns:
            Dictionary of date to holiday name.
        """
        return get_public_holidays(self.config.default_country, year, region)

    def get_custom_holidays(
        self,
        user_id: UUID,
        year: int,
        company_id: UUID | None = None,
    ) -> list[CustomHoliday]:
        """Get user's custom holidays for a year.

        Args:
            user_id: The user ID.
            year: The year.
            company_id: Optional company filter.

        Returns:
            List of custom holidays.
        """
        query = self.db.query(CustomHoliday).filter(
            CustomHoliday.user_id == user_id,
            func.extract("year", CustomHoliday.date) == year,
        )

        if company_id:
            query = query.filter(
                (CustomHoliday.company_id == company_id)
                | (CustomHoliday.company_id.is_(None))
            )
        else:
            query = query.filter(CustomHoliday.company_id.is_(None))

        return query.all()

    def create_custom_holiday(
        self,
        user_id: UUID,
        holiday_date: date,
        name: str,
        company_id: UUID | None = None,
    ) -> CustomHoliday:
        """Create a custom holiday.

        Args:
            user_id: The user ID.
            holiday_date: The date.
            name: The holiday name.
            company_id: Optional company ID.

        Returns:
            The created holiday.
        """
        holiday = CustomHoliday(
            user_id=user_id,
            date=holiday_date,
            name=name,
            company_id=company_id,
        )
        self.db.add(holiday)
        self.db.commit()
        self.db.refresh(holiday)
        return holiday

    def is_holiday(
        self,
        check_date: date,
        user_id: UUID | None = None,
        company_id: UUID | None = None,
    ) -> tuple[bool, str | None]:
        """Check if a date is a holiday.

        Args:
            check_date: The date to check.
            user_id: Optional user for custom holidays.
            company_id: Optional company for custom holidays.

        Returns:
            Tuple of (is_holiday, holiday_name).
        """
        # Check public holidays first
        holiday_name = self.validator.get_public_holidays(check_date.year).get(
            check_date
        )
        if holiday_name:
            return True, holiday_name

        # Check custom holidays
        if user_id:
            custom = self.db.query(CustomHoliday).filter(
                CustomHoliday.user_id == user_id,
                CustomHoliday.date == check_date,
            )
            if company_id:
                custom = custom.filter(
                    (CustomHoliday.company_id == company_id)
                    | (CustomHoliday.company_id.is_(None))
                )
            custom = custom.first()
            if custom:
                return True, custom.name

        return False, None


# --- Report Service ---
