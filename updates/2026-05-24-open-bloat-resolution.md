# Open Pick Bloat Resolution — Stale Pick Resolution Scripts

**Date:** 2026-05-24
**Author:** Qwen Code
**Status:** Implemented, pending production execution

## Problem

`audit_dashboard/data/db_health.json` reported **29,254,204 OPEN picks** as of 2026-05-24T05:54Z. The last terminal write to the trading_picks table was `2026-05-12 23:42:27` — over 270 hours since any pick was closed. The `open_bloat` check in db_health was **RED** (threshold_pass: false).

### Root Cause Analysis

1. **`universal_pick_resolver.py`** resolves picks from JSON active pick files on disk — it does NOT resolve picks stored in the MySQL `trading_picks` table. It processes ~100 systems' active_picks.json files, checks TP/SL with live prices, and applies TIME_EXIT for picks older than per-class MAX_HOLD_HOURS. This works fine for the file-based pick system.

2. **`mysql_stale_picks_resolver.py`** exists in the workflow (`mysql-stale-picks-resolver.yml`, cron: daily 4 AM UTC) but uses a fundamentally different resolution approach:
   - Uses **yfinance** to fetch historical prices (slow, rate-limited, requires per-symbol network calls)
   - Resolves as **WIN/LOSS** based on price comparison at a target date
   - Uses hold periods in **DAYS** (7-30 days) instead of HOURS (48-120h)
   - Default batch size of 500, default 30-day max age
   - Defaults to `--dry-run` on scheduled runs, so even when it runs, it doesn't actually resolve anything

3. The MySQL `trading_picks` table accumulated 29M+ OPEN rows because no process was efficiently closing them with a simple TIME_EXIT based on age thresholds.

### db_health RED Checks

| Check | Tier | Issue |
|-------|------|-------|
| `pnl_integrity` | RED | 38.97% PnL mismatch on sampled rows |
| `won_pnl_contradiction` | RED | WON status rows with avg PnL of -41.13% |
| `open_bloat` | RED | 29,254,204 OPEN picks, 270h since last close |

## Changes

### 1. `tools/resolve_stale_open_picks.py` (NEW)

Batch-resolves stale OPEN picks directly in MySQL using per-asset-class hold windows:

| Asset Class | Max Hold Hours |
|-------------|---------------|
| CRYPTO | 48h |
| EQUITY / ETF / COMMODITY / FUTURES | 96h |
| FOREX / BOND | 120h |

**Key design decisions:**
- **Matches universal_pick_resolver.py constants** — same MAX_HOLD_HOURS_BY_CLASS dict
- **TIME_EXIT approach** — sets status='TIME_EXIT', exit_reason='TIME_EXIT_MAX_HOLD', exit_price=entry_price, pnl_pct=0.0 (flat). This avoids the expensive yfinance price lookups that were bottlenecking the existing resolver.
- **DRY_RUN default** — `--execute` flag required for actual writes
- **Batch size 1000** (configurable via `--batch-size`)
- **Reports by asset class and strategy** — shows which strategies are accumulating stale picks
- **No yfinance dependency** — only requires pymysql

**Usage:**
```bash
# Preview (default)
python tools/resolve_stale_open_picks.py

# Execute
python tools/resolve_stale_open_picks.py --execute

# Large batch
python tools/resolve_stale_open_picks.py --execute --batch-size 10000
```

**For 29M picks**, recommend running in batches of 10,000 with `--max-batches` to avoid hitting GitHub Actions timeout limits.

### 2. `tools/check_resolver_health.py` (NEW)

Health check script that outputs a JSON report:

- **`open_picks_count`** — total OPEN picks, alerts if > 1M (configurable via `--threshold`)
- **`stale_by_asset_class`** — groups OPEN picks by asset class with estimated stale counts
- **`last_resolver_run`** — checks when universal_resolved_picks.json was last modified
- **`db_connectivity`** — verifies MySQL connection

Exit codes: 0 = GREEN, 1 = YELLOW, 2 = RED

**Usage:**
```bash
python tools/check_resolver_health.py
python tools/check_resolver_health.py --threshold 500000
```

### 3. `tools/test_resolver_health.py` (NEW)

Unit tests with mocked DB connections covering:
- MAX_HOLD_HOURS constants match universal_pick_resolver.py
- Pick age calculation from datetime and string timestamps
- Staleness detection per asset class
- PnL computation for LONG/SHORT positions
- DB connectivity checks
- Open picks count threshold alerts
- Last resolver run file checks
- Full health report composition

## Verification

Run tests:
```bash
python tools/test_resolver_health.py
```

## Recommended Production Execution

Given 29M OPEN picks, the resolver should be run in stages:

1. **First, verify with health check:**
   ```bash
   python tools/check_resolver_health.py --json
   ```

2. **Run a small dry run to estimate scope:**
   ```bash
   python tools/resolve_stale_open_picks.py --batch-size 1000 --max-batches 5
   ```

3. **Execute in batches** (to avoid timeout on GitHub Actions):
   ```bash
   python tools/resolve_stale_open_picks.py --execute --batch-size 10000 --max-batches 100
   ```
   Each batch of 10,000 resolves ~10K stale picks. For 29M, this needs ~2900 batches.

4. **Alternative: Run locally** (not in CI) for the full purge:
   ```bash
   python tools/resolve_stale_open_picks.py --execute --batch-size 50000
   ```

## How This Was Verified

- Unit tests pass with mocked DB (no live DB required for test validation)
- Hold window constants match universal_pick_resolver.py exactly
- PnL computation is direction-aware (LONG/SHORT)
- Staleness threshold logic correctly applies per-asset-class windows

## Notes

- The existing `mysql_stale_picks_resolver.py` is NOT replaced — it serves a different purpose (WIN/LOSS resolution based on historical prices). This new script is specifically for the TIME_EXIT bloat cleanup.
- After the initial purge, the `mysql-stale-picks-resolver.yml` workflow should be updated to use `--execute` mode (instead of default `--dry-run`) to prevent future accumulation.
- The `open_bloat` check in `db_health.json` should go from RED to GREEN after resolution completes.
