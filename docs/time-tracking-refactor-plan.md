# Time Tracking Plugin Refactoring Plan

## Executive Summary

The time tracking plugin currently has a per-company view architecture that prevents users from seeing time overlaps across different companies. This document outlines the refactoring needed to implement a unified multi-company view with overlap detection and resolution.

## Current State Analysis

### Implementation Files
- **Active Implementation**: `plugins/time-tracking/frontend/index.js` (2545 lines)
  - JavaScript-based, fully functional
  - Has calendar AND table views (toggle between them)
  - Per-company filtering via dropdown

- **Incomplete Implementation**: `plugins/time-tracking/frontend/index.ts` + React components
  - TypeScript version, partially implemented
  - Not currently used by the plugin system
  - Should be removed or completed

### Critical Issues Identified

#### 1. Per-Company Data Isolation
**Current Behavior:**
```javascript
// Line 446, 494 in index.js
const records = await apiGet(`/records?from=${fromDate}&to=${toDate}&company_id=${selectedCompanyId}`)
```
- User selects ONE company at a time
- Cannot see entries from other companies
- Overlaps are invisible until after creation

**Impact:** User can create:
- Company A: 9:00-12:00
- Company B: 11:00-13:00 (OVERLAP!)
- Database allows this (unique constraint per company)
- No validation prevents it

#### 2. Form State Management Issues
**Cancel doesn't reload data:**
```javascript
// Line 636 in index.js
function closeModal() {
  setShowAddModal(false);
  setEditingRecord(null);
  setFormData({...defaults});
  // NO fetchData() call - UI shows stale data
}
```

**Impact:** If backend validation fails or user cancels mid-edit, UI shows incorrect state until page reload.

#### 3. Database Model
```python
# plugins/time-tracking/backend/models.py:115-116
UniqueConstraint("user_id", "date", "company_id", name="uq_tt_user_date_company")
```
- Allows one record per user/date/company
- Does NOT prevent overlaps across companies
- No backend validation for cross-company conflicts

## Approved Design (from Mockup v3)

### UI Features

#### 1. Company Filter (Toggle Buttons)
- No "All Companies" button needed
- 3 company badges (Acme, TechCorp, Consulting)
- All active by default = show all companies
- Click to toggle individual companies on/off
- Backend queries based on active filters

#### 2. Unified Calendar View
- Shows entries from ALL active companies
- Company badges with color coding:
  - 🔵 Acme Corp (Blue)
  - 🟢 TechCorp (Green)
  - 🟡 Consulting (Yellow)
- Day type displayed for each entry (Work, Vacation, etc.)
- Overlap warning: Red background (no text overlay)

#### 3. Unified Table View
- Same month navigation as calendar
- Company column with color-coded badges
- Shows ALL entries from active companies
- Overlap rows: Red background + "Fix" button

#### 4. Overlap Handling
- Red background indicates overlap
- Entries ARE editable (no cursor-not-allowed)
- "Fix" button in Actions column
- User must resolve before system allows save

#### 5. Monthly Submission
- Company dropdown shows ONLY companies with data in selected month
- Format: "Acme Corp (15 days)"
- Stats calculated per selected company
- Generates report for one company at a time

### Data Flow

```
User Action: Add/Edit Entry
    ↓
Frontend: Collect form data (date, company, times)
    ↓
POST /api/v1/plugin/time-tracking/records
    ↓
Backend: Validate cross-company overlaps
    ↓
If overlap detected:
    → Return 400 with error details
    → Frontend shows validation warning
    → User adjusts times
    ↓
If valid:
    → Save to database
    → Return success
    → Frontend reloads ALL data (fetchData() + fetchCalendarRecords())
```

## Implementation Tasks

### Phase 1: Backend Validation (Highest Priority)

**File:** `plugins/time-tracking/backend/services.py`

