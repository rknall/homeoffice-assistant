# HomeOffice Assistant - Requirements Document

## Overview

A self-hosted web application to centrally manage business trips, expenses, and reports. Integrates with external systems (Paperless-ngx, Immich) to provide a unified interface for the complete trip lifecycle.

## Problem Statement

Managing business trips currently requires:
- Manual coordination across multiple systems (Paperless-ngx for documents, Immich for photos, email for communication)
- Tedious export/rename/package workflow for expense reports
- No central view of trip history and associated artifacts
- Repetitive manual steps that are error-prone

## Users & Roles

| Role | Permissions |
|------|-------------|
| Admin | Full system configuration, user management, integration setup |
| User | Create/manage own trips, generate reports |
| Viewer | Read-only access to assigned trips (future consideration) |

### Authentication (v0.1)
- Simple username/password authentication
- First user to register becomes system administrator
- Admin can create additional users
- Passwords stored with bcrypt hashing
- Session-based auth with secure cookies

### Authentication (v0.3+)
- OAuth2/OIDC integration (Keycloak, Authentik, etc.)
- Optional: Keep local auth as fallback

## Core Concepts

### Event (Trip)
- Unique identifier
- Name/Title
- Description
- Start date / End date
- Associated company (determines expense recipient, storage paths)
- Status: `draft`, `preparation`, `active`, `completed`, `archived`
- Tags (propagated to external systems)

### Company
- Name
- Type: `employer` | `third_party`
- Paperless storage path ID (selected from available paths via API)
- Expense report recipient (email, name)
- Travel report recipient(s) (email, name)
- Default expense report template (future)

### Expense Item
- Linked to Event
- Document reference (Paperless document ID or direct upload)
- Date
- Amount (with currency)
- Payment type: `cash`, `credit_card`, `company_card`, `prepaid`, `other`
- Category: `travel`, `accommodation`, `meals`, `equipment`, `other`
- Description/Notes
- Status: `pending`, `included_in_report`, `reimbursed`

### Contact
- Linked to Event
- Name
- Company/Organization
- Role/Title
- Email, Phone
- Notes
- Met on (date)

### Note
- Linked to Event
- Timestamp
- Content (markdown)
- Type: `observation`, `todo`, `report_section`

### Todo Item
- Linked to Event
- Title
- Description
- Due date (optional)
- Completed (boolean)
- Category: `travel`, `accommodation`, `preparation`, `followup`

### Photo Reference
- Linked to Event
- Immich asset ID
- Caption
- Include in report (boolean)

---

## Workflows

### Phase 1: Preparation

```
User creates Event
    ├── Set name, dates, company
    ├── System creates tag in Paperless-ngx (via API)
    ├── System creates tag/album in Immich (via API)
    ├── User creates todo checklist from template or custom
    └── User can attach pre-booked documents (tickets, etc.)
```

**API Calls:**
- `POST /api/events` - Create event
- `POST /api/events/{id}/sync-tags` - Ensure tags exist in external systems
- `POST /api/events/{id}/todos` - Add todo items
- `POST /api/events/{id}/expenses` - Add pre-booked expense

### Phase 2: During Event

```
User adds items as trip progresses
    ├── Tag documents in Paperless → auto-detected via polling/webhook
    ├── Tag photos in Immich → auto-detected via polling
    ├── Add contacts met
    ├── Add notes/observations
    └── Mark todos as complete
```

**API Calls:**
- `POST /api/events/{id}/contacts` - Add contact
- `POST /api/events/{id}/notes` - Add note
- `PATCH /api/events/{id}/todos/{todo_id}` - Update todo
- `POST /api/events/{id}/expenses` - Manually add expense
- `GET /api/events/{id}/sync` - Pull updates from external systems

### Phase 3: Post-Event

#### Expense Report Generation

```
1. GET /api/events/{id}/expenses → List all expenses
2. User reviews, assigns payment types, verifies amounts
3. POST /api/events/{id}/expense-report/generate
    ├── Fetch documents from Paperless
    ├── Sort by date
    ├── Generate Excel with:
    │   ├── Date | Description | Category | Payment Type | Amount
    │   └── Total sum
    ├── Rename documents: 01_YYYY-MM-DD_description.pdf
    ├── Create ZIP: expense_report_{event}_{date}.zip
    └── Return download link or send directly
4. POST /api/events/{id}/expense-report/send
    └── Email to company's expense recipient
```

#### Travel Report Generation

```
1. GET /api/events/{id}/report-data
    ├── Event details
    ├── Contacts
    ├── Notes (filtered by type=report_section)
    └── Photos (include_in_report=true)
2. User edits/arranges content
3. POST /api/events/{id}/travel-report/generate
    ├── Fetch photos from Immich
    ├── Generate document (PDF/DOCX)
    └── Return download link
4. POST /api/events/{id}/travel-report/send
    └── Email to company's report recipient(s)
```

---

## External Integrations

All integrations are configured via the UI by administrators, NOT via environment variables.
This allows runtime configuration changes without redeployment.

### Integration Architecture

Integrations follow a plugin-like pattern:
- Each integration type implements a common interface
- Integrations are registered in a central registry
- Configuration stored encrypted in database per integration instance
- Health checks verify connectivity before operations
- Graceful degradation when integrations are unavailable

