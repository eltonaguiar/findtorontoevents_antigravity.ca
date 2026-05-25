# Ghost Row Cleanup Script

**Date:** 2026-05-24
**Files changed:** `tools/cleanup_ghost_rows.py`, `tools/test_ghost_cleanup.py`

## What was broken

The MySQL database `ejaguiar1_stocks` table `bt_backtest_trades` contained **56,559 ghost rows** — duplicate entries sharing the same (symbol, strategy, direction, entry_price) with identical data. Top offenders:

| Symbol | Strategy | Direction | Entry Price | Duplicate Rows |
|--------|----------|-----------|-------------|----------------|
| MATICUSDT | quan_engine | LONG | 150000 | 20,474 |
| DOGEUSDT | meta_strategy | LONG | 500000 | 5,661 + 4,199 |
| WIFUSDT | meta_strategy | SHORT | 500000 | 4,644 |
| SHIBUSDT | meta_strategy | LONG | 500000 | 4,158 |
| DOGEUSDT | sandbox_opposite | LONG | 500000 | 2,862 |
| GBPJPY | KIMI_signal_tracker | LONG | 500000 | 1,313 |

Detected by `audit_dashboard/data/db_health.json` ghost_rows check (took 484s to run).

## What was changed

### `tools/cleanup_ghost_rows.py`
- Connects to MySQL using `tools/db_env.py` credential resolution (same pattern as `db_freshness_check.py`, `ghost_sweep_2026_05_08.py`)
- Discovers ghost cohorts: groups by (strategy, symbol, direction, entry_price) with count > min_size
- For each cohort: keeps the row with lowest `id`, deletes the rest
- **DRY_RUN mode by default** — shows what would be deleted, nothing modified
- **`--execute`** flag required for actual deletion
- **`--no-limit`** flag removes the 1000-row safety cap
- Wraps all deletes in a single transaction (rollback on error)
- Reports before/after counts and per-cohort summaries
- Writes JSON report to `tools/ghost_cleanup_report.json`

Usage:
```bash
# Dry run (default)
python tools/cleanup_ghost_rows.py

# Dry run with higher min cohort size
python tools/cleanup_ghost_rows.py --min-size 100

# Execute with safety cap (1000 rows max)
python tools/cleanup_ghost_rows.py --execute

# Execute without cap
python tools/cleanup_ghost_rows.py --execute --no-limit

# Target a single symbol
python tools/cleanup_ghost_rows.py --execute --cohort-only MATICUSDT
```

### `tools/test_ghost_cleanup.py`
- 24 unit tests covering:
  - DELETE SQL generation (basic, with limit, string entry prices, SHORT direction)
  - Cohort detection SQL and result parsing
  - Dry run mode (no deletes, accurate reporting)
  - Execute mode (delete + commit, rollback on error)
  - Safety cap (max_deletes enforcement, no-limit mode)
  - Edge cases (cohort size 1, exact threshold, cap exhaustion)
  - Integration scenario with realistic ghost cohort data from db_health.json

## How it was verified

```
$ python3 -m pytest tools/test_ghost_cleanup.py -v
======================== 24 passed in 0.08s =========================
```

All tests pass. No real database connection required — all DB queries are mocked.

## Safety notes

- **DRY_RUN is the default.** Nothing is deleted without explicit `--execute` flag.
- **1000-row cap** limits damage per run. Use `--no-limit` only after reviewing dry run output.
- **Transaction-wrapped.** Any error during deletion causes full rollback.
- **Confirmation prompt** before `--execute` (skip with `--yes`).
- Uses repo's standard `tools/db_env.py` credential resolution — no hardcoded credentials.
