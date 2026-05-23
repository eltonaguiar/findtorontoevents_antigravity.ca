# DB Review Tools — Index

Grouped tools for reviewing the live `ejaguiar1_stocks` + `ejaguiar1_backtests` MySQL DBs at `mysql.50webs.com`. All tools share the canonical connection helper at `audit_trail/mysql_client.py::_create_connection()`.

## Sources

### `kimi_2026-05-08/` — Kimi-Agent's parallel DB review

22 files, 2.4 MB. Parallel-agent exploration of both DBs.
- `plan.md` — 3-stage plan
- `db_stocks_exploration.md`, `db_backtests_exploration.md` — per-DB exploration
- `stocks_crossvalidation.md`, `backtests_crossvalidation.md` — cross-validation
- `FULL_DATABASE_REVIEW.md` — final integrated report (500+ lines)
- `Database_Review_mysql50webs.docx` — Word version
- `run_*.py`, `micro_*.py` — query scripts (small/big/info/indexed/all)
- `*.json` — query result snapshots

### Existing `audit_*` scripts (in repo root, freebuff-curated)

Use directly via `python <name>.py` — all already wire to `mysql_client._create_connection()`:
- `audit_comprehensive_report.py` — full-spectrum audit across DB
- `audit_final_summary.py` — summary-level aggregation
- `audit_detailed.py` — row-level inspection
- `audit_suspicious.py` — anomaly flagging
- `audit_outliers.py` — statistical outlier detection
- `audit_synthetic_patterns.py` — synthetic-data pattern detector (currently scans `consensus_tracked`; extend to `bt_backtest_trades`)
- `audit-daily.py` — daily run, supports 15GB SQL dump file input

### Pipeline / sync infrastructure

- `audit_trail/mysql_client.py` — `_create_connection()` foundation
- `audit_trail/mysql_schema.sql` — DDL for 12 audit tables
- `audit_trail/recorder.py` — audit-event recorder
- `audit_dashboard/database_consolidation.py` — unified dashboard view
- `alpha_engine/audit_sync.py` — full MySQL sync orchestrator (runs in `audit-dashboard.yml` + `alpha-engine-live.yml`)
- `tools/sql_dump_analyzer.py` (in `specs/`) — streaming phpMyAdmin dump analyzer (multi-line state machine bug — low priority)

### Specs / blueprints

- `AUDIT_BLUEPRINT.md` — full architecture overview (table map, FK relationships, INSERT IGNORE pattern, migration steps)
- `audit_dashboard/BLUEPRINT.md` — dashboard-specific blueprint
- `docs/PERFORMANCE_CHARTER.md` — Tier-1/Tier-2 thresholds (PF/WR/MDD)

### Forensic reports (in `reports/`)

- `db_master_synthesis_2026-05-07.md` — initial forensic synthesis
- `db_action_plan_2026-05-08.md` — 24-todo action plan
- `db_action_plan_delta_2026-05-08.md` — peer-audit reconciliation (+ 8 new findings)
- `db_review_vetted_summary_2026-05-08.md` — vetted single-source-of-truth (20 confirmed F1-F20, 11 retracted)
- `db_evidence_graded_final_2026-05-08.md` — swarm-evidence-graded final
- `freeze_2026_04_02_root_cause_2026-05-08.md` — smoking gun (`circuit_breaker_state.json` stale HALT)
- `uncharted_tables_recon_2026-05-08.md` — 6-family sweep (gm_*, mf_*, fxp_*, etc.)
- `peer_audit_factcheck_2026-05-08.md` + `_part2_2026-05-08.md` — peer-claim verifications
- `forensic_q1_q4_2026-05-07.md`, `q5_q7`, `crypto_edge_hunt_2026-05-07.md`, `non_crypto_resolver_gap_2026-05-07.md`, `meme_sports_edge_2026-05-07.md`

### Workflows

- `.github/workflows/audit-dashboard.yml` — hourly dashboard regen
- `.github/workflows/alpha-engine-live.yml` — every-2h scan + 17-min MySQL sync (90-min timeout)
- `.github/workflows/backfill.yml` — regenerates `backfill_import.sql` (309 MB, 382K+ trades)

## Conventions

- Read-only first. Never INSERT/UPDATE/DELETE without an explicit migration script + rollback path.
- Row counts: ALWAYS use `SELECT COUNT(*)`. Never `information_schema.TABLES.TABLE_ROWS` (InnoDB approximation under-counts by up to 22.7×).
- DB version: MySQL 8.4.7 (NOT MariaDB).
- Connection: `_create_connection()` reads `AUDIT_DB_HOST/USER/PASS/NAME` env vars; default to `mysql.50webs.com` / `ejaguiar1_stocks` / `stocks`.
- For backtests DB: `AUDIT_DB_USER=ejaguiar1_backtests AUDIT_DB_PASS=backtests AUDIT_DB_NAME=ejaguiar1_backtests`.
