# Incremental Expense Submission

## Status
Idea - Not Started

## Plugin Candidate
No - This is a core feature. Expense submission workflow is fundamental to the app.

## Problem
Currently, expense reports are generated as a single batch containing all expenses for an event. In practice, users often need to submit expenses incrementally:

- Submit travel costs immediately after booking
- Submit accommodation after check-out
- Submit remaining expenses after the trip ends
- Re-submit rejected expenses after correction

Without tracking which expenses have already been submitted, users risk:
- Submitting the same expense twice
- Missing expenses in submissions
- Confusion about what's been sent vs. what's pending

## Current State

The existing `ExpenseStatus` enum has:
```python
class ExpenseStatus(str, Enum):
    PENDING = "pending"      # Not yet processed
    INCLUDED = "included"    # Included in a report
    REIMBURSED = "reimbursed"  # Money received
```

This doesn't capture the **submission** aspect - whether an expense has been sent to the employer/client.

## Proposed Solution

### New Status Flow

```
PENDING → SUBMITTED → REIMBURSED
              ↓
          REJECTED → (edit) → PENDING
```

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet submitted, can be edited freely |
| `SUBMITTED` | Sent to employer, awaiting reimbursement |
| `REIMBURSED` | Money received, complete |
| `REJECTED` | Employer rejected, needs correction |

### Submission Tracking

Track each submission as a separate entity:

```python
class ExpenseSubmission(Base, TimestampMixin):
    """Record of an expense report submission."""
    id: UUID
    event_id: UUID

    # When/how submitted
    submitted_at: datetime
    submission_method: str  # email, portal, paper

    # Reference
    reference_number: str | None  # Employer's reference if provided

    # Content snapshot
    total_amount: Decimal
    currency: str
    expense_count: int

    # Status
    status: str  # pending, acknowledged, partially_reimbursed, complete

    notes: str | None


class ExpenseSubmissionItem(Base):
    """Link between submission and individual expenses."""
    id: UUID
    submission_id: UUID
    expense_id: UUID

    # Snapshot of expense at submission time
    amount: Decimal
    currency: str
```

### Updated Expense Model

```python
class Expense(Base, TimestampMixin):
    # ... existing fields ...

    status: ExpenseStatus  # Updated enum

    # Submission tracking
    submitted_at: datetime | None
    submission_id: UUID | None  # FK to ExpenseSubmission
```

### Updated Enum

```python
class ExpenseStatus(str, Enum):
    PENDING = "pending"        # Not yet submitted
    SUBMITTED = "submitted"    # Sent, awaiting response
    REIMBURSED = "reimbursed"  # Complete
    REJECTED = "rejected"      # Needs correction
```

Note: Removing `INCLUDED` as it's ambiguous. "Submitted" is clearer.

## Report Generation Changes

### Generate Report Dialog

```
┌─────────────────────────────────────────────────────┐
│ Generate Expense Report                              │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Include expenses:                                    │
│   ○ All pending expenses (5 expenses, €1,234.56)    │
│   ○ Select specific expenses                         │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ☑ 2024-12-15  Flight to Vienna      €345.00    │ │
│ │ ☑ 2024-12-15  Hotel booking         €450.00    │ │
│ │ ☑ 2024-12-16  Taxi to client        €35.50     │ │
│ │ ☐ 2024-12-16  Lunch (submitted)     €24.00     │ │
│ │ ☑ 2024-12-17  Train ticket          €89.00     │ │
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ After generation:                                    │
│   ☑ Mark selected expenses as "Submitted"           │
│                                                      │
│              [Cancel]  [Generate Report]             │
└─────────────────────────────────────────────────────┘
```

### Report Includes Metadata

Generated reports should include:
- Submission date
- Which expenses are included (vs. previously submitted)
- Running total of all submissions for this event

## UI Changes

### Expense List

Add visual indicators:
- **Pending**: No badge (default state)
- **Submitted**: Blue badge with date
- **Reimbursed**: Green checkmark
- **Rejected**: Red badge, clickable to see reason

### Filters

Add filter options:
- Show: All / Pending only / Submitted / Reimbursed
- Quick action: "Generate report for pending"

### Expense Detail

Show submission history:
```
Submission History
──────────────────
2024-12-20  Submitted in report #1
2024-12-22  Rejected - "Missing receipt"
2024-12-23  Re-submitted in report #2
2025-01-05  Reimbursed
```

### Bulk Actions

- Select multiple → "Mark as Submitted"
- Select multiple → "Mark as Reimbursed"
- Select submitted → "Mark as Rejected"

## API Changes

### New Endpoints

```
# Submissions
GET    /api/v1/events/{id}/submissions
POST   /api/v1/events/{id}/submissions
GET    /api/v1/submissions/{id}

# Expense status updates
PATCH  /api/v1/expenses/{id}/status
POST   /api/v1/expenses/bulk-status
```

### Updated Report Endpoint

```
POST /api/v1/events/{id}/reports/expenses
{
    "expense_ids": ["uuid1", "uuid2", ...],  # Optional, defaults to all pending
    "mark_as_submitted": true,
    "submission_method": "email",
    "notes": "Initial submission for December trip"
}
```

## Migration Considerations

### Existing Data

- All expenses with `INCLUDED` status → migrate to `SUBMITTED`
- Add `submitted_at` field, set to `updated_at` for migrated records
- `PENDING` and `REIMBURSED` remain unchanged

### Backwards Compatibility

- Old behavior (generate report for all) still works
- New "pending only" becomes the default
- UI clearly shows what's included

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Edit submitted expense | Warn user, optionally reset to PENDING |
| Delete submitted expense | Warn that it was already submitted |
| Partial reimbursement | Track per-expense or per-submission? (defer) |
| Multiple events, same submission | Not supported (submit per-event) |

## Future Enhancements (Out of Scope)

- Email tracking (did employer receive it?)
- Portal integration (auto-submit to employer system)
- Approval workflows
- Split reimbursements

## Related
- Expense management (core)
- Report generation (core)
- [Travel Report Generation](travel-report-generation.md) - Different purpose, but similar "what's included" question
