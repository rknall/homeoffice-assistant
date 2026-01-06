# Calendar Integration Specification

## Status
Specification - Ready for Implementation

**UI Mockups:** See [`calendar-mockups.md`](./calendar-mockups.md) for detailed UI layouts and component specifications.

## Overview
A consolidated calendar view that provides users with a unified overview of their work week and month, combining HomeOffice events (business trips) with external calendar sources and todo items.

## Core Problem
Users need to see what's happening across all their work contexts (business trips, work calendar obligations, todos) in a single unified view to effectively plan their week and month.

## Goals
- Provide week and month calendar views
- Display HomeOffice events alongside external calendar events
- Support multiple calendar sources per user (one per company)
- Enable quick navigation and overview of current and upcoming obligations

## Non-Goals (Future Versions)
- Bidirectional sync (creating/editing external events from HomeOffice)
- ICS file export/import
- CalDAV support
- Automatic time-blocking for travel
- Recurring events management
- Calendar event creation from calendar view

## User Stories

### Primary Use Cases
1. As a user, I want to see my current week's schedule combining my business trips and work calendar events
2. As a user, I want to navigate between week and month views to get different perspectives on my schedule
3. As a user, I want to connect my work Google Calendar for each company I work with
4. As a user, I want to see my todos with due dates in the calendar so I can plan my work
5. As a user, I want to distinguish between different types of calendar entries (events, external events, todos) at a glance

### Secondary Use Cases
6. As a user, I want to click on HomeOffice events to open the event detail page
7. As a user, I want to click on external calendar events to see details and jump to Google Calendar
8. As a user, I want the calendar to respect my locale settings (week start day)

## Technical Specification

### 1. Data Model

#### New Model: CalendarConnection
```python
class CalendarConnection(Base, TimestampMixin):
    """Connection between a user, company, and external calendar."""

    id: UUID (primary key)
    user_id: UUID (FK to users)
    company_id: UUID (FK to companies)
    calendar_type: str  # "google_calendar" for MVP
    calendar_id: str  # External calendar identifier from Google
    calendar_name: str  # Display name
    color: str  # Hex color for display (e.g., "#4285F4")

    # OAuth credentials (encrypted)
    access_token: str
    refresh_token: str
    token_expires_at: datetime

    # Settings
    is_active: bool (default True)
    sync_enabled: bool (default True)
    last_sync_at: datetime (nullable)

    # Relationships
    user: User
    company: Company
```

#### New Model: ExternalCalendarEvent (cached)
```python
class ExternalCalendarEvent(Base, TimestampMixin):
    """Cached external calendar events for display."""

    id: UUID (primary key)
    calendar_connection_id: UUID (FK to calendar_connections)
    external_event_id: str  # ID from Google Calendar

    title: str
    description: str (nullable)
    start_time: datetime
    end_time: datetime
    all_day: bool
    location: str (nullable)

    # Link to external event
    external_url: str (nullable)

    # Relationships
    calendar_connection: CalendarConnection
```

### 2. Calendar View Components

#### Frontend Page Structure
```
/calendar - Main calendar page

Components:
- CalendarView (container)
  - CalendarHeader (view switcher, navigation, filters)
  - WeekView (weekly grid display)
  - MonthView (monthly grid display)
  - EventModal (for external event details)
```

#### Calendar Item Types
1. **HomeOffice Events** (from Event model)
   - Display: Event name, dates
   - Color: Configurable per company or default
   - Click: Navigate to event detail page
   - Source: Database (events table)

2. **External Calendar Events** (from ExternalCalendarEvent model)
   - Display: Event title, time
   - Color: From CalendarConnection.color
   - Click: Open modal with details + link to Google Calendar
   - Source: Cached from Google Calendar API

3. **Todos** (from Todo model)
   - Display: Todo title, due date
   - Color: Distinct todo color (configurable)
   - Click: Open todo detail/edit modal
   - Source: Database (todos table with due_date set)
   - Filter: Only show todos with due_date

### 3. Google Calendar Integration

#### Authentication Flow
1. User navigates to Company Settings page
2. "Connected Calendars" section shows existing connections
3. Click "Connect Google Calendar" button
4. OAuth 2.0 flow (using Google Calendar API)
5. User authorizes access (read-only scope)
6. User selects which Google Calendar to connect
7. CalendarConnection record created with tokens
8. Initial sync triggered

#### API Scopes Required
- `https://www.googleapis.com/auth/calendar.readonly`

#### Sync Strategy
- **Initial sync**: Load events from -30 days to +90 days
- **Background sync**: Every 15 minutes for active connections
- **Manual refresh**: Button in calendar view to force sync
- **Incremental sync**: Use Google Calendar sync token for efficiency

#### Rate Limiting & Caching
- Cache external events in database (ExternalCalendarEvent table)
- Display from cache, sync in background
- Respect Google API quotas (typically 1M requests/day)

### 4. UI/UX Specifications

#### Calendar View Types
1. **Week View** (default)
   - Shows 7 days in columns
   - Time slots from 00:00 to 23:00
   - All-day events in header row
   - Respects locale week start day

2. **Month View**
   - Shows 4-6 weeks in grid
   - Each day cell shows:
     - Day number
     - Event indicators (colored dots/bars)
     - Max 3 visible items per day
     - "+N more" link for overflow
   - Click day to see day details

#### Visual Differentiation
- **Color coding**:
  - Each CalendarConnection has a configurable color
  - HomeOffice events use company color (configurable)
  - Todos use dedicated todo color (configurable)
  - Color picker in connection/company settings

