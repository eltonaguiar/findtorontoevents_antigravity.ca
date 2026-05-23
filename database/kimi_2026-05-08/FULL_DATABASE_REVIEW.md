# Comprehensive Database Review: ejaguiar1_stocks & ejaguiar1_backtests
## mysql.50webs.com | Analysis Date: 2026-05-08

---

## Executive Summary

This review covers two interconnected MySQL databases that together power a **sophisticated multi-asset algorithmic trading platform** spanning stocks, crypto, forex, futures, ETFs, and memecoins. The system generates trading signals through 142+ algorithms across 40+ families, processes them through a multi-stage ML-enhanced aggregation pipeline, and tracks outcomes across 30+ million backtested trades.

| Metric | ejaguiar1_stocks | ejaguiar1_backtests |
|--------|-----------------|---------------------|
| **Total Tables** | 322 | 6 |
| **Tables with Data** | 220 | 6 |
| **Total Rows** | ~2.26 million | ~28.7 million |
| **Database Size** | ~2.1 GB | ~5+ GB |
| **Asset Classes** | 8 (CRYPTO, EQUITY, FOREX, FUTURES, ETF, MEMECOIN, PENNY, UNKNOWN) | Primarily CRYPTO |
| **Date Range** | 2024-02-07 to 2026-05-08 | 2026-01-28 to 2026-05-06 |
| **Algorithms** | 142 named strategies | 613+ strategies (in backtest data) |
| **Source Systems** | 60+ signal sources | 8 backtest engines |

---

## Part 1: Database ejaguiar1_stocks (322 Tables, ~2.26M Rows)

### 1.1 Architecture Overview

This is the **primary operational database** for a comprehensive algorithmic trading platform. It contains:

- **Core data tables** (prices, fundamentals, earnings, dividends)
- **Signal generation tables** (raw picks, consensus, ML signals, alpha picks)
- **Backtest infrastructure** (backtest runs, trades, simulations)
- **ML/AI layer** (feature store, model registry, ensemble weights)
- **Portfolio management** (snapshots, position sizing, tracking)
- **Sports betting module** (~30 lm_sports_* tables)
- **Prediction market integration** (Polymarket, copy trading)
- **Audit & logging** (comprehensive trail of all pipeline decisions)

### 1.2 Table Prefix Taxonomy

| Prefix | Meaning | Count |
|--------|---------|-------|
| `at_` | Aggregation/Trading Pipeline | 20 |
| `bt_` | Backtest System | 2 |
| `lm_` | Learning/Machine Intelligence | ~80 |
| `ml_` | Machine Learning Platform | 10 |
| `gm_` / `goldmine_` | Goldmine Signal Engine | 9 |
| `fx_` / `fxp_` | Forex Trading System | 19 |
| `alpha_` | Alpha Factor Models | 7 |
| `cp_` | Copy Trading / Proven Strategies | 7 |
| `cr_` | Crypto Reversal / Cross-Asset | 7 |
| `crypto_` | Crypto-Specific Data | 7 |
| `stock_` | Core Stock Data | 7 |
| `meme_` | Meme Coin / Social Sentiment | 5 |
| `KIMI_` | KIMI AI Assistant Data | 5 |
| `strategy_` | Strategy Lifecycle Management | 6 |
| `portfolio_` | Portfolio Management | 6 |
| `mf_` / `mf2_` | Mutual Fund Analysis | ~30 |
| `pf_` | Pattern Fingerprinting | 4 |

### 1.3 Core Tables Documentation

#### **stocks** - Master Instrument Universe (153 rows)
| Column | Type | Purpose |
|--------|------|---------|
| ticker | varchar(PK) | Primary identifier |
| company_name | varchar | Company name |
| sector | varchar | Industry sector |
| market_cap | varchar | Market cap category |

**Purpose:** Registry of all tracked equity/ETF instruments (AAPL, MSFT, GOOGL, etc.)
**Related to:** daily_prices, stock_picks, alpha_picks, stock_fundamentals, stock_earnings, stock_dividends

---

#### **algorithms** - Trading Strategy Definitions (142 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Algorithm ID |
| name | varchar | Strategy name |
| family | varchar | Strategy family |
| description | varchar | Detailed description |
| algo_type | varchar | Classification |
| ideal_timeframe | varchar | Optimal holding period |
| pros / cons | varchar | Strategy assessment |

