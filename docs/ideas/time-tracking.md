# Time / Working Hours Tracking

## Status
Idea - Not Started (High Priority)

## Plugin Candidate
Yes - **Must be a plugin**. Time tracking is optional and adds significant complexity. Core app should work without it.

## Problem
Users need to track working hours for multiple reasons:

### Legal Requirements (Austria/EU)
Austrian labor law (Arbeitszeitgesetz) and EU Working Time Directive require:
- Daily recording of working hours (start, end, breaks)
- Documentation of rest periods
- Overtime tracking
- Maximum working hour compliance (48h/week average)
- Record retention (typically 2+ years)

### Personal Documentation
- Vacation days taken vs. entitled
- Sick leave
- Doctor visits (with time away from work)
- Public holidays
- Work-from-home vs. office days

### Optional: Project Allocation
- Which project/client did you work on (for billing or internal tracking)
- Ties into business trips (events)

## Proposed Solution

### Two-Layer Model

**Layer 1: Daily Time Record (Required)**
The core of the plugin - what labor law requires:
- Check-in / check-out times
- Break times
- Day type (work day, vacation, sick, etc.)

**Layer 2: Project Allocation (Optional)**
For users who need to track which project/client:
- Split daily hours across projects
- Associate with events/companies

## Data Model

```python
class DayType(str, Enum):
    WORK = "work"              # Normal working day
    VACATION = "vacation"       # Urlaub
    SICK = "sick"              # Krankenstand
    PUBLIC_HOLIDAY = "public_holiday"  # Feiertag
    COMP_TIME = "comp_time"    # Zeitausgleich
    UNPAID_LEAVE = "unpaid_leave"
    PARENTAL_LEAVE = "parental_leave"  # Karenz
    TRAINING = "training"      # Weiterbildung
    OTHER = "other"


class TimeRecord(Base, TimestampMixin):
    """Daily time record - the legal requirement."""
    id: UUID
    user_id: UUID
    date: date  # Unique per user

    # Day classification
    day_type: DayType

    # Working times (nullable for non-work days)
    check_in: time | None
    check_out: time | None
    break_minutes: int | None  # Total break time

    # Calculated
    gross_hours: float | None  # check_out - check_in
    net_hours: float | None    # gross - breaks

    # Location
    work_location: str | None  # office, remote, client_site, travel

    # Notes
    notes: str | None  # e.g., "Doctor appointment 10:00-11:30"

    # For absences
    absence_reason: str | None  # More detail for sick/other


class TimeAllocation(Base, TimestampMixin):
    """Optional: How daily hours are split across projects."""
    id: UUID
    time_record_id: UUID  # FK to TimeRecord

    hours: float
    description: str | None

    # Associations (all optional)
    event_id: UUID | None
    company_id: UUID | None
    project: str | None  # Free-text

    billable: bool


class LeaveBalance(Base, TimestampMixin):
    """Track vacation/leave entitlements per year."""
    id: UUID
    user_id: UUID
    year: int

    vacation_entitled: float  # Days entitled (e.g., 25)
    vacation_taken: float     # Days used
    vacation_remaining: float # Calculated

    comp_time_balance: float  # Overtime hours available as time off

    sick_days_taken: int      # For statistics, no "balance"
```

## Entry Types Summary

| Day Type | Check-in/out | Counts as Work | Reduces Vacation |
|----------|--------------|----------------|------------------|
| Work | Required | Yes | No |
| Vacation | No | No | Yes |
| Sick | No | No | No |
| Public Holiday | No | No | No |
| Comp Time | No | No | No (reduces balance) |
| Training | Optional | Depends | No |

## UI Components

### Daily Entry (Primary View)
```
┌─────────────────────────────────────────────────┐
│ Monday, December 30, 2024                       │
├─────────────────────────────────────────────────┤
│ Day Type: [Work ▼]                              │
│                                                 │
│ Check-in:  [08:30]    Check-out: [17:45]       │
│ Break:     [45] min                             │
│                                                 │
│ Net hours: 8.5h                                 │
│ Location:  [Remote ▼]                           │
│                                                 │
│ Notes: ____________________________________     │
│                                                 │
│ ─── Project Allocation (optional) ───          │
│ [+ Add allocation]                              │
│ • Company A / Project X     6.0h  [billable]   │
│ • Internal / Admin          2.5h               │
└─────────────────────────────────────────────────┘
```

