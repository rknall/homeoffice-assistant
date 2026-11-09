# Database-Independent Backup

## Status
Idea - Not Started

## Plugin Candidate
No - Backup is a core operations concern.

## Problem
`scripts/backup.sh` and `scripts/restore.sh` copy the SQLite file. SQLite is the working target today; PostgreSQL stays documented in the README, `.env.example` and the commented compose service but is not exercised. A PostgreSQL deployment would need a different backup path (`pg_dump`/`pg_restore`), and the current scripts would silently produce no usable database backup there.

## Proposed Solution
- Detect the database type from `DATABASE_URL`
- SQLite: online backup API (current behavior)
- PostgreSQL: `pg_dump` into the same archive layout, restore via `pg_restore`
- Same archive layout for avatars and logos

## Implementation Notes
- Related parked cleanup findings: M1, M7, M8, SM-08 (PostgreSQL compatibility of migrations and models); fix those before offering PostgreSQL as supported.
- Add a restore round-trip test per database type.

## Related
- `scripts/backup.sh`, `scripts/restore.sh`
- docs/architecture/UUID_MIGRATION.md
