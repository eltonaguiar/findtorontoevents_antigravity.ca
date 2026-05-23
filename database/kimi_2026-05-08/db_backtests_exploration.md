# Database Exploration Report: `ejaguiar1_backtests`

**Host:** mysql.50webs.com  
**Database:** ejaguiar1_backtests  
**Explored:** {datetime.now().strftime("%Y-%m-%d %H:%M")}  
**Total Tables:** 6  
**Total Rows:** 28,706,845

---

## Summary

This database is a **multi-system algorithmic trading backtest repository** that consolidates backtest results, trade-level records, and performance metrics from multiple trading strategy engines. It stores data from cryptocurrency-focused backtesting systems (primarily) with some equity backtests, capturing everything from high-level strategy performance summaries down to individual trade executions.

The database contains **28.7+ million rows** of trade data across 6 tables, representing:
- **Strategy archetype testing** (AT tables) — 5 major crypto symbols tested across 6 strategy archetypes
- **Portfolio-level backtest summaries** (backtest_results) — high-level run metrics
- **Individual trade records** (backtest_trades) — 50 equity trades from a custom strategy test
- **Bulk imported trade data** (bt_backtest_trades) — **28.7M trades** from 8 different source systems using 613+ distinct strategies across 583 symbols
- **Run-level summaries** (bt_backtest_runs) — aggregated performance per strategy/symbol from imported sources

---

## Tables Overview

| Table | Rows | Purpose | Related To |
|-------|------|---------|-----------|
| `at_incubator_backtest_results` | 1,285 | Crypto strategy archetype performance (5 symbols x 263 permutations) | Standalone |
| `at_large_backtest_results` | 1,105 | Same as above but with equity curve & trade log JSON | at_incubator_backtest_results |
| `backtest_results` | 2 | High-level equity portfolio backtest summaries | backtest_trades |
| `backtest_trades` | 50 | Equity trade-level records (custom strategy) | backtest_results |
| `bt_backtest_runs` | 285 | Aggregated strategy run data from 8 source systems | bt_backtest_trades |
| `bt_backtest_trades` | 28,705,218 | Individual trade records from multiple engines | bt_backtest_runs |

---

## Detailed Table Documentation

### 1. `at_incubator_backtest_results`

**Purpose:** Parameter optimization results for crypto strategy archetypes. Stores performance metrics for different parameter combinations ("permutations") tested against major crypto pairs.

**Schema:**

| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | int | NO | PRI | None | auto_increment |
| perm_id | varchar(20) | NO | MUL | None | |
| archetype | varchar(80) | NO | | None | |
| symbol | varchar(30) | NO | MUL | None | |
| params_json | json | NO | | None | Strategy parameters |
| total_trades | int | YES | | 0 | |
| wins | int | YES | | 0 | |
| losses | int | YES | | 0 | |
| win_rate | decimal(6,4) | YES | | 0.0000 | |
| sharpe | decimal(10,4) | YES | MUL | 0.0000 | |
| sortino | decimal(10,4) | YES | | 0.0000 | |
| max_drawdown | decimal(10,6) | YES | | 0.000000 | |
| profit_factor | decimal(10,4) | YES | | 0.0000 | |
| total_return | decimal(10,6) | YES | | 0.000000 | |
| avg_trade_pnl | decimal(10,6) | YES | | 0.000000 | |
| avg_hold_bars | decimal(6,1) | YES | | 0.0 | |
| slippage_pct | decimal(6,4) | YES | | 0.0000 | |
| commission_pct | decimal(6,4) | YES | | 0.0000 | |
| backtest_type | enum('fast','full') | YES | | fast | |
| created_at | datetime | NO | | None | |

**Sample Data (Row 1):**
```
id: 1, perm_id: 9ce31cab42ed, archetype: rsi_mean_reversion, symbol: BTC-USD
params_json: {"atr_period": 14, "rsi_period": 3, "sl_atr_mult": 2.19, "tp_atr_mult": 2.92...}
total_trades: 1, wins: 1, losses: 0, win_rate: 1.0000, sharpe: 0.0000, sortino: 0.0000
max_drawdown: 0.000000, profit_factor: 99.0000, total_return: 0.019354
avg_trade_pnl: 0.020854, avg_hold_bars: 0.0, slippage_pct: 0.0000, commission_pct: 0.0000
backtest_type: fast, created_at: 2026-03-10 06:18:23
```

