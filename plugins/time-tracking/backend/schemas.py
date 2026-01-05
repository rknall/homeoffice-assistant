# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin Pydantic schemas."""

from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, ConfigDict


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


# --- Time Entry Schemas ---


class TimeEntryBase(BaseModel):
    """Base schema for time entries."""

    date: date
    company_id: str | None = None
    entry_type: EntryType = EntryType.WORK
    check_in: time | None = None
    check_out: time | None = None
    timezone: str | None = None
    work_location: WorkLocation | None = None
    notes: str | None = None


class TimeEntryCreate(TimeEntryBase):
    """Schema for creating a time entry."""

    pass


class TimeEntryUpdate(BaseModel):
    """Schema for updating a time entry."""

    company_id: str | None = None
    entry_type: EntryType | None = None
    check_in: time | None = None
    check_out: time | None = None
    timezone: str | None = None
    work_location: WorkLocation | None = None
    notes: str | None = None


class TimeEntryResponse(BaseModel):
    """Schema for time entry responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    date: date
    company_id: str | None = None
    company_name: str | None = None  # For display
    entry_type: EntryType
    check_in: time | None = None
    check_out: time | None = None
    timezone: str | None = None
    work_location: WorkLocation | None = None
    notes: str | None = None
    submission_id: str | None = None
    is_locked: bool = False
    # Calculated fields
    is_open: bool = False
    gross_minutes: int | None = None
    gross_hours: float | None = None
    created_at: datetime
    updated_at: datetime


class ComplianceWarning(BaseModel):
    """Schema for compliance warnings (calculated on-the-fly)."""

    level: str  # "info", "warning", "error"
    code: str
    message: str
    requires_explanation: bool = False
    law_reference: str | None = None


# --- Daily Summary Schema ---


class DailySummary(BaseModel):
    """Aggregated data for a single day."""

    date: date
    entries: list[TimeEntryResponse]
    total_gross_hours: float
    total_net_hours: float
    break_minutes: int
    entry_count: int
    has_open_entry: bool
    warnings: list[ComplianceWarning] = []


# --- Leave Balance Schemas ---


class LeaveBalanceBase(BaseModel):
    """Base schema for leave balances."""

    year: int
    company_id: str | None = None
    vacation_entitled: float = 25.0
    vacation_carryover: float = 0.0


class LeaveBalanceUpdate(BaseModel):
    """Schema for updating leave balance."""

    vacation_entitled: float | None = None
    vacation_carryover: float | None = None


class LeaveBalanceResponse(BaseModel):
    """Schema for leave balance responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    company_id: str | None = None
    year: int
    vacation_entitled: float
    vacation_carryover: float
    vacation_taken: float
    vacation_planned: float = 0.0
    vacation_remaining: float
    comp_time_balance: float
    sick_days_taken: int
    created_at: datetime
    updated_at: datetime


# --- Timesheet Submission Schemas ---


class TimesheetSubmissionCreate(BaseModel):
    """Schema for creating a timesheet submission."""

    company_id: str
    period_start: date
    period_end: date
    period_type: str = "month"
    contact_id: str | None = None
    notes: str | None = None


class TimesheetSubmissionResponse(BaseModel):
    """Schema for timesheet submission responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    user_id: str
    period_start: date
    period_end: date
    period_type: str
    submitted_at: datetime
    submitted_by: str
    sent_to_email: str
    pdf_path: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


# --- Company Time Settings Schemas ---


class CompanyTimeSettingsBase(BaseModel):
    """Base schema for company time settings."""

    timezone: str = "Europe/Vienna"
    country_code: str = "AT"
    vacation_days_per_year: float = 25.0
    daily_overtime_threshold: float = 8.0
    weekly_overtime_threshold: float = 40.0
    overtime_threshold_hours: float = 0.0
    comp_time_warning_balance: float = 40.0
    default_timesheet_contact_id: str | None = None
    lock_period_days: int = 7


class CompanyTimeSettingsUpdate(BaseModel):
    """Schema for updating company time settings."""

    timezone: str | None = None
    country_code: str | None = None
    vacation_days_per_year: float | None = None
    daily_overtime_threshold: float | None = None
    weekly_overtime_threshold: float | None = None
    overtime_threshold_hours: float | None = None
    comp_time_warning_balance: float | None = None
    default_timesheet_contact_id: str | None = None
    lock_period_days: int | None = None


class CompanyTimeSettingsResponse(CompanyTimeSettingsBase):
    """Schema for company time settings responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime


# --- Custom Holiday Schemas ---


class CustomHolidayCreate(BaseModel):
    """Schema for creating a custom holiday."""

    date: date
    name: str
    company_id: str | None = None


class CustomHolidayResponse(BaseModel):
    """Schema for custom holiday responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    company_id: str | None = None
    date: date
    name: str
    created_at: datetime
    updated_at: datetime


class PublicHolidayResponse(BaseModel):
    """Schema for public holiday responses."""

    date: date
    name: str


# --- Report Schemas ---


class MonthlyReportRequest(BaseModel):
    """Request schema for monthly report."""

    year: int
    month: int
    company_id: str | None = None


class MonthlyReportResponse(BaseModel):
    """Response schema for monthly report."""

    year: int
    month: int
    company_id: str | None = None
    company_name: str | None = None
    user_name: str
    total_work_days: int
    total_gross_hours: float
    total_net_hours: float
    total_break_minutes: int
    overtime_hours: float
    vacation_days: int
    sick_days: int
    comp_time_days: int
    public_holiday_days: int
    entries: list[TimeEntryResponse]
    daily_summaries: list[DailySummary] = []


class OvertimeReportResponse(BaseModel):
    """Response schema for overtime report."""

    period_start: date
    period_end: date
    company_id: str | None = None
    total_overtime_hours: float
    comp_time_earned: float
    comp_time_taken: float
    comp_time_balance: float
    weekly_breakdown: list[dict]


# --- Quick Action Schemas ---


class CheckInRequest(BaseModel):
    """Request schema for check-in."""

    company_id: str | None = None
    work_location: WorkLocation | None = None
    notes: str | None = None
    timezone: str | None = None


class CheckOutRequest(BaseModel):
    """Request schema for check-out."""

    notes: str | None = None
    timezone: str | None = None


class CheckInStatusResponse(BaseModel):
    """Response schema for current check-in status."""

    is_checked_in: bool = False
    open_entry: TimeEntryResponse | None = None
    today_entries: list[TimeEntryResponse] = []
    today_total_hours: float = 0.0


# --- User Preferences Schemas ---


class UserTimePreferencesResponse(BaseModel):
    """Response schema for user time preferences."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    last_company_id: str | None = None
    last_work_location: str | None = None
    last_check_in: time | None = None
    last_check_out: time | None = None


# --- Plugin Info Schema ---


class PluginInfoResponse(BaseModel):
    """Response schema for plugin info endpoint."""

    plugin_id: str
    plugin_name: str
    version: str
    entry_count: int
    current_balance: LeaveBalanceResponse | None = None
