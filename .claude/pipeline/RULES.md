# Pipeline rules

Every pipeline agent reads this file first.

## Stages

Investigation -> Plan (+ UI Design for UI tasks, user sign-off) -> Plan Review
-> Implement -> Refactor -> Review -> Present

Task types: `bugfix` (broken behavior), `feature` (new functionality),
`infra` (Docker, CI/CD, dependencies, Alembic setup, tooling),
`audit` (verify and refactor existing code: no new behavior; the
investigation inspects the current state of an area instead of a change).
Work branches are `<fix|feature|infra|audit>/<slug>`.

## Paths

All work files live under `docs/specs/` (gitignored) and `docs/mockups/`.

- Work documents: `docs/specs/<task>/work/<stage>[-<area|slice>]-r<round>.md`
  e.g. `investigation-r1.md`, `investigation-frontend-r1.md`, `implement-s2-r1.md`
- Design documents: `docs/specs/<task>/work/design/<topic>.md` (call graphs,
  excerpts, long finding lists: anything too long for a work document).
- Plan: `docs/specs/<task>/plan.md`. Reference by path, never copy.
- Planner round summary: `docs/specs/<task>/work/plan-r<round>.md`.
- Mockups (UI tasks): `docs/mockups/<task>/` with `index.html`.
- Present: `docs/specs/<task>/work/PRESENT.md`
- Ledger: `docs/specs/<task>/work/ledger.md`, written only by the orchestrator.
  One line per dispatch, result, ruling and parked finding. Agents may read it.

Never `git add`, commit, push, tag or deploy. The user does that.
A `v*` tag triggers a production image release; never create one.

## Status protocol

Your final message is exactly one line:

    DONE <path-to-work-document>
    INCOMPLETE <path-to-work-document>
    FAILURE <path-to-work-document>

DONE: stage goal reached. INCOMPLETE: partial, gaps listed in the document.
FAILURE: could not proceed, cause in the document.

## Work document shape

    # <Stage>: <task> (round N)
    Status: DONE | INCOMPLETE | FAILURE
    Inputs: <documents read>
    ## Result
    ## Findings / Open points
    ## Next
    <one routing line per item, syntax per agent definition>

`## Next` is the last section. The orchestrator reads only it.

## Limits (checked at Finish by check_limits.py)

- Work document: max 200 lines. Overflow goes into a design document.
- Handover, TODO and checklist documents: max 70 lines.
- `CLAUDE.md` (any level) and `.github/copilot-instructions.md`: max 200 lines.
- TODO lists hold open items only. Delete done items; no `[x]`, no strikethrough.
- Source size (refactorer/reviewer judgment, not hooked): a new function over
  50 lines, or a change that pushes a file over 500 lines (Python) / 400 lines
  (TSX component), needs a split or a reason in the plan's Decisions.

## Verification gate

`.github/workflows/ci.yml` is the source of truth. The commands below are its
local translation (pip -> `uv run`). When ci.yml changes, update this list in
the same task; a mismatch between the two is a finding.

    export SECRET_KEY='test-secret-key-for-ci-testing-only-32!' DATABASE_URL=sqlite:///./test.db
    uv sync --extra dev --frozen
    uv run --extra dev ruff check .                          # CI lint job
    uv run --extra dev ruff format --check .
    uv run python -m scripts.plugin_deps                     # plugin deps vs lock
    mkdir -p static/assets
    uv run --extra dev pytest --cov=src --cov-report=xml     # tests/ + plugins/
    DATABASE_URL=sqlite:///./data/alembic-check.db uv run alembic upgrade head    # CI migrations job
    DATABASE_URL=sqlite:///./data/alembic-check.db uv run alembic check
    DATABASE_URL=sqlite:///./data/alembic-check.db uv run alembic downgrade base
    DATABASE_URL=sqlite:///./data/alembic-check.db uv run alembic upgrade head
    rm -f data/alembic-check.db
    (cd frontend && bun install --frozen-lockfile)
    (cd frontend && bun run gen:types && git diff --exit-code src/types/api.generated.ts)  # generated API types
    (cd frontend && bun run lint)                            # Biome (pinned)
    (cd frontend && bun run build)                           # tsc + vite
    (cd frontend && bun run test)                            # Vitest
    hadolint docker/Dockerfile                               # CI dockerfile-lint
    shellcheck scripts/*.sh                                  # CI shellcheck

Extra gates by touched files:

- `src/models/`, `alembic/`, plugin `migrations/`: the migration commands of
  the gate above (CI runs them on every change); delete the DB afterwards. New
  models need a migration with a working `downgrade()`.
- `docker/`, `pyproject.toml`, `uv.lock`, `frontend/package.json`, `bun.lock`,
  `alembic/`: `docker build -f docker/Dockerfile -t hoa-review .` (reviewer only;
  CI builds it without push on PRs touching these paths).
- `.github/workflows/`: `actionlint` when installed, otherwise a careful read.

The root `conftest.py` gives every pytest process its own temporary SQLite
database, so test databases never collide. Coverage files do: `--cov` writes
`./.coverage` and `./coverage.xml`, and parallel runs crash on them. An agent
that runs pytest while other agents may run it too either drops `--cov`
(slice checks) or sets its own paths:
`COVERAGE_FILE=.coverage.<id> uv run --extra dev pytest --cov=src --cov-report=xml:coverage-<id>.xml`,
and deletes both files afterwards. Only the single verify or review run uses
the plain gate command. Pre-existing failures outside the task are recorded in
the work document as baseline, not fixed.

## Repository rules

`CLAUDE.md` holds the project conventions (code style, layering, tooling,
shell rules) and is loaded automatically; it is the single source, this file
does not repeat it. Pipeline additions:

- Comments explain reasoning directly; never cite `docs/specs/`, plans or stages.
- `eza` instead of `ls`/`tree` is the user's personal preference (global
  CLAUDE.md), not a project rule. Scripted bulk edits: Python via `uv run`.
- Scratch databases go under `data/` (gitignored) and are deleted after use.
