# Feature Ideas

This folder contains ideas for future features. Each idea is documented in its own file with problem statement, proposed solution, and implementation notes.

Completed ideas are moved to the `done/` subdirectory.

## Active Ideas

### Core Features
| Idea | Status | Description |
|------|--------|-------------|
| [Company Documents](company-documents.md) | Not Started | Attach contracts, NDAs, policies to companies with expiry tracking |
| [Travel Report Generation](travel-report-generation.md) | Partially Planned | Generate narrative trip reports with photos |
| [Recurring Events](recurring-events.md) | Not Started | Event templates and optional recurrence patterns |
| [Database-Independent Backup](database-independent-backup.md) | Not Started | Backup and restore for PostgreSQL as well as SQLite |
| [UI Modernisation](ui-modernisation.md) | Not Started | Per-page UI audit: modals, row actions, consistency (separate task) |
| [Theming](theming.md) | Not Started | Colour tokens, light/dark mode, colour themes |

### Plugins
| Idea | Status | Description |
|------|--------|-------------|
| [Business Card Scanner](business-card-scanner.md) | Not Started | Vision-based contact extraction from business cards (plugin) |
| [Local OCR for Expenses](local-ocr-expense-recognition.md) | Partially implemented v0.5.0 | LLM scanning shipped; local vision models on receipt images remain |
| [Time Tracking PDF Timesheet](time-tracking-pdf-timesheet.md) | Not Started | Printable timesheet export for the time-tracking plugin |

### Infrastructure & Integrations
| Idea | Status | Description |
|------|--------|-------------|
| [OAuth2/OIDC Authentication](oauth2-oidc-authentication.md) | Not scheduled | Single sign-on with Keycloak, Authentik, etc. |
| [File Storage Integrations](file-storage-integrations.md) | Not Started | S3, WebDAV, Nextcloud for document storage |
| [Task Import/Export](task-import-export.md) | Not Started | Sync todos with Todoist, Things, etc. |

## Completed Ideas

See the [done/](done/) folder for implemented features:

| Idea | Implemented | Description |
|------|-------------|-------------|
| [Incremental Expense Submission](done/incremental-expense-submission.md) | v0.3.0-rc1 | Submit expenses in stages, track submission status |
| [Task Management (Internal)](done/task-management-integration.md) | v0.3.0 | Todo CRUD, categories, templates, auto-completion |
| [Time/Working Hours Tracking](done/time-tracking.md) | v0.3.0 (plugin) | Track working hours per event/company/project (plugin) |
| [Calendar Integration](done/calendar-integration.md) | v0.4.0, v0.5.0 | Company calendar connections, calendar page, national holidays |

## Contributing Ideas

When adding a new idea:

1. Create a new markdown file with a descriptive name
2. Include these sections:
   - **Status**: Not Started / In Progress / Planned / Implemented
   - **Plugin Candidate**: Yes/No/Maybe with reasoning
   - **Problem**: What problem does this solve?
   - **Proposed Solution**: High-level approach
   - **Implementation Notes**: Technical details
   - **Related**: Links to related features/ideas
3. Update this README with the new idea

## Picking Ideas for Implementation

When selecting an idea to implement:
1. Consider dependencies (does it require other features first?)
2. Evaluate complexity vs. value
3. Check if there are related ideas that could be combined
4. Move to planning phase and create detailed implementation plan

## After Implementation

When an idea is fully implemented:
1. Update the status to "Implemented in vX.X.X"
2. Move the file to `done/`
3. Update this README
