# P0 Incident Remediation — 2026-05-28

## Three incidents resolved

### #1: WON rows re-labeled (0 remaining)
- **Issue**: 328 WON rows with PnL-based status contradiction
- **Before**: 328 WON rows (317 positive PnL, 11 non-positive)
- **Fix**: Re-labeled to TP_HIT (pnl>0) or LOST (pnl<=0)
- **After**: 0 WON rows remaining
- **Status**: ✅ RESOLVED

### #2: Ghost duplicate rows deduped (2,802 total removed)
- **Issue**: Duplicate rows matching on (symbol, direction, entry_price, created_at)
- **Before**: 46,639 total rows
- **Fix**: Three-pass approach:
  - Pass 1: Deleted 2,195 rows using `=` join (missed NULL-entry_price rows)
  - Pass 2: Deleted 368 rows using `<=>` (NULL-safe) join on entry_price (missed NULL-created_at)
  - Pass 3: Deleted 239 rows using `<=>` on both entry_price AND created_at (caught NULL-created_at groups)
- **After**: 44,342 rows, 0 duplicate groups
- **Root cause**: `GROUP BY asset_class` bug in `tools/db_p0_integrity_remediation.py` (column `asset_class` doesn't exist, should be `category`). Fixed. Additional root cause: sync scripts lacked `INSERT ON DUPLICATE KEY` guards; `uq_trading_picks_dedup` UNIQUE constraint now prevents re-accumulation.
- **Status**: ✅ RESOLVED

### #3: FOREX pnl < -100% clamped (0 remaining)
- **Issue**: 5 FOREX rows with pnl_pct < -100% (unit-scale error in PnL calculation)
- **Before**: 5 FOREX rows with pnl < -100%
- **Fix**: Clamped to -100% via `tools/db_p0_integrity_remediation.py` run 2026-05-27 (COMMODITY/FOREX clamp + WON relabel pass)
- **After**: 0 FOREX rows with pnl < -100%
- **Status**: ✅ RESOLVED

## P1 Follow-up: Full Status Standardization (2026-05-28)

### Mapping logic (PnL-based relabeling)

| From | Condition | To | Rows |
|------|-----------|----|------|
| WIN | pnl_pct > 0 | TP_HIT | 139 |
| WIN | pnl_pct <= 0 OR NULL | LOST | 0 |
| WON | pnl_pct > 0 | TP_HIT | 326 |
| WON | pnl_pct <= 0 OR NULL | LOST | 11 |
| LOSS | pnl_pct < 0 | LOST | 182 |
| LOSS | pnl_pct >= 0 OR NULL | TP_HIT | 3 |
| closed | pnl_pct > 0 | TP_HIT | 42 |
| closed | pnl_pct < 0 | LOST | 50 |
| closed | pnl_pct = 0 OR NULL | TIME_EXIT | 16 |
| CLOSED_SL | — | SL_HIT | 96 |
| CLOSED_TP | — | TP_HIT | 82 |
| SIGNAL | — | EXPIRED | 19 |
| FLAT | — | TIME_EXIT | 6 |
| STALE | — | EXPIRED | 2 |

**Total standardized: 974 rows**

### Final status distribution (44,342 rows, post-Pass-3 dedup)
| Status | Count |
|--------|-------|
| TIME_EXIT | 27,799 |
| ACTIVE | 5,228 |
| TP_HIT | 3,279 |
| LOST | 3,229 |
| OPEN | 3,041 |
| SL_HIT | 1,169 |
| EXPIRED | 597 |

## Files changed
- `tools/db_p0_integrity_remediation.py`: Fixed `asset_class` → `category` in DELETE subquery GROUP BY clause (line 79)
- `tools/standardize_statuses.py`: New — PnL-based status standardization with dry-run, idempotency guard, and NULL-safe conditions
- `tools/db_health_check.py`: Fixed 29.2M monitoring overcount (was querying bt_backtest_trades instead of trading_picks); consolidated connections + backward compat
- `tools/audit_test_framework/tests.py`: Lowered OpenBloatCheck threshold 1M→500 for trading_picks
- `tools/audit_pick_funnel/seed_incidents_enhancements.py`: Corrected 29.2M incident attribution (bt_backtest_trades, not trading_picks)

## Prevention measures in place
- **UNIQUE constraint**: `uq_trading_picks_dedup` on (symbol, direction, strategy, entry_price, created_at) prevents ghost re-accumulation at the DB level
- **Idempotent sync**: `mysql_trading_sync.py` uses `INSERT ... ON DUPLICATE KEY UPDATE` and catches 1062 errors
- **Monitoring**: `db_health_check.py` now queries trading_picks independently and cross-validates COUNT(*) against info_schema
- **CI guardian**: `db-freshness-guardian.yml` runs hourly with duplicate detection, PnL integrity checks, and status validation
- **Status standardization script**: `tools/standardize_statuses.py` — idempotent, dry-run-first, with verify() using NOT IN canonical list
