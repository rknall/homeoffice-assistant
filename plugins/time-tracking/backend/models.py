# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin database models."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import Base


class EntryType(str, Enum):
    """Types of time entries."""

    WORK = "work"
    VACATION = "vacation"
    SICK = "sick"
    DOCTOR_VISIT = "doctor_visit"
    PUBLIC_HOLIDAY = "public_holiday"
    COMP_TIME = "comp_time"
    UNPAID_LEAVE = "unpaid_leave"
    PARENTAL_LEAVE = "parental_leave"
    TRAINING = "training"
    OTHER = "other"


class WorkLocation(str, Enum):
    """Work location types."""

    OFFICE = "office"
    REMOTE = "remote"
    CLIENT_SITE = "client_site"
    TRAVEL = "travel"


class TimeEntry(Base):
    """Individual time entry - the core time tracking record.

    Each entry represents one of:
    - A work session (check_in/check_out pair)
    - A full-day absence (vacation, sick, etc. - no times needed)
    - A partial day (doctor visit with times)

    Multiple entries per day per company are allowed, enabling:
    - Morning session: 09:00-12:30
    - Afternoon session: 13:30-17:00
    """

    __tablename__ = "tt_time_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Entry type classification
    entry_type = Column(String(30), nullable=False, default=EntryType.WORK.value)

    # Working times (nullable for non-work entries like vacation)
    check_in = Column(Time, nullable=True)
    check_out = Column(Time, nullable=True)
    timezone = Column(String(50), nullable=True)

    # Location and notes
    work_location = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)

    # Submission tracking (for locking submitted timesheets)
    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tt_timesheet_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_tt_entry_user_date", "user_id", "date"),
        Index("idx_tt_entry_company_date", "company_id", "date"),
        Index("idx_tt_entry_submission", "submission_id"),
    )

    @property
    def is_open(self) -> bool:
        """Check if this is an open work entry (checked in but not out)."""
        return (
            self.entry_type == EntryType.WORK.value
            and self.check_in is not None
            and self.check_out is None
        )

    @property
    def gross_minutes(self) -> int | None:
        """Calculate gross minutes for this entry."""
        if not self.check_in or not self.check_out:
            return None

        in_minutes = self.check_in.hour * 60 + self.check_in.minute
        out_minutes = self.check_out.hour * 60 + self.check_out.minute

        # Handle overnight shifts
        if out_minutes < in_minutes:
            out_minutes += 24 * 60

        return out_minutes - in_minutes

    @property
    def gross_hours(self) -> float | None:
        """Calculate gross hours for this entry."""
        minutes = self.gross_minutes
        return minutes / 60 if minutes is not None else None

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<TimeEntry(id={self.id}, date={self.date}, "
            f"type={self.entry_type}, in={self.check_in}, out={self.check_out})>"
        )


class LeaveBalance(Base):
    """Track vacation/leave entitlements per year."""

    __tablename__ = "tt_leave_balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    year = Column(Integer, nullable=False)

    # Vacation
    vacation_entitled = Column(Float, default=25.0, nullable=False)
    vacation_carryover = Column(Float, default=0.0, nullable=False)
    vacation_taken = Column(Float, default=0.0, nullable=False)

    # Comp time
    comp_time_balance = Column(Float, default=0.0, nullable=False)

    # Statistics
    sick_days_taken = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "company_id", "year", name="uq_tt_user_company_year"
        ),
    )

    @property
    def vacation_remaining(self) -> float:
        """Calculate remaining vacation days."""
        return self.vacation_entitled + self.vacation_carryover - self.vacation_taken

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<LeaveBalance(id={self.id}, year={self.year})>"


class TimesheetSubmission(Base):
    """Track when timesheets are submitted to employers."""

    __tablename__ = "tt_timesheet_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # month, week, custom

    # Submission
    submitted_at = Column(DateTime, nullable=False)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    sent_to_email = Column(String(254), nullable=False)

    # Attachments
    pdf_path = Column(String(500), nullable=True)
    entry_ids = Column(Text, nullable=False)  # JSON array of UUIDs

    # Status
    status = Column(String(20), default="sent", nullable=False)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<TimesheetSubmission(id={self.id}, "
            f"period={self.period_start} to {self.period_end})>"
        )


class CompanyTimeSettings(Base):
    """Plugin-specific settings per company."""

    __tablename__ = "tt_company_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Regional settings
    timezone = Column(String(50), default="Europe/Vienna", nullable=False)
    country_code = Column(String(2), default="AT", nullable=False)

    # Leave settings
    vacation_days_per_year = Column(Float, default=25.0, nullable=False)

    # Overtime settings
    daily_overtime_threshold = Column(Float, default=8.0, nullable=False)
    weekly_overtime_threshold = Column(Float, default=40.0, nullable=False)
    overtime_threshold_hours = Column(Float, default=0.0, nullable=False)
    comp_time_warning_balance = Column(Float, default=40.0, nullable=False)

    # Submission settings
    default_timesheet_contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company_contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    lock_period_days = Column(Integer, default=7, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<CompanyTimeSettings(id={self.id}, company_id={self.company_id})>"


class CustomHoliday(Base):
    """User-defined holidays."""

    __tablename__ = "tt_custom_holidays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )

    date = Column(Date, nullable=False)
    name = Column(String(200), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<CustomHoliday(id={self.id}, date={self.date}, name={self.name!r})>"


class UserTimePreferences(Base):
    """User preferences for time tracking (last used values)."""

    __tablename__ = "tt_user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )

    last_company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_work_location = Column(String(30), nullable=True)
    last_check_in = Column(Time, nullable=True)
    last_check_out = Column(Time, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<UserTimePreferences(id={self.id}, user_id={self.user_id})>"