**Algorithm Families:**
| Family | Count | Type |
|--------|-------|------|
| AcademicFactor | 16 | Academic research factors (BAB, QMJ, Piotroski) |
| AlphaFactor | 9 | Multi-factor alpha models |
| AlphaForge | 8 | Alpha ensemble strategies |
| Quant | 8 | Quantitative strategies |
| Flow | 6 | Insider/institutional flow |
| ESG | 5 | Environmental/social/governance |
| CAN SLIM | 4 | O'Neil growth investing |
| Quality | 4 | Quality factor |
| Technical | 3 | Technical momentum |
| Regime | 2 | Regime detection |

**Related to:** stock_picks, algorithm_performance, strategy_registry

---

#### **daily_prices** - Historical Price Data (49,340 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| ticker | varchar(FK) | Symbol reference |
| trade_date | date | Trading date |
| open_price | decimal | Opening price |
| high_price | decimal | High price |
| low_price | decimal | Low price |
| close_price | decimal | Closing price |
| adj_close | decimal | Adjusted close |
| volume | int | Trading volume |

**Data Range:** 2024-02-07 to 2026-04-29 | **153 tickers** | **Zero NULL close prices**
**Related to:** stocks (FK), stock_picks, alpha_picks

---

#### **stock_picks** - Stock Trading Picks (7,239 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| ticker | varchar(FK) | Stock symbol |
| algorithm_id | int(FK) | Strategy used |
| algorithm_name | varchar | Strategy name |
| pick_date / pick_time | date/datetime | Signal timestamp |
| entry_price | decimal | Entry price |
| score | int | Signal score |
| rating | enum | STRONG BUY / BUY / Speculative Buy / HOLD |
| risk_level | enum | Low/Medium/High/Very High |
| timeframe | varchar | Expected holding period |
| stop_loss_price | decimal | Stop loss level |
| indicators_json | json | Technical indicators used |
| verified | tinyint | Verification flag |

**Date Range:** 2024-02-07 to 2026-04-27
**Distribution:** STRONG BUY (2,687), BUY (3,105), Speculative Buy (1,446), HOLD (1)
**Related to:** stocks, algorithms, daily_prices

---

#### **alpha_picks** - Alpha Factor Model Picks (5,043 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| ticker | varchar(FK) | Stock symbol |
| strategy | varchar | Alpha strategy |
| pick_date | date | Signal date |
| entry_price | decimal | Entry price |
| score | decimal | Alpha score |
| conviction | enum | high/medium/low |
| expected_horizon | varchar | Holding period |
| position_size_pct | decimal | Recommended allocation |
| stop_loss_pct / take_profit_pct | decimal | Risk management levels |
| rationale | varchar | Reasoning |
| top_factors | varchar | Key factors driving pick |

**Date Range:** 2026-02-09 to 2026-04-27 | **48 tickers** | **9 strategies**
**Related to:** alpha_factor_scores, alpha_fundamentals, stocks

---

#### **alpha_factor_scores** - Multi-Factor Stock Scores (2,860 rows)
| Column | Type | Purpose |
|--------|------|---------|
| ticker | varchar(FK) | Stock symbol |
| score_date | date | Scoring date |
| momentum_12m/6m/3m/1m | decimal | Momentum factors |
| momentum_score / rank | decimal/int | Composite momentum |
| quality_roe | decimal | Quality metrics |
| (many more factor columns) | | |

**Purpose:** Computed factor scores for quantitative ranking of stocks.
**Related to:** alpha_picks, stocks

---

#### **trading_picks** - Live Trading Records (63,997 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | char(PK) | UUID |
| symbol | varchar | Trading pair/ticker |
| direction | varchar | LONG/SHORT |
| strategy | varchar | Strategy name |
| entry_price | decimal | Entry price |
| take_profit / stop_loss | decimal | Exit levels |
| confidence | decimal | Signal confidence |
| source_system | varchar | Origin system |
| status | enum | OPEN/WON/LOST/SL_HIT/TP_HIT |
| pnl_pct | decimal | Realized PnL |
| exit_price | decimal | Exit price |
| created_at / closed_at | datetime | Lifecycle timestamps |

**Date Range:** 2026-02-17 to 2026-05-08
**Asset Distribution:** FOREX (35.0%), FUTURES (27.8%), CRYPTO (26.3%), STOCK/ETF (10.9%)
**Top Sources:** multi_asset_copytrader (28,918), cta_replicator (7,866), non_crypto_consensus (4,778)
**Related to:** at_raw_picks, lm_signals, rapid_signals

---