### Week View
- 7-day overview
- Quick entry for simple days
- Color-coded by day type
- Weekly totals

### Month Calendar
- Calendar grid showing day types
- Click to edit
- Visual vacation/sick overview

### Leave Management
- Vacation balance display
- Request vacation (mark future days)
- Sick leave entry
- Public holiday calendar (Austria/country-specific)

### Reports
- Monthly summary (for employer)
- Overtime calculation
- Vacation balance
- Export (CSV, PDF)

## Timer Feature

Optional real-time tracking:
- Start/stop button in header
- Running timer display
- Auto-fills check-in/check-out
- Pause for breaks

## Compliance Features

### Austrian Labor Law Helpers
- Warning if > 10h/day (legal maximum with exceptions)
- Warning if < 11h rest between days
- Weekly hour totals (max 48h average over 17 weeks)
- Break requirements (30min after 6h)

### Audit Trail
- All changes logged
- Required for labor inspections

## Public Holidays

Built-in calendar for:
- Austrian public holidays
- Regional holidays (Landesfeiertage)
- User can add custom holidays
- Auto-marks days as `public_holiday`

## Settings

### Plugin Settings
- Default work hours (e.g., 8h)
- Default break duration
- Enable/disable project allocation
- Enable/disable timer
- Country (for public holidays)
- Overtime threshold

### Per-User Settings
- Vacation days entitled per year
- Work week (Mon-Fri default)
- Typical work location

## API Endpoints (Plugin)

```
# Daily records
GET    /api/v1/plugins/time-tracking/records?from=&to=
POST   /api/v1/plugins/time-tracking/records
PUT    /api/v1/plugins/time-tracking/records/{id}
DELETE /api/v1/plugins/time-tracking/records/{id}

# Quick actions
POST   /api/v1/plugins/time-tracking/check-in
POST   /api/v1/plugins/time-tracking/check-out
GET    /api/v1/plugins/time-tracking/timer/status

# Project allocations
GET    /api/v1/plugins/time-tracking/records/{id}/allocations
POST   /api/v1/plugins/time-tracking/records/{id}/allocations
PUT    /api/v1/plugins/time-tracking/allocations/{id}
DELETE /api/v1/plugins/time-tracking/allocations/{id}

# Leave management
GET    /api/v1/plugins/time-tracking/leave-balance?year=
PUT    /api/v1/plugins/time-tracking/leave-balance

# Reports
GET    /api/v1/plugins/time-tracking/reports/monthly?year=&month=
GET    /api/v1/plugins/time-tracking/reports/overtime?from=&to=
GET    /api/v1/plugins/time-tracking/reports/export?format=csv&from=&to=

# Public holidays
GET    /api/v1/plugins/time-tracking/holidays?year=&country=
```

## Export Format (Monthly Report)

For submitting to employer:

```
Time Report - December 2024
Employee: Roland Knall
──────────────────────────────────────────────────────
Date       Type      In     Out    Break  Net    Notes
──────────────────────────────────────────────────────
01 Sun     -         -      -      -      -
02 Mon     Work      08:30  17:30  0:45   8.25h  Remote
03 Tue     Work      09:00  18:00  0:30   8.50h  Office
04 Wed     Sick      -      -      -      -
05 Thu     Sick      -      -      -      -
...
24 Tue     Vacation  -      -      -      -
25 Wed     Holiday   -      -      -      -      Christmas
...
──────────────────────────────────────────────────────
Summary:
  Working days: 18
  Hours worked: 152.5h
  Overtime: +8.5h
  Vacation taken: 3 days
  Sick days: 2 days

Vacation balance: 22 days remaining
```

## What This Plugin Does NOT Do

- Payroll calculations
- Tax calculations
- Shift planning / scheduling
- Team management / approval workflows
- Invoice generation

## Plugin Architecture Questions

Before implementation, need to define:
1. How do plugins register models/migrations?
2. How do plugins inject UI components?
3. How are plugin settings stored?
4. Plugin enable/disable mechanism?

## Related
- Event management - Travel days could auto-mark work location
- Company management - For project allocation
- [Calendar Integration](calendar-integration.md) - Could sync vacation days
