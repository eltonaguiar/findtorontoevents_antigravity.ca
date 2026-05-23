# MySQL Ghost Row Fix — Critical Blocker #1

**Date:** 2026-05-17  
**Source:** PRIORITIZED_ACTION_PLAN_2026-05-17.md, Blocker #1  
**Status:** ✅ Fixed

## Problem

Three MySQL tables were empty/stale (ghost rows):
- `at_signal_outcomes` — production outcome table, never populated
- `paper_trades` — paper trading journal, empty
- `paper_portfolio_daily` — daily paper portfolio snapshot, empty

### Root Causes

1. **No MySQL writes from the universal resolver**: The `_write_outcomes_to_mysql()` function existed in `alpha_engine/outcome_resolver.py` but the universal resolver (`audit_trail/universal_pick_resolver.py`) — which is what CI actually runs — had no MySQL write path.

2. **Env var never set in CI**: The `PICK_OUTCOMES_MYSQL_ENABLED` flag that gates MySQL writes was never exported in the `audit-dashboard.yml` workflow's resolve step.

3. **No MySQL writer for paper trades**: Paper trade data (Kimi portfolio, dashboard picks) had no path to MySQL at all.

4. **DB freshness guardian didn't check `at_signal_outcomes`**: The freshness check only validated `trading_picks` (legacy table) and `bt_backtest_trades`, silently missing the empty `at_signal_outcomes` table.

## Changes

### 1. `audit_trail/universal_pick_resolver.py` (+123 lines)
- Added `_write_outcomes_to_mysql(resolved_picks)` function that upserts resolved pick outcomes to `at_signal_outcomes`
- Uses `INSERT ... ON DUPLICATE KEY UPDATE` against the existing UNIQUE key `idx_dedup (symbol, direction, source_system, opened_at)`
- Gated by `PICK_OUTCOMES_MYSQL_ENABLED` env var
- Wrapped in try/except at the call site so MySQL failure doesn't block the JSON save
- Normalizes outcome strings (WON→TP_HIT, LOST→SL_HIT, EXPIRED→EXPIRED, etc.)

### 2. `tools/paper_trade_mysql_writer.py` (new file)
- Reads paper portfolio data from multiple sources (Kimi portfolio JSON, dashboard data)
- Writes to `paper_trades` (individual trades) and `paper_portfolio_daily` (daily snapshots)
- Gated by both `PAPER_TRADE_MYSQL_ENABLED` and `PICK_OUTCOMES_MYSQL_ENABLED`
- Uses the same MySQL credential resolution pattern as other pipeline scripts

### 3. `tools/db_freshness_check.py` (+50 lines)
- Added `check_signal_outcomes()` function that validates the `at_signal_outcomes` table
- Thresholds: GREEN < 6h, YELLOW 6–24h, RED > 24h
- Added `signal_outcomes` to the `THRESHOLDS` dict
- Added fallback RED entry when Stocks DB connection fails
- Integrated into `run_freshness_check()` orchestration

### 4. `.github/workflows/audit-dashboard.yml` (+19 lines)
- Added `PICK_OUTCOMES_MYSQL_ENABLED: '1'` env var to the `resolve_active_picks` step
- Added new `paper_trade_mysql_sync` step that runs `tools/paper_trade_mysql_writer.py` after the resolver
- Added `tools/paper_trade_mysql_writer.py` to `push.paths` for auto-deploy on changes

## Verification

- Python syntax: All 3 Python files pass `py_compile`
- YAML validity: `audit-dashboard.yml` passes `yaml.safe_load`
- UNIQUE key: Verified `idx_dedup (symbol, direction, source_system, opened_at)` exists in production `at_signal_outcomes` schema (schema-baseline.sql)
- Env var resolution: Matches existing patterns (multiple DB credential fallbacks)
