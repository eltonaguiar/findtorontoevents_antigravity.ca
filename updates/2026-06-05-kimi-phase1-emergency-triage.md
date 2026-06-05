# KIMI Phase 1 Emergency Triage — 2026-06-05

**Author**: KIMI (Claude Code CLI deep-dive + execution)  
**Branch**: `kimi-phase1-2026-06-05`  
**Scope**: MASTERPLAN_JUNE52026_KIMI.MD Phase 1 execution — DB fixes, source bans, resolver hygiene, strategy kill switch, OHLCV tooling  
**Companion docs**: `MASTERPLAN_JUNE52026_KIMI.MD`, `updates/2026-06-05-zero-pnl-safeguard-stale-pick-resolver-fixes.md`

---

## 1. What Was Broken (Ground Truth)

Live MySQL queries against `ejaguiar1_stocks` revealed:

| Issue | Count / Metric | Severity |
|-------|---------------|----------|
| **Resolver backlog** | 33,498 unresolved picks (85.7% of `at_pick_outcomes`) | P0 |
| **Stuck OPEN picks** | 9,945 OPEN, avg age 39.2 days, 7,468 >30 days | P0 |
| **TP/SL asymmetry** | TP_HIT 84% WR vs SL_HIT 4% WR | P0 |
| **Zero-PnL resolved** | 1,034 picks marked WON/LOST with pnl_pct=0 | P1 |
| **Poison source: Predictions** | 6,168 rows, avg PnL +124%, impossible prices | P0 |
| **Poison source: sandbox_opposite** | 351 rows, 12× duplicate emissions | P0 |
| **Poison source: rapid_fire** | 273 rows, duplicate emitter | P0 |
| **Poison source: incubator_gainer** | 5,103 rows, 94% abandonment | P0 |
| **Backfill corruption** | 31 rows with PnL up to +370,850% | P1 |
| **Toxic strategies** | 11 strategies with N≥50, WR<40% or avg PnL<−2% | P1 |
| **Empty OHLCV tables** | `crypto_ohlcv`=0 rows, `stock_ohlcv`=0 rows | P1 |
| **Stale equity prices** | `daily_prices` max 2026-04-29 (37 days old) | P1 |

---

## 2. DB Fixes Executed (Live MySQL)

### 2.1 Backups Created

```sql
-- Backup tables created inside ejaguiar1_stocks (backups DB connection flaky)
CREATE TABLE at_raw_picks_kimi_backup_20260605_052954 LIKE at_raw_picks;
INSERT INTO at_raw_picks_kimi_backup_20260605_052954 SELECT * FROM at_raw_picks;  -- 74,291 rows

CREATE TABLE at_pick_outcomes_kimi_backup_20260605_052954 LIKE at_pick_outcomes;
INSERT INTO at_pick_outcomes_kimi_backup_20260605_052954 SELECT * FROM at_pick_outcomes;  -- 39,418 rows

CREATE TABLE at_signal_outcomes_kimi_backup_20260605_052954 LIKE at_signal_outcomes;
INSERT INTO at_signal_outcomes_kimi_backup_20260605_052954 SELECT * FROM at_signal_outcomes;  -- 2,467 rows
```

### 2.2 Source Bans Applied

Updated `at_raw_picks.was_banned=1` for existing rows from poison sources:

| Source | Rows Banned |
|--------|-------------|
| `Predictions` | 6,168 |
| `sandbox_opposite` | 351 |
| `rapid_fire` | 273 |
| `incubator_gainer` | 5,103 |
| **Total** | **11,895** |

### 2.3 Backfill Corruption Quarantined

```sql
UPDATE at_raw_picks 
SET status='EXPIRED', exit_reason='BACKFILL_QUARANTINE', was_banned=1
WHERE exit_reason LIKE '%BACKFILL%' AND was_banned=0;
-- 6 rows quarantined
```

### 2.4 Stale OPEN Picks Resolved

Added `ABANDONED` to `at_raw_picks.status` ENUM and batch-resolved stale picks:

```sql
ALTER TABLE at_raw_picks MODIFY status 
  ENUM('OPEN','WON','LOST','EXPIRED','CLOSED','ABANDONED');

UPDATE at_raw_picks 
SET status='ABANDONED', exit_reason='STALE_TIMEOUT', pnl_pct=0, closed_at=NOW()
WHERE status='OPEN' AND recorded_at < NOW() - INTERVAL 30 DAY;
-- 7,396 rows resolved
```

### 2.5 Zero-PnL Outcomes Fixed

`at_pick_outcomes` lacks `entry_price`/`exit_price` columns (pick_id format is `::SYMBOL::DATE`, not UUID). Could not recompute from join (only 14 match `at_raw_picks`). Safest fix:

```sql
UPDATE at_pick_outcomes 
SET status='FLAT', resolution_method='MANUAL'
WHERE pnl_pct = 0 AND status IN ('WON','LOST');
-- 1,034 rows fixed
```

### 2.6 Toxic Strategies Killed (Dry-Run + Execute)

Ran `tools/strategy_kill_switch.py`:

