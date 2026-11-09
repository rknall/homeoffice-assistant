# HomeOffice Assistant

[![CI](https://github.com/rknall/homeoffice-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/rknall/homeoffice-assistant/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/rknall/homeoffice-assistant)](https://github.com/rknall/homeoffice-assistant/releases/latest)
[![License](https://img.shields.io/badge/license-GPL--2.0--only-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/rknall/homeoffice-assistant/pkgs/container/homeoffice-assistant)

A self-hosted personal productivity and work management assistant with powerful integrations.

If HomeOffice Assistant helps you, you can support development at [Buy Me a Coffee](https://buymeacoffee.com/TvrRmWD).

## What is HomeOffice Assistant?

HomeOffice Assistant is a comprehensive solution for managing your work life. Focused on business travel and working-time management, it helps you:

- **Plan Events**: Track business trips with dates, locations, and companies
- **Manage Expenses**: Record and categorize all trip-related expenses, scan receipts with an LLM
- **Store Documents**: Integrate with Paperless-ngx to automatically link receipts and invoices
- **Organize Photos**: Connect to Immich to display event photos based on location and date
- **Generate Reports**: Create detailed Excel expense reports with attachments
- **Share Results**: Email reports directly to finance teams or clients
- **Track Working Time**: Record hours, leave and overtime with the bundled time-tracking plugin

Perfect for consultants, sales teams, field engineers, or anyone who travels frequently for work.

## Key Features

### Event Management
- Create events for business trips with dates and locations
- Cover images from Unsplash or your Immich photo library
- Location autocomplete with city, country, and coordinates
- Notes, photo references and document references per event
- Breadcrumb navigation and timeline views

### Expense Tracking
- Record expenses with categories, payment types, and currencies
- One global system currency; other currencies are converted with the daily ECB rate
- Private expenses and reimbursement tracking; incremental submission status
- Link expenses to Paperless documents, with side-by-side document preview
- AI expense scanning: an OpenAI-compatible LLM reads the document text and fills in the expense form
- Excel report generation with all receipts bundled in ZIP

### Calendar and Tasks
- Calendar with week and month views, company calendar connections, and national holidays for 100+ countries
- Todos with categories and templates, auto-completed when reports are sent

### Time Tracking (plugin)
- Working hours, breaks, leave balance and overtime per company
- Bundled in `plugins/time-tracking`; further plugins can be added through the plugin system

### Integrations
- **Paperless-ngx**: Automatic document retrieval and storage
- **Immich**: Display event photos based on location and time
- **Unsplash**: Professional cover images for events
- **LLM** (OpenAI-compatible): AI expense scanning
- **SMTP**: Email reports directly from the application

### Administration
- First-run setup wizard for easy onboarding
- Role-based access control with global and company-scoped roles (Global Admin, Member, Company Viewer and custom roles)
- Regional settings with browser auto-detection
- Customizable email templates
- Backup and restore from the UI and from scripts

## Quick Start

### First-Time Setup

The easiest way to get started is with Docker:

1. **Generate a secret key:**
   ```bash
   echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env
   ```

2. **Prepare the data directory:**

   The container runs as uid 1000, so the data directory must be writable by it:
   ```bash
   mkdir -p data && chown -R 1000:1000 ./data
   ```

3. **Start the application:**
   ```bash
   docker run -d \
     --name homeoffice-assistant \
     -p 8000:8000 \
     -v $(pwd)/data:/app/data \
     --env-file .env \
     ghcr.io/rknall/homeoffice-assistant:latest
   ```

4. **Open your browser:**

   Navigate to http://localhost:8000

   You'll see a setup wizard to create your admin account.

5. **Create your first company:**

   After logging in, go to Settings → Companies and add at least one company (your employer or client).

6. **Create your first event:**

   Now you can create events and start tracking expenses!

### Docker Compose (Recommended)

For a more permanent setup, use Docker Compose:

1. **Create a `docker-compose.yml` file:**
   ```yaml
   services:
     homeoffice-assistant:
       image: ghcr.io/rknall/homeoffice-assistant:latest
       container_name: homeoffice-assistant
       ports:
         - "8000:8000"
       volumes:
         - ./data:/app/data
       environment:
         - SECRET_KEY=${SECRET_KEY}
       restart: unless-stopped
   ```

2. **Create `.env` file:**
   ```bash
   echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env
   ```

3. **Prepare the data directory:**
   ```bash
   mkdir -p data && chown -R 1000:1000 ./data
   ```

4. **Start:**
   ```bash
   docker compose up -d
   ```

### Optional: Configure Integrations

After initial setup, you can connect external services in **Settings → Integrations**:

- **Paperless-ngx**: Link your document management system for automatic expense receipts
- **Immich**: Connect your photo server to display event photos
- **Unsplash**: Enable cover image search (requires free API key)
- **LLM**: Configure an OpenAI-compatible API for AI expense scanning
- **SMTP**: Configure email for sending expense reports

## Screenshots

*Coming soon: Screenshots of the dashboard, event detail page, and expense tracking.*

## Development

Requires [uv](https://docs.astral.sh/uv/) (Python 3.14) and [bun](https://bun.sh/).

### Local Development (without Docker)

Tests and the dev server need `SECRET_KEY` (32+ characters); set `DATABASE_URL`
to use another database than the default SQLite file.

**Backend:**
```bash
export SECRET_KEY=$(uv run python -c "import secrets; print(secrets.token_urlsafe(32))")
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

**Frontend (separate terminal):**
```bash
cd frontend
bun install
bun run dev
```

Access at http://localhost:5173 (frontend) and http://localhost:8000 (backend)

**Checks:**
```bash
uv run --extra dev pytest tests/ plugins/*/tests/   # backend tests
uv run --extra dev ruff check src/                  # backend lint
(cd frontend && bun run test && bun run lint)       # Vitest and Biome
```

Use `bun run test` (Vitest), not `bun test`.

**API types:** the frontend types in `frontend/src/types/api.generated.ts` are
generated from the backend OpenAPI schema. After changing API schemas run
`bun run gen:types` inside `frontend/` and commit the result; CI fails when the
committed file is stale.

### Docker Development

```bash
# Set secret key
export SECRET_KEY=$(uv run python -c "import secrets; print(secrets.token_urlsafe(32))")

# Build and run
mkdir -p data && chown -R 1000:1000 ./data
docker compose up --build
```

Access at http://localhost:8123

### Contributing

All pull requests run CI: Ruff (Python) and Biome (TypeScript) linting, the
pytest and Vitest suites, a generated-types drift check and the Docker build.
Project conventions are in [CLAUDE.md](CLAUDE.md).

## Deployment

### Production with Docker

The application is available as a multi-architecture Docker image supporting `linux/amd64` and `linux/arm64`.

**Pull the latest release:**
```bash
docker pull ghcr.io/rknall/homeoffice-assistant:latest
```

**Or pin a version** (see the [releases](https://github.com/rknall/homeoffice-assistant/releases) for available tags):
```bash
docker pull ghcr.io/rknall/homeoffice-assistant:v<version>
```

The container runs as uid 1000 and must run as a single replica (the default
database is a single-writer SQLite file). The host `data/` directory must be
writable by uid 1000; installs from earlier versions that ran as root need a
one-time fix:

```bash
chown -R 1000:1000 ./data
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Encryption key (min 32 chars; the application refuses to start with a shorter one) |
| `DATABASE_URL` | No | SQLite | Database connection string |
| `FORWARDED_ALLOW_IPS` | No | `127.0.0.1` | Proxy addresses (comma-separated, or `*`) whose `X-Forwarded-*` headers are trusted |

> **Note**: Only `SECRET_KEY` is required. All other configuration (integrations, SMTP, etc.) is managed through the web UI.

### Behind a TLS-Terminating Proxy

When a reverse proxy terminates TLS, set `FORWARDED_ALLOW_IPS` to the proxy's
address (for example the Docker network gateway, or `*` if only the proxy can
reach the container). Without it the application does not see the original
HTTPS scheme and the session cookie is not marked secure.

### Plugins

Plugins are loaded from `plugins/`. The image installs no Python packages at
runtime: a plugin whose `python_dependencies` are not already in the image
fails to load, with a log line naming the missing packages. Add such
dependencies to the image (the `dependencies` in `pyproject.toml`) and rebuild.

### Access Control

Every user holds one or more roles. Existing users without a role, and newly
created or self-registered users, get the **Member** role, which grants the
access every user had before roles were enforced. This is a breaking change for
users who only hold company-scoped roles (for example Company Viewer): they no
longer reach routes outside their companies, including the time-tracking
plugin, until an admin grants the needed role or plugin permission.

### Upgrade Notes

- Back up `data/` before upgrading: the migrations rebuild several tables on SQLite.
- Fix ownership of `data/` for uid 1000 (see above) and use a `SECRET_KEY` of 32+ characters.
- The `Member` role is created by a migration (see Access Control).
- Removed endpoints (no callers): `GET /currencies/rate`, `POST /currencies/backfill`,
  `GET /email-templates/variables/{reason}`, `GET /email-templates/{id}/validate-contacts/{company_id}`,
  `GET /companies/{id}/contacts/by-type/{type}`, `POST /events/{id}/sync-paperless`,
  `POST /events/{id}/expenses/bulk-update`, `GET /events/{id}/expenses/summary`,
  `PATCH /events/{id}/expenses/{expense_id}/status`, and the Paperless tags and
  custom-field routes under `/integrations/{id}/`.
- Status codes: `POST /users` returns 201 and deleting a photo returns 204.
- Pre-restore backups are kept in `data/backups/pre_restore/`.
- API clients: regenerate the frontend types with `bun run gen:types`.

### Using PostgreSQL (Optional)

SQLite is the tested default. PostgreSQL stays documented for production use,
but the backup scripts and the in-app backup only cover SQLite (see the
[database-independent backup idea](docs/ideas/database-independent-backup.md)),
so back up PostgreSQL with `pg_dump`.

To use it, uncomment the `db` service in `docker-compose.yml`, add a
`volumes: postgres_data:` entry and set in `.env`:
```
SECRET_KEY=your-secret-key
POSTGRES_PASSWORD=your-db-password
DATABASE_URL=postgresql://homeoffice_assistant:your-db-password@db:5432/homeoffice_assistant
```

## Backup & Restore

### Create Backup

**On the host** (from the project directory):
```bash
./scripts/backup.sh [backup_dir]
```

**From a running container:**
```bash
./scripts/backup.sh --docker homeoffice-assistant ./backups
```

The database is copied through the SQLite online backup API, so it is safe
while the application runs. Any failure exits non-zero.

**Or via UI:**

Go to Settings → Backup/Restore and click "Download Backup"

### Restore Backup

Stop the application first. `--force` is required because restore overwrites
the current database, avatars and logos (the current database is kept as
`homeoffice_assistant.db.pre-restore.<timestamp>`). A restore through the UI
saves the previous state under `data/backups/pre_restore/`.

```bash
./scripts/restore.sh --force ./backups/homeoffice_assistant_backup_YYYYMMDD_HHMMSS.tar.gz
```

Backups include:
- SQLite database
- User avatars
- Company logos

## Database Management

### Automatic Migrations

Database migrations run automatically on container startup. No manual intervention needed!

### Reset Database

**Development (SQLite):**
```bash
rm -f data/homeoffice_assistant.db
uv run alembic upgrade head
```

**Docker:**
```bash
docker compose down
rm -rf data/
docker compose up
```

After reset, visit the application to run through the setup wizard again.

## Documentation

- [Release Notes](RELEASENOTES.md) - Full changelog
- [Development Guide](CLAUDE.md) - Architecture and development instructions
- [Feature Ideas](docs/ideas/README.md) - Planned and completed ideas

## Issues & Support

Found a bug or have a feature request? Please [open an issue](https://github.com/rknall/homeoffice-assistant/issues/new).

## License

This project is licensed under the **GNU General Public License v2.0 only (GPL-2.0-only)**.

See [LICENSE](LICENSE) for the full license text.

```
SPDX-License-Identifier: GPL-2.0-only
```

---

**Made with love for productive home office workers**