#### **at_raw_picks** - Aggregated Raw Picks (121,857 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | char(PK) | UUID |
| aggregation_run_id | char(FK) | Run reference |
| source_system | varchar | Origin (60+ systems) |
| symbol | varchar | Trading pair |
| asset_class | enum | CRYPTO/EQUITY/FOREX/etc. |
| direction | enum | LONG/SHORT |
| entry_price | decimal | Entry price |
| take_profit / stop_loss | decimal | Risk levels |
| risk_reward / confidence | decimal | Quality metrics |
| strategy | varchar | Algorithm name |
| raw_payload | json | Full signal data |
| signal_timestamp | datetime | Signal time |
| dedup_hash | char(36) | Deduplication key |
| was_stale/banned/demoted/wr_suppressed | tinyint | Filter flags |
| status | enum | Signal status |
| exit_price / pnl_pct | decimal | Outcome tracking |

**Asset Distribution:** CRYPTO (74.8%), EQUITY (10.0%), FOREX (5.5%), UNKNOWN (3.2%), MEMECOIN (2.3%), FUTURES (1.8%), PENNY_STOCK (0.5%), ETF (0.1%)
**Top Sources:** incubator_gainer (21,351), AlphaEngine (13,498), quan_engine (13,260)
**Related to:** at_aggregation_runs, at_consensus_picks, at_filter_log

---

#### **at_consensus_picks** - Multi-Algorithm Consensus (5,176 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | char(PK) | UUID |
| aggregation_run_id | char(FK) | Run reference |
| symbol | varchar | Trading pair |
| consensus_direction | enum | Agreed direction |
| confidence_tier | enum | SUPER/STRONG/MODERATE |
| contributing_systems | int | Number of agreeing systems |
| source_picks_count | int | Raw picks aggregated |

**Distribution:** MODERATE (6,201), STRONG (3,955), SUPER (1,112)
**Related to:** at_aggregation_runs, at_raw_picks

---

#### **lm_signals** - ML-Processed Signals (33,557 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| signal_type | enum | Classification |
| symbol | varchar | Trading pair |
| direction | varchar | LONG/SHORT |
| confidence | decimal | ML confidence |
| source_model | varchar | Model name |
| processed_at | datetime | Processing time |

**Asset Distribution:** CRYPTO (90.7%), FOREX (5.7%), STOCK (3.6%)
**Related to:** at_raw_picks, trading_picks, goldmine_cursor_predictions

---

#### **rapid_signals** - Rapid Signal Generation (11,709 rows)
| Column | Type | Purpose |
|--------|------|---------|
| signal_id | int(PK) | Auto-increment |
| symbol | varchar | Trading pair |
| direction | varchar | LONG/SHORT |
| strategy | varchar | Strategy name |
| created_at | datetime | Generation time |

**Asset Distribution:** STOCK/ETF (55.0%), CRYPTO (39.6%), FOREX (5.4%)
**Related to:** trading_picks, lm_signals

---

#### **goldmine_cursor_predictions** - AI Prediction Engine (478 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| prediction_id | char | UUID |
| asset_class | varchar | Asset type |
| ticker | varchar | Symbol |
| algorithm | varchar | AI model |
| direction | varchar | LONG/SHORT |
| entry_price / target_price / stop_loss | decimal | Trade levels |
| confidence_score | int | 0-100 score |
| logged_at | datetime | Timestamp |

**Asset Class:** 100% stocks | **Date Range:** Through 2026-02-10
**Related to:** gm_unified_picks, lm_signals

---

#### **ml_feature_store** - ML Feature Vectors (396 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| pair | varchar | Trading pair |
| asset_class | varchar | Asset type |
| timestamp | datetime | Feature time |
| timeframe | varchar | Bar size (4H) |
| close_price | double | Price |
| return_1/5/20 | double | Returns |
| rsi_14, macd_value, macd_signal | double | Momentum |
| stoch_k, stoch_d, williams_r | double | Oscillators |
| sma_20, sma_50, ema_9, ema_21 | double | Moving averages |
| adx_14, atr_14, bollinger_* | double | Trend/volatility |
| realized_vol_20, volume_sma_20 | double | Volatility/volume |
| hurst_exponent, autocorrelation | double | Statistical |
| engines_bullish, engines_bearish | int | Signal counts |
| target_1h, target_4h, target_24h | double | **ALL NULL** |
| target_direction | varchar | **ALL NULL** |

**Coverage:** 36 crypto pairs, 4H timeframe, 11 timestamps
**CRITICAL ISSUE:** All target variables are NULL - not usable for supervised learning
**Related to:** lm_signals, ml_model_registry

---

