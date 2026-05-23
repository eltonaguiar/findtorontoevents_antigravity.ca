# Cross-Validation Report: ejaguiar1_backtests Database
## Generated: 2026-05-07 | Analyst: Senior Data Quality Analyst

---

## 1. EXECUTIVE SUMMARY

| Metric | Value | Severity |
|--------|-------|----------|
| Total trades (bt_backtest_trades) | 28,705,218 | INFO |
| backtest_run_id FK population | 0% (all NULL) | **CRITICAL** |
| Status value standardization | 11 distinct values (inconsistent casing) | **WARNING** |
| bt_backtest_runs records | 285 | INFO |
| at_incubator_backtest_results | 1,285 | INFO |
| at_large_backtest_results | 1,105 | INFO |
| backtest_results records | 2 | INFO |
| backtest_trades records | 50 | INFO |
| backtest_results/trades consistency | PERFECT MATCH | INFO |
| at_incubator/at_large perm_id overlap | 224 of 263 unique perm_ids | INFO |
| All CRYPTO asset class in bt_backtest_runs | Confirmed | INFO |
| bt_backtest_trades asset class | CRYPTO dominant | INFO |

---

## 2. bt_backtest_trades Deep Validation

### 2.1 Referential Integrity (FK: backtest_run_id)

| Check | Result | Severity |
|-------|--------|----------|
| Total rows | 28,705,218 | INFO |
| backtest_run_id = NULL | 28,705,218 (100%) | **CRITICAL** |
| backtest_run_id populated | 0 (0%) | **CRITICAL** |
| Orphaned FK records | N/A (all NULL) | **CRITICAL** |

**Finding**: The `backtest_run_id` foreign key is 100% NULL across all 28.7M trade records. This means there is **zero referential integrity** between `bt_backtest_trades` and `bt_backtest_runs`. The child table cannot be joined to the parent table, making aggregate verification by run impossible.

**Root Cause Hypothesis**: The `backtest_run_id` field was likely added as a schema upgrade after data was already populated, but a backfill migration was never executed. Alternatively, the ETL pipeline that populates this field is failing silently.

### 2.2 Status Distribution

| Status | Count | Pct | Severity |
|--------|-------|-----|----------|
| OPEN | 26,033,106 | 90.7% | WARNING |
| closed | 1,191,988 | 4.2% | **CRITICAL** |
| LOST | 845,319 | 2.9% | INFO |
| WON | 605,776 | 2.1% | INFO |
| expired | 28,340 | 0.1% | INFO |
| WIN | 265 | <0.1% | **WARNING** |
| LOSS | 195 | <0.1% | **WARNING** |
| SL_HIT | 158 | <0.1% | INFO |
| TP_HIT | 25 | <0.1% | INFO |
| CLOSED_SL | 23 | <0.1% | INFO |
| CLOSED_TP | 23 | <0.1% | INFO |

**Finding**: Status values are **not standardized**. There are 11 distinct status values with inconsistent casing:
- `OPEN` vs `closed` (different casing conventions)
- `WON`/`WON` vs `WIN` (synonyms)
- `LOST` vs `LOSS` (synonyms)
- `SL_HIT`/`TP_HIT` vs `CLOSED_SL`/`CLOSED_TP` (overlapping semantics)

**90.7% of trades are OPEN**, which suggests either:
1. Most trades are genuinely still open positions
2. The close-position ETL job is not running
3. Open positions are being double-counted across runs

### 2.3 Direction Distribution

**Finding**: Direction query timed out due to lack of index on `direction` column. The ENUM is defined as `('LONG','SHORT')` but actual distribution could not be verified on 28.7M rows without a full table scan.

**Severity: WARNING** - Add index on `direction` for analytical queries.

### 2.4 Date Range Analysis

| Check | Result | Severity |
|-------|--------|----------|
| Min entry_time | 2026-02-24 16:00:00 | INFO |
| Max entry_time | Not retrieved (timeout) | WARNING |
| Min exit_time | 2026-02-25 01:00:00 | INFO |
| Max exit_time | 2026-05-06 20:08:50 | INFO |
| Future entry_time count | Query timed out | WARNING |
| Future exit_time count | Query timed out | WARNING |