```
IntegrationProvider (abstract)
├── get_type() -> str
├── get_config_schema() -> JSONSchema  # For UI form generation
├── validate_config(config) -> bool
├── health_check() -> HealthStatus
└── ... provider-specific methods

DocumentProvider(IntegrationProvider)
├── list_storage_paths() -> list[StoragePath]
├── list_tags() -> list[Tag]
├── create_tag(name) -> Tag
├── get_documents(filters) -> list[Document]
└── download_document(id) -> bytes

PhotoProvider(IntegrationProvider)
├── list_albums() -> list[Album]
├── create_album(name) -> Album
├── get_assets(filters) -> list[Asset]
└── download_asset(id) -> bytes

EmailProvider(IntegrationProvider)
├── send_email(to, subject, body, attachments) -> bool
└── verify_connection() -> bool
```

### Paperless-ngx (v0.1)
- **Auth:** API token (configured in UI)
- **Configuration UI Fields:**
  - Instance URL
  - API Token
  - Custom Field Name for Event Tag (e.g., "Trip" or "Event")
- **Capabilities:**
  - List available storage paths (for company assignment)
  - Create/manage tags
  - Query documents by tag and storage path
  - Download documents
  - (Optional) Webhook for new document notifications

### Immich (v0.2+)
- **Auth:** API key (configured in UI)
- **Configuration UI Fields:**
  - Instance URL
  - API Key
- **Capabilities:**
  - Create/manage albums or tags
  - Query assets by tag/album
  - Download assets (photos)

### Email/SMTP (v0.2+)
- **Configuration UI Fields:**
  - SMTP Host
  - SMTP Port
  - Username
  - Password
  - From Address
  - TLS/SSL toggle
- **Capabilities:**
  - Send expense reports
  - Send travel reports
  - Notifications (optional)

### Future Integrations
- Generic file storage (S3, WebDAV, Nextcloud)
- Calendar integration (for event dates)
- Task management (Todoist, etc.)

---

## Non-Functional Requirements

### Security
- Multi-user with role-based access
- v0.1: Username/password auth with session cookies
- v0.3+: OAuth2/OIDC ready (Keycloak, Authentik, etc.)
- All integration credentials (API tokens, passwords) stored encrypted in database
- Encryption key derived from SECRET_KEY environment variable
- HTTPS in production

### Deployment
- Single Docker container (or docker-compose for DB)
- SQLite for simple deployments, PostgreSQL for production
- Environment-based configuration
- Health check endpoint

### Testing
- Unit tests for all business logic
- Integration tests for external APIs (mocked)
- API endpoint tests
- Minimum 80% code coverage target

### Tech Stack
- **Backend:** Python (FastAPI)
- **Database:** SQLAlchemy ORM, SQLite/PostgreSQL
- **Frontend:** React with TypeScript, Tailwind CSS
  - Use Anthropic Skills for design guidance (see Frontend section)
- **Task Queue:** Optional (Celery/RQ for async report generation)
- **Containerization:** Docker with multi-stage build

### Frontend Design

Use **Anthropic Skills** (https://github.com/anthropics/skills/) for:
- `frontend-design` skill for UI components and layouts
- Document template generation for reports
- Consistent, professional styling

**UI Requirements:**
- Clean, modern interface using Tailwind CSS
- Responsive design (works on mobile for field use)
- Dark mode support
- Accessible (WCAG 2.1 AA)

**Key Views:**
1. Dashboard - Overview of active trips, pending expenses
2. Event List - All trips with filtering/search
3. Event Detail - Single trip with all associated data
4. Expense Editor - Table view with inline editing
5. Report Preview - See what will be generated
6. Settings - Integration configuration, user management
7. Integration Setup - Per-integration configuration forms

---

## Data Model (Simplified)

```
User (id, username, email, hashed_password, role, is_admin, created_at)
  └── has many Events

Company (id, name, type, paperless_storage_path_id, expense_recipient_email, expense_recipient_name, report_recipients JSON, created_at)

Event (id, user_id, company_id, name, description, start_date, end_date, status, external_tag, created_at)
  ├── has many Expenses
  ├── has many Contacts
  ├── has many Notes
  ├── has many Todos
  └── has many PhotoReferences

Expense (id, event_id, paperless_doc_id, date, amount, currency, payment_type, category, description, status, original_filename)

Contact (id, event_id, name, company, role, email, phone, notes, met_on)

Note (id, event_id, content, note_type, created_at)

Todo (id, event_id, title, description, due_date, completed, category)

PhotoReference (id, event_id, immich_asset_id, caption, include_in_report)

# Integration configuration - stored in DB, not env vars
IntegrationConfig (id, integration_type, name, config_encrypted, is_active, created_by, created_at)
  # integration_type: 'paperless', 'immich', 'smtp', etc.
  # config_encrypted: JSON blob with all config (url, token, custom_field_name, etc.)

SystemSettings (key, value_encrypted)
  # For global settings like default integrations, first-run flag, etc.
```

---

## MVP Scope (v0.1)

1. **Core:**
   - Event CRUD
   - Company CRUD with storage path selection
   - Multi-user with username/password auth
   - First registered user = admin
   - Admin can create additional users

2. **Expenses:**
   - Manual expense entry
   - Paperless integration (fetch by tag and storage path)
   - Expense report generation (Excel + ZIP)

3. **Integrations:**
   - Paperless-ngx (read documents, create tags, list storage paths)
   - Configuration via UI (not environment variables)
   - Configurable custom field name for event tags

4. **Frontend:**
   - React + TypeScript + Tailwind
   - Use Anthropic frontend-design skill
   - All core views (dashboard, events, expenses, settings)
   - Integration configuration UI

5. **API:**
   - RESTful JSON API
   - OpenAPI documentation

**Deferred to v0.2:**
- Immich integration
- Travel report generation
- Email sending (SMTP configuration)
- Todo management UI
- Contact management UI

**Deferred to v0.3+:**
- OAuth2/OIDC authentication
- Additional integrations (file storage, calendar)
- Plugin system for custom integrations
