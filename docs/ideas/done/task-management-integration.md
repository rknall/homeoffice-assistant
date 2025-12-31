# Task Management (Internal Todo System)

## Status
Implemented in v0.3.0

## What Was Implemented

### Todo Management
- Full CRUD operations on event detail page with tabbed interface
- Category-based organization (Travel, Accommodation, Preparation, Equipment, Contacts, Follow-up, Other)
- Due date tracking with overdue highlighting
- Quick-complete from dashboard Action Items
- Auto-complete: Report-related todos automatically marked done when expense reports are sent/exported
- Incomplete todo count badge on Todos tab
- Sorted display: incomplete todos first (by due date), then completed

### Todo Templates
- Predefined todo templates that users can apply to events with a single click
- Templates include calculated due dates relative to event start/end dates
- Global system templates seeded on first run (Business Trip, Conference Event sets)
- User-defined custom templates manageable in Settings > Todo Templates
- "Add from Template" button on event Todos tab for multi-select template application
- Template picker modal shows computed due dates before applying

## What's NOT Implemented (Moved to Separate Idea)

External task sync (Todoist, Things, Microsoft To Do, CalDAV) has been moved to:
- [Task Import/Export Integration](task-import-export.md)

## Related
- [Task Import/Export](task-import-export.md) - External sync (not started)
- Event detail page Todos tab
