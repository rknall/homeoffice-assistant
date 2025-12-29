# Release Notes

## Version 0.3.0-alpha2

### Major Features

#### Todo Management
- Full todo CRUD on event detail page with tabbed interface
- Category-based organization (Travel, Accommodation, Preparation, Equipment, Contacts, Follow-up, Other)
- Due date tracking with overdue highlighting
- Quick-complete from dashboard Action Items with checkbox
- Auto-complete: Report-related todos automatically marked done when expense reports are sent or exported
- Incomplete todo count badge on Todos tab
- Sorted display: incomplete todos first (by due date), then completed

#### Event Detail Page Tabs
- Reorganized event detail page with tab navigation: Expenses | Documents | Photos | Todos
- Cleaner separation of content sections
- Tab badges showing relevant counts (e.g., incomplete todos)

#### Dashboard Redesign
- Action-oriented dashboard replacing the previous event list duplication
- Stats row showing Active, Upcoming, and Past event counts with clickable filters
- Upcoming Events timeline showing events with start date >= today, sorted chronologically
- Action Items panel showing events needing expense reports and incomplete todos
- Expense breakdown chart showing spending by category for the last 90 days
- New `/dashboard/summary` API endpoint for aggregated dashboard data

#### Events Page Redesign
- Timeline-based grouping: Upcoming, Active, Recently Completed, Older
- Filter bar with status pills (All/Upcoming/Active/Past), company dropdown, and search
- Enhanced event cards showing expense count, total amount, and incomplete todos
- URL state synchronization for filters (shareable filtered views)
- Collapsible timeline sections with event counts

#### Automatic Event Status
- Event status (Upcoming/Active/Past) is now automatically computed from dates
- Removed manual status controls - status is derived from start_date and end_date
- UPCOMING: start_date > today, ACTIVE: start_date <= today <= end_date, PAST: end_date < today

#### Plugin System
- Extensible plugin architecture for third-party extensions
- Backend plugin infrastructure with BasePlugin abstract class
- Plugin manifest support (id, name, version, description, capabilities, permissions)
- Plugin lifecycle management (install, enable, disable, uninstall)
- Per-plugin database migrations with separate Alembic version tables
- Event bus for plugin subscriptions to application events (22 event types)
- Permission system for controlling plugin access to resources
- Plugin settings stored encrypted in database
- REST API for plugin management (7 endpoints)
- Admin UI for plugin management in Settings > Plugins
- Frontend plugin loader with dynamic import support
- Plugin navigation items dynamically added to sidebar
- Plugin routes dynamically registered in React Router

#### Event System Integration
- Application events published for user actions (login, logout, registration)
- Event lifecycle events (created, updated, deleted)
- Expense lifecycle events (created, updated)
- Company lifecycle events (created, updated)
- Plugins can subscribe to events via EventBus

#### Example Plugin
- Complete reference plugin implementation in `plugins/example/`
- Demonstrates backend routes, database models, and event subscriptions
- Simple notes CRUD functionality
- Frontend module with dynamic React components

### Improvements

- Started UUID migration by updating ORM models to use native UUID primary and foreign keys; follow-up schemas and Alembic migration pending.
- Added targeted unit tests for Paperless, Immich, and SMTP providers to boost integration coverage and validate connection flows, pagination, and email handling.

#### Developer Tooling
- Added `scripts/dev_checks.py`, a combined runner for linting (`ruff check`, `npm run lint`) and tests (`pytest`, `npm run test`) with consolidated per-file issue counts and suite summaries.
- The runner now prints short failure snippets (when not in `--verbose` mode) so you immediately see the offending error lines without digging through full logs.

---

## Version 0.2.3

### Major Features

#### Company Contacts
- Multiple contacts per company with email, phone, title, department, and notes
- Contact type tagging system (Billing, HR, Technical, Support, Office, Sales, Management, Other)
- Main contact designation with automatic selection of first contact
- Contacts displayed in company detail view with type badges

#### Company Information Enhancements
- Company logo upload and display (PNG, JPG, GIF, SVG, WebP up to 5MB)
- New company fields: website URL, address, and country
- Country autocomplete with browser locale detection

#### Email Template Contact Types
- Link email templates to specific contact types (e.g., Billing)
- Auto-select recipients based on template contact types when sending reports
- Fallback to main contact if no matching types found
- Template validation shows which contact types are missing

### Improvements

#### Company Management
- Enhanced company form with logo upload, address fields, and country selection
- Removed legacy expense recipient fields (replaced by company contacts)
- Contacts section on company detail page

#### Report Sending
- Multiple recipients in single email
- Automatic recipient selection from contacts matching template types
- Clear validation messages when contacts are missing

### Bug Fixes

- Fixed backup service tests after project rename from Travel Manager to HomeOffice Assistant

---

## Version 0.2.0

### Major Features

#### Immich Integration
- Connect to Immich photo server for event photos
- Search photos by date range and location
- Select cover images for events from Immich library
- Photo thumbnails displayed in event views

#### Location Support
- Add location fields (city, country, coordinates) to events
- Location displayed on event cards and detail pages
- Map pin indicators in event listings

#### Cover Images
- Event cover images with gradient overlays
- Cover image backgrounds on event list and detail pages
- Dashboard displays event cover thumbnails
- Support for both Immich photos and Unsplash images

#### Unsplash Integration
- Search and select cover images from Unsplash
- Unsplash form fields for image selection
- Proper attribution for Unsplash images

### Improvements

#### User Registration
- Added display name (full name) field to registration
- Real-time password validation with requirement indicators
- Auto-generate username from first name
- Username availability check with automatic suffix if taken
- Enhanced email validation

#### Regional Settings
- "Detect from Browser" button to auto-detect locale settings
- Auto-detects date format, time format, and timezone
- Success notification when settings are saved

#### Event Management
- "New Event" button disabled until at least one company exists
- Tooltip explains company requirement
- Removed redundant "New Event" button from dashboard

#### Company Management
- Email validation with real-time error display on blur
- Unique email constraint prevents duplicate expense recipient emails

#### Shared Validation
- Reusable email validation utilities (`frontend/src/lib/validation.ts`)
- Consistent email validation across Company forms and SMTP integration settings

#### Email Templates
- Prevent deletion of last global template (backend + frontend)
- Prefill option when creating new templates with default content
- "Use Default" / "Start Empty" prompt for new templates

#### UI/UX Improvements
- Shared form modals for consistent editing experience
- Improved backup/restore functionality
- Better form styling and layout

### Bug Fixes

- Fix event location and cover image saving
- Fix Immich search for future events

### Warnings & Guidance

- SMTP configuration warning on Email Templates settings page when no email integration configured
- SMTP configuration warning on Company detail page with link to integration settings

---

## Version 0.1.1

### Features
- Backup and restore functionality
- Paperless integration improvements

### Bug Fixes
- Various Paperless integration fixes

---

## Version 0.1.0

Initial release with core functionality:
- Event management (CRUD operations)
- Company management with Paperless storage path selection
- Expense tracking and management
- Paperless-ngx integration for document management
- Expense report generation (Excel + ZIP)
- User authentication with session management
- SMTP email integration for sending reports
- Customizable email templates
- Regional date/time format settings
- Breadcrumb navigation