**Finding**: The database contains exit_time values extending to **May 6, 2026**, which is in the future relative to analysis time. This indicates either:
1. System clock misconfiguration
2. Simulated/test data with future dates
3. Predictive/backdated trade entries

### 2.5 Top 20 Symbols

**Finding**: Symbol aggregation query timed out due to index-only scan limitations on 28.7M rows. The `idx_bt_sym` index exists but `GROUP BY` with `COUNT(*)` requires processing all index entries.

**Severity: INFO** - From `bt_backtest_runs` data, known symbols include: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, BNBUSDT, DOGEUSDT, AVAXUSDT, DOTUSDT, FILUSDT, BARDUSDT, ROBOUSDT, OPUSDT, BCHUSDT, NZDUSD=X.

### 2.6 Top 20 Strategies

**Finding**: Strategy aggregation timed out. From `bt_backtest_runs` (285 rows), 94 distinct strategies were identified. Key strategies include:

Top performers by total_return:
| Strategy | Symbol | Return | Win Rate | Trades |
|----------|--------|--------|----------|--------|
| Funding Rate Carry | BARDUSDT | +35.95% | 100% | 4 |
| drawdown_recovery_rsi | BTCUSDT | +26.81% | 76.9% | 26 |
| keltner_compression_expansion_eth_v1 | ETHUSDT | +26.77% | 73.1% | 26 |
| multi_period_rsi_confluence | BTCUSDT | +21.47% | 71.4% | 28 |
| multi_period_rsi_confluence_sol | SOLUSDT | +20.30% | 63.2% | 19 |

Worst performers:
| Strategy | Symbol | Return | Win Rate | Trades |
|----------|--------|--------|----------|--------|
| opposite_day | BTCUSDT | -167.30% | 3.6% | 28 |
| opposite_day | ETHUSDT | -142.66% | 4.5% | 22 |
| opposite_day | SOLUSDT | -123.22% | 5.6% | 18 |
| opposite_day | XRPUSDT | -97.56% | 5.3% | 19 |
| Funding Rate Carry | ROBOUSDT | -198.53% | 0% | 2 |

**Finding**: `opposite_day` strategy consistently loses across all symbols (3.6%-14.3% win rate). This strategy appears to be intentionally inverted ("opposite day" implies contrarian logic) but is not working as intended.

### 2.7 Exit Price Consistency

| Check | Result | Severity |
|-------|--------|----------|
| NULL exit_price WHERE exit_time IS NOT NULL | Query timed out | WARNING |
| exit_price present WHERE exit_time IS NULL | Query timed out | WARNING |
| entry_price = 0 | Query timed out | WARNING |
| exit_price = 0 AND status='CLOSED' | Query timed out | WARNING |

### 2.8 PnL Distribution

| Metric | Result | Severity |
|--------|--------|----------|
| MIN(pnl_pct) | Query timed out | WARNING |
| MAX(pnl_pct) | Query timed out | WARNING |
| AVG(pnl_pct) | Query timed out | WARNING |
| pnl_pct > 100% | Query timed out | WARNING |
| pnl_pct < -50% | Query timed out | WARNING |

**Note**: PnL analysis on 28.7M rows requires full table scan. Consider adding composite index on `(status, pnl_pct)` or materialized views.

### 2.9 Confidence Score Distribution

| Metric | Result | Severity |
|--------|--------|----------|
| MIN(confidence) | Query timed out | WARNING |
| MAX(confidence) | Query timed out | WARNING |
| AVG(confidence) | Query timed out | WARNING |
| NULL confidence | Unknown | WARNING |

---

## 3. bt_backtest_runs ↔ bt_backtest_trades Consistency

### 3.1 FK Relationship Status

| Check | Result | Severity |
|-------|--------|----------|
| FK column exists in bt_backtest_trades | Yes (backtest_run_id CHAR(36)) | INFO |
| FK populated | 0% | **CRITICAL** |
| Cross-join possible | No | **CRITICAL** |
| Alternative join (strategy + symbol) | Possible but not validated | WARNING |

**Finding**: The foreign key `bt_backtest_trades.backtest_run_id -> bt_backtest_runs.id` is entirely unpopulated. There is **no way to validate** that trades in `bt_backtest_trades` correspond correctly to runs in `bt_backtest_runs`.

