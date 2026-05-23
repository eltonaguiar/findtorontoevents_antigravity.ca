# Why 84% of Trades Were Stuck as OPEN in ejaguiar1_stocks

**Date:** 2026-04-11
**Author:** OpenClaw Analysis
**Status:** CRITICAL historical incident analysis (snapshot-based)

---

## Executive Summary

The `ejaguiar1_stocks` database on `mysql.50webs.com` has **1,718 out of 2,162 (79.5%) picks stuck in OPEN status** that should have been closed. Only 444 picks (20.5%) have been settled (WON/LOST/EXPIRED/CLOSED).

This is not a market issue — it was a **sync pipeline bug** that prevented OPEN picks from being updated to CLOSED status in MySQL at the time of this snapshot.

---

## Data Snapshot (from SQL dump `10_123_0_33 (6).sql`)

| Status  | Count | Pct    |
|---------|-------|--------|
| OPEN    | 1,718 | 79.5%  |
| WON     | 196   | 9.1%   |
| LOST    | 173   | 8.0%   |
| CLOSED  | 47    | 2.2%   |
| EXPIRED | 28    | 1.3%   |
| **Total** | **2,162** | **100%** |

### Asset Class Distribution (all tables)

| Asset Class | Mentions |
|-------------|----------|
| CRYPTO      | 9,505    |
| FOREX       | 781      |
| MEMECOIN    | 376      |
| UNKNOWN     | 328      |
| EQUITY      | 323      |
| ETF         | 22       |
| SPORTS      | 7        |
| PENNY_STOCK | 7        |

### Filter Activity

| Filter Reason   | Count |
|-----------------|-------|
| demoted_system  | 56    |
| wr_suppressed   | 14    |

---

## Root Cause (Historical): INSERT IGNORE Never Updates OPEN -> CLOSED

### The Bug (sync_all_picks_to_mysql.py)

The sync script uses `INSERT IGNORE` for all pick inserts:

```python
cur.execute(
    "INSERT IGNORE INTO at_raw_picks "
    "(id, aggregation_run_id, source_system, symbol, ...) "
    "VALUES (%s,%s,%s,%s,...)",
    (pick_id, self.run_id, source_system, symbol, ...)
)
```

**How the bug works:**

1. **First sync:** Pick X is OPEN -> `INSERT INTO at_raw_picks ... status='OPEN'`
2. **Locally, pick X closes** (TP hit, SL hit, or time exit after 24h) -> `rapid_fire_data/pick_tracker.py` writes to `closed_picks.json` with status='TP_HIT'
3. **Next sync runs:** Picks up the same pick from `closed_picks.json`, tries `INSERT INTO at_raw_picks ... status='WON'`
4. **`INSERT IGNORE`** sees the `dedup_hash` already exists -> silently drops the insert
5. **Result:** Pick X stays `OPEN` forever in MySQL

The `dedup_hash` is computed from `(symbol, direction, entry_price, rounded_5min_timestamp)` — identical for both the OPEN and CLOSED versions of the same pick.

### There Was Zero UPDATE Logic In The Affected Snapshot

In the affected snapshot of `sync_all_picks_to_mysql.py`:

- No `UPDATE at_raw_picks SET status=` anywhere
- No `ON DUPLICATE KEY UPDATE` clause
- No post-sync reconciliation pass
- The `_insert_raw_pick()` method only did `INSERT IGNORE` and did not modify existing rows

### The MySQL Check Is Circular

Guard 3 in `_insert_raw_pick()` checks if an OPEN pick already exists before inserting:

```python
cur.execute(
    "SELECT COUNT(*) FROM at_raw_picks "
    "WHERE symbol=%s AND direction=%s AND source_system=%s AND status='OPEN'",
    (symbol, direction, source_system)
)
existing = cur.fetchone()[0]
if existing > 0:
    self.stats["dupes_skipped"] += 1
    return False  # <-- Silently drops the CLOSED update
```

This confirms the OPEN row exists and then does nothing. It skips the insert. It doesn't update the existing row to CLOSED.

---

## Secondary Issues

### 1. SQL Dumps Committed to GitHub (SECURITY)

- `data/10_123_0_33 (6).sql` — 33MB MySQL dump from internal IP `10.123.0.33:3306`
- Not in `.gitignore` — new dumps will keep getting committed
- `quick_sql_extract.py` references `C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql` (4.2GB)
- Files matching `10_123_0_33 (N)_partXXXX.txt` pattern are split SQL dumps

