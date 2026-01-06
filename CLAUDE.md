# CLAUDE.md - Project Guidelines for Claude Code

## Project: HomeOffice Assistant

A self-hosted personal productivity and work management assistant with external system integrations.

## Quick Reference

```bash
# Backend
source .venv/bin/activate
pip install -e ".[dev]"
pytest                          # Run tests
uvicorn src.main:app --reload   # Dev server on :8000

# Frontend
cd frontend
bun install
bun run dev                     # Dev server on :5173
bun run build                   # Production build
bun test                        # Run tests

# Docker (full stack)
docker compose up --build
```

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Zustand, Vite |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Testing** | pytest (backend), Vitest (frontend) |
| **Linting** | Ruff (Python), Biome (TypeScript) |

## Project Structure

```
homeoffice-assistant/
├── src/                        # Backend (Python/FastAPI)
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings
│   ├── database.py             # SQLAlchemy setup
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── api/v1/                 # API route handlers
│   ├── services/               # Business logic
│   ├── integrations/           # External system clients (Paperless, Immich)
│   └── plugins/                # Plugin system
├── frontend/src/
│   ├── api/                    # API client
│   ├── components/             # UI components (ui/, layout/, forms/)
│   ├── pages/                  # Page components
│   ├── hooks/                  # Custom React hooks
│   ├── stores/                 # Zustand state management
│   └── types/                  # TypeScript types
├── tests/                      # Backend tests (unit/, integration/)
├── alembic/                    # Database migrations
└── docker-compose.yml
```

## Configuration

**Environment variables** (minimal - most config is in database):
```bash
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>  # REQUIRED
DATABASE_URL=sqlite:///./data/homeoffice_assistant.db # Optional
```

**Database-stored config** (encrypted via Fernet):
- Integration credentials (Paperless, Immich, SMTP)
- System settings

## Development Guidelines

### Do
- Use `/skill frontend-design` before UI work
- Run tests before pushing (`pytest` + `bun test`)
- Update `RELEASENOTES.md` for new features
- Use TypeScript strictly (no `any`)
- Keep business logic in services, not route handlers

### Do NOT
- Modify `.env SECRET_KEY` after initial setup (breaks encryption compatibility)
- Put credentials in env vars (use database config)
- Skip tests
- Use `*` imports
- Downgrade tool or library versions
- Use `__future__` imports in Python
- Use npm/npx (use bun/bunx instead)

### Demo Instance
- Port: 8123
- Admin: `roland` / `pass123!`

## Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

Runs automatically: **ruff** (Python), **biome** (TypeScript)

## Code Style

### Python (Ruff)
- Max 88 chars, Google-style docstrings
- `snake_case` functions/variables, `PascalCase` classes
- Type hints required

### TypeScript (Biome)
- Max 100 chars, single quotes (double in JSX)
- `camelCase` functions/variables, `PascalCase` components/types
- Accessibility: `htmlFor` on labels, `type` on buttons

## Release Notes

Update `RELEASENOTES.md` when:
- Adding new features
- Making substantial changes
- Fixing bugs
- Introducing breaking changes

Sync version in `frontend/src/components/layout/Footer.tsx` with app version.

## Git Tags and Releases

**Version tags MUST use the `v` prefix** (e.g., `v0.4.0`, `v0.4.0-dev`, `v1.0.0-beta1`).

The release workflow only triggers on `v*` tags. If the user requests a tag without the `v` prefix, always add it automatically.