**Add overlap detection:**
```python
def validate_time_overlap(
    db: Session,
    user_id: UUID,
    date: date,
    check_in: time,
    check_out: time,
    company_id: UUID,
    exclude_entry_id: UUID | None = None
) -> tuple[bool, list[dict]]:
    """
    Check for time overlaps across ALL companies for this user/date.

    Returns:
        (is_valid, conflicting_entries)
    """
    # Query ALL entries for user on this date (all companies)
    existing_entries = db.query(TimeEntry).join(TimeRecord).filter(
        TimeRecord.user_id == user_id,
        TimeRecord.date == date,
        TimeEntry.id != exclude_entry_id if exclude_entry_id else True
    ).all()

    conflicts = []
    for entry in existing_entries:
        if times_overlap(check_in, check_out, entry.check_in, entry.check_out):
            conflicts.append({
                'entry_id': entry.id,
                'company_id': entry.record.company_id,
                'check_in': entry.check_in,
                'check_out': entry.check_out,
            })

    return len(conflicts) == 0, conflicts
```

**Update create_record and update_record:**
```python
def create_record(self, user_id: UUID, record_date: date, ...) -> TimeRecord:
    # Existing validation...

    # NEW: Check for overlaps if work day
    if day_type == DayType.WORK and check_in and check_out:
        is_valid, conflicts = validate_time_overlap(
            self.db, user_id, record_date, check_in, check_out, company_id
        )
        if not is_valid:
            raise ValueError(f"Time overlap detected with existing entries: {conflicts}")

    # Continue with save...
```

**API endpoint changes:**
```python
# routes.py
@router.post("/records")
async def create_time_record(...):
    try:
        record = service.create_record(...)
        return record
    except ValueError as e:
        # Overlap or other validation error
        raise HTTPException(status_code=400, detail=str(e))
```

### Phase 2: Backend API Updates

**Make company_id optional in list endpoint:**

```python
# plugins/time-tracking/backend/routes.py
@router.get("/records")
async def list_records(
    from_date: str,
    to_date: str,
    company_id: UUID | None = None,  # Made optional
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(TimeRecord).filter(
        TimeRecord.user_id == current_user.id,
        TimeRecord.date >= from_date,
        TimeRecord.date <= to_date
    )

    # Only filter by company if provided
    if company_id:
        query = query.filter(TimeRecord.company_id == company_id)

    return query.all()
```

**Include company info in response:**
```python
# schemas.py
class TimeRecordResponse(BaseModel):
    id: UUID
    date: date
    company_id: UUID
    company_name: str | None  # NEW: Include for display
    day_type: str
    # ... other fields
```

### Phase 3: Frontend Refactoring

**File:** `plugins/time-tracking/frontend/index.js`

#### 3.1: Remove Company Dropdown

**Remove:**
```javascript
// Lines 768-775
<select value={selectedCompanyId} onChange={(e) => setSelectedCompanyId(e.target.value)}>
  {companies.map(c => h("option", { key: c.id, value: c.id }, c.name))}
</select>
```

#### 3.2: Add Company Filter State

```javascript
// Replace line 200
const [selectedCompanyId, setSelectedCompanyId] = useState(null);

// With:
const [activeCompanyFilters, setActiveCompanyFilters] = useState([]);

// Initialize with all companies on mount
useEffect(() => {
  if (companies.length > 0 && activeCompanyFilters.length === 0) {
    setActiveCompanyFilters(companies.map(c => c.id));
  }
}, [companies]);
```

#### 3.3: Update Data Fetching

```javascript
// Lines 446, 494 - Update API calls
async function fetchCalendarRecords() {
  try {
    const { year, month } = calendarMonth;
    const lastDay = new Date(year, month, 0).getDate();
    const fromDate = `${year}-${String(month).padStart(2, "0")}-01`;
    const toDate = `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;

    // NEW: Build query with multiple company IDs or none for all
    let url = `/records?from=${fromDate}&to=${toDate}`;
    if (activeCompanyFilters.length > 0 && activeCompanyFilters.length < companies.length) {
      // Only add filter if not showing all companies
      url += activeCompanyFilters.map(id => `&company_id=${id}`).join('');
    }

    const records = await apiGet(url);
    setCalendarRecords(records);
  } catch (e) {
    console.error("Failed to fetch calendar records:", e);
  }
}
```

#### 3.4: Fix Cancel Behavior

```javascript
// Line 636 - Add data reload
function closeModal() {
  setShowAddModal(false);
  setEditingRecord(null);
  setFormData({
    date: new Date().toISOString().split("T")[0],
    day_type: "work",
    check_in: "09:00",
    check_out: "17:00",
    work_location: "remote",
    notes: "",
  });

  // NEW: Reload data to ensure UI is in sync
  fetchData();
  fetchCalendarRecords();
}