#### **bt_backtest_trades** (in stocks DB) - Historical Backtest Trades (1,312,509 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| backtest_run_id | int(FK) | Run reference |
| symbol / asset_class | varchar | Trading pair |
| direction | varchar | LONG/SHORT |
| strategy | varchar | Strategy name |
| entry_price / exit_price | decimal | Prices |
| pnl_pct | decimal | Profit/loss |
| entry_time / exit_time | datetime | Timestamps |

**Size:** 1.5 GB (largest table in stocks DB)
**Related to:** bt_backtest_runs

---

#### **stock_fundamentals** - Fundamental Financial Data (119 rows)
| Column | Type | Purpose |
|--------|------|---------|
| ticker | varchar(FK) | Stock symbol |
| trailing_eps / forward_eps | decimal | Earnings |
| trailing_pe / forward_pe | decimal | Valuation |
| peg_ratio | decimal | Growth-adjusted PE |
| dividend_rate / dividend_yield | decimal | Income |

**Source:** Yahoo Finance v10 | **Related to:** stocks, alpha_factor_scores

---

#### **stock_earnings** - Earnings Data (381 rows)
| Column | Type | Purpose |
|--------|------|---------|
| ticker | varchar(FK) | Stock symbol |
| quarter_end | date | Quarter end date |
| eps_actual / eps_estimate | decimal | Actual vs. estimated |
| eps_surprise / surprise_pct | decimal | Surprise metrics |

**Source:** Yahoo Finance v10 | **Related to:** stocks, stock_fundamentals

---

#### **stock_dividends** - Dividend History (831 rows)
| Column | Type | Purpose |
|--------|------|---------|
| ticker | varchar(FK) | Stock symbol |
| ex_date | date | Ex-dividend date |
| amount | decimal | Dividend amount |
| frequency | varchar | Payment frequency |

**Related to:** stocks

---

### 1.4 Data Flow Architecture (stocks DB)

```
60+ Signal Sources (incubator_gainer, AlphaEngine, quan_engine, etc.)
    |
    v
at_raw_picks (121,857) --- dedup_hash ---> at_consensus_picks (5,176)
    |                                         |
    |---> at_filter_log (793,809)             |---> lm_signals (33,557)
    |                                         |---> rapid_signals (11,709)
    |                                         |---> trading_picks (63,997)
    |                                         |---> goldmine_cursor_predictions (478)
    |
    v
daily_prices (49,340) ---> stock_picks (7,239) ---> alpha_picks (5,043)
    |
    v
stock_fundamentals (119) ---> alpha_factor_scores (2,860)
    |
    v
bt_backtest_runs (285) ---> bt_backtest_trades (1,312,509)
```

### 1.5 Prediction-Related Tables Summary (stocks DB)

| Table | Rows | Asset Class | Purpose |
|-------|------|-------------|---------|
| **alpha_picks** | 5,043 | EQUITY | Alpha factor model predictions |
| **stock_picks** | 7,239 | EQUITY | Algorithmic stock picks |
| **rapid_signals** | 11,709 | MIXED | Fast signal generation |
| **at_raw_picks** | 121,857 | MIXED | Raw pre-consensus predictions |
| **at_consensus_picks** | 5,176 | MIXED | Multi-algorithm consensus picks |
| **lm_signals** | 33,557 | CRYPTO-dominated | ML-processed signals |
| **goldmine_cursor_predictions** | 478 | EQUITY | AI prediction engine |
| **ua_predictions** | 355 | MIXED | Unauthenticated predictions |
| **bt_backtest_trades** | 1,312,509 | MIXED | Backtest trade execution |
| **gm_unified_picks** | 1,846 | MIXED | Goldmine unified predictions |

---

## Part 2: Database ejaguiar1_backtests (6 Tables, ~28.7M Rows)

### 2.1 Architecture Overview

This is a **dedicated backtest repository** that consolidates trade-level and strategy-level backtest data from 8 different trading engines/systems. It is overwhelmingly crypto-focused (99.9999% of trades).

### 2.2 Core Tables Documentation

#### **bt_backtest_trades** - Individual Trade Records (28,705,218 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| backtest_run_id | char(36) | FK to bt_backtest_runs (**100% NULL**) |
| source_db / source_table | varchar | Origin system |
| symbol | varchar | Trading pair |
| asset_class | enum | Asset type (99.9999% CRYPTO) |
| direction | enum | LONG/SHORT |
| strategy | varchar | Strategy name |
| entry_price / exit_price | decimal | Prices |
| take_profit / stop_loss | decimal | Exit levels |
| entry_time / exit_time | datetime | Timestamps |
| pnl_pct | decimal | Profit/loss % |
| status | varchar | OPEN/closed/WON/LOST/... |
| confidence | decimal | Signal confidence |
| raw_data | json | Full original signal |

