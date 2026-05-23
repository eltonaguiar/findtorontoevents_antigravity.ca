# Wave 0 Census Report — Final
**Generated:** 2026-05-08 15:50 UTC  
**DB:** `ejaguiar1_stocks` @ `mysql.50webs.com`  
**Mode:** READ-ONLY (no writes performed)  
**Schema baseline:** `schema-baseline.sql` (322 tables)

---

## Executive Summary

| Metric | Value | Severity |
|--------|-------|----------|
| Total rows (`bt_backtest_trades`) | **~29.8M** (actual) / 1.3M (info_schema estimate — stale) | INFO |
| OPEN rows | **26,963,524** (90.4%) | INFO |
| Constant-PnL ghost rows identified | **~655K** | [HIGH] |
| Phantom EXPIRED (pnl=0, exit=entry) | **15,744** (100% of non-crypto expired) | [CRITICAL] |
| PnL integrity mismatch (>1%) | **58.0%** of sampled closed rows | [CRITICAL] |
| Forward validator status | **UNKNOWN** (query timed out — likely FROZEN per prior audit) | [WARNING] |
| Missing composite indexes | **Yes** — no (status, asset_class), (status, entry_time), or (imported_at) indexes | [WARNING] |

---

## 0-A: OPEN-Population Census

### Status Distribution
| Status | Count | % |
|--------|-------|---|
| `OPEN` | 26,963,524 | 90.4% |
| `closed` | 1,306,499 | 4.4% |
| `LOST` | 930,121 | 3.1% |
| `WON` | 666,247 | 2.2% |
| `expired` | 30,065 | 0.1% |
| `WIN` | 265 | <0.01% |
| `LOSS` | 195 | <0.01% |
| Other (`SL_HIT`, `TP_HIT`, etc.) | 229 | <0.01% |

**Key insight:** 26.9M OPEN rows is ~90% of the table. This is extremely high. The `information_schema.TABLE_ROWS` estimate of 1,312,509 is **stale/wrong** — the actual count is 23x higher.

### OPEN Asset Class (from 50K sample)
| Asset Class | Sample Count | Est. Full Count |
|-------------|-------------|-----------------|
| CRYPTO | 30,737 (61.5%) | ~16.6M |
| EQUITY | 10,780 (21.6%) | ~5.8M |
| MEMECOIN | 4,346 (8.7%) | ~2.3M |
| FOREX | 4,137 (8.3%) | ~2.2M |

### OPEN Strategy (from 50K sample — top 10)
| Strategy | Sample Count |
|----------|-------------|
| FearGreedReversal | 16,210 |
| BBSqueeze | 3,348 |
| RSIDivergence | 2,835 |
| MACDCrossover | 2,724 |
| LondonBreakout | 2,217 |
| KeltnerBounce | 2,113 |
| CarryMomentum | 1,833 |
| OptionsFlowContrarian | 1,639 |
| PairsTrading | 1,622 |
| BollingerSqueeze | 1,616 |

**Note:** Full OPEN-by-class and OPEN-by-strategy GROUP BY queries timed out on 27M rows despite `idx_bt_status` index. Composite index `(status, asset_class)` would fix this.

### OPEN Age Buckets
**Query timed out** — queries on `entry_time` without a composite index on `(status, entry_time)` cause full scans.  
*Recommendation:* Add `INDEX idx_bt_status_entry (status, entry_time)`.

---

## 0-B: Ghost Sweeps

### P0-1: `quan_engine` MATICUSDT Constant-PnL Ghosts
| Strategy | Symbol | Direction | PnL% | Count |
|----------|--------|-----------|------|-------|
| quan_engine | MATICUSDT | LONG | -15.0 | 220,533 |
| meta_strategy | MATICUSDT | LONG | 0.0 | 2,714 |
| quan_engine | MATICUSDT | LONG | NULL | 1,877 |
| meta_strategy | MATICUSDT | LONG | NULL | 792 |
| **TOTAL** | | | | **225,916** |

### P0-2: `meta_strategy` Constant-PnL Template (top 20 of many)
| Strategy | Symbol | Direction | PnL% | Count |
|----------|--------|-----------|------|-------|
| meta_strategy | DYDXUSDT | LONG | -3.0 | 28,785 |
| meta_strategy | PENGUUSDT | LONG | 5.0 | 26,280 |
| meta_strategy | ALGOUSDT | LONG | -3.0 | 25,580 |
| meta_strategy | DYDXUSDT | LONG | 5.0 | 23,634 |
| meta_strategy | AVAXUSDT | LONG | -3.0 | 23,241 |
| meta_strategy | PENGUUSDT | LONG | -3.0 | 22,536 |
| meta_strategy | ONDOUSDT | LONG | -3.0 | 22,318 |
| meta_strategy | ETHUSDT | LONG | 5.0 | 21,610 |
| meta_strategy | RENDERUSDT | LONG | -3.0 | 20,678 |
| meta_strategy | ENAUSDT | LONG | 5.0 | 19,603 |
| ... 10 more symbols ... | | | | |
| **TOTAL** | | | | **413,112** |

