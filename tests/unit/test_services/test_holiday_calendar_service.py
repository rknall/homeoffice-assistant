# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for holiday_calendar_service."""

from datetime import date

import pytest

from src.schemas.holiday_calendar import (
    HolidayCalendarCreate,
    HolidayCalendarUpdate,
)
from src.services import holiday_calendar_service as service


def make_calendar(db_session, user, country="AT", subdivision=None, label="AT"):
    return service.create_holiday_calendar(
        db_session,
        user.id,
        HolidayCalendarCreate(
            country_code=country, subdivision=subdivision, display_label=label
        ),
    )


def test_create_normalises_codes_to_upper_case(db_session, test_user):
    calendar = make_calendar(db_session, test_user, "at", "9", "Vienna")

    assert calendar.country_code == "AT"
    assert calendar.subdivision == "9"
    assert calendar.user_id == test_user.id


def test_list_is_scoped_to_user_and_sorted_by_label(db_session, test_user, second_user):
    make_calendar(db_session, test_user, "DE", None, "Zed")
    make_calendar(db_session, test_user, "AT", None, "Alpha")
    make_calendar(db_session, second_user, "FR", None, "Foreign")

    labels = [
        c.display_label for c in service.get_holiday_calendars(db_session, test_user.id)
    ]

    assert labels == ["Alpha", "Zed"]


def test_get_by_user_rejects_other_owner(db_session, test_user, second_user):
    calendar = make_calendar(db_session, test_user)

    assert (
        service.get_holiday_calendar_by_user(db_session, test_user.id, calendar.id)
        == calendar
    )
    assert (
        service.get_holiday_calendar_by_user(db_session, second_user.id, calendar.id)
        is None
    )


def test_update_changes_label_and_delete_removes(db_session, test_user):
    calendar = make_calendar(db_session, test_user)

    updated = service.update_holiday_calendar(
        db_session, calendar, HolidayCalendarUpdate(display_label="Home")
    )
    assert updated.display_label == "Home"
    assert updated.country_code == "AT"

    calendar_id = calendar.id
    service.delete_holiday_calendar(db_session, calendar)
    assert (
        service.get_holiday_calendar_by_user(db_session, test_user.id, calendar_id)
        is None
    )


def test_holidays_for_date_range_filters_and_sorts(db_session, test_user):
    at = make_calendar(db_session, test_user, "AT", None, "AT")
    de = make_calendar(db_session, test_user, "DE", None, "DE")

    entries = service.get_holidays_for_date_range(
        [at, de], date(2025, 12, 24), date(2025, 12, 31)
    )

    dates = [e.date for e in entries]
    assert dates == sorted(dates)
    assert all(date(2025, 12, 24) <= d <= date(2025, 12, 31) for d in dates)
    christmas = {e.display_label for e in entries if e.date == date(2025, 12, 25)}
    assert christmas == {"AT", "DE"}


def test_holidays_for_date_range_spans_years(db_session, test_user):
    at = make_calendar(db_session, test_user, "AT", None, "AT")

    entries = service.get_holidays_for_date_range(
        [at], date(2025, 12, 31), date(2026, 1, 1)
    )

    assert date(2026, 1, 1) in [e.date for e in entries]


def test_holidays_for_date_range_skips_invalid_country(db_session, test_user):
    bad = make_calendar(db_session, test_user, "ZZ", None, "ZZ")
    good = make_calendar(db_session, test_user, "AT", None, "AT")

    entries = service.get_holidays_for_date_range(
        [bad, good], date(2025, 12, 25), date(2025, 12, 25)
    )

    assert [e.display_label for e in entries] == ["AT"]


def test_holidays_for_date_range_uses_subdivision(db_session, test_user):
    bavaria = make_calendar(db_session, test_user, "DE", "BY", "BY")
    berlin = make_calendar(db_session, test_user, "DE", "BE", "BE")

    entries = service.get_holidays_for_date_range(
        [bavaria, berlin], date(2025, 1, 6), date(2025, 1, 6)
    )

    # Epiphany is a public holiday in Bavaria only.
    assert [e.display_label for e in entries] == ["BY"]


def test_holidays_preview_defaults_label_and_year():
    entries = service.get_holidays_preview("AT", None, 2025)

    assert entries
    assert all(e.date.year == 2025 for e in entries)
    assert {e.display_label for e in entries} == {"AT"}
    labelled = service.get_holidays_preview("DE", "BY", 2025)
    assert {e.display_label for e in labelled} == {"DE-BY"}


def test_holidays_preview_unknown_region_raises():
    with pytest.raises(service.UnknownHolidayRegionError):
        service.get_holidays_preview("XX", None, 2025)
    with pytest.raises(service.UnknownHolidayRegionError):
        service.get_holidays_preview("AT", "ZZ", 2025)


def test_supported_countries_contain_priority_country():
    countries = service.get_supported_countries()

    codes = [c.code for c in countries]
    assert "AT" in codes


def test_country_names_come_from_the_library():
    countries = {c.code: c.name for c in service.get_supported_countries()}

    assert countries["AT"] == "Austria"
    assert countries["GB"] == "United Kingdom"
    assert countries["US"] == "United States"
    assert next(iter(countries)) == "AT"


def test_public_holidays_for_one_year():
    result = service.get_public_holidays("AT", 2025)

    assert date(2025, 12, 25) in result
    assert date(2025, 1, 6) in result