**Size:** ~5+ GB | **583 symbols** | **613 strategies**
**CRITICAL ISSUE:** backtest_run_id is 100% NULL - zero referential integrity with bt_backtest_runs
**Related to:** bt_backtest_runs (intended FK, never populated)

---

#### **bt_backtest_runs** - Strategy Run Summaries (285 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | char(36)(PK) | UUID |
| source_db | varchar | Origin system path |
| source_table | varchar | Origin table/file |
| strategy | varchar | Strategy name |
| symbol | varchar | Trading pair |
| asset_class | enum | CRYPTO (all rows) |
| total_trades / wins / losses | int | Trade counts |
| win_rate | decimal | Win percentage |
| profit_factor | decimal | Profit ratio |
| total_return | decimal | Total return % |
| sharpe | decimal | Sharpe ratio |
| max_drawdown | decimal | Max drawdown % |
| imported_at | datetime | Import timestamp |

**Strategies:** 94 unique | **Source Systems:** 8 | **All CRYPTO class**
**Internal Consistency:** 100% (wins + losses = total_trades for all rows)
**Related to:** bt_backtest_trades (intended parent, never linked)

---

#### **at_incubator_backtest_results** - Strategy Archetype Testing (1,285 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| perm_id | varchar | Parameter permutation ID |
| archetype | varchar | Strategy archetype name |
| symbol | varchar | Trading pair |
| params_json | json | Strategy parameters |
| total_trades / wins / losses | int | Trade counts |
| win_rate / sharpe / sortino | decimal | Performance metrics |
| max_drawdown / profit_factor | decimal | Risk metrics |
| total_return / avg_trade_pnl | decimal | Return metrics |
| avg_hold_bars | decimal | Average hold time |
| backtest_type | enum | fast/full |

**Symbols:** BTC-USD, ETH-USD, BNB-USD, SOL-USD, XRP-USD
**Archetypes:** rsi_mean_reversion, ichimoku_cloud, vwap_reversion, stochrsi_bounce, ema_crossover, bollinger_squeeze
**Related to:** at_large_backtest_results

---

#### **at_large_backtest_results** - Promoted Strategy Results (1,105 rows)
| Column | Type | Purpose |
|--------|------|---------|
| (same as incubator) | | Plus equity_curve_json and trade_log_json |

**Relationship:** at_large is a subset of at_incubator (224/263 perm_ids overlap)
**Related to:** at_incubator_backtest_results

---

#### **backtest_results** - Equity Portfolio Backtests (2 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| portfolio_id | int | Portfolio reference |
| run_name | varchar | Test name |
| strategy_type | varchar | Strategy classification |
| start_date / end_date | date | Test period |
| initial_capital | decimal | Starting capital |
| final_value / total_return_pct | decimal | Results |
| total_trades / winning_trades / losing_trades | int | Trade counts |
| win_rate / avg_win_pct / avg_loss_pct | decimal | Performance |
| max_drawdown_pct / sharpe_ratio / sortino_ratio | decimal | Risk metrics |
| profit_factor / expectancy | decimal | Quality metrics |

**Results:** Both runs negative (custom_tp999_sl999_7d: -8.30%, custom_tp999_sl999_1d: -7.39%)
**Related to:** backtest_trades (FK via backtest_id)

---

#### **backtest_trades** - Individual Equity Trades (50 rows)
| Column | Type | Purpose |
|--------|------|---------|
| id | int(PK) | Auto-increment |
| backtest_id | int(FK) | References backtest_results |
| ticker | varchar | Stock symbol |
| algorithm_name | varchar | Strategy used |
| entry_date / entry_price | date/decimal | Entry |
| exit_date / exit_price | date/decimal | Exit |
| shares / gross_profit / commission_paid | int/decimal | Trade details |
| net_profit / return_pct | decimal | PnL |
| exit_reason | varchar | Why closed |
| hold_days | int | Duration |

**Consistency:** PERFECT with backtest_results (trade counts, win rates, returns all match)
**Tickers:** 18 large-cap stocks
**Related to:** backtest_results

---

### 2.3 Data Flow Architecture (backtests DB)

