# DB Backup Script (Python fallback)

`tools/db_backup_to_backups.py` — backs up MySQL tables to `ejaguiar1_backups`
**without** requiring `mysqldump`. Zoo's swarm hit this on 2026-05-31:
mysqldump is not installed on the 50webs host.

## When to use

Before any destructive remediation (DELETE, TRUNCATE, ALTER, UPDATE in bulk)
against a production table in `ejaguiar1_stocks`, `ejaguiar1_backtests`,
`ejaguiar1_events`, etc.

Per `CLAUDE.md`, destructive DB ops require **operator greenlight**. This
script is the safe-snapshot step that precedes greenlight.

## How it works

For each source table:

1. Pre-flight row-count. If rows > `--row-limit` (default 1M), the table is
   skipped and logged — operator must raise the limit explicitly.
2. `CREATE TABLE ejaguiar1_backups.<table>_<UTC_ISO> AS SELECT * FROM <db>.<table>`
3. Verify row counts match; log to `ejaguiar1_backups.db_audit_log`
   (table created by zoo's swarm).

Idempotent: if a backup with the same UTC suffix already exists, it skips
with a WARN line.

## Usage

```bash
# Dry-run first (no writes, just row counts)
python3 tools/db_backup_to_backups.py \
    --source-db ejaguiar1_stocks \
    --tables trading_picks,at_raw_picks \
    --dry-run

# Real run (after operator greenlight)
python3 tools/db_backup_to_backups.py \
    --source-db ejaguiar1_stocks \
    --tables trading_picks,at_raw_picks \
    --row-limit 1000000
```

## Exit codes

- `0` — all tables backed up cleanly
- `1` — partial (some tables skipped: missing / too big / already exists)
- `2` — hard failure (connect failed, SQL error, verify mismatch)

## Credentials

Reads `DB_HOST`, `DB_USER`, `DB_PASS` from env. Falls back to 50webs
convention `<user>1234560` documented in
`memory/reference-db-password-convention.md`.

## Why this exists

The 2026-05-31 audit-truth-layer cleanup needed snapshots before correcting
leverage and direction-blind PnL columns. Zoo discovered `mysqldump` is not
on the host; this Python path is the workaround so backups are no longer
gated on a binary we cannot install.