| Strategy | Asset Class | N | WR | Avg PnL | Kill Reason |
|----------|-------------|---|-----|---------|-------------|
| `futures_momentum` | COMMODITY | 647 | 35.4% | −0.75% | wr_below_floor, total_pnl_destroyed |
| `cta_cross_asset_tsmom` | COMMODITY | 100 | 19.0% | −1.43% | wr_below_floor, total_pnl_destroyed |
| `copy_hl_lb_None` | CRYPTO | 406 | 34.2% | +0.02% | wr_below_floor |
| `ensemble` | CRYPTO | 103 | 40.8% | −7.21% | avg_pnl_below_floor, total_pnl_destroyed |
| `enhanced_ml_A_xgboost` | CRYPTO | 62 | 29.0% | −0.49% | wr_below_floor |
| `MomentumEMA` | EQUITY | 54 | 18.5% | −1.07% | wr_below_floor |
| `forex_rsi2_mean_reversion` | FOREX | 661 | 45.7% | −0.15% | wr_below_floor |
| `ig_contrarian_sentiment` | FOREX | 127 | 1.6% | +0.04% | wr_below_floor |
| `myfxbook_retail_contrarian` | FOREX | 127 | 45.7% | −0.23% | wr_below_floor |
| `forex_carry_momentum` | FOREX | 154 | 7.8% | +5.03% | wr_below_floor |
| `fx_smart_carry_trade_momentum` | FOREX | 55 | 38.2% | −0.07% | wr_below_floor |

Kill switch output written to:
- `audit_dashboard/data/strategy_kill_switch.json`
- `audit_trail/data/strategy_kill_audit.jsonl`
- `alpha_engine/strategy_blocklist.py` updated with `_RETIRED_STRATEGIES`

---

## 3. Code Changes

### 3.1 `alpha_engine/production_scanner.py`

Added `BANNED_SOURCES` constant and `apply_source_ban_gate()` function. Wired into `main()` after `filter_bad_symbols()`.

```python
BANNED_SOURCES = {
    "Predictions",
    "sandbox_opposite",
    "rapid_fire",
    "incubator_gainer",
}
```

### 3.2 `audit_trail/universal_pick_resolver.py`

Added `_compute_pnl()` helper with zero-PnL safeguard. Replaced inline PnL computations in `check_tp_sl()`, `_check_tp_sl_intrabar()`, and TIME_EXPIRY path.

### 3.3 `tools/resolve_stale_open_picks.py`

- Table-awareness (`--table at_raw_picks` vs `trading_picks`)
- ENUM safety: auto-alters `at_raw_picks.status` to include `ABANDONED`
- Dry-run pagination fix: `scan_offset` advances by `len(picks)`

### 3.4 `tools/strategy_kill_switch.py` (NEW)

Auto-disables toxic strategies based on live `at_pick_outcomes` perf. Dry-run by default; `--execute` persists to blocklist + audit trail.

### 3.5 `tools/refresh_crypto_ohlcv.py` (NEW)

Fetches 720× 1h klines from Binance public API for all CRYPTO/MEMECOIN symbols in `at_raw_picks`. Bulk-upserts into `crypto_ohlcv`. Dry-run by default.

### 3.6 `tools/refresh_stock_ohlcv.py` (NEW)

Fetches 60d of 1h bars from yfinance for non-crypto symbols. Bulk-upserts into `stock_ohlcv`. Dry-run by default.

---

## 4. What Remains (Phase 1 Tail)

- [ ] **Populate OHLCV tables**: Run `tools/refresh_crypto_ohlcv.py --execute` and `tools/refresh_stock_ohlcv.py --execute` (scripts ready, data feeds need time)
- [ ] **Refresh `daily_prices`**: Backfill from 2026-04-29 to present (separate cron)
- [ ] **Fix TP/SL asymmetry root cause**: The 84%/4% split needs intrabar OHLCV + price-feed audit (deferred until OHLCV tables populated)
- [ ] **Forward validation gate**: Still 0% of picks pass; needs Phase 2 promotion gate build

---

## 5. Verification Commands

```bash
# Confirm source bans are active
python3 -c "import pymysql; c=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',password='stocks1234560',database='ejaguiar1_stocks'); cur=c.cursor(); cur.execute('SELECT source_system,COUNT(*) FROM at_raw_picks WHERE was_banned=1 GROUP BY source_system'); [print(r) for r in cur.fetchall()]; c.close()"

# Confirm stale picks resolved
python3 -c "import pymysql; c=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',password='stocks1234560',database='ejaguiar1_stocks'); cur=c.cursor(); cur.execute(\"SELECT status,COUNT(*) FROM at_raw_picks GROUP BY status\"); [print(r) for r in cur.fetchall()]; c.close()"

# Confirm zero-PnL fixed
python3 -c "import pymysql; c=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',password='stocks1234560',database='ejaguiar1_stocks'); cur=c.cursor(); cur.execute(\"SELECT COUNT(*) FROM at_pick_outcomes WHERE pnl_pct=0 AND status IN ('WON','LOST')\"); print('remaining zero-pnl:', cur.fetchone()[0]); c.close()"

# Strategy kill switch dry-run
python3 tools/strategy_kill_switch.py
```

---

## 6. Safety Notes

- All destructive DB operations were preceded by backup tables (`*_kimi_backup_20260605_052954`).
- Source bans used `was_banned=1` (soft delete) rather than `DELETE` — reversible.
- Stale picks set to `ABANDONED` rather than deleted — reversible.
- Zero-PnL picks set to `FLAT` rather than recomputed with potentially wrong prices — safest choice given missing price columns.
- `strategy_kill_switch.py` defaults to dry-run; `--execute` required for blocklist mutation.
- `refresh_*_ohlcv.py` default to dry-run; `--execute` required for DB writes.

---

*Generated 2026-06-05 by KIMI execution session. All DB changes verified with live SELECTs.*
