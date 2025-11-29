# Travel Manager

A self-hosted web application for managing business trips, expenses, and reports with external system integrations.

## Features

- Event management for business trips
- Company management (employers and third parties)
- Expense tracking with categories and payment types
- Paperless-ngx integration for document management
- Excel expense report generation
- User authentication with session management

## Quick Start

### Development

\`\`\`bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn src.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
\`\`\`

### Docker (Development)

\`\`\`bash
# Set required secret
export SECRET_KEY=\$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Run with Docker Compose
docker compose up --build
\`\`\`

Access the application at http://localhost:8000

## Production Deployment

### Using Docker (Portainer)

1. Pull the latest image:
   ```bash
   docker pull ghcr.io/rknall/travel-manager:latest
   ```

2. Create a `.env` file with your secret key:
   ```bash
   echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env
   ```

3. Deploy using docker-compose:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

The image supports both `linux/amd64` and `linux/arm64` architectures.

### Backup & Restore

**Create backup from running container:**
```bash
./scripts/docker-backup.sh travel-manager ./backups
```

**Restore backup:**
```bash
./scripts/restore.sh ./backups/travel_manager_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| SECRET_KEY | Yes | Secret key for encryption (min 32 chars) |
| DATABASE_URL | No | Database connection string (default: SQLite) |

## Configuration

Only two environment variables are required:

- \`SECRET_KEY\`: Required for encryption (generate with \`python -c "import secrets; print(secrets.token_urlsafe(32))"\`)
- \`DATABASE_URL\`: Optional, defaults to SQLite at \`./data/travel_manager.db\`

All other configuration (Paperless integration, etc.) is managed through the web UI.

## Database Management

### Initial Setup

Database migrations run automatically on startup (both development and Docker).

### Reset Database

**Development (SQLite):**
```bash
rm -f data/travel_manager.db
source .venv/bin/activate
alembic upgrade head
```

**Docker:**
```bash
docker compose down
rm -rf data/
docker compose up
```

After reset, visit the application to create a new admin user through the setup wizard.

## License

This project is licensed under the GNU General Public License v2.0 only (GPL-2.0-only).

See [LICENSE](LICENSE) for the full license text.

SPDX-License-Identifier: GPL-2.0-only