**Pattern:** `meta_strategy` ghosts follow a clear template: always LONG, always exactly -3.0% or 5.0% PnL, across 20+ crypto symbols. These are synthetic/test data that was never cleaned up.

### P0-3: Phantom EXPIRED Rows (pnl=0, exit_price=entry_price)
| Asset Class | Total EXPIRED | Phantoms | Phantom % |
|-------------|--------------|----------|-----------|
| FOREX | 5,412 | 5,412 | **100%** [CRITICAL] |
| FUTURES | 4,920 | 4,920 | **100%** [CRITICAL] |
| EQUITY | 3,936 | 3,936 | **100%** [CRITICAL] |
| ETF | 984 | 984 | **100%** [CRITICAL] |
| PENNY_STOCK | 492 | 492 | **100%** [CRITICAL] |
| CRYPTO | 13,354 | 0 | 0% [OK] |
| MEMECOIN | 1,082 | 0 | 0% [OK] |
| **TOTAL** | **30,180** | **15,744** | **52.2%** |

**Critical finding:** Every single FOREX, FUTURES, EQUITY, ETF, and PENNY_STOCK expired row is a phantom — PnL=0 and exit price equals entry price. This means these positions were never actually tracked to resolution. Only CRYPTO and MEMECOIN have legitimate expired rows.

---

## 0-C: PnL Integrity Check

### Sampled (100K closed rows — WON/LOST/closed/WIN/LOSS)
| Metric | Value |
|--------|-------|
| Sample size | 100,000 |
| Rows with >1% PnL mismatch | **58,030** |
| Mismatch rate | **58.0%** |

**Verdict:** [CRITICAL] SEVERE — over half of closed trades have PnL that differs by >1% from the recomputed value `(exit_price - entry_price) / entry_price * 100`. This indicates widespread data corruption in the `pnl_pct` column, likely from the constant-PnL ghost rows and phantom expired entries.

*Full-table query timed out — the 100K sample is directional but representative.*

---

## 0-D: Data-Type Sanity (first 500K rows sample)

| Column | NULL Count | % NULL | Verdict |
|--------|-----------|--------|---------|
| confidence | 19,033 | 3.8% | [OK] |
| pnl_pct | 473,926 | 94.8% | Expected for OPEN rows |
| entry_price | 36,153 | 7.2% | [WARN] |
| exit_price | 476,099 | 95.2% | Expected for OPEN rows |
| strategy | 21,055 | 4.2% | [OK] |
| direction | 425 | 0.09% | [OK] |

**Note:** Full-table NULL scan timed out. Sample from first 500K rows (by `id`). The high NULL rates on `pnl_pct` and `exit_price` are expected for OPEN positions that haven't been resolved yet. The 7.2% NULL `entry_price` on 500K rows is concerning but may be skewed by the sample range (early rows may have incomplete data).

---

## 0-E: Index Health

### `bt_backtest_trades` (6 single-column indexes, 1.5 GB total)
| Key_name | Column_name |
|----------|-------------|
| PRIMARY | id |
| backtest_run_id | backtest_run_id |
| idx_bt_sym | symbol |
| idx_bt_asset | asset_class |
| idx_bt_strat | strategy |
| idx_bt_status | status |

### `trading_picks` (1 index — PRIMARY only, 7.4 MB)
| Key_name | Column_name |
|----------|-------------|
| PRIMARY | id |

### Composite Index Gap Analysis

**Missing indexes (needed per action plan):**

| Composite Index | Purpose | Priority |
|-----------------|---------|----------|
| `(status, entry_time)` | Age bucket queries, stale OPEN cleanup | P0 |
| `(status, asset_class)` | OPEN-by-class census, quarantine filters | P0 |
| `(strategy, asset_class)` | Ghost cohort sweeps | P1 |
| `(imported_at)` | Freeze detection, recent activity checks | P1 |
| `(status, imported_at)` | Forward validator health monitoring | P1 |

**EXPLAIN verification:**  
- `WHERE status='OPEN'` uses `idx_bt_status` with `Using index` — efficient for COUNT only  
- `GROUP BY asset_class WHERE status='OPEN'` uses indexes but requires `Using temporary` — causes timeout on 27M rows without composite index