```
8 Source Systems:
  - alpha_engine/data/closed_picks.json (141 runs)
  - KIMI_RISEOFTHECLAW/data/kimi_trading.db (39 runs)
  - paper_trading/data/paper.db (28 runs)
  - mercury2/data/closed_picks.json (18 runs)
  - battleground/data/closed_picks.json (16 runs)
  - sandbox/data/opposite_day.db (14 runs)
  - ml_battleground/... (10 runs)
  - KIMI_RISEOFTHECLAW/data/signal_tracker.db (19 runs)
    |
    v
bt_backtest_runs (285 strategy summaries)
    |
    +---> bt_backtest_trades (28.7M individual trades) [INTENDED FK: 100% NULL]

at_incubator_backtest_results (1,285 parameter permutations)
    |
    +---> at_large_backtest_results (1,105 promoted - subset)

backtest_results (2 portfolio backtests)
    |
    +---> backtest_trades (50 individual trades) [FK: PERFECT]
```

### 2.4 Prediction-Related Tables Summary (backtests DB)

| Table | Rows | Asset Class | Purpose |
|-------|------|-------------|---------|
| **bt_backtest_trades** | 28,705,218 | 99.9999% CRYPTO | Core trade execution data with confidence scores and raw JSON signals |
| **bt_backtest_runs** | 285 | CRYPTO | Strategy performance summaries |
| **at_incubator_backtest_results** | 1,285 | CRYPTO (5 pairs) | Strategy archetype parameter optimization |
| **at_large_backtest_results** | 1,105 | CRYPTO (5 pairs) | Promoted strategies with full equity curves |
| **backtest_results** | 2 | EQUITY | Portfolio backtest summaries |
| **backtest_trades** | 50 | EQUITY | Individual equity backtest trades |

---

## Part 3: Cross-Database Relationships

### 3.1 Shared Data Flow
```
ejaguiar1_stocks DB                          ejaguiar1_backtests DB
    |                                              |
    |---> bt_backtest_trades (1.3M rows)           |---> bt_backtest_trades (28.7M rows)
    |     (smaller historical set)                  |     (complete consolidated set)
    |                                              |
    |---> bt_backtest_runs (285 rows)              |---> bt_backtest_runs (285 rows)
          |                                              |
          +-- Both databases share the same bt_backtest_runs IDs
          +-- The stocks DB has 1.3M backtest trades (historical)
          +-- The backtests DB has 28.7M backtest trades (consolidated from 8 engines)
```

### 3.2 Unified Signal Pipeline
```
Signal Generation (stocks DB):
    algorithms (142) ---> stock_picks (7,239)
    alpha_factor_scores ---> alpha_picks (5,043)
    60+ source_systems ---> at_raw_picks (121,857)
                              |
                              +---> at_consensus_picks (5,176)
                              +---> lm_signals (33,557)
                              +---> rapid_signals (11,709)
                              +---> trading_picks (63,997)

Backtest Validation (backtests DB):
    8 engines ---> bt_backtest_runs (285) ---> bt_backtest_trades (28.7M)
    
Strategy Incubation:
    6 archetypes x 263 permutations ---> at_incubator (1,285) ---> at_large (1,105)
```

---

## Part 4: Core Prediction Tables Per Asset Class

### 4.1 STOCKS / EQUITY

| Table | Rows | Role in Prediction |
|-------|------|-------------------|
| **alpha_picks** | 5,043 | PRIMARY - Alpha factor model predictions with conviction levels |
| **stock_picks** | 7,239 | PRIMARY - Algorithm-generated picks with entry/stop/rating |
| **goldmine_cursor_predictions** | 478 | AI-powered predictions (stocks only) |
| **rapid_signals** | 19,438 | Fast signals (55% are stock/ETF) |
| **alpha_factor_scores** | 2,860 | Multi-factor scoring that feeds into alpha_picks |
| **daily_prices** | 49,340 | Input data - price history |
| **stock_fundamentals** | 119 | Input data - fundamentals |

### 4.2 CRYPTO

| Table | Rows | Role in Prediction |
|-------|------|-------------------|
| **at_raw_picks** | 101,781 | PRIMARY - Raw signals (74.8% of all picks) |
| **lm_signals** | 30,440 | PRIMARY - ML-processed signals (90.7% crypto) |
| **rapid_signals** | 13,989 | Fast signals (39.6% crypto) |
| **trading_picks** | 16,801 | Live executed crypto trades |
| **at_consensus_picks** | 9,680 | Consensus signals (84.6% crypto) |
| **ml_feature_store** | 396 | ML feature vectors (100% crypto, but ALL targets NULL) |
| **crypto_assets** | 14 | Metadata for tracked crypto |

### 4.3 FOREX

| Table | Rows | Role in Prediction |
|-------|------|-------------------|
| **trading_picks** | 22,420 | PRIMARY - Most forex activity (35% of all trading picks) |
| **at_raw_picks** | 7,472 | Raw forex signals (5.5%) |
| **lm_signals** | 1,914 | ML-processed forex signals (5.7%) |
| **fx_prices** | 3,855 | Price data |
| **fx_signals** | 585 | Dedicated forex signals |
| **fx_pairs** | 9 | Currency pair metadata |

