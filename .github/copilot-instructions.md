# GitHub Copilot Review Instructions

When reviewing code in this repository, apply the following guidelines from CLAUDE.md:

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic
- **Frontend**: React 18, TypeScript, Tailwind CSS, Zustand, Vite
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Linting**: Ruff (Python), Biome (TypeScript)

## Code Style

### Python (Ruff)

- Max 88 characters per line
- Google-style docstrings
- `snake_case` for functions/variables, `PascalCase` for classes
- Type hints required for function parameters and return types

### TypeScript (Biome)

- Max 100 characters per line
- Single quotes for strings, double quotes in JSX
- `camelCase` for functions/variables, `PascalCase` for components/types
- Accessibility required: `htmlFor` on labels, `type` attribute on buttons

## Review Focus Areas

Flag violations of these rules:

### Do NOT allow

- `*` imports in Python
- `__future__` imports in Python
- npm/npx usage (project uses bun/bunx)
- Credentials or secrets in environment variables (should use database config)
- Business logic in route handlers (should be in services)
- `any` type in TypeScript
- Missing type hints in Python
- Downgrading library versions

### Require

- Tests for new functionality
- Type hints on all Python functions
- Strict TypeScript (no `any`)
- Business logic in `src/services/`, not in API route handlers
- Updates to `RELEASENOTES.md` for new features

## Architecture

- API routes: `src/api/v1/`
- Business logic: `src/services/`
- Database models: `src/models/`
- External integrations: `src/integrations/`
- Frontend components: `frontend/src/components/`
- Frontend state: `frontend/src/stores/` (Zustand)
