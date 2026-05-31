# VERIFIED P1 — bt_backtest_trades cross-DB sync is 25 days stale

**Date:** 2026-05-31
**Severity:** P1 (silent data staleness, affects any backtest computed off backtests-side)
**Status:** Verified; draft remediation workflow added; operator action required.

## Verified counts (both sides)

| Side | DB | MAX(id) | MAX(import_at) | Lag |
|------|----|---------|----------------|-----|
| Source | ejaguiar1_stocks.bt_backtest_trades | 32,724,171 | 2026-05-13 | live |
| Target | ejaguiar1_backtests.bt_backtest_trades | 28,705,218 | 2026-05-06 | **25 days behind today** |

Gap: ~4,018,953 rows missing on the backtests-side. Qwen's "3.7M row gap" claim VERIFIED (within rounding).

## Root cause

`tools/migrate_backtests_to_backtests_db.py` exists and works (pymysql-based,
no mysqldump dependency — survives the env where zoo's mysqldump failed). But
it is a **manual one-shot script**: never scheduled via GitHub Actions, never
referenced by any cron/workflow. Last manual run shipped the 2026-05-06
snapshot to backtests-side and nobody re-ran it since.

This means any analytics path that reads from `ejaguiar1_backtests.bt_backtest_trades`
(pf_registry recomputes, strategy_summary refreshes, hedge-fund-tier reports
that consult backtests-side as "the canonical immutable trade ledger") is
silently 25 days stale.

## Remediation

Draft workflow added at `.github/workflows/bt-backtest-trades-sync.yml.draft`:

- Weekly cron Sunday 04:00 UTC + manual workflow_dispatch
- Uses pymysql (no mysqldump)
- Pre-flight compares MAX(import_at) on both sides; aborts if no work
- Incremental sync: `INSERT IGNORE INTO target ... WHERE import_at > target_max`
- 5000-row batch commits, SSDictCursor on source for streaming
- Posts SESSION_SUMMARY via cross-PC gateway when done
- `.yml.draft` extension keeps GitHub from auto-scheduling

## Operator action required

1. Confirm GitHub Secrets exist: `MYSQL_HOST`, `AUDIT_DB_USER`, `AUDIT_DB_PASS`, `BACKTESTS_DB_USER`, `BACKTESTS_DB_PASS`
2. Run `python tools/migrate_backtests_to_backtests_db.py --dry-run` once locally
3. `git mv .github/workflows/bt-backtest-trades-sync.yml.draft .github/workflows/bt-backtest-trades-sync.yml`
4. Trigger first run manually with `dry_run=true`, review counts
5. Trigger again with `dry_run=false` for the catch-up sync (4M rows, off-hours)
6. Let the weekly cron take over

## Warning until enabled

Until the workflow is enabled, any agent recomputing pf_registry /
strategy_summary off the backtests-side must add a 25d-staleness warning to
its output. Prefer reading from `ejaguiar1_stocks.bt_backtest_trades` directly
when freshness matters.

## Memory link

`project-bt-sync-staleness-2026-05-31` — see also `project-day1-close-2026-05-31`,
`project-money-ready-2026-05-31` (the resolver+plumbing thesis).