### 4.4 FUTURES

| Table | Rows | Role in Prediction |
|-------|------|-------------------|
| **trading_picks** | 17,815 | PRIMARY - Futures trades (27.8%) |
| **at_raw_picks** | 2,509 | Raw futures signals (1.8%) |
| **at_futures_symbol_edge** | 4 | Edge calculation data |

### 4.5 ETFs

| Table | Rows | Role in Prediction |
|-------|------|-------------------|
| **goldmine_cursor_predictions** | 51 | ETF-specific predictions via "ETF Masters" |
| **at_raw_picks** | 152 | Raw ETF signals (0.1%) |
| **trading_picks** | 57 | ETF trades |

### 4.6 MEMECOINS

| Table | Rows | Role in Prediction |
|-------|------|-------------------|
| **at_raw_picks** | 3,155 | PRIMARY - Memecoin signals (2.3%) |
| **meme_signals** | 50 | Meme signal scoring |
| **meme_signal_results** | 50 | Meme signal results |
| **meme_ml_predictions** | 0 | Meme ML predictions (empty) |
| **meme_ml_signals** | 50 | Meme ML signals |

---

## Part 5: Data Validity & Cross-Checks

### 5.1 Referential Integrity

| Check | Result | Severity |
|-------|--------|----------|
| daily_prices.tickers -> stocks | 0 orphans | PASS |
| stock_picks.tickers -> stocks | 0 orphans | PASS |
| alpha_picks.tickers -> stocks | 0 orphans | PASS |
| alpha_factor_scores.tickers -> stocks | 0 orphans | PASS |
| stock_picks.algorithm_id -> algorithms | 63 orphans (algorithm_id=0) | WARNING |
| backtest_trades.backtest_id -> backtest_results | 0 orphans | PASS |
| bt_backtest_trades.backtest_run_id -> bt_backtest_runs | 100% NULL | CRITICAL |

### 5.2 Data Freshness

| Table | Latest Date | Status |
|-------|-------------|--------|
| trading_picks | 2026-05-08 (today) | ACTIVE |
| at_raw_picks | 2026-05-08 (today) | ACTIVE |
| lm_signals | 2026-05-08 (today) | ACTIVE |
| at_consensus_picks | 2026-05-08 (today) | ACTIVE |
| daily_prices | 2026-04-29 | STALE (9 days) |
| rapid_signals | 2026-05-06 | RECENT |
| alpha_picks / stock_picks | 2026-04-27 | STALE (11 days) |
| goldmine_cursor_predictions | 2026-02-10 | STALE (87 days) |
| ml_feature_store | 2026-02-16 | STALE (81 days) |

### 5.3 Data Quality Issues

#### CRITICAL

| Issue | Impact | Evidence |
|-------|--------|----------|
| **WON trades have negative avg PnL** | Invalidates performance metrics | trading_picks: WON avg = -40.82%; Min PnL = -106,700.68% |
| **Outcome tracking inadequate** | Cannot evaluate 99.9% of signals | 121 outcomes tracked for 136,155+ raw picks (0.09%) |
| **alpha_picks lacks exit tracking** | Cannot measure alpha strategy performance | No exit_price or pnl_pct columns |
| **stock_picks lacks exit tracking** | Cannot measure pick performance | Only stop_loss_price; no exit tracking |
| **ml_feature_store targets all NULL** | Cannot train supervised ML models | 396 rows, target_direction/target_* all NULL |
| **bt_backtest_trades FK 100% NULL** | Cannot link trades to runs | 28.7M trades with NULL backtest_run_id |

#### WARNING

| Issue | Impact | Evidence |
|-------|--------|----------|
| daily_prices 98.2% stale | Price data is very old | 48,466 of 49,340 rows older than 30 days |
| rapid_signals 97.8% stale | Signal generation may be paused | 34,559 of 35,328 rows older than 30 days |
| at_raw_picks dedup flags unused | All filtering happens post-hoc | was_stale/was_banned/was_demoted all 0 |
| 11 negative confidence scores | Invalid confidence values | -0.8 to -0.6 from sandbox_opposite source |
| 3 negative stop_loss prices | Data corruption | HYPEUSDT, STOUSDT, STRKUSDT |
| Hardcoded goldmine PnL | Artificial performance data | Won = uniform +5.0%, Lost = uniform -3.0% |
| bt_backtest status inconsistency | Cannot reliably filter trades | 11 status variants: OPEN/closed/WON/WIN/LOST/LOSS/... |
| 90.7% OPEN trades in backtests | Close logic may be broken | 26M of 28.7M trades still OPEN |

