# Time Tracking PDF Timesheet

## Status
Idea - Not Started

## Plugin Candidate
Yes - Extends the time-tracking plugin (`plugins/time-tracking`).

## Problem
`plugins/time-tracking/backend/report_generator.py` exists but is not wired into a user-facing flow; users cannot get a printable timesheet for a month or period (for employer or labor-law records).

## Proposed Solution
- Decide whether to wire up and finish `report_generator.py` or replace it
- Export button on the time-tracking page: month or custom range, per company
- PDF with daily entries, breaks, totals and overtime/compliance flags

## Implementation Notes
- The generator was deliberately left untouched by the system-cleanup task; this idea records the open question.
- Cover the output with tests before changing it.

## Related
- docs/ideas/done/time-tracking.md
