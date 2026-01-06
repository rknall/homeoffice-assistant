# Calendar Integration

## Status
Specification Complete - See `/docs/specs/calendar-integration.md`

**Note:** This document contains the original brainstorming. The full specification with implementation details is in `/docs/specs/calendar-integration.md`.

## Problem
Events have dates that could sync with calendar applications. Users may want to see their business trips in their regular calendar, or import calendar events as trips.

## Proposed Features

### Export to Calendar
- Generate ICS files for events
- CalDAV sync (push events to calendar server)
- Google Calendar API integration

### Import from Calendar
- Import events from ICS files
- Subscribe to CalDAV calendars
- Auto-create trips from calendar events matching criteria

## Use Cases
- See business trips in Outlook/Google Calendar
- Block time automatically when trip is created
- Import company travel calendar to create events

## Implementation Notes

### ICS Export (Simple)
- Generate .ics file download per event
- Include event name, dates, location
- Optional: Add todos as VTODO items

### CalDAV Sync (Advanced)
- Connect to Nextcloud/Google/etc. calendar
- Two-way sync of event dates
- Handle conflicts

## Configuration
- Calendar provider (ICS export, CalDAV, Google)
- Calendar URL / credentials
- Sync direction (export only, import only, bidirectional)
- Event category/calendar to sync

## Reference
- REQUIREMENTS.md line 248

## Related
- Event management
- Todo system