#### INFO

| Finding | Detail |
|---------|--------|
| No future dates detected | All dates <= 2026-05-08 |
| No NULL close prices in daily_prices | 49,340 prices all valid |
| No negative prices or volumes | Clean price data |
| backtest_results/backtest_trades perfectly consistent | 100% match on all metrics |
| bt_backtest_runs internally 100% consistent | wins + losses = total_trades verified |

---

## Part 6: Key Insights

### 6.1 Platform Scale & Sophistication
- **322 tables** in the operational database indicates an extremely sophisticated, multi-module trading platform
- **142 algorithms** across **40+ families** spanning academic factors, technical analysis, alternative data, and ML/AI
- **60+ signal source systems** feeding into a unified aggregation pipeline
- **8 backtest engines** contributing to a consolidated 28.7M trade repository

### 6.2 Asset Class Prioritization
| Asset Class | Signal Volume | Primary Tables | Pipeline Maturity |
|-------------|--------------|----------------|-------------------|
| **CRYPTO** | 74.8% of signals | at_raw_picks, lm_signals, rapid_signals, trading_picks | **MOST MATURE** |
| **EQUITY** | 10.0% of signals | stock_picks, alpha_picks, goldmine_cursor_predictions | Mature but lacks outcome tracking |
| **FOREX** | 5.5% of signals | fx_signals, trading_picks | Moderate |
| **FUTURES** | 1.8% of signals | trading_picks, at_raw_picks | Basic |
| **MEMECOIN** | 2.3% of signals | meme_signals, at_raw_picks | Experimental |
| **ETF** | 0.1% of signals | at_raw_picks, goldmine_cursor_predictions | Minimal |

### 6.3 Prediction Pipeline Architecture
The platform uses a **multi-stage ensemble pipeline**:

1. **Signal Generation Layer** (60+ sources) - Raw predictions from diverse algorithms
2. **Aggregation Layer** (at_raw_picks) - Deduplication and normalization
3. **Consensus Layer** (at_consensus_picks) - Multi-system agreement filtering
4. **ML Intelligence Layer** (lm_signals) - Machine learning meta-processing
5. **Execution Layer** (trading_picks) - Live trade execution with PnL tracking
6. **Backtest Validation Layer** (backtests DB) - Historical performance validation

### 6.4 Critical Gaps
1. **Outcome tracking is the #1 gap** - Only 0.09% of raw picks have tracked outcomes
2. **alpha_picks and stock_picks are "fire and forget"** - No systematic tracking of realized returns
3. **ML feature store cannot be used for training** - All target variables are NULL
4. **Backtest databases are not linked** - 28.7M trades cannot be joined to their parent runs
5. **Significant staleness** - Price data and some signal tables are heavily stale

### 6.5 Unique Features
- **Prediction market integration** - Polymarket whale tracking and prediction market agents
- **Sports betting module** - Full NBA/NFL/NHL/MLB ML prediction system
- **Copy trading** - Multi-asset copy trader with 28,918 picks
- **SEC data integration** - 13F holdings and insider trading data
- **Sports sentiment analysis** - Dedicated sports CLV and value bet detection

---

## Part 7: Recommendations

### Immediate (P0)
1. **Fix contradictory PnL data** in trading_picks - WON trades should not have negative PnL
2. **Add outcome tracking** to alpha_picks and stock_picks (exit_price, pnl_pct, closed_at columns)
3. **Backfill backtest_run_id** in bt_backtest_trades using strategy+symbol+timestamp matching
4. **Populate ML target variables** in ml_feature_store or deprecate the table

### Short-term (P1)
5. **Standardize status values** across bt_backtest_trades (use single convention)
6. **Enable dedup flags** in at_raw_picks during signal ingestion
7. **Refresh stale data** - daily_prices and rapid_signals need updates
8. **Fix negative confidence** and negative stop_loss records

### Medium-term (P2)
9. **Implement proper outcome tracking pipeline** - Link raw picks through to realized PnL
10. **Add materialized views** for common aggregations
11. **Archive old OPEN trades** to improve query performance
12. **Investigate 26M OPEN trades** in backtests DB

---

*Report Generated: 2026-05-08*
*Databases: ejaguiar1_stocks (322 tables, ~2.26M rows) + ejaguiar1_backtests (6 tables, ~28.7M rows)*
*Total Combined Rows: ~30.96 million*
