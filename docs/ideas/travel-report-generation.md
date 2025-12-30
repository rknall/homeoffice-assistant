# Travel Report Generation

## Status
Idea - Partially Planned (deferred from v0.2)

## Problem
After a business trip, users often need to create a summary report for their employer or client. This is different from the expense report - it's a narrative document with photos and key takeaways.

## Proposed Features

### Report Content
- Event summary (dates, location, purpose)
- Key contacts met (from Contacts)
- Notes/observations (filtered by type=report_section)
- Selected photos (from Immich, include_in_report=true)
- Action items / follow-ups

### Output Formats
- PDF (professional layout)
- DOCX (editable)
- Markdown (for further editing)

### Report Templates
- Default professional template
- Custom templates per company
- Drag-and-drop section ordering

## Implementation Notes

### Data Sources
```python
class TravelReportData:
    event: Event
    contacts: list[Contact]
    notes: list[Note]  # filtered by type
    photos: list[PhotoReference]  # filtered by include_in_report
    todos: list[Todo]  # completed follow-ups
```

### Generation Flow
1. User clicks "Generate Travel Report"
2. Preview shows assembled content
3. User can reorder sections, edit text
4. Generate final document
5. Optional: Email to recipients

### Photo Handling
- Fetch from Immich by asset ID
- Resize for document
- Include captions

## UI Components
- Report preview/editor page
- Section reordering (drag and drop)
- Photo selection from Immich
- Template selector

## Reference
- REQUIREMENTS.md lines 153-166

## Related
- Immich integration
- Contact management
- Notes system
- Expense report (different purpose, but similar flow)
