# Release Notes

## Version 0.6.0 (in development)

### Major Features

#### AI Expense Scanning
- New LLM integration type (Settings > Integrations): any OpenAI-compatible API (OpenAI, LiteLLM proxy, ...) with base URL, API key, and model
- LLM integration supports optional HTTP basic authentication (username/password) for APIs behind a gateway such as Pangolin or nginx; the API key then moves to the `x-api-key` header, which requires the upstream API to read it from there (for LiteLLM: `general_settings.litellm_key_header_name`) or the gateway to strip the `Authorization` header after authenticating
- "Fetch models" button in the LLM integration form lists the models the endpoint offers, so the model name can be picked instead of typed; works before the integration is saved
- "Scan Document with AI" button when creating an expense from a Paperless document or editing an expense with a linked document
- The LLM reads the document's OCR text and autofills date, amount, currency, category, payment type, and description
- Values the model cannot determine are left untouched and reported as warnings; scanned values stay editable and nothing is saved without user review
- Credentials are stored encrypted like all other integrations

#### Global Currency Setting
- System-wide currency is now configured in Settings > Regional (default: EUR), replacing the per-company base currency
- All expenses entered in other currencies are converted to the system currency using the daily ECB exchange rate
- Expense report emails now show the converted total in the system currency, matching the attached Excel report
- Expense report emails only include the expenses actually contained in the report (respects selection and private-expense exclusion)
- Expense reports (download, email, and email preview) never include reimbursed expenses; when expenses are selected in the list only those are reported, otherwise all open expenses
- Fixed the optional recipient address in the email report dialog being ignored
- Dashboard expense overview and event expense totals are expressed in the system currency
- Migration seeds the global setting from the most common existing company currency
- Changing the system currency invalidates stored conversions; they are recomputed with the correct daily rates automatically

#### National Holidays
- Display national holidays in the calendar with visual highlighting (gray background like weekends)
- Configure multiple countries/regions for holiday display in Settings > Holidays
- Holiday labels show country prefix (e.g., "AT - Neujahr", "DE-BY - Karfreitag")
- Filter holidays on/off in calendar view
- Preview holidays before adding a country configuration
- Support for 100+ countries via Python `holidays` library
- Regional subdivision support (e.g., German federal states, US states)

#### Expense Report Improvements
- "Include private expenses" switch in the export report dialog (private expenses remain excluded by default)
- Excel report: no total for the original-amount column when currencies are mixed, currency label when uniform, rate columns only for actual conversions, separator before totals
- Fixed: creating an expense ignored the private flag (it could only be set via edit)

### Bug Fixes
- Fixed currency conversion being broken by the Frankfurter API move to api.frankfurter.dev/v1 (rate fetching and currency list failed)
- Fixed expense report email totals using raw amounts, a wrong currency label, and leaking private expenses into the total
- Fixed report ZIP attachments being unopenable when a Paperless document was scanned from an image: Paperless serves the archived PDF, but the file was named with the original image extension
- Fixed the submitted total counting an expense once per submission, so emailing a report and then downloading it doubled the amount
- Logout now invalidates the server-side session, not just the browser cookie (a leaked session token could previously stay valid until expiry)
- Fixed backup restore: restoring a backup through Settings > Backup now works end to end (the staged database is migrated before it replaces the live one); pre-restore safety backups are kept under `data/backups/pre_restore` and survive container recreation
- In-app backups now include company logos (`data/logos`); archives without logos still restore and leave the current logos alone
- Fixed the calendar not loading events, holidays, todos and company calendars (it called a non-existent endpoint), and holidays being shown one day off; todos now load with one range request (`GET /api/v1/todos?due_from=&due_to=`, requires `event.read`)
- Fixed avatar images being broken (served now at `/avatars/...`) and company logos not showing in the company list after upload; deleting a company removes its logo file
- A rejected logo upload now shows the server's message instead of closing the company form silently; Escape closes modals; company rows no longer contain nested buttons
- Fixed a failed plugin install leaving a half-installed plugin listed; time-tracking planned-vacation calculation now covers future years; time-tracking holiday lookups with an unknown region return 422 instead of 500
- Fixed the Setup page calling `navigate()` during render, a failed login clearing the username field, and the LLM edit form for users without permission showing a blank form
- Fixed the expense report preview total including private and reimbursed expenses

### Security
- Stored XSS via SVG logos closed: SVG logos stay allowed but are content-checked on upload and served with a restrictive Content-Security-Policy
- Bulk expense status changes can no longer touch expenses outside the event (cross-user status change)
- Every route now checks permissions, company-scoped where a company is involved (including time-tracking plugin routes); previously many permissions were seeded but not enforced
- Plugin settings of a plugin that is registered but not loaded are returned masked and cannot be overwritten blind (fail closed)
- Secrets are never returned by the API: integration and plugin config responses carry an empty value plus `secrets_set` (names of stored secrets); the settings forms show "Stored, leave blank to keep" for Paperless token, Immich API key, Unsplash access key and LLM API key, and a blank field keeps the stored value on edit
- Unsplash key moved from plaintext into the encrypted integration; `/integrations/llm/models` is admin-only, `/locations/autocomplete` requires login, `check-username` is restricted after setup
- Error messages for SMTP, LLM, report sending, document scanning and plugin/backup errors no longer contain raw exception text; they show a category (server unreachable, authentication failed, unexpected response)
- LLM input is capped at 20000 characters