**Risk:** Database schema, table structures, and potentially sensitive trading data exposed in a public repo.

### 2. pick_tracker.py Only Runs When Scheduled

`rapid_fire_data/pick_tracker.py` checks TP/SL/time-exits every run, but:
- If it doesn't run within 24h, time exits don't fire
- If the process crashes or isn't scheduled, picks accumulate as OPEN
- Even when it does close picks locally, the sync never propagates the closure

### 3. PnL Scale Inconsistencies

The `_parse_pick_fields` method has this heuristic:
```python
if pnl and 0 < abs(pnl) < 1:
    pnl = pnl * 100
```
This assumes any PnL between 0 and 1 is a decimal fraction. But a legitimate 0.5% return would be doubled to 1.0%.

### 4. bt_backtest_trades Table Is Empty

The `bt_backtest_trades` INSERT method exists but the table has 0 rows in the dump. Backtest-to-forward comparison queries return no results.

### 5. Source System Proliferation

The sync script reads from **25+ JSON source directories** and **20+ SQLite databases**. Many generate OPEN picks that are never closed. Source systems like `paper_trading` (24 picks, 100% OPEN) and `predictions` (20 picks, 95% OPEN) feed the OPEN pile.

---

## Fix: ON DUPLICATE KEY UPDATE

### Required Change in sync_all_picks_to_mysql.py

Replace `INSERT IGNORE` with `ON DUPLICATE KEY UPDATE` (syntax-correct example):

```python
cur.execute(
    """INSERT INTO at_raw_picks
       (id, aggregation_run_id, source_system, symbol, asset_class, direction,
        entry_price, take_profit, stop_loss, risk_reward, confidence, strategy,
        raw_payload, signal_timestamp, recorded_at, dedup_hash, created_by,
        status, exit_price, pnl_pct, exit_reason)
       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
       ON DUPLICATE KEY UPDATE
         status = IF(VALUES(status) IN ('WON','LOST','EXPIRED','CLOSED'),
                     VALUES(status), status),
         exit_price = COALESCE(VALUES(exit_price), exit_price),
         pnl_pct = COALESCE(VALUES(pnl_pct), pnl_pct),
         exit_reason = COALESCE(VALUES(exit_reason), exit_reason),
         closed_at = IF(VALUES(status) IN ('WON','LOST','EXPIRED','CLOSED'),
                        NOW(), closed_at)""",
    (pick_id, self.run_id, source_system, symbol, ...)
)
```

### Backfill Script

One-time SQL to close stale OPEN picks:

```sql
UPDATE at_raw_picks
SET status = 'EXPIRED',
    exit_reason = 'backfill_time_exit',
    closed_at = NOW()
WHERE status = 'OPEN'
  AND signal_timestamp < DATE_SUB(NOW(), INTERVAL 48 HOUR);
```

Conservative: only marks picks EXPIRED if >48h old (double the 24h max hold).

---

## Recommended Actions (Priority Order)

### P0 — Fix the Sync Bug
1. Replace `INSERT IGNORE` with `ON DUPLICATE KEY UPDATE` in `_insert_raw_pick()`
2. Run backfill script to close stale OPEN picks
3. Verify next sync cycle propagates CLOSED status

### P1 — Security
1. Add `data/*.sql` and `data/10_123_0_33*.txt` to `.gitignore`
2. Remove existing SQL dump from git tracking: `git rm --cached data/10_123_0_33*.sql`
3. Audit repo history for credentials in SQL dumps

### P2 — Data Quality
1. Fix PnL scale heuristic (don't blindly multiply small decimals)
2. Add `bt_backtest_trades` to the sync pipeline
3. Reduce source system count — only sync from systems that actually close trades

### P3 — Monitoring
1. Add health check: alert when OPEN rate exceeds 30%
2. Track per-source-system close rates
3. Add `at_raw_picks.closed_at` to dashboard queries

---

## Related Files

- `sync_all_picks_to_mysql.py` — script analyzed in snapshot
- `rapid_fire_data/pick_tracker.py` — local trade closer (works, sync doesn't pick up closes)
- `audit_trail/mysql_schema.sql` — table definitions
- `audit_trail/queries.sql` — query library
- `tools/sql/ejaguiar1_stocks_readonly_analytics.sql` — read-only analytics
- `docs/EJAGUIAR1_SQL_EDGE_REVIEW_2026-04-06.md` — prior SQL review
- `docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md` — scoring analysis
