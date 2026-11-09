# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time-tracking services against a real database.

The pure calculations are tested elsewhere; these tests run the service
classes through the shared session so queries, commits and the lock rules are
exercised.
"""

import importlib
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, User
from src.models.enums import CompanyType
from src.security import get_password_hash

services = importlib.import_module("plugins.time-tracking.backend.services")
models = importlib.import_module("plugins.time-tracking.backend.models")

WORK = models.EntryType.WORK.value
VACATION = models.EntryType.VACATION.value


@pytest.fixture
def user(tt_client: TestClient, db_session: Session) -> User:
    """Create a user; ``tt_client`` creates the plugin tables."""
    row = User(
        username="svc-user",
        email="svc-user@example.com",
        hashed_password=get_password_hash("svc-user-secret-123"),
        is_active=True,
    )
    db_session.add(row)
    db_session.commit()
    return row


@pytest.fixture
def company(db_session: Session, user: User) -> Company:
    """Create one employer company."""
    row = Company(name="Svc Co", type=CompanyType.EMPLOYER)
    db_session.add(row)
    db_session.commit()
    return row


def test_create_entry_rounds_times_in_employer_favor(
    db_session: Session, user: User
) -> None:
    """Check-in rounds up and check-out rounds down to five minutes."""
    service = services.TimeEntryService(db_session)
    entry = service.create_entry(
        user.id,
        date(2024, 1, 10),
        WORK,
        check_in=time(9, 1),
        check_out=time(12, 59),
    )
    assert entry.check_in == time(9, 5)
    assert entry.check_out == time(12, 55)
    assert service.get_entry(entry.id, user.id) is not None


def test_overlapping_entry_is_rejected(db_session: Session, user: User) -> None:
    """A second work session inside the first raises ValueError."""
    service = services.TimeEntryService(db_session)
    day = date(2024, 1, 10)
    service.create_entry(user.id, day, WORK, check_in=time(9, 0), check_out=time(12, 0))
    with pytest.raises(ValueError):
        service.create_entry(
            user.id, day, WORK, check_in=time(11, 0), check_out=time(13, 0)
        )
    service.create_entry(
        user.id, day, WORK, check_in=time(13, 0), check_out=time(17, 0)
    )
    assert len(service.get_entries_for_date(user.id, day)) == 2


def test_half_day_only_for_single_day_vacation(db_session: Session, user: User) -> None:
    """Half-day is dropped for work and refused for multi-day vacation."""
    service = services.TimeEntryService(db_session)
    day = date(2024, 2, 5)
    work = service.create_entry(user.id, day, WORK, is_half_day=True)
    assert work.is_half_day is False
    with pytest.raises(ValueError):
        service.create_entry(
            user.id,
            day,
            VACATION,
            end_date=day + timedelta(days=2),
            is_half_day=True,
        )


def test_check_in_twice_and_check_out_flow(db_session: Session, user: User) -> None:
    """Check-in opens an entry, a second check-in fails, check-out closes it."""
    service = services.TimeEntryService(db_session)
    with pytest.raises(ValueError):
        service.check_out(user.id)
    opened = service.check_in(user.id, check_in_time=time(8, 0))
    assert service.has_open_entry(user.id)
    with pytest.raises(ValueError):
        service.check_in(user.id, check_in_time=time(8, 30))
    closed = service.check_out(user.id, check_out_time=time(16, 0), notes="done")
    assert closed.id == opened.id
    assert closed.check_out == time(16, 0)
    assert closed.notes == "done"
    assert not service.has_open_entry(user.id)


def test_update_and_delete_are_scoped_to_owner(db_session: Session, user: User) -> None:
    """Another user's entry id is treated as not found."""
    service = services.TimeEntryService(db_session)
    entry = service.create_entry(
        user.id, date.today(), WORK, check_in=time(9, 0), check_out=time(10, 0)
    )
    other = User(
        username="other-svc",
        email="other-svc@example.com",
        hashed_password=get_password_hash("other-svc-secret-123"),
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    assert service.update_entry(entry.id, other.id, notes="x") is None
    assert service.delete_entry(entry.id, other.id) is False
    updated = service.update_entry(entry.id, user.id, notes="mine")
    assert updated is not None and updated.notes == "mine"
    assert service.delete_entry(entry.id, user.id) is True
    assert service.get_entry(entry.id, user.id) is None


def test_old_entry_is_locked(db_session: Session, user: User) -> None:
    """An entry past the month-end lock window cannot be edited or deleted."""
    service = services.TimeEntryService(db_session)
    entry = service.create_entry(
        user.id, date(2020, 1, 15), WORK, check_in=time(9, 0), check_out=time(10, 0)
    )
    assert service.is_entry_locked(entry)
    with pytest.raises(ValueError):
        service.update_entry(entry.id, user.id, notes="late")
    with pytest.raises(ValueError):
        service.delete_entry(entry.id, user.id)


def test_lock_period_follows_company_settings(
    db_session: Session, user: User, company: Company
) -> None:
    """A long lock period keeps last month's entry editable."""
    service = services.TimeEntryService(db_session)
    settings = services.CompanySettingsService(db_session)
    first_of_month = date.today().replace(day=1)
    last_month = first_of_month - timedelta(days=1)
    entry = service.create_entry(
        user.id,
        last_month.replace(day=1),
        WORK,
        company_id=company.id,
        check_in=time(9, 0),
        check_out=time(10, 0),
    )
    settings.update_settings(company.id, lock_period_days=0)
    if date.today() > last_month:
        assert service.is_entry_locked(entry)
    settings.update_settings(company.id, lock_period_days=60)
    assert not service.is_entry_locked(entry)


def test_leave_balance_created_with_defaults_and_carryover(
    db_session: Session, user: User
) -> None:
    """A new balance has 25 days; the next year carries the remainder."""
    service = services.LeaveBalanceService(db_session)
    first = service.get_balance(user.id, 2023)
    assert first.vacation_entitled == 25.0
    assert first.vacation_carryover == 0.0
    assert service.get_balance(user.id, 2023).id == first.id
    updated = service.update_balance(user.id, 2023, vacation_entitled=30.0)
    assert updated.vacation_entitled == 30.0
    following = service.get_balance(user.id, 2024)
    assert following.vacation_carryover == first.vacation_remaining


def test_balance_uses_company_vacation_days(
    db_session: Session, user: User, company: Company
) -> None:
    """A new balance takes the company's vacation days per year."""
    services.CompanySettingsService(db_session).update_settings(
        company.id, vacation_days_per_year=28.0
    )
    balance = services.LeaveBalanceService(db_session).get_balance(
        user.id, 2023, company.id
    )
    assert balance.vacation_entitled == 28.0


def test_comp_time_balance_counts_overtime_and_comp_days(
    db_session: Session, user: User
) -> None:
    """Hours over eight on a weekday add up; a comp-time day subtracts eight."""
    service = services.TimeEntryService(db_session)
    leave = services.LeaveBalanceService(db_session)
    monday = date(2024, 1, 8)
    service.create_entry(
        user.id, monday, WORK, check_in=time(8, 0), check_out=time(18, 0)
    )
    assert leave.calculate_comp_time_balance(user.id) == pytest.approx(2.0)
    service.create_entry(user.id, date(2024, 1, 9), models.EntryType.COMP_TIME.value)
    assert leave.calculate_comp_time_balance(user.id) == pytest.approx(-6.0)


def test_company_settings_get_or_create_and_update(
    db_session: Session, company: Company
) -> None:
    """Settings are created on demand with defaults and updated in place."""
    service = services.CompanySettingsService(db_session)
    assert service.get_settings(company.id) is None
    created = service.get_or_create_settings(company.id)
    assert created.timezone == "Europe/Vienna"
    assert created.lock_period_days == 7
    updated = service.update_settings(company.id, lock_period_days=14, timezone=None)
    assert updated.id == created.id
    assert updated.lock_period_days == 14
    assert updated.timezone == "Europe/Vienna"
