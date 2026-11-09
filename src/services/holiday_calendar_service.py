# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Holiday calendar service for managing national holiday configurations."""

import logging
import re
import uuid
from datetime import date

import holidays
from holidays import registry
from holidays.holiday_base import HolidayBase
from sqlalchemy.orm import Session

from src.models import HolidayCalendar
from src.schemas.holiday_calendar import (
    CountryInfo,
    HolidayCalendarCreate,
    HolidayCalendarUpdate,
    HolidayEntry,
)

logger = logging.getLogger(__name__)

PRIORITY_COUNTRIES = (
    "AT",
    "DE",
    "CH",
    "IT",
    "FR",
    "ES",
    "GB",
    "NL",
    "BE",
    "PL",
    "CZ",
    "HU",
    "SK",
    "SI",
    "HR",
    "RO",
    "BG",
    "GR",
    "PT",
    "DK",
    "SE",
    "NO",
    "FI",
    "IE",
    "US",
    "CA",
    "AU",
    "NZ",
    "JP",
    "IN",
)


class UnknownHolidayRegionError(ValueError):
    """Raised for a country or subdivision the holidays library does not know."""


def load_holidays(
    country_code: str, subdivision: str | None, years: list[int] | int
) -> HolidayBase:
    """Load the holidays of a country and optional subdivision.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.
        subdivision: Optional subdivision code.
        years: Year or years to load.

    Returns:
        The holidays for the requested years.

    Raises:
        UnknownHolidayRegionError: If the country or subdivision is unknown.
    """
    try:
        return holidays.country_holidays(country_code, subdiv=subdivision, years=years)
    except NotImplementedError as exc:
        raise UnknownHolidayRegionError(str(exc)) from exc


def validate_region(country_code: str, subdivision: str | None) -> None:
    """Check that a country and optional subdivision exist in the library.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.
        subdivision: Optional subdivision code.

    Raises:
        UnknownHolidayRegionError: If the country or subdivision is unknown.
    """
    load_holidays(country_code, subdivision, [date.today().year])


def get_holiday_calendars(db: Session, user_id: uuid.UUID) -> list[HolidayCalendar]:
    """Get all holiday calendar configurations for a user."""
    return (
        db.query(HolidayCalendar)
        .filter(HolidayCalendar.user_id == user_id)
        .order_by(HolidayCalendar.display_label)
        .all()
    )


def get_holiday_calendar_by_user(
    db: Session, user_id: uuid.UUID, calendar_id: uuid.UUID
) -> HolidayCalendar | None:
    """Get a holiday calendar by ID, ensuring it belongs to the specified user."""
    return (
        db.query(HolidayCalendar)
        .filter(
            HolidayCalendar.id == calendar_id,
            HolidayCalendar.user_id == user_id,
        )
        .first()
    )


def create_holiday_calendar(
    db: Session, user_id: uuid.UUID, data: HolidayCalendarCreate
) -> HolidayCalendar:
    """Create a new holiday calendar configuration for a user."""
    calendar = HolidayCalendar(
        user_id=user_id,
        country_code=data.country_code,
        subdivision=data.subdivision,
        display_label=data.display_label,
    )
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


def update_holiday_calendar(
    db: Session, calendar: HolidayCalendar, data: HolidayCalendarUpdate
) -> HolidayCalendar:
    """Update an existing holiday calendar configuration."""
    if data.display_label is not None:
        calendar.display_label = data.display_label

    db.commit()
    db.refresh(calendar)
    return calendar


def delete_holiday_calendar(db: Session, calendar: HolidayCalendar) -> None:
    """Delete a holiday calendar configuration."""
    db.delete(calendar)
    db.commit()


def get_holidays_for_date_range(
    calendars: list[HolidayCalendar],
    start_date: date,
    end_date: date,
) -> list[HolidayEntry]:
    """Get all holidays for the configured calendars within a date range.

    Args:
        calendars: List of HolidayCalendar configurations
        start_date: Start of the date range (inclusive)
        end_date: End of the date range (inclusive)

    Returns:
        List of HolidayEntry objects for all matching holidays
    """
    result: list[HolidayEntry] = []

    # Get unique years in the range
    years = list(range(start_date.year, end_date.year + 1))

    for calendar in calendars:
        try:
            country_holidays = load_holidays(
                calendar.country_code, calendar.subdivision, years
            )
        except UnknownHolidayRegionError:
            # Stored calendars may name regions the library no longer supports.
            logger.debug(
                "Skipping invalid country/subdivision: %s/%s",
                calendar.country_code,
                calendar.subdivision,
            )
            continue

        for holiday_date, holiday_name in sorted(country_holidays.items()):
            if start_date <= holiday_date <= end_date:
                result.append(
                    HolidayEntry(
                        date=holiday_date,
                        name=holiday_name,
                        country_code=calendar.country_code,
                        subdivision=calendar.subdivision,
                        display_label=calendar.display_label,
                    )
                )

    # Sort by date
    result.sort(key=lambda x: x.date)
    return result


def get_supported_countries() -> list[CountryInfo]:
    """Get all supported countries with their subdivisions.

    Priority countries come first, the remaining ones alphabetically.

    Returns:
        List of CountryInfo objects with country codes, names, and subdivisions
    """
    supported = holidays.list_supported_countries()
    others = sorted(
        code for code in supported if code not in PRIORITY_COUNTRIES and len(code) == 2
    )
    result: list[CountryInfo] = []
    for country_code in [*PRIORITY_COUNTRIES, *others]:
        if country_code not in supported:
            continue
        country_class = getattr(holidays, country_code, None)
        if country_class is None:
            continue
        result.append(
            CountryInfo(
                code=country_code,
                name=_get_country_name(country_code),
                subdivisions=list(getattr(country_class, "subdivisions", [])),
            )
        )
    return result


def get_public_holidays(
    country_code: str, year: int, subdivision: str | None = None
) -> dict[date, str]:
    """Get the public holidays of a country for one year.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.
        year: The year.
        subdivision: Optional subdivision code.

    Returns:
        Dictionary mapping dates to holiday names.

    Raises:
        UnknownHolidayRegionError: If the country or subdivision is unknown.
    """
    return dict(load_holidays(country_code, subdivision, year).items())


def get_holidays_preview(
    country_code: str,
    subdivision: str | None,
    year: int | None = None,
) -> list[HolidayEntry]:
    """Get a preview of holidays for a country/subdivision.

    Args:
        country_code: ISO 3166-1 alpha-2 country code
        subdivision: Optional subdivision code
        year: Year to get holidays for (defaults to current year)

    Returns:
        List of HolidayEntry objects

    Raises:
        UnknownHolidayRegionError: If the country or subdivision is unknown.
    """
    if year is None:
        year = date.today().year

    country_holidays = load_holidays(country_code, subdivision, [year])
    display_label = f"{country_code}-{subdivision}" if subdivision else country_code
    return [
        HolidayEntry(
            date=holiday_date,
            name=holiday_name,
            country_code=country_code,
            subdivision=subdivision,
            display_label=display_label,
        )
        for holiday_date, holiday_name in sorted(country_holidays.items())
    ]


def _get_country_name(country_code: str) -> str:
    """Get a human-readable country name from the holidays library registry."""
    for class_name, alpha2, *_ in registry.COUNTRIES.values():
        if alpha2 == country_code:
            return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", class_name)
    return country_code