### `trading_picks` Index Gap
No indexes beyond PRIMARY on a 24K-row table with 7.4 MB.  
**Recommendation:** Add `INDEX idx_tp_strategy (strategy)`, `INDEX idx_tp_status (status)`.

---

## P0-5: Forward Validator Freeze Check

**Query timed out** — `SELECT MAX(imported_at) FROM bt_backtest_trades WHERE status IN ('WON','LOST')` requires scanning ~1.6M rows without an index on `imported_at`.

**Prior audit finding (from `reports/db_action_plan_2026-05-08.md`):**  
Last WON/LOST write was >26 hours before the prior audit, indicating the forward validator is likely FROZEN. A composite index `(status, imported_at)` would make this check instantaneous.

---

## Top 15 Largest Tables

| Table | Rows (est.) | Size (MB) |
|-------|------------|-----------|
| bt_backtest_trades | 1,312,509 | 1,543.8 |
| at_raw_picks | 121,857 | 311.7 |
| at_filter_log | 505,080 | 131.3 |
| now_history | 23,859 | 15.3 |
| lm_signals | 33,557 | 15.2 |
| at_audit_events | 27,602 | 10.4 |
| alpha_fundamentals | 2,964 | 7.8 |
| trading_picks | 24,644 | 7.4 |
| at_consensus_picks | 5,176 | 6.7 |
| at_discord_notifications | 4,637 | 5.4 |
| daily_prices | 49,340 | 4.9 |
| lm_sports_clv | 20,607 | 4.7 |
| cw_scan_log | 666 | 4.4 |
| at_discord_gate_log | 10,640 | 3.6 |
| rapid_signals | 11,709 | 3.6 |

**Note:** `information_schema.TABLE_ROWS` for `bt_backtest_trades` is **stale** — actual count is ~29.8M. The size (1,543.8 MB) is more accurate.

---

## Action Items — Prioritized

### [CRITICAL] P0 — Must Fix Now
1. **Delete 639K ghost rows** — `quan_engine` MATICUSDT (225,916) + `meta_strategy` template (413,112)  
   ```sql
   DELETE FROM bt_backtest_trades WHERE strategy='quan_engine' AND symbol='MATICUSDT' AND status='OPEN';
   DELETE FROM bt_backtest_trades WHERE strategy='meta_strategy' AND status='OPEN';
   ```
   *Validate first with SELECT count before deleting.*

2. **Delete 15,744 phantom EXPIRED rows** — all non-crypto expired with pnl=0 and exit=entry  
   ```sql
   DELETE FROM bt_backtest_trades WHERE status='expired' AND asset_class IN ('FOREX','FUTURES','EQUITY','ETF','PENNY_STOCK');
   ```

3. **Investigate PnL corruption** — 58% mismatch rate requires root-cause analysis  
   - Are the ghost/phantom rows skewing the sample?  
   - Is the importer writing incorrect `pnl_pct` values?  
   - Run PnL recompute on a clean sample (post-ghost-deletion)

### [HIGH] P1 — This Week
4. **Add composite indexes** to `bt_backtest_trades`:
   ```sql
   ALTER TABLE bt_backtest_trades ADD INDEX idx_bt_status_entry (status, entry_time);
   ALTER TABLE bt_backtest_trades ADD INDEX idx_bt_status_asset (status, asset_class);
   ALTER TABLE bt_backtest_trades ADD INDEX idx_bt_status_imported (status, imported_at);
   ALTER TABLE bt_backtest_trades ADD INDEX idx_bt_strat_asset (strategy, asset_class);
   ```

5. **Add indexes to `trading_picks`**:
   ```sql
   ALTER TABLE trading_picks ADD INDEX idx_tp_strategy (strategy);
   ALTER TABLE trading_picks ADD INDEX idx_tp_status (status);
   ```

6. **Unfreeze forward validator** — diagnose why WON/LOST writes stopped

### [WARNING] P2 — This Sprint
7. **Run ANALYZE TABLE** on `bt_backtest_trades` to update stale `information_schema` estimates
8. **Add `terminal_outcome` column** per Wave 2 plan
9. **Set up query logging** for audit trail

---

## Queries That Timed Out (Require New Indexes)

| Query | Reason | Fix |
|-------|--------|-----|
| OPEN by asset_class | GROUP BY on 27M rows with temp table | Add `(status, asset_class)` index |
| OPEN by strategy | GROUP BY on 27M rows with temp table | Add `(status, strategy)` index |
| OPEN age buckets | Range scan on entry_time without index | Add `(status, entry_time)` index |
| Freeze check (MAX imported_at) | Full scan of 1.6M WON/LOST rows | Add `(status, imported_at)` index |
| Full-table NULL ratios | Full scan of 29.8M rows | Sample-based approach sufficient |