// Line 670 - Same for entry edit
function closeEntryEdit() {
  setEditingEntry(null);
  setEntryFormData({ check_in: "", check_out: "" });

  // NEW: Reload data
  fetchData();
  fetchCalendarRecords();
}
```

#### 3.5: Add Company Filter UI

```javascript
// After line 106 (after view toggle), add filter legend
h(
  "div",
  { className: "bg-white border border-gray-200 rounded-lg p-3 mb-4 shadow-sm" },
  h(
    "div",
    { className: "flex items-center gap-4 text-sm" },
    h("span", { className: "font-medium text-gray-700" }, "Filter by Company:"),

    // Company filter buttons
    companies.map(company =>
      h(
        "button",
        {
          key: company.id,
          onClick: () => toggleCompanyFilter(company.id),
          className: `company-filter px-3 py-1.5 rounded-lg text-xs font-medium ${
            activeCompanyFilters.includes(company.id) ? "active" : ""
          } badge-${company.id}` // Style based on company
        },
        company.name
      )
    ),

    h("span", { className: "ml-auto text-xs text-gray-500" },
      "🔴 Red background = Time overlap (must fix to edit)")
  )
)

// Add toggle function
function toggleCompanyFilter(companyId) {
  setActiveCompanyFilters(prev => {
    if (prev.includes(companyId)) {
      return prev.filter(id => id !== companyId);
    } else {
      return [...prev, companyId];
    }
  });
}

// Trigger refetch when filters change
useEffect(() => {
  if (activeCompanyFilters.length > 0) {
    fetchCalendarRecords();
  }
}, [activeCompanyFilters]);
```

#### 3.6: Add Overlap Detection to UI

```javascript
// Add function to check if record has overlaps
function hasOverlap(record) {
  // Backend will return overlap flag
  return record.has_overlap === true;
}

// Update calendar day rendering (line 983)
const record = cell.isCurrentMonth
  ? getRecordForDate(cell.year, cell.month, cell.day)
  : null;

return h(
  "div",
  {
    key: idx,
    onClick: () => cell.isCurrentMonth && setSelectedDay(cell),
    className: `min-h-20 p-2 border-b border-r cursor-pointer transition-colors ${
      !cell.isCurrentMonth
        ? "bg-gray-50 text-gray-400"
        : isWeekendDay
          ? "bg-gray-50"
          : hasOverlap(record)
            ? "overlap-warning"  // Red background
            : "bg-white hover:bg-blue-50"
    }`,
  },
  // Day content...
);
```

#### 3.7: Update Monthly Submission

```javascript
// Get companies with data in selected month
const companiesWithData = useMemo(() => {
  const counts = {};
  monthRecords.forEach(record => {
    counts[record.company_id] = (counts[record.company_id] || 0) + 1;
  });

  return companies
    .filter(c => counts[c.id] > 0)
    .map(c => ({
      ...c,
      dayCount: counts[c.id]
    }));
}, [monthRecords, companies]);

// Update dropdown (line 1404)
h(
  "select",
  {
    value: selectedSubmissionCompany,
    onChange: (e) => setSelectedSubmissionCompany(e.target.value),
    className: "w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
  },
  companiesWithData.map(c =>
    h("option", { key: c.id, value: c.id },
      `${c.name} (${c.dayCount} days)`)
  )
)
```

### Phase 4: CSS Updates

**Add to styles section (line 8):**
```css
.overlap-warning {
    background-color: #FEE2E2;
    border: 2px solid #EF4444;
}

.company-filter {
    cursor: pointer;
    transition: all 0.2s;
    opacity: 0.6;
}

