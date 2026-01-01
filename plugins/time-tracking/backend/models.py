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
from sqlalchemy.orm import relationship

from src.models.base import Base


class DayType(str, Enum):
    """Types of days for time tracking."""

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


class TimeRecord(Base):
    """Daily time record - legal requirement."""

    __tablename__ = "tt_time_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Day classification
    day_type = Column(String(30), nullable=False, default=DayType.WORK.value)

    # Working times (nullable for non-work days)
    check_in = Column(Time, nullable=True)
    check_in_timezone = Column(String(50), nullable=True)
    check_out = Column(Time, nullable=True)
    check_out_timezone = Column(String(50), nullable=True)

    # Partial absences (for work days)
    partial_absence_type = Column(String(30), nullable=True)
    partial_absence_hours = Column(Float, nullable=True)

    # Calculated values
    gross_hours = Column(Float, nullable=True)
    break_minutes = Column(Integer, nullable=True)
    net_hours = Column(Float, nullable=True)

    # Location
    work_location = Column(String(30), nullable=True)

    # Notes and compliance
    notes = Column(Text, nullable=True)
    compliance_warnings = Column(Text, nullable=True)  # JSON array

    # Submission tracking
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

    # Relationship to time entries (individual check-in/check-out pairs)
    entries = relationship(
        "TimeEntry",
        back_populates="time_record",
        cascade="all, delete-orphan",
        order_by="TimeEntry.sequence",
    )

    __table_args__ = (
        # Allow one record per user per date per company
        UniqueConstraint(
            "user_id", "date", "company_id", name="uq_tt_user_date_company"
        ),
        Index("idx_tt_user_date_range", "user_id", "date"),
        Index("idx_tt_company_date", "company_id", "date"),
        Index("idx_tt_submission", "submission_id"),
    )

    @property
    def has_open_entry(self) -> bool:
        """Check if any entry is missing check_out (still checked in)."""
        return any(e.check_out is None for e in self.entries)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<TimeRecord(id={self.id}, date={self.date}, type={self.day_type})>"


class TimeEntry(Base):
    """Individual check-in/check-out pair within a day.

    A TimeRecord can have multiple TimeEntry rows, enabling:
    - Multiple check-in/out pairs per day (e.g., morning session, afternoon session)
    - Open check-ins (check_out is NULL until user clocks out)
    - Break calculation from gaps between entries
    """

    __tablename__ = "tt_time_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tt_time_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence = Column(Integer, nullable=False)  # 1, 2, 3... for ordering within day

    # Check-in/out times
    check_in = Column(Time, nullable=False)
    check_in_timezone = Column(String(50), nullable=True)
    check_out = Column(Time, nullable=True)  # Nullable for open/active entries
    check_out_timezone = Column(String(50), nullable=True)

    # Calculated for this entry only (in minutes for precision)
    gross_minutes = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationship back to parent record
    time_record = relationship("TimeRecord", back_populates="entries")

    __table_args__ = (
        UniqueConstraint("time_record_id", "sequence", name="uq_tt_entry_seq"),
        Index("idx_tt_entry_record", "time_record_id"),
    )

    @property
    def is_open(self) -> bool:
        """Check if this entry is still open (no check_out)."""
        return self.check_out is None

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<TimeEntry(id={self.id}, seq={self.sequence}, "
            f"in={self.check_in}, out={self.check_out})>"
        )


class TimeAllocation(Base):
    """Optional: How daily hours are split across projects."""

    __tablename__ = "tt_time_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tt_time_records.id", ondelete="CASCADE"),
        nullable=False,
    )

    hours = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)

    # Associations (all optional)
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<TimeAllocation(id={self.id}, hours={self.hours})>"


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
    record_ids = Column(Text, nullable=False)  # JSON array of UUIDs

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


class TimeRecordAudit(Base):
    """Immutable audit log for time record changes."""

    __tablename__ = "tt_time_record_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Not FK - record may be deleted but we keep audit
    time_record_id = Column(UUID(as_uuid=True), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    change_type = Column(String(20), nullable=False)  # created, updated, deleted
    old_values = Column(Text, nullable=True)  # JSON
    new_values = Column(Text, nullable=False)  # JSON
    reason = Column(Text, nullable=True)

    # Timestamp (immutable, so only created_at)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<TimeRecordAudit(id={self.id}, "
            f"record_id={self.time_record_id}, type={self.change_type})>"
        )


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