**Data Quality:**
- No duplicate primary keys
- 263 distinct perm_ids across 1,285 rows (~5 symbol variants per permutation)
- 5 symbols tested: BTC-USD, ETH-USD, BNB-USD, SOL-USD, XRP-USD
- 6 archetypes: rsi_mean_reversion, ichimoku_cloud, vwap_reversion, stochrsi_bounce, ema_crossover, bollinger_squeeze
- Date range: 2026-03-10 to 2026-05-06
- Many rows have 0 trades (untested or failed parameter combinations)
- Indexes on: perm_id, symbol, sharpe

**Related Tables:** Shares identical schema with `at_large_backtest_results` (minus equity_curve_json and trade_log_json)

---

### 2. `at_large_backtest_results`

**Purpose:** Extended version of incubator results with full equity curve and trade log stored as JSON.

**Schema:** Same as `at_incubator_backtest_results` PLUS:

| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| equity_curve_json | json | YES | | None | Full equity curve data |
| trade_log_json | json | YES | | None | Individual trade records |

**Sample Data:** Same structure as incubator with 224 distinct perm_ids across 1,105 rows.

**Data Quality:**
- No duplicate primary keys
- Date range: 2026-03-10 to 2026-05-06
- Same 5 symbols and 6 archetypes as incubator
- 224 distinct perm_ids (vs 263 in incubator — smaller parameter search space but more detailed output)

**Related Tables:** `at_incubator_backtest_results` — same data structure, different granularity of stored output

---

### 3. `backtest_results`

**Purpose:** High-level summary of custom equity portfolio backtest runs. Only 2 records representing different holding period configurations.

**Schema:**

| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | int | NO | PRI | None | auto_increment |
| portfolio_id | int | NO | MUL | 0 | |
| run_name | varchar(200) | NO | | | |
| algorithm_filter | varchar(500) | NO | | | |
| strategy_type | varchar(50) | NO | MUL | | |
| start_date | date | YES | | None | |
| end_date | date | YES | | None | |
| initial_capital | decimal(12,2) | NO | | 10000.00 | |
| final_value | decimal(12,2) | NO | | 0.00 | |
| total_return_pct | decimal(10,4) | NO | | 0.0000 | |
| total_trades | int | NO | | 0 | |
| winning_trades | int | NO | | 0 | |
| losing_trades | int | NO | | 0 | |
| win_rate | decimal(5,2) | NO | | 0.00 | |
| avg_win_pct | decimal(10,4) | NO | | 0.0000 | |
| avg_loss_pct | decimal(10,4) | NO | | 0.0000 | |
| max_drawdown_pct | decimal(10,4) | NO | | 0.0000 | |
| total_commissions | decimal(12,2) | NO | | 0.00 | |
| sharpe_ratio | decimal(10,4) | NO | | 0.0000 | |
| sortino_ratio | decimal(10,4) | NO | | 0.0000 | |
| profit_factor | decimal(10,4) | NO | | 0.0000 | |
| expectancy | decimal(10,4) | NO | | 0.0000 | |
| params_json | text | YES | | None | |
| created_at | datetime | NO | | | |

**Sample Data:**

| id | run_name | strategy_type | start_date | end_date | initial_capital | final_value | total_return_pct | total_trades | win_rate |
|----|----------|---------------|------------|----------|-----------------|-------------|------------------|--------------|----------|
| 1 | custom_tp999_sl999_7d | custom | 2026-01-28 | 2026-02-06 | 10000.00 | 9169.72 | -8.3028 | 25 | 16.00% |
| 2 | custom_tp999_sl999_1d | custom | 2026-02-06 | 2026-02-06 | 10000.00 | 9260.90 | -7.3910 | 25 | 4.00% |

**Data Quality:**
- Only 2 rows — very small, test-level data
- Both runs negative return (custom strategy underperformed)
- 18 equity tickers traded (see backtest_trades)
- Indexes on: portfolio_id, strategy_type

**Related Tables:** `backtest_trades` — backtest_id FK references this table

---

### 4. `backtest_trades`

**Purpose:** Individual trade records for the 2 custom equity backtest runs. 50 trades across 18 equity tickers.

**Schema:**

| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | int | NO | PRI | None | auto_increment |
| backtest_id | int | NO | MUL | 0 | FK to backtest_results |
| ticker | varchar(10) | NO | MUL | None | |
| algorithm_name | varchar(100) | NO | | | |
| entry_date | date | NO | | None | |
| entry_price | decimal(12,4) | NO | | 0.0000 | |
| exit_date | date | YES | | None | |
| exit_price | decimal(12,4) | NO | | 0.0000 | |
| shares | int | NO | | 0 | |
| gross_profit | decimal(12,2) | NO | | 0.00 | |
| commission_paid | decimal(8,2) | NO | | 0.00 | |
| net_profit | decimal(12,2) | NO | | 0.00 | |
| return_pct | decimal(10,4) | NO | | 0.0000 | |
| exit_reason | varchar(50) | NO | | | |
| hold_days | int | NO | | 0 | |

**Sample Data:**

| id | ticker | algorithm_name | entry_date | entry_price | exit_date | exit_price | return_pct | exit_reason | hold_days |
|----|--------|----------------|------------|-------------|-----------|------------|------------|-------------|-----------|
| 1 | ABBV | Technical Momentum | 2026-01-28 | 225.0497 | 2026-02-05 | 217.9249 | -5.3876 | max_hold | 7 |
| 2 | AMZN | Technical Momentum | 2026-01-28 | 245.9034 | 2026-02-05 | 221.5766 | -11.9262 | max_hold | 7 |
| 3 | CVX | Technical Momentum | 2026-01-28 | 169.8953 | 2026-02-05 | 178.3338 | +2.6126 | max_hold | 7 |

**Data Quality:**
- No duplicate primary keys
- 50 trades, 18 tickers, 4 algorithm variants
- Date range: 2026-01-28 to 2026-02-06
- Exit reasons: max_hold (primary), end_of_data
- All trades have both entry and exit dates
- Indexes on: backtest_id, ticker

**Tickers:** ABBV, AMZN, CAT, CVX, F, GM, GME, GOOGL, JNJ, LRCX, META, MSFT, NVDA, PFE, SBUX, UNH, WMT, XOM

**Related Tables:** `backtest_results` (FK via backtest_id)

---

### 5. `bt_backtest_runs`

**Purpose:** Aggregated performance summaries for **94 distinct strategies** imported from 8 different trading engines/systems. All 285 records are CRYPTO asset class.

**Schema:**

| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | char(36) | NO | PRI | None | UUID |
| source_db | varchar(200) | NO | | None | Source system path |
| source_table | varchar(100) | NO | | None | Source table/file |
| strategy | varchar(200) | YES | MUL | None | Strategy name |
| symbol | varchar(50) | YES | MUL | None | Trading pair |
| asset_class | enum(...) | YES | MUL | UNKNOWN | CRYPTO, FOREX, etc. |
| total_trades | int | YES | | 0 | |
| wins | int | YES | | 0 | |
| losses | int | YES | | 0 | |
| win_rate | decimal(5,4) | YES | | None | |
| profit_factor | decimal(10,4) | YES | | None | |
| total_return | decimal(10,4) | YES | | None | |
| sharpe | decimal(10,4) | YES | | None | |
| max_drawdown | decimal(10,4) | YES | | None | |
| imported_at | datetime | NO | | | |

**Sample Data:**

| id | source_db | strategy | symbol | asset_class | total_trades | win_rate | profit_factor | total_return | sharpe | max_drawdown |
|----|-----------|----------|--------|-------------|--------------|----------|---------------|--------------|--------|--------------|
| 001a8759-... | alpha_engine/data/closed_picks.json | session_momentum_continuation | NZDUSD=X | CRYPTO | 1 | 1.0000 | 999.9990 | 0.0045 | 0.0000 | 0.0000 |
| 00be2d70-... | battleground/data/closed_picks.json | crypto_keltner_compression_expansion_v1 | BTCUSDT | CRYPTO | 24 | 0.6667 | 4.1710 | 10.5921 | 7.8060 | 2.3782 |
| 02727f25-... | alpha_engine/data/closed_picks.json | fourier_cycle_detector | FILUSDT | CRYPTO | 1 | 0.0000 | 0.0000 | -0.1063 | 0.0000 | 0.1063 |

**Data Quality:**
- No duplicate primary keys (UUIDs)
- 285 records, all CRYPTO class
- 94 unique strategies
- 8 source systems
- All imported on 2026-03-06 23:58:10 (batch import)
- Indexes on: strategy, symbol, asset_class

**Source Systems:**
1. `alpha_engine/data/closed_picks.json`
2. `battleground/data/closed_picks.json`
3. `KIMI_RISEOFTHECLAW/data/signal_tracker.db`
4. `KIMI_RISEOFTHECLAW/data/kimi_trading.db`
5. `paper_trading/data/paper.db`
6. `mercury2/data/closed_picks.json`
7. `ml_battleground/system_f_clawsofdoom/data/closed_picks.json`
8. `sandbox/data/opposite_day.db`

