# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Holiday calendar service for managing national holiday configurations."""

import logging
import uuid
from datetime import date

import holidays
from sqlalchemy.orm import Session

from src.models import HolidayCalendar
from src.schemas.holiday_calendar import (
    CountryInfo,
    HolidayCalendarCreate,
    HolidayCalendarUpdate,
    HolidayEntry,
)

logger = logging.getLogger(__name__)


def get_holiday_calendars(db: Session, user_id: uuid.UUID) -> list[HolidayCalendar]:
    """Get all holiday calendar configurations for a user."""
    return (
        db.query(HolidayCalendar)
        .filter(HolidayCalendar.user_id == user_id)
        .order_by(HolidayCalendar.display_label)
        .all()
    )


def get_holiday_calendar(
    db: Session, calendar_id: uuid.UUID
) -> HolidayCalendar | None:
    """Get a single holiday calendar configuration by ID."""
    return (
        db.query(HolidayCalendar).filter(HolidayCalendar.id == calendar_id).first()
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
            # Get holidays for this country/subdivision
            if calendar.subdivision:
                country_holidays = holidays.country_holidays(
                    calendar.country_code,
                    subdiv=calendar.subdivision,
                    years=years,
                )
            else:
                country_holidays = holidays.country_holidays(
                    calendar.country_code,
                    years=years,
                )

            # Filter holidays within the date range
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
        except Exception:
            # Skip invalid country/subdivision combinations - this is expected
            # for unsupported country codes or subdivisions
            logger.debug(
                "Skipping invalid country/subdivision: %s/%s",
                calendar.country_code,
                calendar.subdivision,
            )
            continue

    # Sort by date
    result.sort(key=lambda x: x.date)
    return result


def get_supported_countries() -> list[CountryInfo]:
    """Get all supported countries with their subdivisions.

    Returns:
        List of CountryInfo objects with country codes, names, and subdivisions
    """
    result: list[CountryInfo] = []

    # Common countries to prioritize (European focus based on the app)
    priority_countries = [
        "AT", "DE", "CH", "IT", "FR", "ES", "GB", "NL", "BE", "PL",
        "CZ", "HU", "SK", "SI", "HR", "RO", "BG", "GR", "PT", "DK",
        "SE", "NO", "FI", "IE", "US", "CA", "AU", "NZ", "JP", "IN",
    ]

    supported = holidays.list_supported_countries()

    for country_code in priority_countries:
        if country_code in supported:
            try:
                country_class = getattr(holidays, country_code, None)
                if country_class:
                    subdivisions = (
                        list(country_class.subdivisions)
                        if hasattr(country_class, "subdivisions")
                        else []
                    )
                    # Get the country name
                    country_name = _get_country_name(country_code)
                    result.append(
                        CountryInfo(
                            code=country_code,
                            name=country_name,
                            subdivisions=subdivisions,
                        )
                    )
            except Exception:
                logger.debug("Skipping unsupported priority country: %s", country_code)
                continue

    # Add remaining countries alphabetically
    for country_code in sorted(supported.keys()):
        if country_code not in priority_countries and len(country_code) == 2:
            try:
                country_class = getattr(holidays, country_code, None)
                if country_class:
                    subdivisions = (
                        list(country_class.subdivisions)
                        if hasattr(country_class, "subdivisions")
                        else []
                    )
                    country_name = _get_country_name(country_code)
                    result.append(
                        CountryInfo(
                            code=country_code,
                            name=country_name,
                            subdivisions=subdivisions,
                        )
                    )
            except Exception:
                logger.debug("Skipping unsupported country: %s", country_code)
                continue

    return result


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
    """
    if year is None:
        year = date.today().year

    result: list[HolidayEntry] = []

    try:
        if subdivision:
            country_holidays = holidays.country_holidays(
                country_code,
                subdiv=subdivision,
                years=[year],
            )
        else:
            country_holidays = holidays.country_holidays(
                country_code,
                years=[year],
            )

        display_label = f"{country_code}-{subdivision}" if subdivision else country_code

        for holiday_date, holiday_name in sorted(country_holidays.items()):
            result.append(
                HolidayEntry(
                    date=holiday_date,
                    name=holiday_name,
                    country_code=country_code,
                    subdivision=subdivision,
                    display_label=display_label,
                )
            )
    except Exception:
        logger.debug(
            "Failed to get holidays preview for %s/%s",
            country_code,
            subdivision,
        )

    return result


def _get_country_name(country_code: str) -> str:
    """Get a human-readable country name from a country code."""
    country_names = {
        "AT": "Austria",
        "DE": "Germany",
        "CH": "Switzerland",
        "IT": "Italy",
        "FR": "France",
        "ES": "Spain",
        "GB": "United Kingdom",
        "NL": "Netherlands",
        "BE": "Belgium",
        "PL": "Poland",
        "CZ": "Czech Republic",
        "HU": "Hungary",
        "SK": "Slovakia",
        "SI": "Slovenia",
        "HR": "Croatia",
        "RO": "Romania",
        "BG": "Bulgaria",
        "GR": "Greece",
        "PT": "Portugal",
        "DK": "Denmark",
        "SE": "Sweden",
        "NO": "Norway",
        "FI": "Finland",
        "IE": "Ireland",
        "US": "United States",
        "CA": "Canada",
        "AU": "Australia",
        "NZ": "New Zealand",
        "JP": "Japan",
        "IN": "India",
        "CN": "China",
        "BR": "Brazil",
        "MX": "Mexico",
        "AR": "Argentina",
        "ZA": "South Africa",
        "RU": "Russia",
        "UA": "Ukraine",
        "TR": "Turkey",
        "IL": "Israel",
        "SA": "Saudi Arabia",
        "AE": "United Arab Emirates",
        "SG": "Singapore",
        "MY": "Malaysia",
        "TH": "Thailand",
        "ID": "Indonesia",
        "PH": "Philippines",
        "VN": "Vietnam",
        "KR": "South Korea",
        "TW": "Taiwan",
        "HK": "Hong Kong",
    }
    return country_names.get(country_code, country_code)
