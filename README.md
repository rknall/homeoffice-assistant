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

### Docker

\`\`\`bash
# Set required secret
export SECRET_KEY=\$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Run with Docker Compose
docker compose up --build
\`\`\`

Access the application at http://localhost:8000

## Configuration

Only two environment variables are required:

- \`SECRET_KEY\`: Required for encryption (generate with \`python -c "import secrets; print(secrets.token_urlsafe(32))"\`)
- \`DATABASE_URL\`: Optional, defaults to SQLite at \`./data/travel_manager.db\`

All other configuration (Paperless integration, etc.) is managed through the web UI.

## License

MIT