### Permissions and Roles
- New built-in **Member** role holds the standard user permissions (including all time-tracking codes); new and self-registered users get it, and users without any role are migrated to it
- Custom roles holding `system.admin` are protected like Global Admin
- Users with only company-scoped roles can still open the event pages (locale, currency and custom-field reads only need a login)

### UI
- Browser `confirm()` dialogs replaced by an in-app overlay dialog that dims the background (Cancel/Escape/Tab handled); plugin frontends can use `window.hoaHost.confirmAction`
- Removed the timesheet "submission" panels of the Time Tracking plugin, which called an endpoint that never existed
- Time Tracking company settings widget now appears on the company detail page
- Label and status names come from one shared source; date formats follow the configured locale in emails and report previews

### Breaking Changes
- Users who hold only company-scoped roles lose access they previously had by accident (event, time-tracking and other routes now require the matching permission); grant roles where needed
- `SECRET_KEY` must be at least 32 characters, otherwise the app refuses to start. Do not change an existing key: it would break stored secrets
- Removed unused endpoints: currencies rate/backfill, email-template variables/validate-contacts, contacts by-type, events sync-paperless, integration tags/custom-fields, and further endpoints with no caller (see the OpenAPI schema); the `is_admin` and `is_encrypted` columns are dropped
- `POST /users` returns 201 and photo `DELETE` returns 204 (previously 200)
- Plugins no longer install Python dependencies at runtime: an external plugin whose `python_dependencies` are not in the image fails to load with a clear log line
- Docker: the container runs as uid 1000; the host `data/` directory must be writable by uid 1000 (`chown -R 1000:1000 data`); the plugins bind mount and the compose healthcheck were removed; avatars are stored under `data/avatars`
- Set `FORWARDED_ALLOW_IPS` (default `127.0.0.1`) to your reverse proxy address when running behind a TLS proxy so secure cookies work
- Scripts: `docker-backup.sh` replaced by `backup.sh --docker`; `restore.sh` requires `--force`; the application version has a single source (`src/version.py`)

### Upgrade Notes
- Five new database migrations run at container start: `3f8b2c61d9a4` (INCLUDED expense status becomes SUBMITTED), `5b2d9f3e6a18` (Member role), `9d4e7a15c0b2` (aligns the schema with the models, rebuilds most tables on SQLite), `c61a0e5f8b37` (drops `system_settings.is_encrypted`), `e8c47b2a1f05` (drops `users.is_admin`). **Back up `data/` first** (Settings > Backup or `scripts/backup.sh`); downgrade is supported but rebuilds tables again

### Maintenance
- All frontend dependencies upgraded to latest (React 19.2.7, Tailwind 4.3.2, Biome 2.5.2, lucide-react 1.x, ...)
- Biome version pinned in CI to match the project (no more drift between local and CI lint)
- Python environment fully managed by uv (`uv.lock` committed); stale `.venv` setups replaced
- Accessibility lint fixes (ambiguous link texts, label without control)

---

## Version 0.4.0

### Major Features

#### Calendar Integration
- Connect external calendars (Google Calendar, Outlook, iCal/CalDAV) to companies
- Calendar page with week and month views for visualizing events
- Filter calendar by company and calendar source
- Sync external calendar events with event management
- Connected Calendars tab on company detail page for managing calendar connections
- Support for multiple calendars per company
- Calendar sync status tracking and manual sync trigger

---

## Version 0.3.0

### Major Features

#### Document References
- Link Paperless documents to events without creating expenses (for contracts, itineraries, confirmations, etc.)
- Redesigned Documents tab with two sections: "Linked Documents" and "Available from Paperless"
- Document type categorization (Contract, Itinerary, Confirmation, Other) with styled badges
- Notes field for adding context to linked documents
- "Include in reports" option for document references
- Consistent action buttons: View, Edit, Unlink (no dangerous delete from Paperless)
- Documents linked to expenses or as references are hidden from the available list
- Collapsible "Available from Paperless" section showing unlinked document count

#### Multi-Currency Support
- Automatic currency conversion for expenses using ECB exchange rates via frankfurter.app
- Company base currency setting that flows to all expense calculations
- Each expense stores original amount, converted amount, exchange rate, and rate date for full audit trail
- Currency selector populated from supported currencies API (no invalid currency codes)
- Dashboard expense breakdown now shows totals in the company's base currency
- Exchange rates cached locally to minimize API calls
- Falls back to nearest available rate for weekends/holidays
- Excel expense reports now include both original and converted amounts with exchange rate info
- `GET /api/v1/currencies` endpoint returns list of supported currencies
- New CurrencyCache model for storing historical exchange rates
- Event detail page shows conversion rates in Total Expenses card (e.g., "1 EUR = 1.1787 USD")
- Per-expense converted amounts displayed with rate tooltip on hover
- Backfill API endpoint (`POST /currencies/backfill`) to convert existing expenses