**Related Tables:** `bt_backtest_trades` (FK via backtest_run_id, though currently appears unlinked)

---

### 6. `bt_backtest_trades`

**Purpose:** **28.7 million individual trade records** imported from multiple trading systems. The core trade-level dataset of the database.

**Schema:**

| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | int | NO | PRI | None | auto_increment |
| backtest_run_id | char(36) | YES | MUL | None | FK to bt_backtest_runs (UUID) |
| source_db | varchar(200) | NO | | None | Source system |
| source_table | varchar(100) | NO | | None | Source table |
| symbol | varchar(50) | NO | MUL | None | Trading pair |
| asset_class | enum(...) | YES | MUL | UNKNOWN | |
| direction | enum('LONG','SHORT') | YES | | None | Trade direction |
| strategy | varchar(200) | YES | MUL | None | Strategy name |
| entry_price | decimal(18,8) | YES | | None | |
| exit_price | decimal(18,8) | YES | | None | |
| take_profit | decimal(18,8) | YES | | None | |
| stop_loss | decimal(18,8) | YES | | None | |
| entry_time | datetime | YES | | None | |
| exit_time | datetime | YES | | None | |
| pnl_pct | decimal(10,4) | YES | | None | Profit/loss % |
| status | varchar(20) | YES | MUL | None | Trade status |
| confidence | decimal(5,4) | YES | | None | Signal confidence |
| raw_data | json | YES | | None | Full raw signal data |
| imported_at | datetime | NO | | | |

**Sample Data:**

| id | symbol | direction | strategy | entry_price | exit_price | pnl_pct | entry_time | exit_time |
|----|--------|-----------|----------|-------------|------------|---------|------------|-----------|
| 1 | BTCUSDT | SHORT | crypto_kalman_trend_residual_reversion_v1 | 64264.30 | 65018.54 | -1.1737 | 2026-02-24 16:00:00 | 2026-02-25 01:00:00 |
| 2 | BTCUSDT | SHORT | crypto_kalman_trend_residual_reversion_v1 | 64436.70 | 65127.06 | -1.0714 | 2026-02-24 18:00:00 | 2026-02-25 01:00:00 |

**Data Quality:**
- No duplicate primary keys
- 28,705,218 rows — the dominant table by far (99.98% of all data)
- 583 distinct symbols, 613 distinct strategies
- backtest_run_id appears mostly NULL (FK link not established during import)
- Both LONG and SHORT directions present
- Indexed on: backtest_run_id, symbol, asset_class, strategy, status

**Key Observations:**
- The backtest_run_id field (FK to bt_backtest_runs) appears to be mostly unpopulated, suggesting the bulk import did not link individual trades to their parent runs
- raw_data JSON column stores the full original signal data for traceability
- Decimal precision of 18,8 for prices supports both high-value (BTC) and fractional assets

---

## Table Relationships

### Relationship Map

```
at_incubator_backtest_results  <--shares schema-->  at_large_backtest_results
                                                          (both: perm_id -> symbol x archetype results)

backtest_results (1)  <--backtest_id-->  backtest_trades (many)
                                                          (FK: backtest_trades.backtest_id)

bt_backtest_runs (1)  <--backtest_run_id-->  bt_backtest_trades (many)
                                                          (FK: bt_backtest_trades.backtest_run_id, mostly NULL)
```

### Shared Columns Summary

| Column | Tables | Purpose |
|--------|--------|---------|
| symbol | 4 tables (all except backtest_*) | Trading pair/ticker identifier |
| strategy | 2 tables (bt_*) | Strategy name |
| sharpe | 4 tables | Risk-adjusted return metric |
| total_trades, win_rate, profit_factor | 5 tables | Core performance metrics |
| total_return, max_drawdown | 4 tables | PnL metrics |
| params_json | 3 tables | Strategy parameters (JSON) |
| created_at / imported_at | All tables | Timestamp column |

### Foreign Keys

| Parent Table | Child Table | FK Column | Referenced Column | Status |
|-------------|------------|-----------|------------------|--------|
| backtest_results | backtest_trades | backtest_id | backtest_results.id | Active (all 50 trades linked) |
| bt_backtest_runs | bt_backtest_trades | backtest_run_id | bt_backtest_runs.id | Inactive (mostly NULL) |

---

## Data Quality Assessment