- **Visual indicators**:
  - External events: Show small calendar icon
  - HomeOffice events: Show location icon if city/country set
  - Todos: Show checkbox icon

#### Locale Settings Integration
- Use existing locale settings (User model)
- Respect `week_start_day` preference (Sunday/Monday/etc.)
- Use locale-appropriate date/time formatting

#### Navigation
- Previous/Next week or month buttons
- "Today" button to jump to current week/month
- Date picker to jump to specific date
- Tab/button to switch between week/month views

#### Filtering & Display Options
- Checkboxes to toggle visibility:
  - [ ] HomeOffice Events
  - [ ] External Calendars (expandable list per connection)
  - [ ] Todos
- Company filter dropdown (show only selected companies)
- Settings saved in user preferences

### 5. API Endpoints

#### Calendar Connections
```
POST   /api/v1/calendar-connections                    # Initiate OAuth
GET    /api/v1/calendar-connections                    # List user's connections
GET    /api/v1/calendar-connections/{id}               # Get connection details
PUT    /api/v1/calendar-connections/{id}               # Update connection (color, settings)
DELETE /api/v1/calendar-connections/{id}               # Remove connection
POST   /api/v1/calendar-connections/{id}/sync          # Manual sync trigger
GET    /api/v1/calendar-connections/oauth/callback     # OAuth callback handler
```

#### Calendar Data
```
GET    /api/v1/calendar/events?start={date}&end={date} # Get all calendar items for range
```

Returns combined response:
```json
{
  "events": [
    {
      "id": "uuid",
      "type": "homeoffice_event",
      "title": "Berlin Trip",
      "start": "2026-01-15",
      "end": "2026-01-17",
      "all_day": true,
      "company_id": "uuid",
      "company_name": "Acme Corp",
      "color": "#FF5733",
      "url": "/events/uuid"
    },
    {
      "id": "uuid",
      "type": "external_event",
      "title": "Team Meeting",
      "start": "2026-01-16T14:00:00Z",
      "end": "2026-01-16T15:00:00Z",
      "all_day": false,
      "connection_id": "uuid",
      "connection_name": "Work Calendar",
      "color": "#4285F4",
      "external_url": "https://calendar.google.com/...",
      "location": "Conference Room A"
    },
    {
      "id": "uuid",
      "type": "todo",
      "title": "Submit expense report",
      "start": "2026-01-18",
      "all_day": true,
      "color": "#9C27B0",
      "url": "/todos/uuid"
    }
  ]
}
```

### 6. Configuration UI

#### Company Settings Page
Add new section: "Connected Calendars"
- List of connected calendars for this company (for current user)
- Each row shows:
  - Calendar name
  - Color picker
  - Last sync time
  - Active toggle
  - Remove button
- "Connect Google Calendar" button

#### User Preferences
Add calendar preferences:
- Default view (week/month)
- Default visibility toggles
- Todo color preference

### 7. Implementation Phases

#### Phase 1: Calendar View Foundation
- Create calendar view page and routing
- Implement week and month view components
- Display existing HomeOffice events
- Basic navigation (prev/next, today, date picker)
- View switcher (week/month)
- Locale integration (week start day)

#### Phase 2: Google Calendar Integration
- Implement CalendarConnection and ExternalCalendarEvent models
- Alembic migration
- Google OAuth flow
- Calendar selection UI
- Initial sync implementation
- Display external events in calendar view

#### Phase 3: Todos & Polish
- Add todos with due dates to calendar view
- Implement external event modal
- Color configuration UI
- Filtering and visibility toggles
- Background sync service
- Manual refresh

#### Phase 4: Performance & UX
- Caching optimization
- Loading states and error handling
- Mobile responsive design
- Accessibility improvements
- User preferences persistence

### 8. Technical Dependencies

#### Backend
- `google-auth-oauthlib` - Google OAuth
- `google-api-python-client` - Google Calendar API
- Existing FastAPI/SQLAlchemy stack

#### Frontend
- Calendar component library (options):
  - `react-big-calendar` (feature-rich, widely used)
  - `@fullcalendar/react` (comprehensive, good docs)
  - Custom implementation with date-fns
- Date utilities: `date-fns` (already in use)

### 9. Security Considerations

- OAuth tokens stored encrypted (use Fernet like integration configs)
- Tokens scoped to read-only calendar access
- Per-user authentication (no service accounts)
- Token refresh handling
- Secure token storage in database
- HTTPS required for OAuth callbacks

### 10. Testing Requirements

#### Backend Tests
- CalendarConnection CRUD operations
- OAuth flow (mocked)
- Google Calendar API sync (mocked)
- Calendar events endpoint (combined data)
- Token refresh logic

#### Frontend Tests
- Calendar view rendering (week/month)
- Navigation and date switching
- Event display and interaction
- Filtering and visibility toggles
- OAuth initiation flow

### 11. Future Enhancements (Post-MVP)
- Export HomeOffice events to external calendars
- Two-way sync (edit external events)
- CalDAV support for other calendar providers
- ICS file import/export
- Automatic travel time blocking
- Recurring events support
- Calendar sharing between users
- Event creation from calendar view
- Drag-and-drop rescheduling
- Integration with other calendar providers (Microsoft 365, Apple iCloud)

## Open Questions
None - specification complete

## References
- Original idea: `/docs/ideas/calendar-integration.md`
- Google Calendar API: https://developers.google.com/calendar/api/guides/overview
- Existing Event model: `/src/models/event.py`
- Existing Todo model: `/src/models/todo.py`

## Approval
- Specification reviewed: [Pending]
- Ready for implementation: [Pending]
