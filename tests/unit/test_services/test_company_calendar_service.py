# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for company_calendar_service."""

from src.models import Company
from src.models.enums import CalendarType, CompanyType
from src.schemas.company_calendar import (
    CompanyCalendarCreate,
    CompanyCalendarUpdate,
)
from src.services import company_calendar_service as service


def make_company(db_session, name: str = "Acme") -> Company:
    company = Company(name=name, type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def make_data(name: str, **kwargs) -> CompanyCalendarCreate:
    return CompanyCalendarCreate(
        name=name,
        calendar_type=CalendarType.ICAL,
        external_id=f"https://example.com/{name}.ics",
        **kwargs,
    )


def test_create_and_get_calendar(db_session):
    company = make_company(db_session)
    calendar = service.create_calendar(
        db_session, company.id, make_data("Team", color="#abcdef")
    )

    assert calendar.company_id == company.id
    assert calendar.color == "#ABCDEF"
    assert calendar.is_active is True
    assert (
        service.get_calendar_by_company(db_session, company.id, calendar.id) == calendar
    )


def test_get_calendars_sorted_by_name_and_scoped_to_company(db_session):
    company = make_company(db_session)
    other = make_company(db_session, "Other")
    service.create_calendar(db_session, company.id, make_data("Zeta"))
    service.create_calendar(db_session, company.id, make_data("Alpha"))
    service.create_calendar(db_session, other.id, make_data("Foreign"))

    names = [c.name for c in service.get_calendars(db_session, company.id)]

    assert names == ["Alpha", "Zeta"]


def test_get_calendar_by_company_rejects_other_company(db_session):
    company = make_company(db_session)
    other = make_company(db_session, "Other")
    calendar = service.create_calendar(db_session, company.id, make_data("Team"))

    found = service.get_calendar_by_company(db_session, company.id, calendar.id)
    missing = service.get_calendar_by_company(db_session, other.id, calendar.id)

    assert found == calendar
    assert missing is None


def test_update_calendar_changes_only_set_fields(db_session):
    company = make_company(db_session)
    calendar = service.create_calendar(db_session, company.id, make_data("Team"))

    updated = service.update_calendar(
        db_session,
        calendar,
        CompanyCalendarUpdate(name="Renamed", is_active=False, color="#112233"),
    )

    assert updated.name == "Renamed"
    assert updated.is_active is False
    assert updated.color == "#112233"
    assert updated.external_id == "https://example.com/Team.ics"
    assert updated.sync_interval_minutes == 30


def test_update_last_synced_sets_timestamp(db_session):
    company = make_company(db_session)
    calendar = service.create_calendar(db_session, company.id, make_data("Team"))
    assert calendar.last_synced_at is None

    synced = service.update_last_synced(db_session, calendar)

    assert synced.last_synced_at is not None
    assert synced.last_synced_at.tzinfo is None


def test_delete_calendar(db_session):
    company = make_company(db_session)
    calendar = service.create_calendar(db_session, company.id, make_data("Team"))
    calendar_id = calendar.id

    service.delete_calendar(db_session, calendar)

    assert service.get_calendar_by_company(db_session, company.id, calendar_id) is None
