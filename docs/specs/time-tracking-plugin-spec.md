# Time Tracking Plugin - Complete Specification

**Status:** In Development
**Version:** 1.0.0-draft
**Last Updated:** 2026-01-01
**Plugin Type:** Optional

---

## Table of Contents

1. [Overview](#overview)
2. [Plugin Architecture](#plugin-architecture)
3. [Legal Compliance & Data Retention](#legal-compliance--data-retention)
4. [Timer & Time Entry](#timer--time-entry)
5. [Project Allocation](#project-allocation)
6. [Leave Management](#leave-management)
7. [Reporting & Export](#reporting--export)
8. [Data Models](#data-models)
9. [API Endpoints](#api-endpoints)
10. [UI Components](#ui-components)
11. [Settings & Configuration](#settings--configuration)

---

## Overview

### Purpose
Track working hours for legal compliance (Austrian labor law), personal documentation, and optional project allocation. Self-hosted, privacy-focused solution for freelancers and contractors.

### Key Requirements
- **Legal compliance:** Austrian Arbeitszeitgesetz and EU Working Time Directive
- **Privacy:** Self-hosted, user owns all data
- **Flexibility:** Works for simple time tracking or detailed project billing
- **Integration:** Leverages existing HomeOffice Assistant features (companies, contacts, email)

### Two-Layer Model

**Layer 1: Daily Time Records (Required)**
- Check-in/check-out times
- Break calculation
- Day type (work, vacation, sick, doctor visit, etc.)
- Legal compliance validation

**Layer 2: Project Allocation (Optional)**
- Split hours across projects/clients
- Link to Events and Companies
- Future: Billable tracking (v2)

---

## Plugin Architecture

### Q1-Q3: Plugin System Integration ✅

**Structure:**
```
plugins/time-tracking/
├── plugin.json                    # Manifest
├── backend/
│   ├── plugin.py                  # TimeTrackingPlugin class
│   ├── models.py                  # All database models
│   ├── routes.py                  # API endpoints
│   ├── schemas.py                 # Pydantic request/response models
│   ├── services.py                # Business logic
│   ├── validators.py              # Compliance validators
│   └── migrations/
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
│           └── xxxx_initial.py
└── frontend/
    ├── index.js                   # Plugin entry point
    ├── components/
    │   ├── TimeRecordForm.js
    │   ├── WeekView.js
    │   ├── MonthCalendar.js
    │   └── CompanyTimeSettingsWidget.js
    └── routes.js
```

**Integration Points:**
- **Backend:** Routes mounted at `/api/v1/plugins/time-tracking/`
- **Database:** Independent tables with `tt_` prefix
- **Migrations:** Plugin-specific Alembic environment
- **Frontend:** Widget injection via `companyDetail` widget
- **Events:** Subscribe to user login/logout for automatic tracking hints

**Plugin Manifest:**
```json
{
  "id": "time-tracking",
  "name": "Time Tracking",
  "version": "1.0.0",
  "description": "Track working hours with legal compliance for Austrian labor law",
  "author": "Roland Knall",
  "capabilities": {
    "backend": true,
    "frontend": true,
    "config": true
  },
  "required_permissions": [
    "user.read",
    "company.read",
    "event.read",
    "integration.use"
  ],
  "dependencies": []
}
```

---

## Legal Compliance & Data Retention

### Q4: Audit Trail & Data Retention ✅

**Approach: Hybrid (recommended for MVP)**

**Features:**
- Full audit trail for all changes (who, when, what changed)
- Configurable lock period (default: 7 days after month-end)
- Locked records require admin override to edit
- PDF export suitable for official employer submission
- No automatic deletion (manual only, with warnings)

**Audit Model:**
```python
class TimeRecordAudit(Base, TimestampMixin):
    """Immutable audit log for time record changes."""
    __tablename__ = "tt_time_record_audit"

    id: UUID
    time_record_id: UUID
    changed_by: UUID  # User who made the change
    changed_at: datetime
    change_type: str  # "created", "updated", "deleted"
    old_values: JSON | None
    new_values: JSON
    reason: str | None  # Optional explanation for changes
```

**Lock Logic:**
- Records automatically lock 7 days after the end of their month
- Example: Record from Jan 15, 2025 locks on Feb 8, 2025
- Locked records show "🔒 Locked" badge in UI
- Admin can unlock with reason logged to audit trail

**Retention:**
- Keep all records indefinitely (or until user manually archives)
- No automatic deletion (labor law requires 2+ years)
- Export/archive functionality for old records

---

### Q5: Rest Period Validation ✅

**Approach: Smart validation with exceptions (Option D)**

**11-Hour Rest Rule (Austrian Law):**
- Validate minimum 11h rest between shifts
- Show warning if violated, don't block entry
- Require explanation in notes field
- Track violations in compliance report

**Special Cases:**
- **Travel time:** Time to/from work locations (doesn't count as rest)
- **On-call work:** Configurable exception
- **Emergencies:** Allow override with explanation
- **Doctor visits:** Count as work time (see Q14)

**UI Behavior:**
```
⚠️ Rest Period Warning
Only 8h 30m since last shift (11h required by law)

Reason for exception:
[ ] On-call duty
[ ] Emergency
[ ] Travel
[ ] Other: _______________

[Continue Anyway]  [Cancel]
```

**Validation Service:**
```python
class AustrianComplianceValidator:
    def validate_rest_period(
        self,
        current: TimeRecord,
        previous: TimeRecord
    ) -> list[ComplianceWarning]:
        """Check 11-hour rest requirement."""
        if not previous:
            return []

        # Calculate rest period considering timezones
        rest_hours = calculate_rest_hours(previous, current)

        if rest_hours < 11:
            return [ComplianceWarning(
                level="warning",
                code="INSUFFICIENT_REST",
                message=f"Only {rest_hours:.1f}h rest (11h required)",
                requires_explanation=True,
                law_reference="Arbeitszeitgesetz §3"
            )]
        return []
```

---

### Q6: Multi-Country Support ✅

**Approach: Austria-only MVP, designed for extensibility (Option A → C)**

**MVP Implementation:**
- Hard-coded Austrian labor law rules
- Austrian public holidays (via `holidays` library)
- Single `AustrianComplianceValidator`

**Future-Ready Design:**
```python
# Abstract base for extensibility
class ComplianceValidator(ABC):
    """Base class for country-specific labor law validation."""

    @abstractmethod
    def validate_daily_hours(self, record: TimeRecord) -> list[ComplianceWarning]:
        """Check daily hour limits."""
        ...

    @abstractmethod
    def validate_rest_period(
        self,
        current: TimeRecord,
        previous: TimeRecord
    ) -> list[ComplianceWarning]:
        """Check rest between shifts."""
        ...

    @abstractmethod
    def validate_weekly_hours(
        self,
        records: list[TimeRecord]
    ) -> list[ComplianceWarning]:
        """Check weekly limits."""
        ...

    @abstractmethod
    def get_public_holidays(
        self,
        year: int,
        region: str | None = None
    ) -> list[date]:
        """Return public holidays."""
        ...

# Austrian implementation
class AustrianComplianceValidator(ComplianceValidator):
    """Austrian labor law (Arbeitszeitgesetz)."""

    def validate_daily_hours(self, record: TimeRecord):
        warnings = []
        if record.net_hours > 10:
            warnings.append(ComplianceWarning(
                level="error",
                message="Exceeds 10h/day legal maximum (§3 AZG)"
            ))
        elif record.net_hours > 8:
            warnings.append(ComplianceWarning(
                level="info",
                message="Overtime: exceeds 8h/day normal hours"
            ))
        return warnings

    def get_public_holidays(self, year: int, region: str | None = None):
        import holidays
        at_holidays = holidays.Austria(years=year, subdiv=region)
        return list(at_holidays.keys())
```

**Company Model Extension:**
```python
class CompanyTimeSettings(Base):
    """Plugin-specific company settings."""
    company_id: UUID
    country_code: str = "AT"  # Future: use to select validator
    # ... other settings
```

---

### Q21a: Timezone Handling ✅

**Approach: Per-company timezone with local time capture**

**Requirements:**
- Record times in local timezone (where user actually worked)
- Calculate hours in company's reporting timezone
- Handle international travel (Vienna → New York)

**Data Model:**
```python
class CompanyTimeSettings(Base):
    company_id: UUID
    timezone: str = "Europe/Vienna"  # IANA timezone string
    # ...

class TimeRecord(Base):
    company_id: UUID | None  # Link to employer

    # Store actual times with timezone
    check_in: time | None
    check_in_timezone: str | None  # e.g., "America/New_York"
    check_out: time | None
    check_out_timezone: str | None  # e.g., "America/New_York"

    # Calculated in company's timezone
    gross_hours: float | None
    net_hours: float | None
```

**Behavior Example:**
```
User in NYC (EST), employer in Vienna (CET)
Check-in:  08:00 EST (stored: 08:00 + "America/New_York")
Check-out: 17:00 EST (stored: 17:00 + "America/New_York")

Display in report (company timezone CET):
Check-in:  14:00 CET
Check-out: 23:00 CET
Net hours: 9h (calculated in CET)
```

**UI Features:**
- Auto-detect user's current timezone
- Show both local time and company time in detail view
- Reports always use company timezone
- Warning when timezone differs from company default

---

## Timer & Time Entry

### Q7: Timer Feature ✅

**Decision: Deferred to v2**

**MVP Approach:**
- Manual entry only (user types in times)
- Simple, reliable, no timer state management
- Matches real-world usage (most fill timesheets retroactively)

**v2 Features:**
- Real-time timer (start/stop button)
- Server-synced state
- Multi-device support
- Browser notifications

---

### Q8: Break Tracking ✅

**Decision: Automatic calculation (MVP), manual override in v2**

**MVP Logic:**
```python
def calculate_break_minutes(gross_hours: float) -> int:
    """Calculate required break based on Austrian law."""
    if gross_hours > 6.0:
        return 30  # 30min break required after 6h work
    return 0

def calculate_net_hours(
    check_in: time,
    check_out: time,
    break_override: int | None = None
) -> tuple[float, int]:
    """Calculate net hours and break time."""
    gross_seconds = (check_out - check_in).total_seconds()
    gross_hours = gross_seconds / 3600

    break_minutes = break_override or calculate_break_minutes(gross_hours)
    net_hours = gross_hours - (break_minutes / 60)

    return net_hours, break_minutes
```

**User Experience:**
```
Check-in:  08:05
Check-out: 17:40
           ─────────
Gross:     9h 35m
Break:     30m (automatic, >6h worked)
Net:       9h 5m
```

**v2 Enhancement:**
- Optional `break_minutes_override` field
- For edge cases (worked through lunch, longer break)

---

### Time Rounding ✅

**Rule: Round to nearest 5 minutes, in employer's favor**

**Implementation:**
```python
def round_time_employer_favor(t: time, is_check_in: bool) -> time:
    """Round to nearest 5 minutes.

    Check-in: Round UP (benefits employer)
    Check-out: Round DOWN (benefits employer)
    """
    minutes = t.hour * 60 + t.minute

    if is_check_in:
        # Round up to next 5 minutes
        rounded = ((minutes + 4) // 5) * 5
    else:
        # Round down to previous 5 minutes
        rounded = (minutes // 5) * 5

    return time(hour=rounded // 60, minute=rounded % 60)
```

**Examples:**
```
Actual: 08:03 → Rounded: 08:05 (check-in)
Actual: 08:07 → Rounded: 08:10 (check-in)
Actual: 17:43 → Rounded: 17:40 (check-out)
Actual: 17:47 → Rounded: 17:45 (check-out)

Result: Conservative, fair to employer
```

---

### Q9: Offline Support ✅

**Decision: No offline support in MVP (Option A)**

**Rationale:**
- Self-hosted app used at home/office with WiFi
- Manual entry (no real-time timer to sync)
- Offline adds significant complexity (conflict resolution, sync logic)
- Can defer to v2+ if needed

---

## Project Allocation

### Q10: Allocation Validation ✅

**Decision: Optional feature (Option D)**

**Behavior:**
- Project allocation is entirely optional
- Most days won't need allocation (vacation, sick, simple work days)
- When allocations added, show soft warning if they don't sum to net_hours
- Never block saving

**Example:**
```
Day: Work (8h net)

Allocations (optional):
  Company A - Project X: 5h
  Internal - Admin:      2h
                        ───
  Total:                 7h

⚠️ 1h unallocated (missing time not assigned to project)
[Save Anyway]  [Add Allocation]
```

---

### Q11: Project Hierarchy ✅

**Decision: Flat/flexible structure (Option A)**

**Data Model:**
```python
class TimeAllocation(Base, TimestampMixin):
    """Optional: Split daily hours across projects."""
    __tablename__ = "tt_time_allocations"

    id: UUID
    time_record_id: UUID  # FK to TimeRecord

    hours: float
    description: str | None  # Free-text project description

    # Optional links to existing entities
    event_id: UUID | None      # Link to business trip
    company_id: UUID | None    # Link to client/employer

    # Note: billable field removed (deferred to v2)
```

**Rationale:**
- Leverage existing Company and Event models
- Free-text description keeps it flexible
- No new Project model needed for MVP
- Simple, covers 95% of use cases

**UI:**
```
Add Allocation:
  Company:    [Company A ▼] (optional)
  Event:      [NYC Business Trip ▼] (optional)
  Project:    [Free text description]
  Hours:      [5.0]

[Add]  [Cancel]
```

---

### Q12: Billable Tracking ✅

**Decision: Defer to v2**

**MVP:**
- No billable flag
- No hourly rates
- No invoice generation
- User handles billing elsewhere

**Simplified Model:**
```python
class TimeAllocation(Base):
    # Removed: billable: bool
    # Removed: hourly_rate: float
    # Just track hours and description
```

---

## Leave Management

### Q13: Vacation Workflow ✅

**Decision: Direct entry (Option A)**

**Behavior:**
- User marks day as "vacation"
- Balance auto-decrements immediately
- No approval workflow (self-hosted personal use)
- Simple self-service

**Flow:**
```
User: Create TimeRecord
  Date: 2025-06-15
  Type: Vacation

System: ✓ Created
        ✓ Vacation balance: 25 → 24 days
```

---

### Q14: Partial Day Absences ✅

**Decision: Hybrid approach with doctor visits as work time**

**Austrian Law Requirement:**
- Doctor visits count as work time (paid time, not vacation/sick)
- Must track separately for compliance

**Data Model:**
```python
class DayType(str, Enum):
    WORK = "work"
    VACATION = "vacation"
    SICK = "sick"
    DOCTOR_VISIT = "doctor_visit"  # Special: counts as work
    PUBLIC_HOLIDAY = "public_holiday"
    COMP_TIME = "comp_time"
    UNPAID_LEAVE = "unpaid_leave"
    PARENTAL_LEAVE = "parental_leave"
    TRAINING = "training"
    OTHER = "other"

class TimeRecord(Base):
    day_type: DayType
    check_in: time | None
    check_out: time | None

    # For partial absences on work days
    partial_absence_type: DayType | None  # e.g., "doctor_visit"
    partial_absence_hours: float | None   # e.g., 2.0

    # Calculated
    gross_hours: float | None
    break_minutes: int | None
    net_hours: float | None  # Includes doctor time for compliance
```

**Calculation Example:**
```
Day type: Work
Check-in: 08:00, Check-out: 17:00
Partial absence: Doctor visit (2h)

Gross: 9h
Break: 30m (automatic)
Doctor: 2h (counts as work time!)
Actual at desk: 6h 30m
Net hours (for compliance): 8h 30m (includes doctor)
```

**UI:**
```
Time Entry:
  Day Type: [Work ▼]
  Check-in: [08:00]
  Check-out: [17:00]

  Partial Absence:
    Type: [Doctor Visit ▼]
    Hours: [2.0]
    Notes: Dentist appointment 10:00-12:00

Summary:
  Gross: 9h
  Break: 30m (auto)
  Doctor: 2h (counts as work)
  Net: 8h 30m ✓
```

---

### Q15: Comp Time (Zeitausgleich) ✅

**Decision: Automatic accrual (Option B)**

**Accrual Rules:**
1. **Daily overtime:** Any hours > 8h/day
2. **Weekend multiplier:**
   - Saturday: 1x
   - Sunday: 2x
3. **Holiday multiplier:** National holidays 2x
4. **Threshold:** Configurable per-company (default: 0h, all overtime counts)
5. **Balance warning:** Configurable per-company (default: 40h)
6. **Expiration:** Never expires

**Examples:**
```
Monday (work): 9h → +1h comp time
Sunday (work): 6h → +12h comp time (6h × 2)
Dec 25 (holiday): 4h → +8h comp time (4h × 2)
```

**Calculation Service:**
```python
def calculate_comp_time_earned(
    record: TimeRecord,
    company_settings: CompanyTimeSettings
) -> float:
    """Calculate comp time earned for this day."""
    if record.day_type not in [DayType.WORK, DayType.DOCTOR_VISIT]:
        return 0.0

    # Calculate overtime (hours beyond 8)
    overtime = max(0, record.net_hours - 8.0)

    # Apply threshold (e.g., first 2h/week don't count)
    if overtime <= company_settings.overtime_threshold_hours:
        return 0.0

    overtime -= company_settings.overtime_threshold_hours

    # Apply multipliers
    multiplier = 1.0
    if record.is_sunday():
        multiplier = 2.0
    elif record.is_public_holiday():
        multiplier = 2.0
    elif record.is_saturday():
        multiplier = 1.0  # Could add bonus if desired

    return overtime * multiplier
```

**Company Settings:**
```python
class CompanyTimeSettings(Base):
    company_id: UUID

    # Comp time settings
    overtime_threshold_hours: float = 0.0  # Start counting after X hours
    comp_time_warning_balance: float = 40.0  # Warn when exceeds
```

**Balance Tracking:**
```python
class LeaveBalance(Base):
    user_id: UUID
    company_id: UUID | None
    year: int

    comp_time_balance: float  # Auto-calculated
    # +: Earned from overtime
    # -: Days taken as comp_time
```

**Taking Comp Time:**
```
User creates TimeRecord:
  Date: 2025-06-20
  Type: Comp Time

System:
  ✓ Deducts 8h from comp_time_balance
  ✓ Balance: 42h → 34h
```

---

### Q16: Public Holidays ✅

**Decision: Python `holidays` library (offline)**

**Implementation:**
```python
import holidays

def get_public_holidays(
    country_code: str,
    year: int,
    region: str | None = None
) -> dict[date, str]:
    """Get public holidays using the holidays library."""
    country_holidays = holidays.country_holidays(
        country_code,
        years=year,
        subdiv=region
    )
    return {d: name for d, name in country_holidays.items()}

# Usage
at_holidays = get_public_holidays("AT", 2025)
# {
#   date(2025, 1, 1): "Neujahr",
#   date(2025, 1, 6): "Heilige Drei Könige",
#   date(2025, 4, 21): "Ostermontag",
#   date(2025, 5, 1): "Staatsfeiertag",
#   ...
# }
```

**Features:**
- Offline (no API calls)
- 100+ countries supported
- Regional holidays (Austrian states)
- Updated via pip
- Users can add custom holidays

**Custom Holidays:**
```python
class CustomHoliday(Base):
    """User-defined holidays."""
    __tablename__ = "tt_custom_holidays"

    id: UUID
    user_id: UUID
    date: date
    name: str
    applies_to_company_id: UUID | None  # Global or company-specific
```

---

## Reporting & Export

### Q17: Report Customization ✅

**Decision: Fixed templates with filtering + Email integration (Option B + Email)**

**Report Types:**
1. **Monthly Summary** - For employer submission
2. **Overtime Report** - Track overtime hours
3. **Vacation Balance** - Days taken vs. remaining
4. **Comp Time Balance** - Hours available

**Filtering:**
- Date range selection
- Filter by company
- Filter by project (if allocations used)
- Filter by day type

**Email Integration:**

Uses existing HomeOffice Assistant infrastructure:
- `EmailTemplate` model with variable substitution
- `CompanyContact` with contact_types (use "hr" or "payroll")
- `SmtpProvider` for email delivery

**Flow:**
```
1. User: "Send Monthly Report"
2. Select: Month, Company
3. Generate: PDF report
4. Load: Email template (company-specific or default)
5. Send: To HR contact via SMTP
6. Track: Create TimesheetSubmission record
```

**Submission Tracking:**
```python
class TimesheetSubmission(Base, TimestampMixin):
    """Track when timesheets are submitted to employers."""
    __tablename__ = "tt_timesheet_submissions"

    id: UUID
    company_id: UUID
    user_id: UUID

    # Period covered
    period_start: date
    period_end: date
    period_type: str  # "month", "week", "custom"

    # Submission details
    submitted_at: datetime
    submitted_by: UUID
    sent_to_email: str  # Which contact received it

    # Attachments
    pdf_path: str | None  # Stored report file
    record_ids: JSON  # [uuid, uuid, ...] TimeRecords included

    # Status
    status: str  # "sent", "acknowledged", "disputed"
    notes: str | None
```

**TimeRecord changes:**
```python
class TimeRecord(Base):
    # ... existing fields ...

    # Submission tracking
    submission_id: UUID | None  # FK to TimesheetSubmission
    is_submitted: bool = False  # Computed from submission_id
```

**UI Indicators:**
- "✓ Submitted" badge on sent records
- Lock submitted records (prevent editing without unlock)
- Show submission history in company detail

**Email Template Variables:**
```
Available for timesheet templates:
- {user_name}
- {company_name}
- {period_start}
- {period_end}
- {total_hours}
- {working_days}
- {vacation_days}
- {sick_days}
- {overtime_hours}
```

---

### Vacation Balance Tracking ✅

**Auto-Calculation:**
```python
class LeaveBalance(Base, TimestampMixin):
    """Track vacation/leave entitlements per year."""
    __tablename__ = "tt_leave_balances"

    id: UUID
    user_id: UUID
    company_id: UUID | None  # Per-company or global
    year: int  # Unique per user+company+year

    # Vacation
    vacation_entitled: float  # Days per year (e.g., 25)
    vacation_taken: float     # Auto-calculated from records
    # vacation_remaining computed: entitled - taken

    # Comp time
    comp_time_balance: float  # Hours (auto-calculated)

    # Statistics
    sick_days_taken: int      # For reference, no "balance"
```

**Auto-Update Logic:**
```python
# When TimeRecord created/updated/deleted:
def update_leave_balance(user_id: UUID, year: int, company_id: UUID):
    balance = get_or_create_balance(user_id, year, company_id)

    # Recalculate vacation taken
    vacation_records = TimeRecord.query.filter(
        year=year,
        day_type=DayType.VACATION
    )
    balance.vacation_taken = len(vacation_records)

    # Recalculate sick days
    sick_records = TimeRecord.query.filter(
        year=year,
        day_type=DayType.SICK
    )
    balance.sick_days_taken = len(sick_records)

    # Recalculate comp time
    balance.comp_time_balance = calculate_comp_time_balance(
        user_id, company_id
    )

    db.commit()
```

**Company Settings:**
```python
class CompanyTimeSettings(Base):
    company_id: UUID
    vacation_days_per_year: float = 25.0  # Austrian default
```

**UI Widget:**
```
Vacation Balance 2025:
  Entitled: 25 days
  Taken:    7 days
  Remaining: 18 days

Comp Time Balance:
  Available: 12.5 hours
  [Take Comp Time Day]
```

---

### Plugin Self-Sufficiency ✅

**Core Principle:** Plugin owns all its data, doesn't pollute core models

**Instead of adding to core Company:**
```python
# ❌ BAD: Modifying core model
class Company(Base):
    vacation_days_per_year: float  # Plugin-specific!
    timezone: str  # Plugin-specific!
```

**Plugin stores its own settings:**
```python
# ✅ GOOD: Plugin-owned table
class CompanyTimeSettings(Base, TimestampMixin):
    """Plugin-specific settings per company."""
    __tablename__ = "tt_company_settings"

    id: UUID
    company_id: UUID  # FK to core Company (unique)

    # Time tracking settings
    timezone: str = "Europe/Vienna"
    country_code: str = "AT"
    vacation_days_per_year: float = 25.0
    overtime_threshold_hours: float = 0.0
    comp_time_warning_balance: float = 40.0

    # Email settings
    default_timesheet_contact_id: UUID | None  # FK to CompanyContact
```

**Contact Types:**
Instead of adding "timesheet" to core enum, use existing types:
- Recognize "hr" or "payroll" contacts for timesheet submission
- Plugin settings can specify preference

**Frontend Integration:**
Plugin injects settings widget into company detail page:
```javascript
// plugins/time-tracking/frontend/index.js
export const widgets = {
  companyDetail: CompanyTimeSettingsWidget
}

function CompanyTimeSettingsWidget({ companyId }) {
  // Fetch/edit CompanyTimeSettings for this company
  // Appears as a card in CompanyDetail page
  return <Card>...</Card>
}
```

**Benefits:**
- ✅ Core app unchanged
- ✅ Plugin fully self-contained
- ✅ Clean uninstall (drop `tt_*` tables)
- ✅ No enum pollution

---

## Data Models

### Core Models

```python
class DayType(str, Enum):
    """Types of days for time tracking."""
    WORK = "work"
    VACATION = "vacation"
    SICK = "sick"
    DOCTOR_VISIT = "doctor_visit"  # Counts as work time (Austrian law)
    PUBLIC_HOLIDAY = "public_holiday"
    COMP_TIME = "comp_time"
    UNPAID_LEAVE = "unpaid_leave"
    PARENTAL_LEAVE = "parental_leave"
    TRAINING = "training"
    OTHER = "other"


class TimeRecord(Base, TimestampMixin):
    """Daily time record - legal requirement."""
    __tablename__ = "tt_time_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL")
    )

    # Day classification
    day_type: Mapped[DayType] = mapped_column(nullable=False)

    # Working times (nullable for non-work days)
    check_in: Mapped[time | None]
    check_in_timezone: Mapped[str | None]  # IANA timezone
    check_out: Mapped[time | None]
    check_out_timezone: Mapped[str | None]

    # Partial absences (for work days)
    partial_absence_type: Mapped[DayType | None]
    partial_absence_hours: Mapped[float | None]

    # Calculated values
    gross_hours: Mapped[float | None]
    break_minutes: Mapped[int | None]  # Auto-calculated
    net_hours: Mapped[float | None]

    # Location
    work_location: Mapped[str | None]  # "office", "remote", "client_site", "travel"

    # Notes and compliance
    notes: Mapped[str | None] = mapped_column(Text)
    compliance_warnings: Mapped[str | None] = mapped_column(Text)  # JSON array

    # Submission tracking
    submission_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tt_timesheet_submissions.id")
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date"),
        Index("idx_user_date_range", "user_id", "date"),
    )


class TimeAllocation(Base, TimestampMixin):
    """Optional: How daily hours are split across projects."""
    __tablename__ = "tt_time_allocations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    time_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("tt_time_records.id", ondelete="CASCADE")
    )

    hours: Mapped[float] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

    # Associations (all optional)
    event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL")
    )
    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL")
    )


class LeaveBalance(Base, TimestampMixin):
    """Track vacation/leave entitlements per year."""
    __tablename__ = "tt_leave_balances"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )
    year: Mapped[int] = mapped_column(nullable=False)

    # Vacation
    vacation_entitled: Mapped[float] = mapped_column(default=25.0)
    vacation_taken: Mapped[float] = mapped_column(default=0.0)
    # vacation_remaining = vacation_entitled - vacation_taken (computed)

    # Comp time
    comp_time_balance: Mapped[float] = mapped_column(default=0.0)

    # Statistics
    sick_days_taken: Mapped[int] = mapped_column(default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "company_id", "year", name="uq_user_company_year"),
    )


class TimesheetSubmission(Base, TimestampMixin):
    """Track when timesheets are submitted to employers."""
    __tablename__ = "tt_timesheet_submissions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    # Period
    period_start: Mapped[date]
    period_end: Mapped[date]
    period_type: Mapped[str] = mapped_column(String(20))  # month, week, custom

    # Submission
    submitted_at: Mapped[datetime]
    submitted_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    sent_to_email: Mapped[str]

    # Attachments
    pdf_path: Mapped[str | None]
    record_ids: Mapped[str] = mapped_column(Text)  # JSON array of UUIDs

    # Status
    status: Mapped[str] = mapped_column(String(20), default="sent")
    notes: Mapped[str | None] = mapped_column(Text)


class CompanyTimeSettings(Base, TimestampMixin):
    """Plugin-specific settings per company."""
    __tablename__ = "tt_company_settings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True
    )

    # Regional settings
    timezone: Mapped[str] = mapped_column(default="Europe/Vienna")
    country_code: Mapped[str] = mapped_column(String(2), default="AT")

    # Leave settings
    vacation_days_per_year: Mapped[float] = mapped_column(default=25.0)

    # Overtime settings
    overtime_threshold_hours: Mapped[float] = mapped_column(default=0.0)
    comp_time_warning_balance: Mapped[float] = mapped_column(default=40.0)

    # Submission settings
    default_timesheet_contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("company_contacts.id", ondelete="SET NULL")
    )
    lock_period_days: Mapped[int] = mapped_column(default=7)


class TimeRecordAudit(Base, TimestampMixin):
    """Immutable audit log for time record changes."""
    __tablename__ = "tt_time_record_audit"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    time_record_id: Mapped[UUID]  # Not FK (record might be deleted)
    changed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    change_type: Mapped[str] = mapped_column(String(20))  # created, updated, deleted
    old_values: Mapped[str | None] = mapped_column(Text)  # JSON
    new_values: Mapped[str] = mapped_column(Text)  # JSON
    reason: Mapped[str | None] = mapped_column(Text)


class CustomHoliday(Base, TimestampMixin):
    """User-defined holidays."""
    __tablename__ = "tt_custom_holidays"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )

    date: Mapped[date]
    name: Mapped[str] = mapped_column(String(200))
```

---

## API Endpoints

### Time Records

```
GET    /api/v1/plugins/time-tracking/records
  Query: from=DATE, to=DATE, company_id=UUID, day_type=TYPE
  Response: [TimeRecord, ...]

POST   /api/v1/plugins/time-tracking/records
  Body: TimeRecordCreate
  Response: TimeRecord

GET    /api/v1/plugins/time-tracking/records/{id}
  Response: TimeRecord

PUT    /api/v1/plugins/time-tracking/records/{id}
  Body: TimeRecordUpdate
  Response: TimeRecord

DELETE /api/v1/plugins/time-tracking/records/{id}
  Response: {success: bool}
```

### Quick Actions

```
POST   /api/v1/plugins/time-tracking/check-in
  Body: {company_id?, work_location?, notes?}
  Response: TimeRecord (creates today's record)

POST   /api/v1/plugins/time-tracking/check-out
  Body: {notes?}
  Response: TimeRecord (updates today's record)

GET    /api/v1/plugins/time-tracking/today
  Response: TimeRecord | null
```

### Allocations

```
GET    /api/v1/plugins/time-tracking/records/{record_id}/allocations
  Response: [TimeAllocation, ...]

POST   /api/v1/plugins/time-tracking/records/{record_id}/allocations
  Body: TimeAllocationCreate
  Response: TimeAllocation

PUT    /api/v1/plugins/time-tracking/allocations/{id}
  Body: TimeAllocationUpdate
  Response: TimeAllocation

DELETE /api/v1/plugins/time-tracking/allocations/{id}
  Response: {success: bool}
```

### Leave Management

```
GET    /api/v1/plugins/time-tracking/leave-balance
  Query: year=INT, company_id=UUID
  Response: LeaveBalance

PUT    /api/v1/plugins/time-tracking/leave-balance
  Body: {year, company_id?, vacation_entitled}
  Response: LeaveBalance
```

### Reports

```
GET    /api/v1/plugins/time-tracking/reports/monthly
  Query: year=INT, month=INT, company_id=UUID
  Response: MonthlyReport

GET    /api/v1/plugins/time-tracking/reports/overtime
  Query: from=DATE, to=DATE, company_id=UUID
  Response: OvertimeReport

POST   /api/v1/plugins/time-tracking/reports/submit
  Body: {company_id, period_start, period_end, contact_id?}
  Response: TimesheetSubmission

GET    /api/v1/plugins/time-tracking/reports/export
  Query: format=pdf|csv, from=DATE, to=DATE, company_id=UUID
  Response: File download
```

### Settings

```
GET    /api/v1/plugins/time-tracking/settings/company/{company_id}
  Response: CompanyTimeSettings

PUT    /api/v1/plugins/time-tracking/settings/company/{company_id}
  Body: CompanyTimeSettingsUpdate
  Response: CompanyTimeSettings
```

### Public Holidays

```
GET    /api/v1/plugins/time-tracking/holidays
  Query: year=INT, country=CODE, region=CODE?
  Response: [{date, name}, ...]

POST   /api/v1/plugins/time-tracking/holidays/custom
  Body: {date, name, company_id?}
  Response: CustomHoliday
```

---

## UI Components

### Main Views

1. **Daily Entry** - Primary view for creating/editing time records
2. **Week View** - 7-day overview with quick entry
3. **Month Calendar** - Calendar grid showing all days
4. **Leave Management** - Vacation balance, request time off
5. **Reports** - Generate and send timesheets
6. **Company Settings Widget** - Injected into company detail page

### Component Structure

```
plugins/time-tracking/frontend/
├── index.js                           # Plugin entry point
├── components/
│   ├── TimeRecordForm.js             # Daily entry form
│   ├── WeekView.js                   # Weekly overview
│   ├── MonthCalendar.js              # Monthly calendar
│   ├── LeaveBalanceWidget.js         # Vacation/comp time display
│   ├── CompanyTimeSettingsWidget.js  # Company settings (injected)
│   ├── TimesheetSubmissionModal.js   # Send report modal
│   └── ComplianceWarnings.js         # Display warnings
└── routes.js
```

---

## Settings & Configuration

### Plugin Settings (Global)

```json
{
  "default_work_hours": 8.0,
  "default_break_minutes": 30,
  "enable_project_allocation": true,
  "default_country": "AT"
}
```

### Company Settings (Per-Company)

Managed via `CompanyTimeSettings` model:
- Timezone
- Country code
- Vacation days per year
- Overtime threshold
- Comp time warning level
- Default timesheet contact
- Lock period

---

## MVP Scope Summary

### ✅ **MUST HAVE (MVP v1.0)**

**Core Features:**
- Daily time records (manual entry)
- Check-in/check-out with auto-rounding (5min, employer favor)
- Automatic break calculation (30m if >6h)
- Day types (work, vacation, sick, doctor visit, etc.)
- Partial day absences (doctor visits count as work)
- Timezone support (per-company, handles travel)

**Compliance:**
- Austrian labor law validation
- 11h rest period warnings
- 10h/day maximum enforcement
- Audit trail for all changes
- Lock records after configurable period
- Public holidays (via `holidays` library)

**Leave Management:**
- Vacation balance tracking (auto-calculated)
- Automatic comp time accrual (daily >8h, Sunday/holiday 2x)
- Sick day tracking (statistics only)
- Direct entry (no approval workflow)

**Reporting:**
- Monthly summary export (PDF/CSV)
- Email to HR contact (via existing SMTP)
- Track submissions (prevent editing submitted records)
- Overtime report
- Vacation balance report

**Project Allocation (Optional):**
- Split hours across projects
- Link to Companies and Events
- Free-text descriptions
- Soft validation (warnings only)

**Settings:**
- Per-company timezone, country, vacation days
- Overtime thresholds
- Comp time warning levels
- Default contacts for submissions

### 🔮 **DEFER TO v2+**

**Features:**
- Real-time timer (start/stop button)
- Manual break override
- Billable tracking and rates
- Invoice generation
- Multi-country validators (beyond Austria)
- Approval workflows
- Mobile app / PWA
- Offline support
- Advanced project hierarchy
- Custom report builder
- Scheduled reports (auto-send monthly)
- Team management / multi-user

---

## Export Formats & Privacy

### Q18: Export Formats ✅

**Decision: PDF + CSV (Option B)**

**PDF Report Format:**
Professional formatted report suitable for employer submission with complete monthly summary, vacation balance, and comp time balance.

**CSV Export Structure:**
```csv
date,day_type,check_in,check_out,break_minutes,net_hours,work_location,notes
2024-12-02,work,08:30,17:30,45,8.25,remote,
2024-12-03,work,09:00,18:00,30,8.50,office,
...
```

**Export Endpoints:**
- `/reports/export?format=pdf&from=DATE&to=DATE`
- `/reports/export?format=csv&from=DATE&to=DATE`

---

### Q19: Privacy & Access Control ✅

**Decision: User + Admin (Option B)**

**Access Rules:**
- **Regular users:** Can only see/edit their own time records
- **Admins:** Can view all users' records (read-only, for support)
- **Admins cannot edit** other users' records (data integrity)

**Backend Implementation:**
```python
def get_time_records(
    db: Session,
    current_user: User,
    user_id: UUID | None = None,
    ...
) -> list[TimeRecord]:
    # Non-admins can only access their own records
    if not current_user.is_admin and user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    # ...
```

---

## Data Integrity & Edge Cases

### Q20: Retroactive Edits ✅

**Decision: Lock after configurable period (Option B)**

**Lock Logic:**
- Records lock X days after month-end (default: 7 days)
- Example: Jan 15 record locks on Feb 8
- Locked records show 🔒 badge
- Admin can unlock with reason (logged to audit)

**Settings:**
```python
class CompanyTimeSettings(Base):
    lock_period_days: int = 7  # Configurable per company
```

---

### Q22: Missing Data Handling ✅

**Decision: Warnings + Block submission if incomplete (Option B+)**

**Missing Day Detection:**
- Dashboard shows: "⚠️ 3 days missing this month"
- Lists missing workdays (Mon-Fri, excluding holidays)
- **Blocks submission** if days are missing

**Submission Validation:**
```python
@router.post("/reports/submit")
def submit_timesheet(...):
    missing = get_missing_workdays(...)
    if missing:
        raise HTTPException(400, {
            "error": "Cannot submit incomplete timesheet",
            "missing_dates": [...],
        })
```

---

### Q23: Year-End Rollovers ✅

**Decision: Full carryover (Option C - corrected)**

**Austrian Law Compliance:**
- **Vacation:** ALL unused days MUST carry over (legal requirement)
- **Comp time:** ALL carries over (no expiration)

**Updated Model:**
```python
class LeaveBalance(Base):
    vacation_entitled: float  # Includes carryover
    vacation_carryover: float  # Amount from previous year
    vacation_taken: float
    comp_time_balance: float  # Carries over fully
```

**Example:**
```
2024: 25 entitled, 18 taken → 7 remaining
2025: 25 new + 7 carryover = 32 total entitled
```

---

## Performance & Scalability

### Q24: Data Volume Expectations ✅

**Decision: Basic indexing (Option B)**

**Expected Volume:**
- ~3,650 TimeRecords per user over 10 years
- ~10,000 TimeAllocations if using projects
- Well within database capabilities

**Index Strategy:**
```python
class TimeRecord(Base):
    __table_args__ = (
        UniqueConstraint("user_id", "date"),
        Index("idx_user_date_range", "user_id", "date"),
        Index("idx_company_date", "company_id", "date"),
        Index("idx_submission", "submission_id"),
    )
```

**No need for:** Partitioning, archiving, denormalization, or aggressive caching.

---

### Q25: Calendar View Performance ✅

**Decision: Lazy loading by month (Option B)**

**Implementation:**
- Load only visible month (~30 records)
- Prefetch adjacent months for smooth navigation
- Cache loaded months in memory
- API endpoint: `/records/month/{year}/{month}`

**Benefits:**
- Faster initial load
- Reduced bandwidth
- Smooth navigation with prefetch

---

## User Experience & Workflows

### Q26: Primary Entry Workflows ✅

**Decision: Flexible (Option D) + API support**

**Multiple Entry Methods:**

1. **Quick Actions (API + UI):**
   - `POST /check-in` - Quick check-in for today
   - `POST /check-out` - Quick check-out for today
   - Auto-detect timezone, round times

2. **API Usage:**
   ```bash
   # Shell script
   curl -X POST .../check-in -H "Authorization: Bearer $TOKEN"

   # iOS Shortcut / Siri
   "Hey Siri, check in to work"

   # Python automation
   requests.post(".../check-in", ...)
   ```

3. **Manual Form Entry:**
   - Full date/time picker
   - All fields available
   - Retroactive entry

4. **Week Batch Entry:**
   - Inline editing for whole week
   - Bulk save

**API Endpoints:**
```
POST /check-in          # Quick check-in
POST /check-out         # Quick check-out
GET  /today             # Get today's record
POST /records           # Full CRUD
POST /records/bulk      # Batch create
```

---

### Q27: Mobile Experience ✅

**Decision: Responsive web (MVP), PWA in v2 (Option A)**

**MVP (v1.0):**
- Responsive web design
- Touch-friendly UI
- API for automation (Shortcuts, scripts)

**v2 Features (deferred):**
- Progressive Web App (installable)
- Offline support
- Push notifications
- GPS location detection

---

### Q28: Keyboard Shortcuts ✅

**Decision: Power user basics (Option C)**

**Keyboard Shortcuts:**
```
Global:
  Ctrl/Cmd + N     → New time record
  Ctrl/Cmd + T     → Jump to today
  Ctrl/Cmd + S     → Quick save
  Ctrl/Cmd + I     → Check in now
  Ctrl/Cmd + O     → Check out now
  Ctrl/Cmd + D     → Duplicate yesterday
  Esc              → Close modal/cancel

Calendar navigation:
  Arrow keys       → Navigate days/weeks
  Home/End         → First/last day of month
  PageUp/PageDown  → Previous/next month

Form:
  Tab/Shift+Tab    → Next/previous field
  Enter            → Submit (when not in textarea)
```

**Quick Copy Feature:**
- "Copy from yesterday" button
- Copies times and settings (not allocations/notes)

**v2 (deferred):**
- Templates for common patterns
- Bulk edit
- Command palette (Cmd+K)

---

## Settings & Configuration

### Q29: Default Values ✅

**Decision: Last used (Option B for v1)**

**User Preferences:**
```python
class UserTimePreferences(Base):
    user_id: UUID
    last_company_id: UUID | None
    last_work_location: str | None
    last_check_in: time | None
    last_check_out: time | None
```

**Behavior:**
- Auto-save last-used values when creating record
- Pre-fill form with last-used values
- UI shows: "Last used: Acme Corp"

**v2+ (deferred):**
- Pattern detection (always work 8:30-17:30)
- Day-of-week suggestions
- Smart pre-fill based on patterns

---

### Q30: Overtime Calculation ✅

**Decision: Austrian standard (Option D)**

**Rules:**
- **Daily threshold:** >8h/day is overtime (for comp time accrual)
- **Weekly threshold:** >40h/week (for reporting/summary)
- **Mode:** Use daily for automatic comp time calculation

**Company Settings:**
```python
class CompanyTimeSettings(Base):
    daily_overtime_threshold: float = 8.0   # Hours/day
    weekly_overtime_threshold: float = 40.0  # Hours/week
    overtime_accrual_mode: str = "daily"
```

**Reporting:**
```
Weekly Summary:
  Daily overtime total: 1.5h (from >8h/day)
  Weekly overtime: 1.0h (from >40h/week)
  Comp time earned: +1.5h (from daily threshold)
```

---

## Integration with Existing Features

### Q31: Event Integration ✅

**Decision: Auto-suggest (Option B)**

**Behavior:**
- Detect events overlapping with time record date
- Show suggestion: "📅 Active event: NYC Conference"
- User can click to link (pre-fill company, location, allocation)
- Bulk create: Offer to create records for all event days

**UI:**
```javascript
<Alert>
  📅 Active event: NYC Conference
  <Button onClick={linkToEvent}>Link to Event</Button>
</Alert>

// For multi-day events
<Alert>
  Event runs Dec 10-14 (5 days)
  <Button onClick={createRecordsForEvent}>
    Create time records for all event days
  </Button>
</Alert>
```

**Benefits:**
- Suggests when relevant
- User maintains control
- Avoids false positives (weekends during event)
- Bulk create saves time

---

### Q32: Expense Integration ✅

**Decision: None (Option A)**

**Rationale:**
- Expenses already link to Events and Companies
- Time allocations also link to Events and Companies
- No need to directly couple
- Keeps plugin simple and focused

**Future (v3+):**
Could add project-based expense reports by joining via Event/Company relationships if needed.

---

### Q33: Calendar Integration ✅

**Decision: Event subscription (Option D)**

**Implementation:**
Time tracking publishes events via plugin event bus:

```python
# Events published by time tracking plugin
"time_tracking.vacation_created"
"time_tracking.vacation_cancelled"
"time_tracking.comp_time_taken"
"time_tracking.overtime_threshold_exceeded"
"time_tracking.timesheet_submitted"
```

**Calendar plugin can subscribe:**
```python
class CalendarIntegrationPlugin(BasePlugin):
    def get_event_handlers(self):
        return {
            "time_tracking.vacation_created": self._on_vacation_created,
        }

    async def _on_vacation_created(self, payload):
        # Create calendar event when vacation taken
        await self.create_calendar_event(...)
```

**Benefits:**
- Loose coupling (plugins independent)
- Optional (works without calendar plugin)
- Extensible (any plugin can subscribe)
- Uses existing event bus

**v2+ (deferred):**
Two-way sync with conflict resolution.

---

## MVP Scope Summary

### Q34: MVP Feature Set ✅

**✅ MUST HAVE (v1.0):**

**Core Features:**
- Daily time records (manual entry)
- Check-in/check-out with auto-rounding (5min, employer favor)
- Automatic break calculation (30m if >6h)
- Day types (work, vacation, sick, doctor visit, etc.)
- Partial day absences (doctor visits count as work)
- Timezone support (per-company, handles travel)

**Compliance:**
- Austrian labor law validation
- 11h rest period warnings (smart validation)
- 10h/day maximum enforcement
- Audit trail for all changes
- Lock records after configurable period
- Public holidays (via `holidays` library)

**Leave Management:**
- Vacation balance tracking (auto-calculated, full carryover)
- Automatic comp time accrual (daily >8h, Sunday/holiday 2x)
- Sick day tracking (statistics only)
- Direct entry (no approval workflow)

**Reporting:**
- Monthly summary export (PDF/CSV)
- Email to HR contact (via existing SMTP)
- Track submissions (prevent editing submitted records)
- Block submission if days missing
- Overtime report
- Vacation balance report

**Project Allocation (Optional):**
- Split hours across projects
- Link to Companies and Events
- Free-text descriptions
- Soft validation (warnings only)

**Settings:**
- Per-company timezone, country, vacation days
- Overtime thresholds
- Comp time warning levels
- Default contacts for submissions
- Lock periods

**UX:**
- API for automation (check-in/out endpoints)
- Keyboard shortcuts
- Last-used defaults
- Event suggestions
- Missing day warnings
- Lazy-loaded calendar (month view)
- Responsive web design

**Privacy:**
- User + Admin access control
- Users see only their own records
- Admins can view (read-only) for support

### 🔮 DEFER TO v2+

**Features:**
- Real-time timer (start/stop button)
- Manual break override
- Billable tracking and rates
- Invoice generation
- Multi-country validators (beyond Austria)
- Approval workflows
- Mobile app / PWA
- Offline support
- Pattern detection / smart suggestions
- Advanced project hierarchy
- Custom report builder
- Scheduled reports (auto-send monthly)
- Team management / multi-user
- Two-way calendar sync

---

### Q35: Plugin Extensibility ✅

**Decision: Event-based (MVP), Provider pattern (v2)**

**MVP (v1.0):**
- Event bus integration (already in plugin system)
- Publishes time tracking events for other plugins
- Loose coupling via events

**v2:**
- Provider pattern for compliance validators
- Provider pattern for export formats
- Extensible without core changes

**Published Events:**
```python
"time_tracking.vacation_created"
"time_tracking.vacation_cancelled"
"time_tracking.comp_time_taken"
"time_tracking.overtime_threshold_exceeded"
"time_tracking.timesheet_submitted"
```

---

## Implementation Roadmap

### Phase 1: Core Foundation (Week 1-2)
- [ ] Database models and migrations
- [ ] Basic API endpoints (CRUD)
- [ ] Time calculation logic (rounding, breaks, net hours)
- [ ] Timezone handling
- [ ] Austrian compliance validator

### Phase 2: Leave Management (Week 3)
- [ ] Vacation balance tracking
- [ ] Comp time accrual logic
- [ ] Public holidays integration
- [ ] Year-end rollover logic

### Phase 3: UI Components (Week 4-5)
- [ ] Daily entry form
- [ ] Week view
- [ ] Month calendar (lazy loading)
- [ ] Company settings widget
- [ ] Leave balance widget

### Phase 4: Reporting (Week 6)
- [ ] PDF report generation
- [ ] CSV export
- [ ] Email integration
- [ ] Submission tracking
- [ ] Missing day validation

### Phase 5: Polish & Testing (Week 7-8)
- [ ] Keyboard shortcuts
- [ ] API documentation
- [ ] Audit trail
- [ ] Lock mechanism
- [ ] Comprehensive testing
- [ ] Documentation

---

## Current Status

**All questions answered!** ✅ (Q1-Q35)

**Specification:** Complete and ready for implementation

**Next Steps:**
1. Review specification with stakeholders
2. Create GitHub issues from roadmap
3. Begin Phase 1 implementation

---

## Document History

- 2026-01-01: Initial draft based on idea doc
- 2026-01-01: Completed full Q&A session (Q1-Q35)
- 2026-01-01: Finalized MVP scope and implementation roadmap