#### Todo Management
- Full todo CRUD on event detail page with tabbed interface
- Category-based organization (Travel, Accommodation, Preparation, Equipment, Contacts, Follow-up, Other)
- Due date tracking with overdue highlighting
- Quick-complete from dashboard Action Items with checkbox
- Auto-complete: Report-related todos automatically marked done when expense reports are sent or exported
- Incomplete todo count badge on Todos tab
- Sorted display: incomplete todos first (by due date), then completed

#### Todo Templates
- Predefined todo templates that users can apply to events with a single click
- Templates include calculated due dates relative to event start/end dates (e.g., "14 days before start")
- Global system templates seeded on first run: Business Trip and Conference Event sets
- User-defined custom templates manageable in Settings > Todo Templates
- "Add from Template" button on event Todos tab for multi-select template application
- Template picker modal shows computed due dates before applying
- Template sets group related todos (e.g., "Business Trip" includes flight, accommodation, documents, expenses)

#### Report Tracking
- Events now track when expense reports were sent/exported via `report_sent_at` timestamp
- Dashboard "Reports Due" section only shows events that haven't had a report sent
- Sending or exporting an expense report automatically marks the event as reported

#### Incremental Expense Submission
- Submit expenses incrementally instead of all at once
- New expense status workflow: PENDING → SUBMITTED → REIMBURSED (with REJECTED as alternate path)
- Status badges in expense table with color-coded indicators (gray/blue/green/red)
- Filter expenses by status (All/Pending/Submitted/Reimbursed/Rejected)
- Bulk selection and status update for multiple expenses
- Generate Report modal with three selection modes:
  - All pending expenses
  - Select specific expenses
  - All expenses
- Option to automatically mark selected expenses as submitted when generating reports
- Rejection reason tracking with display in expense table
- Submissions tab showing complete submission history
- Submission summary cards showing total submitted, awaiting reimbursement, reimbursed, and pending amounts
- Expandable submission details showing individual expense items
- New database models: ExpenseSubmission and ExpenseSubmissionItem for full audit trail
- New API endpoints: POST/GET submissions, bulk status update, submission summary

#### Private Expenses
- Mark expenses as "private" to exclude them from official expense reports
- Private expenses remain visible in the expense list for personal tracking
- Purple "Private" badge displayed next to status in expense table
- Private expenses filtered from all Generate Report modal selection modes
- Checkbox in expense edit form: "Private expense - Excluded from official reports"

#### Event Detail Page Tabs
- Reorganized event detail page with tab navigation: Expenses | Submissions | Documents | Photos | Todos
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
- Removed legacy `status` column from database (migration included)

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

#### Time Tracking Plugin
- Full-featured time tracking with Austrian labor law (Arbeitszeitgesetz) compliance
- Time record management with check-in/check-out, day types, and work location tracking
- Automatic time rounding to 5-minute intervals in employer's favor
- Break calculation per Austrian law (30 min after 6h work)
- Compliance validation: 10h daily max, 11h rest period, 50h weekly max
- Leave balance tracking: vacation days, sick days, comp time
- Comp time accrual with 2x multiplier for Sunday/holiday work
- Austrian public holiday detection via `holidays` library
- Custom holiday support for company-specific holidays
- PDF timesheet report generation with ReportLab
- Email submission of timesheets via SMTP integration
- Submission history tracking with status (pending, sent, failed)
- Company-specific time settings (overtime thresholds, vacation days, lock periods)
- Time allocations for splitting hours across events/projects
- 64 unit tests covering time calculations, validators, and leave balances
- **Unified multi-company view**: Calendar and table views for all companies with color-coded entries
- **Company filter toggles**: Toggle visibility of time records by company
- **Time overlap detection**: Visual indicators for overlapping time entries across companies
- **Sortable table view**: Click column headers to sort by date, company, type, etc.
- **Monthly submission panel**: Submit timesheets with company selection and email recipient
- **TypeScript migration**: Frontend migrated to TypeScript with esbuild bundling

### Improvements

- Started UUID migration by updating ORM models to use native UUID primary and foreign keys; follow-up schemas and Alembic migration pending.
- Added targeted unit tests for Paperless, Immich, and SMTP providers to boost integration coverage and validate connection flows, pagination, and email handling.

#### Developer Tooling
- Added `scripts/dev_checks.py`, a combined runner for linting (`ruff check`, `npm run lint`) and tests (`pytest`, `npm run test`) with consolidated per-file issue counts and suite summaries.
- The runner now prints short failure snippets (when not in `--verbose` mode) so you immediately see the offending error lines without digging through full logs.
- **GitHub Copilot Code Review**: Added comprehensive documentation for enabling AI-powered PR code review
  - Guide for enabling Copilot code review through repository settings (no workflow needed)
  - Explains automated security scanning, code quality checks, and best practices validation
  - Setup instructions for repository admins and organization owners
  - Best practices and troubleshooting guide in `docs/COPILOT_REVIEW.md`
  - Requires GitHub Copilot Business or Enterprise license

### Bug Fixes

- Currency dropdown now shows saved value instead of defaulting to first option when editing expenses

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