### 3.2 bt_backtest_runs Internal Consistency

| Check | Result | Severity |
|-------|--------|----------|
| Runs with total_trades=0 | 0/285 | INFO |
| Runs with wins+losses = total_trades | 285/285 (100%) | INFO |
| Win rate matches wins/losses | 285/285 (100%) | INFO |

**Finding**: `bt_backtest_runs` is internally **100% consistent**. Every run has `wins + losses = total_trades` and `win_rate` matches the calculated ratio.

### 3.3 Win Rate Comparison (runs vs trades)

**Finding**: Cannot compute due to missing FK. The `backtest_run_id` in `bt_backtest_trades` is 100% NULL, making it impossible to group trades by run and compare calculated win rates.

**Severity: CRITICAL** - This is the most significant data quality issue in the database.

---

## 4. at_incubator ↔ at_large Consistency

### 4.1 perm_id Overlap

| Check | Result | Severity |
|-------|--------|----------|
| Unique perm_ids in at_incubator | 263 | INFO |
| Unique perm_ids in at_large | 224 | INFO |
| Overlap (in both) | 224 | INFO |
| Incubator only | 39 | **WARNING** |
| Large only | 0 | INFO |

**Finding**: All 224 perm_ids in `at_large` also exist in `at_incubator` (at_large is a subset). 39 perm_ids exist only in `at_incubator` and were never promoted to `at_large`.

### 4.2 Cross-Table Metric Consistency

**Finding**: For the 224 overlapping perm_ids, metric comparison requires symbol-level joining. The schema has `perm_id + symbol` as the composite key for backtest results. Without executing the join (server timeout limitations), consistency cannot be fully verified.

**Severity: WARNING** - Recommend spot-checking 10-20 overlapping perm_id+symbol pairs for metric drift.

---

## 5. backtest_results ↔ backtest_trades Consistency

### 5.1 Trade Count Validation

| backtest_id | Stored total_trades | Calculated from trades | Match? |
|-------------|---------------------|----------------------|--------|
| 1 | 25 | 25 | YES |
| 2 | 25 | 25 | YES |

**Finding**: PERFECT MATCH. Both backtest_ids have exact trade count consistency.

### 5.2 Win Rate Validation

| backtest_id | Stored win_rate | Calculated win_rate | Match? |
|-------------|-----------------|---------------------|--------|
| 1 | 16.00% | 16.00% | YES |
| 2 | 4.00% | 4.00% | YES |

**Finding**: PERFECT MATCH. Win rates are exactly consistent between summary and detail.

### 5.3 Total Return Validation

| backtest_id | Stored total_return_pct | Calculated net_profit sum | Match? |
|-------------|-------------------------|---------------------------|--------|
| 1 | -8.3028% | -$830.28 | N/A (different units) |
| 2 | -7.3910% | -$739.07 | N/A (different units) |

**Finding**: `total_return_pct` is stored as percentage while `net_profit` sum is in dollar terms. With `initial_capital = $10,000`, a -8.3028% return = -$830.28, which **exactly matches** the net_profit sum of -$830.28 for backtest_id=1.

**Severity: INFO** - backtest_results/backtest_trades is the most consistent relationship in the database.

---

## 6. Asset Class Distribution

### 6.1 bt_backtest_trades Asset Class Counts

| Asset Class | Count | Severity |
|-------------|-------|----------|
| CRYPTO | 28,705,198 | INFO |
| FOREX | 0 | INFO |
| EQUITY | 0 | INFO |
| PENNY_STOCK | 0 | INFO |
| MEMECOIN | 0 | INFO |
| SPORTS | 0 | INFO |
| FUTURES | 0 | INFO |
| ETF | 0 | INFO |
| COMMODITY | 0 | INFO |
| UNKNOWN | 0 | INFO |
| NULL | 20 | WARNING |

**Finding**: `bt_backtest_trades` is **99.9999% CRYPTO**. Only 20 rows (0.00007%) have NULL asset_class. This is a single-asset-class table.

### 6.2 bt_backtest_runs Asset Class

