# Setup prompt: agent pipeline for a Python web service

Paste the block below into Claude Code in a project root to (re)create the
pipeline. The installed result in this repo is the reference implementation:
`.claude/pipeline/RULES.md`, `.claude/skills/hoa-pipeline/SKILL.md`,
`.claude/agents/hoa-*.md`, `.claude/pipeline/check_limits.py`.

```text
Set up a subagent pipeline for this repository (Python/FastAPI backend,
React/Bun frontend, Alembic, Docker image released by GitHub Actions).
Prefix all names with <prefix>- (e.g. hoa-).

Files:
- .claude/pipeline/RULES.md: shared rules every agent reads first
- .claude/skills/<prefix>-pipeline/SKILL.md: the orchestrator (main loop)
- .claude/agents/<prefix>-{investigator,planner,plan-reviewer,implementer,
  refactorer,reviewer,presenter,uidesign}.md, each with name, description
  ("Dispatched by the <prefix>-pipeline skill only"), default model
- .claude/pipeline/check_limits.py: limits checker with --hook, CLI and
  --selftest modes, run at Finish via `uv run --no-project python -I`
- a short "Agent Pipeline" section in CLAUDE.md (CLAUDE.md max 200 lines)

Stages: Investigation -> Plan (+ UI Design with user sign-off for visible UI)
-> Plan Review -> Implement (slices in parallel waves, then one verify run)
-> Refactor (audit only, findings go back to the planner) -> Review -> Present.

Task types: bugfix, feature, infra (Docker, CI/CD, deps, tooling), audit
(verify and refactor the existing system). Audit: the root investigator
requests one sub-investigation per area (backend api, services/models,
migrations, plugins, frontend, docker, ci-cd, docs/agent instructions);
each writes a findings register design/findings-<area>.md with rows
id | must/should/could | file:line | problem | fix. Then exactly one
ask-user scope question (severity, areas, or report-only). Out-of-scope
findings stay parked in the register for later audit tasks.

Orchestrator rules: only dispatches, routes and keeps a ledger
(docs/specs/<task>/work/ledger.md, one line per dispatch/result/ruling);
never investigates, plans, edits or reviews itself. Model set explicitly on
every dispatch: investigator/planner/plan-reviewer/reviewer opus,
sub-investigator sonnet (opus for auth, RBAC, encryption, migrations),
implementer per slice tier haiku|sonnet|opus, refactorer/presenter/uidesign
sonnet. Agents reply with exactly one line DONE|INCOMPLETE|FAILURE <path>;
the orchestrator reads only the `## Next` section of that document.
INCOMPLETE: retry once one tier higher. Max 3 replans, 2 reimplements per
round, one level of sub-investigations. Rulings instead of stalls; ask the
user only in Investigation, at UI sign-off, and for destructive, security,
data-losing or push/tag/deploy actions. Work branch <fix|feature|infra|audit>/<slug>;
never commit, push, tag (v* tags deploy!) or deploy. Teardown only on
explicit user request, `git branch -d`, never -D.

Paths: plans docs/specs/<task>/plan.md, work documents
docs/specs/<task>/work/<stage>[-<area|slice>]-r<round>.md, overflow in
docs/specs/<task>/work/design/, mockups docs/mockups/<task>/ (all gitignored).
Work document shape: title, Status, Inputs, Result, Findings/Open points,
Next (last section, routing lines only).

Limits (checked at Finish by check_limits.py): work documents 200 lines (design/ unlimited);
handover/todo/checklist 70 lines; CLAUDE.md and copilot-instructions.md
200 lines; TODO lists hold open items only (no [x], no strikethrough).
Judgment limits (refactorer/reviewer): new function > 50 lines, Python file
> 500 lines or TSX component > 400 lines after the change needs a split or
a reason in the plan.

Verification gate: ci.yml is the source of truth; RULES.md holds its local
translation (pip -> uv run) and must be updated whenever ci.yml changes:
ruff check, ruff format --check on changed files, pytest core and plugins,
Biome, frontend build, Vitest, hadolint. Extra gates: alembic upgrade head +
alembic check on a scratch DB for model/migration changes; docker build when
Dockerfile, lockfiles or alembic change (reviewer only); actionlint for
workflow changes. Implementers in slice mode run only file-local checks
(parallel runs collide); one verify run fixes in-scope failures; the
reviewer re-runs everything and records baseline failures separately.

Planner/refactorer/reviewer enforce single source of truth: no hand lists
of enums, permissions, settings keys or routes, no re-implemented
derivation, no hand-copied frontend types without a drift test. Model
change + migration (with downgrade) are one slice. Presenter updates
RELEASENOTES.md for user-visible changes and writes PRESENT.md (summary,
changes, release notes, deployment impact, watch-outs, how to test, audit
status, references), max 200 lines.

RULES.md must not repeat CLAUDE.md conventions; it references them.
Verify the commands actually run locally before writing them down.
```
