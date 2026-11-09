# CLAUDE.md - Project Guidelines for Claude Code

## Project: HomeOffice Assistant

A self-hosted personal productivity and work management assistant with external
system integrations. Deployed as a single Docker image (backend + built frontend),
released by GitHub Actions on `v*` tags.

## Quick Reference

```bash
# Backend
uv sync --extra dev                              # Install with dev tools
uv run --extra dev pytest tests/                 # Core tests
uv run --extra dev pytest plugins/*/tests/       # Plugin tests
uv run --extra dev ruff check src/               # Lint (CI gate)
uv run uvicorn src.main:app --reload             # Dev server on :8000

# Frontend (run inside frontend/)
bun install
bun run dev                     # Dev server on :5173
bun run build                   # tsc + production build
bun run test                    # Vitest (NOT `bun test`, Bun's own runner skips most tests)
bun run lint                    # Biome

# Docker (full stack)
docker compose up --build
```

Tests need `SECRET_KEY` set (any 32+ chars) and a `DATABASE_URL`; CI uses
`sqlite:///./test.db`. The full local equivalent of CI is in
`.claude/pipeline/RULES.md` (Verification gate).

## Agent Pipeline

Every request that changes backend, frontend, plugins, migrations, Docker, CI/CD
or docs runs through the `hoa-pipeline` skill automatically, without being asked.
Requests to verify, audit or refactor existing code run as task type `audit`.
Read-only questions and git housekeeping are answered directly.
The main loop only dispatches the `hoa-*` agents in `.claude/agents/` and never
does a stage's work itself. Stages, task types, paths, document limits and the
verification gate: `.claude/pipeline/RULES.md`. Plans and work documents go to
`docs/specs/<task>/`.

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, Python 3.14 |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Zustand, Vite |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Testing** | pytest (backend), Vitest (frontend) |
| **Linting** | Ruff (Python), Biome (TypeScript), hadolint (Dockerfile) |

## Project Structure

```
homeoffice-assistant/
├── src/                        # Backend (Python/FastAPI)
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings
│   ├── database.py             # SQLAlchemy setup
│   ├── version.py              # APP_VERSION, read from pyproject.toml
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── api/v1/                 # API route handlers
│   ├── services/               # Business logic
│   ├── integrations/           # External system clients (Paperless, Immich, LLM, SMTP)
│   ├── rbac/                   # Roles and permissions
│   ├── plugins/                # Plugin system (loader, registry, migrations)
│   └── utils/                  # Shared helpers
├── plugins/<name>/             # Plugins: backend/, frontend/, tests/, manifest
├── frontend/src/
│   ├── api/                    # API client
│   ├── components/             # UI components
│   ├── pages/                  # Page components
│   ├── lib/, utils/            # Shared frontend helpers
│   ├── plugins/                # Frontend plugin loader
│   ├── stores/                 # Zustand state management
│   └── types/                  # TypeScript types (api.generated.ts is generated)
├── tests/                      # Backend tests (unit/, integration/)
├── scripts/                    # CI and ops scripts (plugin_deps, backup, restore)
├── alembic/                    # Database migrations
├── docker/                     # Dockerfile, entrypoint
└── .github/workflows/          # ci.yml (checks), release.yml (image on v* tags)
```

## Configuration

**Environment variables** (minimal - most config is in database):
```bash
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>  # REQUIRED
DATABASE_URL=sqlite:///./data/homeoffice_assistant.db # Optional
```

**Database-stored config** (encrypted via Fernet): integration credentials
(Paperless, Immich, SMTP, LLM) and system settings.

## Development Guidelines

### Shell Command Rules
- **Never** use `git -C <repo>`; the shell is already in the correct repo. If there is no git repository, STOP and ask the user how to proceed
- **Never** prefix shell commands with `cd <cwd>`; a subshell `(cd frontend && ...)` for frontend commands is fine
- **Always** run python and pip through `uv run`. NEVER source or activate a virtualenv
- Use bun/bunx, never npm/npx

### Do
- Keep business logic in services, not route handlers
- Add or change tests with every behavior change; run tests before pushing
- Ship an Alembic migration (with `downgrade()`) with every model change
- Use TypeScript strictly (no `any`)

### Do NOT
- Modify `.env SECRET_KEY` after initial setup (breaks encryption compatibility)
- Put credentials in env vars (use database config)
- Skip tests
- Use `*` imports or `from __future__` imports in Python
- Downgrade tool or library versions

### Demo Instance
Port and credentials live in the untracked `CLAUDE.local.md` (gitignored).

### Troubleshooting Frontend Changes Not Showing
1. First, close the browser and reopen to clear cache
2. If still not working, rebuild Docker image: `docker compose build --no-cache`
3. Never rebuild more than once - assume it fixes all caching issues
4. If rebuild doesn't help, the issue is in the TypeScript code
5. If code appears correct but changes still don't show, STOP and ask the user

## Code Style

### Python (Ruff)
- Max 88 chars, Google-style docstrings
- `snake_case` functions/variables, `PascalCase` classes
- Type hints required
- No `# noqa` comments - fix the underlying issue instead
- SQLAlchemy boolean filters: use `Model.is_active` not `Model.is_active == True`

### TypeScript (Biome)
- Max 100 chars, single quotes (double in JSX)
- `camelCase` functions/variables, `PascalCase` components/types
- Accessibility: `htmlFor` on labels, `type` on buttons

Pre-commit (ruff, ruff-format, Biome): `uvx pre-commit install`.

## Release Notes

**REQUIRED**: update `RELEASENOTES.md` for every new feature, substantial change,
user-visible bug fix and breaking change. When creating or updating a pull request,
verify the section for the branch matches what was actually implemented.
The version lives in `pyproject.toml` and `frontend/package.json`; the Footer
reads it at build time and `tests/unit/test_version.py` fails when they drift.

## Git Tags and Releases

**Version tags MUST use the `v` prefix** (e.g., `v0.4.0`, `v0.4.0-dev`, `v1.0.0-beta1`).
The release workflow only triggers on `v*` tags. If the user requests a tag without
the `v` prefix, add it automatically.

## Mockups and Specifications

Local-only, gitignored, never commit: `docs/mockups/<feature>/` (HTML mockups with
an `index.html`) and `docs/specs/<feature>/` (plans and pipeline work documents).

**Mockups are REQUIRED** for any UI change beyond trivial modifications: new pages or
views, layout changes, new or redesigned components, navigation and form redesigns.
Never ASCII mockups. In the pipeline the `hoa-uidesign` agent builds them with the
`frontend-design` skill in the current design language, the user signs off before
implementation, and the reviewer compares the implementation against them with Playwright.