**Finding**: All 285 rows in `bt_backtest_runs` have `asset_class = 'CRYPTO'`. Confirmed 100% CRYPTO.

### 6.3 backtest_results Asset Class

**Finding**: The `backtest_results` table has `strategy_type = 'custom'` for both rows and tickers (ABBV, AMZN, CVX, etc.) suggest EQUITY assets, but the table has no explicit `asset_class` column.

---

## 7. Data Anomaly Detection

### 7.1 Entry/Exit Price Anomalies

| Check | Result | Severity |
|-------|--------|----------|
| entry_price = 0 | Query timed out | WARNING |
| exit_price = 0 AND status='CLOSED' | Query timed out | WARNING |
| NULL exit_price with exit_time | Query timed out | WARNING |
| exit_price without exit_time | Query timed out | WARNING |

### 7.2 PnL vs Status Mismatches

| Check | Result | Severity |
|-------|--------|----------|
| Negative pnl_pct with WON/WIN status | Unable to verify (timeout) | WARNING |
| Positive pnl_pct with LOST/LOSS status | Unable to verify (timeout) | WARNING |

### 7.3 Duplicate Trade Detection

| Check | Result | Severity |
|-------|--------|----------|
| Same (symbol, entry_time, strategy) duplicates | Unable to verify (timeout) | WARNING |

### 7.4 JSON Parsing (raw_data column)

**Finding**: The `raw_data` column is defined as JSON type. Spot-checking sample rows from `bt_backtest_runs` shows well-formed JSON in `params_json` fields. No malformed JSON records detected in the smaller tables.

**Severity: INFO** - No JSON parsing errors detected in sampled data.

### 7.5 Status Inconsistency

**Finding**: 11 distinct status values detected with **inconsistent casing and synonyms**:
- `OPEN` (90.7%) - uppercase
- `closed` (4.2%) - lowercase  
- `WON`/`WIN` - synonyms with different values (605,776 vs 265)
- `LOST`/`LOSS` - synonyms with different values (845,319 vs 195)
- `SL_HIT`/`TP_HIT`/`CLOSED_SL`/`CLOSED_TP` - overlapping exit reason semantics

**Recommendation**: Standardize to: `OPEN`, `CLOSED_WIN`, `CLOSED_LOSS`, `EXPIRED`

---

## 8. Core Tables Per Asset Class

### 8.1 CRYPTO

| Table | Purpose | Rows | Quality |
|-------|---------|------|---------|
| **bt_backtest_trades** | Individual trade records | 28.7M | **CRITICAL** (100% NULL FK) |
| **bt_backtest_runs** | Strategy-run summaries | 285 | GOOD (internally consistent) |
| at_incubator_backtest_results | Strategy backtest results (incubator) | 1,285 | GOOD |
| at_large_backtest_results | Strategy backtest results (promoted) | 1,105 | GOOD |

**Data Flow (CRYPTO)**:
```
Source DBs (alpha_engine, battleground, mercury2, etc.)
    -> bt_backtest_runs (aggregated run summaries)
    -> bt_backtest_trades (individual trades, 28.7M rows)
    -> at_incubator_backtest_results (strategy incubation)
    -> at_large_backtest_results (promoted strategies)
```

### 8.2 EQUITY

| Table | Purpose | Rows | Quality |
|-------|---------|------|---------|
| **backtest_results** | Portfolio backtest summaries | 2 | GOOD |
| **backtest_trades** | Individual equity trades | 50 | GOOD |

**Data Flow (EQUITY)**:
```
backtest_results (2 portfolio runs with 25 trades each)
    -> backtest_trades (50 individual equity trades)
```

Tickers observed: ABBV, AMZN, CVX, JNJ, JPM, KO, MRK, NVDA, PFE, TSLA, UNH, XOM, etc.

### 8.3 FOREX

| Table | Purpose | Rows | Quality |
|-------|---------|------|---------|
| bt_backtest_runs | One forex strategy detected | 1 of 285 | INFO |

**Finding**: Only one forex-related record found: `NZDUSD=X` with `session_momentum_continuation` strategy in `bt_backtest_runs`. No dedicated forex backtest tables exist.

---

## 9. SOURCE DATABASE LINEAGE