| Table | Rows | Duplicate PKs | NULL Columns | Date Range | Issues |
|-------|------|--------------|--------------|------------|--------|
| at_incubator_backtest_results | 1,285 | None | None significant | 2026-03-10 to 2026-05-06 | Many 0-trade rows (untested perms) |
| at_large_backtest_results | 1,105 | None | None significant | 2026-03-10 to 2026-05-06 | Same as above |
| backtest_results | 2 | None | None | 2026-01-28 to 2026-02-06 | Very small dataset |
| backtest_trades | 50 | None | exit_date nullable (all filled) | 2026-01-28 to 2026-02-06 | All trades closed |
| bt_backtest_runs | 285 | None | None significant | 2026-03-06 (single import) | All CRYPTO class |
| bt_backtest_trades | 28,705,218 | None | backtest_run_id, exit_time, take_profit, stop_loss NULL | N/A (query timeout) | FK mostly unlinked; some open trades likely |

### Key Quality Notes
1. **bt_backtest_trades has 28.7M rows** — queries timeout without proper indexing
2. **backtest_run_id in bt_backtest_trades is mostly NULL** — the FK relationship to bt_backtest_runs was not populated during import
3. **exit_time can be NULL** in bt_backtest_trades — represents open/unclosed trades
4. **take_profit and stop_loss NULLable** — not all strategies define explicit TP/SL levels
5. **All bt_backtest_runs data is CRYPTO** — the enum supports 10 asset classes but only CRYPTO is used

---

## Key Insights

1. **Multi-Engine Consolidation**: The database serves as a central repository for backtest data from at least 8 distinct trading systems (alpha_engine, battleground, KIMI_RISEOFTHECLAW, paper_trading, mercury2, ml_battleground, sandbox, and more).

2. **Strategy Diversity**: 613+ unique strategies are represented, ranging from simple RSI mean reversion to complex Kalman filter trend detection, Fourier cycle analysis, and funding rate arbitrage.

3. **Crypto-Focused**: All bt_backtest_runs data is CRYPTO class. The AT tables test only 5 major crypto pairs. The database is clearly designed for cryptocurrency algorithmic trading research.

4. **Scale**: The 28.7M trade records represent a substantial backtesting dataset — likely years of hourly/daily signals across hundreds of crypto pairs.

5. **Two Parallel Systems**: 
   - **AT system** (at_* tables): Strategy archetype testing with parameter optimization on 5 symbols
   - **BT system** (bt_* tables): Bulk import engine consolidating trades from multiple production systems

6. **Data Freshness**: All bt_backtest_runs data imported on 2026-03-06. AT table data spans March to May 2026, suggesting ongoing experimentation.

7. **Naming Conventions**: The database name "backtests" and table names clearly indicate this is a backtesting/research database, not a production trading system.

---

## Prediction/Signal/Forecast/Backtest-Related Tables

**ALL 6 tables are directly related to backtesting and model outputs.** Here's the classification:

### Backtest Result Tables
| Table | Type | Description |
|-------|------|-------------|
| `at_incubator_backtest_results` | **Backtest Results** | Parameter-optimized strategy performance metrics |
| `at_large_backtest_results` | **Backtest Results** | Same with full equity curve and trade log JSON |
| `backtest_results` | **Backtest Results** | High-level portfolio backtest summaries |
| `bt_backtest_runs` | **Backtest Results** | Aggregated per-strategy performance from imported systems |

### Trade-Level Tables
| Table | Type | Description |
|-------|------|-------------|
| `backtest_trades` | **Individual Trades** | Equity trade records from custom backtest runs |
| `bt_backtest_trades` | **Individual Trades** | 28.7M crypto trade records from 8+ systems |

### Tables Most Likely Containing Predictions/Signals
1. **bt_backtest_trades** — Contains `confidence` (decimal 5,4) and `raw_data` (JSON) columns, suggesting these are generated signal executions with model confidence scores
2. **bt_backtest_runs** — Strategy-level summaries that represent the output of predictive models
3. **backtest_results** + **backtest_trades** — Custom backtest output

### Signal-Related Column Evidence
- `confidence` in bt_backtest_trades (5,4 decimal) — likely model confidence score
- `raw_data` JSON in bt_backtest_trades — stores full signal/prediction context
- `strategy` columns — name the predictive algorithm used
- `direction` (LONG/SHORT) — the prediction direction
- `params_json` — model hyperparameters

---

*Report generated from automated MySQL database exploration.*