.company-filter.active {
    opacity: 1;
    transform: scale(1.1);
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.company-filter:hover {
    opacity: 0.8;
    transform: scale(1.05);
}

/* Company-specific badge colors */
.badge-acme { background-color: #3B82F6; color: white; }
.badge-techcorp { background-color: #10B981; color: white; }
.badge-consulting { background-color: #F59E0B; color: white; }
```

### Phase 5: Cleanup

**Decision needed: Keep index.js OR migrate to TypeScript**

**Option A: Keep JavaScript (Faster)**
- Delete unused TypeScript files:
  - `index.ts`
  - `components/TimeTrackingPage.tsx`
  - `components/WeekView.tsx`
  - `components/TimeRecordForm.tsx`
- Keep only `index.js` and `CompanyTimeSettingsWidget.tsx`

**Option B: Migrate to TypeScript (Better long-term)**
- Complete the TypeScript implementation
- Port all functionality from `index.js`
- Remove `index.js`
- Update build process

**Recommendation:** Option A for faster delivery, Option B for maintainability.

## Testing Requirements

### Backend Tests

**File:** `tests/unit/test_services/test_time_tracking.py`

```python
def test_overlap_detection_same_company():
    """Test overlap detection for same company."""
    # Create entry 9:00-12:00 for Company A
    # Try to create 11:00-13:00 for Company A
    # Should fail with overlap error

def test_overlap_detection_different_companies():
    """Test overlap detection across companies."""
    # Create entry 9:00-12:00 for Company A
    # Try to create 11:00-13:00 for Company B
    # Should fail with overlap error

def test_no_overlap_sequential():
    """Test sequential entries don't trigger overlap."""
    # Create entry 9:00-12:00
    # Create entry 12:00-15:00
    # Should succeed (no overlap)

def test_overlap_validation_on_update():
    """Test overlap detection when updating existing entry."""
    # Create entry 9:00-12:00
    # Create entry 13:00-15:00
    # Update first to 9:00-14:00
    # Should fail with overlap error
```

### Frontend Tests

**File:** `plugins/time-tracking/frontend/__tests__/index.test.js`

```javascript
describe('Company Filtering', () => {
  test('All companies active by default', () => {
    // Verify all filter buttons have "active" class on load
  });

  test('Toggle company filter on/off', () => {
    // Click filter button
    // Verify active state changes
    // Verify data refetch with correct company IDs
  });

  test('Fetch all data when all filters active', () => {
    // All buttons active
    // Verify API call has no company_id parameter
  });
});

describe('Overlap Detection', () => {
  test('Shows red background for overlapping entries', () => {
    // Render calendar with overlap data
    // Verify CSS class applied
  });

  test('Allows editing overlapping entries', () => {
    // Click on overlap entry
    // Verify edit modal opens
    // Verify "Fix" button visible
  });
});

describe('Data Refresh', () => {
  test('Reload data on cancel', () => {
    // Open edit modal
    // Click cancel
    // Verify fetchData() and fetchCalendarRecords() called
  });
});
```

## Migration Path

### Step 1: Backend Validation (1-2 days)
- Implement overlap detection function
- Update create/update record methods
- Add tests
- Deploy to test environment

### Step 2: Frontend State Management (1 day)
- Add company filter state
- Fix cancel behavior
- Test data reload

### Step 3: Frontend UI Updates (2-3 days)
- Remove company dropdown
- Add filter legend
- Update calendar/table rendering
- Add overlap styling
- Update monthly submission

### Step 4: Testing & QA (1-2 days)
- Unit tests
- Integration tests
- Manual testing
- Edge case validation

### Step 5: Documentation & Deployment (1 day)
- Update RELEASENOTES.md
- User documentation
- Deploy to production

**Total Estimated Time: 6-9 days**

## Risk Mitigation

### Breaking Changes
- **Risk:** Existing data might have overlaps
- **Mitigation:** Run migration script to detect and flag existing overlaps
- **Action:** Provide admin tool to review and fix

### Performance
- **Risk:** Querying all companies could be slow
- **Mitigation:** Add database indexes on user_id, date, company_id
- **Action:** Monitor query performance

### User Experience
- **Risk:** Users confused by new filtering
- **Mitigation:** Add tooltip/help text
- **Action:** Beta test with small group first

## Success Criteria

✅ Users can see entries from all companies in unified view
✅ Overlap detection prevents conflicting time entries
✅ Calendar and table views show same data with different layouts
✅ Month navigation works for both views
✅ Overlapping entries are editable with clear warnings
✅ Monthly reports generated per company
✅ All tests pass
✅ No performance degradation

## Post-Implementation

### Monitoring
- Track overlap detection frequency
- Monitor API response times
- Collect user feedback

### Future Enhancements
- Bulk edit for fixing overlaps
- Automatic overlap resolution suggestions
- Export combined reports across companies
- Mobile-responsive improvements

---

**Document Version:** 1.0
**Last Updated:** 2026-01-01
**Status:** Ready for Implementation