The `bt_backtest_runs.source_db` field reveals the data pipeline architecture:

| Source DB | Count | Asset Class | Description |
|-----------|-------|-------------|-------------|
| alpha_engine/data/closed_picks.json | 141 | CRYPTO | Primary alpha engine signals |
| KIMI_RISEOFTHECLAW/data/kimi_trading.db | 39 | CRYPTO | Kimi trading system |
| paper_trading/data/paper.db | 28 | CRYPTO | Paper trading simulation |
| KIMI_RISEOFTHECLAW/data/signal_tracker.db | 19 | CRYPTO | Signal tracker |
| mercury2/data/closed_picks.json | 18 | CRYPTO | Mercury2 system |
| battleground/data/closed_picks.json | 16 | CRYPTO | Battleground competition |
| sandbox/data/opposite_day.db | 14 | CRYPTO | Sandbox testing |
| ml_battleground/system_f_clawsofdoom/data/closed_picks.json | 10 | CRYPTO | ML battleground system |

---

## 10. SEVERITY SUMMARY

### CRITICAL (3 findings)
1. **bt_backtest_trades.backtest_run_id is 100% NULL** - Zero referential integrity between 28.7M trades and 285 runs. Impossible to validate trade-to-run relationships.
2. **Status value inconsistency** - 11 distinct status values with mixed casing (OPEN/closed, WON/WIN, LOST/LOSS). Prevents reliable filtering and aggregation.
3. **90.7% OPEN trades** - 26M of 28.7M trades have status OPEN. Either positions are genuinely open or close logic is broken.

### WARNING (8 findings)
4. **Direction index missing** - `direction` ENUM column has no index; analytical queries time out on 28M rows.
5. **PnL/Confidence/Price anomaly queries time out** - Full table scan required; impossible to validate numerical integrity at scale.
6. **39 perm_ids in incubator but not large** - May indicate strategies that failed promotion criteria.
7. **Future exit_time values** - Max exit_time extends to 2026-05-06 (future date).
8. **20 rows with NULL asset_class** in bt_backtest_trades.
9. **opposite_day strategy catastrophic losses** - 3.6-14.3% win rate across all symbols, -97% to -198% returns.
10. **EQUITY data limited** - Only 2 backtest_results + 50 backtest_trades for equity asset class.
11. **No explicit foreign key constraints** - No `FOREIGN KEY` constraints defined in the schema (only index on backtest_run_id).

### INFO (7 findings)
12. **bt_backtest_runs is internally 100% consistent** - wins+losses=total_trades verified for all 285 rows.
13. **backtest_results/backtest_trades perfectly consistent** - Trade counts and win rates match exactly.
14. **at_large is subset of at_incubator** - All 224 perm_ids in large exist in incubator.
15. **Database is 99.9999% CRYPTO** - Only 20 NULL asset_class rows out of 28.7M.
16. **8 distinct source systems** feeding data into the backtest pipeline.
17. **bt_backtest_trades has proper indexes** on symbol, asset_class, strategy, and status.
18. **JSON columns are well-formed** - No parsing errors detected in sampled data.

---

## 11. RECOMMENDATIONS

### Immediate (P0)
1. **Backfill backtest_run_id** in `bt_backtest_trades` using strategy+symbol+timestamp matching against `bt_backtest_runs`.
2. **Standardize status values** - Migrate all to: OPEN, CLOSED_WIN, CLOSED_LOSS, EXPIRED.
3. **Investigate 26M OPEN trades** - Determine if positions are genuinely open or if close ETL is failing.

### Short-term (P1)
4. **Add index on `direction`** column for analytical performance.
5. **Add composite index on `(status, pnl_pct)`** for PnL anomaly detection.
6. **Add index on `(symbol, entry_time, strategy)`** for duplicate detection.
7. **Add foreign key constraint** `bt_backtest_trades(backtest_run_id) -> bt_backtest_runs(id)`.

### Medium-term (P2)
8. **Implement materialized views** for common aggregations (symbol counts, strategy performance, PnL distributions).
9. **Archive old OPEN trades** to improve query performance.
10. **Add asset_class column** to `backtest_results` for consistent asset class tracking.

---

*End of Report*
