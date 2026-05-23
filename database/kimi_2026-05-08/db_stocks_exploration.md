# Database: ejaguiar1_stocks

## Summary

| Metric | Value |
|--------|-------|
| Total Tables | 322 |
| Empty Tables | 102 |
| Tables with Data | 220 |
| Total Estimated Rows | ~2.26 million |
| Total Database Size | ~2.1 GB |
| Storage Engines | InnoDB (primary), MyISAM |
| Foreign Key Relationships | 5 |
| Date Range | 2024-02-07 to 2026-05-08 |

This is a **comprehensive algorithmic trading platform database** spanning multiple asset classes (stocks, crypto, forex, futures, ETFs) with 142+ named trading algorithms organized into 40+ families. The system generates trading signals, tracks backtests, manages portfolios, and includes a sophisticated ML/ensemble layer with sports betting, sentiment analysis, and prediction market integration.

---

## Tables Overview

| # | Table | Rows | Purpose |
|---|-------|------|---------|
| 1 | `bt_backtest_trades` | 1,312,509 | Historical backtest trade records from strategy evaluation |
| 2 | `at_filter_log` | 505,080 | Audit trail of signal filtering/deduplication decisions |
| 3 | `at_raw_picks` | 121,857 | Raw aggregated picks from all source systems before consensus |
| 4 | `daily_prices` | 49,340 | Daily OHLCV price data for 153 tickers (2024-2026) |
| 5 | `lm_signals` | 33,557 | Signal intelligence layer - ML-processed signals with meta-data |
| 6 | `at_audit_events` | 27,602 | Audit trail of aggregation pipeline events |
| 7 | `trading_picks` | 24,644 | Live and historical trading picks with PnL tracking |
| 8 | `stock_picks` | 7,239 | Stock-specific picks from 142 algorithms |
| 9 | `alpha_picks` | 5,043 | Alpha factor model picks with conviction levels |
| 10 | `at_consensus_picks` | 5,176 | Multi-algorithm consensus picks |
| 11 | `at_aggregation_runs` | 1,847 | Aggregation run metadata |
| 12 | `gm_unified_picks` | 1,846 | Goldmine unified pick system |
| 13 | `rapid_signals` | 11,709 | Rapid signal generation output |
| 14 | `goldmine_cursor_predictions` | 478 | AI prediction engine outputs |
| 15 | `ua_predictions` | 355 | Unauthenticated prediction signals |
| 16 | `ml_feature_store` | 396 | ML feature vectors (technical indicators) |
| 17 | `stocks` | 153 | Master stock/instrument universe |
| 18 | `algorithms` | 142 | Trading algorithm definitions and metadata |
| 19 | `crypto_assets` | 14 | Crypto asset definitions |
| 20 | `stock_earnings` | 381 | Quarterly earnings data |
| 21 | `stock_dividends` | 831 | Dividend history |
| 22 | `stock_fundamentals` | 119 | Fundamental financial metrics |
| 23 | `alpha_factor_scores` | 2,860 | Multi-factor stock scores |
| 24 | `portfolio_snapshots` | 26 | Portfolio performance snapshots |
| 25 | `backtest_results` | 2 | Backtest run summaries |

### Table Prefix/Suffix Guide

| Prefix/Suffix | Meaning | Count |
|---------------|---------|-------|
| `alpha_` | Alpha factor model tables | 7 |
| `at_` | Aggregation/trading pipeline | 20 |
| `bt_` | Backtest system | 2 |
| `cp_` | Copy trading / proven strategies | 7 |
| `cr_` | Crypto reversal / cross-asset | 7 |
| `crypto_` | Crypto-specific data | 7 |
| `fx_` | Forex trading system | 10 |
| `fxp_` | Forex pairs / portfolios | 9 |
| `gm_` / `goldmine_` | Goldmine signal engine | 9 |
| `KIMI_` | KIMI AI assistant data | 5 |
| `lm_` | Learning/machine intelligence | ~80 |
| `mf_` / `mf2_` | Mutual fund analysis | ~30 |
| `ml_` | Machine learning platform | 10 |
| `meme_` | Meme coin / social sentiment | 5 |
| `pf_` | Pattern fingerprinting | 4 |
| `portfolio_` | Portfolio management | 6 |
| `stock_` | Core stock data | 7 |
| `strategy_` | Strategy lifecycle management | 6 |

---

## Detailed Table Documentation

### `stocks` - Master Instrument Universe

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| ticker | varchar | NO | PRI | None |
| company_name | varchar | NO | | None |
| sector | varchar | YES | | '' |
| market_cap | varchar | YES | | '' |

**Purpose:** Registry of 153 stock/ETF tickers tracked by the system (e.g., GM, PFE, F, SBUX, UNH, AAPL, ABBV, ABT, GOOGL, CAT).

**Data Quality:**
- 153 tickers, many with missing sector info
- 7239 stock picks reference these tickers
- Primary key used as foreign key in price, picks, fundamentals tables

**Related Tables:** `daily_prices`, `stock_picks`, `alpha_picks`, `alpha_factor_scores`, `stock_fundamentals`, `stock_earnings`, `stock_dividends`

---

### `daily_prices` - Historical Price Data

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| ticker | varchar | NO | MUL | None |
| trade_date | date | NO | MUL | None |
| open_price | decimal | NO | | None |
| high_price | decimal | NO | | None |
| low_price | decimal | NO | | None |
| close_price | decimal | NO | | None |
| adj_close | decimal | NO | | None |
| volume | int | NO | | None |

**Purpose:** Daily OHLCV price history for all tracked instruments.

**Data Quality:**
- **Rows:** 49,340
- **Tickers:** 153 distinct
- **Date Range:** 2024-02-07 to 2026-04-29
- **NULL close prices:** 0 (clean)
- **Primary Key:** id (auto-increment)
- **Indexes:** ticker, trade_date for fast lookups

**Sample Data:**
| ticker | trade_date | open | high | low | close | volume |
|--------|------------|------|------|-----|-------|--------|
| ABBV | 2025-02-07 | 193.16 | 193.86 | 190.44 | 190.60 | 3,805,900 |

**Related Tables:** `stocks`, `stock_ohlcv`, `crypto_ohlcv`

---

### `algorithms` - Trading Strategy Definitions

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| name | varchar | NO | | None |
| family | varchar | NO | | None |
| description | varchar | YES | | None |
| algo_type | varchar | NO | | None |
| ideal_timeframe | varchar | YES | | None |
| pros | varchar | YES | | None |
| cons | varchar | YES | | None |

**Purpose:** Registry of 142 named trading algorithms organized into 40+ families.

**Algorithm Families:**
| Family | Count | Type |
|--------|-------|------|
| AcademicFactor | 16 | Academic research factors |
| AlphaFactor | 9 | Multi-factor alpha models |
| AlphaForge | 8 | Alpha ensemble strategies |
| Flow | 6 | Insider/institutional flow |
| ESG | 5 | Environmental/social/governance |
| Innovation | 5 | Patent/IP/network effects |
| SupplyChain | 3 | Supply chain monitoring |
| CAN SLIM | 4 | O'Neil growth investing |
| QuantFund | 5 | Quant fund style |
| NoBedTime | 5 | Overnight/consensus strategies |
| Quant | 8 | Quantitative strategies |
| MetaAI | 3 | Meta-learning ensemble |
| Earnings | 3 | Earnings-based strategies |
| Sector | 3 | Sector rotation |
| Quality | 4 | Quality factor |
| Regime | 2 | Regime detection |
| Academic | 7 | Academic research |
| Technical | 3 | Technical momentum |
| Composite | 1 | Composite rating |
| Volatility | 1 | Volatility strategies |
| And many more | | |

**Key Algorithms:**
- `[1] CAN SLIM` - O'Neil growth screener
- `[5] Technical Momentum` - Volume/RSI/breakouts
- `[8] Composite Rating` - Multi-factor composite
- `[11] Alpha Predator` - Momentum-based alpha
- `[38] Meta-Learner Arbitrator` - Meta ensemble
- `[40] God-Mode Alpha` - Ultimate meta-alpha

**Related Tables:** `stock_picks`, `algorithm_performance`, `algorithm_rolling_perf`, `strategy_registry`

---

### `stock_picks` - Stock Trading Picks

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| ticker | varchar | NO | MUL | None |
| algorithm_id | int | NO | MUL | None |
| algorithm_name | varchar | NO | | None |
| pick_date | date | NO | MUL | None |
| pick_time | datetime | NO | | None |
| entry_price | decimal | NO | | None |
| simulated_entry_price | decimal | NO | | None |
| score | int | NO | | None |
| rating | enum | NO | | None |
| risk_level | enum | NO | | None |
| timeframe | varchar | NO | | None |
| stop_loss_price | decimal | NO | | None |
| pick_hash | varchar | YES | | '' |
| indicators_json | json | YES | | None |
| verified | tinyint | YES | | 0 |

**Purpose:** Individual stock picks generated by algorithms with entry prices, ratings, risk levels.

**Data Quality:**
- **Rows:** 7,239
- **Date Range:** 2024-02-07 to 2026-04-27
- **Ratings:** STRONG BUY (2,687), BUY (3,105), Speculative Buy (1,446), HOLD (1)
- **Risk Levels:** Low (3,439), Medium (2,914), High (21), Very High (4)
- **Duplicate tickers across dates:** 7,105 (normal - different dates)
- **NULL entry prices:** 0 (clean)

**Sample Data:**
| ticker | algorithm | pick_date | score | rating | risk | timeframe | stop_loss |
|--------|-----------|-----------|-------|--------|------|-----------|-----------|
| GM | Technical Momentum | 2026-01-28 | 100 | STRONG BUY | High | 3d | 82.42 |
| PFE | Technical Momentum | 2026-01-28 | 85 | STRONG BUY | High | 3d | 25.69 |

**Related Tables:** `algorithms`, `stocks`, `daily_prices`, `stock_fundamentals`

---

### `alpha_picks` - Alpha Factor Model Picks

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| ticker | varchar | NO | MUL | None |
| strategy | varchar | NO | | None |
| pick_date | date | NO | MUL | None |
| entry_price | decimal | NO | | None |
| score | decimal | NO | | None |
| conviction | enum | NO | | None |
| expected_horizon | varchar | YES | | None |
| risk_level | enum | YES | | None |
| position_size_pct | decimal | YES | | None |
| stop_loss_pct | decimal | YES | | None |
| take_profit_pct | decimal | YES | | None |
| rationale | varchar | YES | | None |
| top_factors | varchar | YES | | None |
| avoid_reasons | varchar | YES | | None |
| pick_hash | char | YES | UNI | None |
| created_at | datetime | YES | | None |

**Purpose:** Sophisticated alpha factor model picks with position sizing, conviction levels, and rationale.

**Data Quality:**
- **Rows:** 5,043
- **Date Range:** 2026-02-09 to 2026-04-27
- **Conviction:** high (1,927), medium (1,776), low (1,340)
- **Stop Loss:** 20%, Take Profit: 40% (standard)
- **Unique pick_hash:** Yes (UNI constraint)

**Sample Data:**
| ticker | strategy | pick_date | score | conviction | horizon | risk | pos_size |
|--------|----------|-----------|-------|------------|---------|------|----------|
| GOOGL | Alpha Factor Momentum | 2026-02-09 | 91.08 | high | 1m | Medium | 8% |
| CAT | Alpha Factor Momentum | 2026-02-09 | 89.80 | high | 1m | Medium | 8% |

**Related Tables:** `alpha_factor_scores`, `alpha_fundamentals`, `alpha_universe`

---

### `alpha_factor_scores` - Multi-Factor Stock Scores

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| ticker | varchar | NO | MUL | None |
| score_date | date | NO | MUL | None |
| momentum_12m | decimal | YES | | None |
| momentum_6m | decimal | YES | | None |
| momentum_3m | decimal | YES | | None |
| momentum_1m | decimal | YES | | None |
| momentum_score | decimal | YES | | None |
| momentum_rank | int | YES | | None |
| quality_roe | decimal | YES | | None |
| ... (many more factor columns) | | | | |

**Purpose:** Computed factor scores (momentum, quality, value, growth, etc.) for stock ranking.

**Data Quality:**
- **Rows:** 2,860
- **Data freshness:** Latest scores from 2026-02-09

**Related Tables:** `alpha_picks`, `stocks`, `alpha_fundamentals`

---

### `trading_picks` - Live Trading Records

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | char | NO | PRI | None |
| symbol | varchar | NO | MUL | None |
| direction | varchar | YES | | '' |
| strategy | varchar | YES | | '' |
| entry_price | decimal | NO | | None |
| take_profit | decimal | YES | | None |
| stop_loss | decimal | YES | | None |
| confidence | decimal | YES | | None |
| source_system | varchar | YES | | '' |
| status | enum | NO | | None |
| pnl_pct | decimal | YES | | None |
| exit_price | decimal | YES | | None |
| created_at | datetime | YES | | None |
| closed_at | datetime | YES | | None |
| exit_reason | varchar | YES | | None |
| updated_at | datetime | YES | | None |

**Purpose:** Live trading picks across all asset classes with full lifecycle tracking.

**Data Quality:**
- **Rows:** ~63,997 (actually trading_picks shows more rows on full count)
- **Date Range:** 2026-02-17 to 2026-05-08
- **Top Symbols:** BTCUSDT (3,683), USDCAD (2,687), EURJPY (2,548)
- **Status Distribution:**
  - OPEN: ~49,441 (77%)
  - WON: 2,549 (4%)
  - LOST: 3,072 (4.8%)
  - SL_HIT: 818 (1.3%)
  - TP_HIT: 629 (1.0%)
  - And others...
- **Source Systems:** 60+ different systems contributing picks

**Top Source Systems:**
| Source | Count |
|--------|-------|
| multi_asset_copytrader | 28,918 |
| cta_replicator | 7,866 |
| non_crypto_consensus | 4,778 |
| alpha_engine | 961 |
| ml_crypto_pred | 1,478 |
| prediction_market_agents | 1,920 |
| copy_trader_polymarket | 1,457 |
| polymarket_whale_tracker | 1,856 |

**Related Tables:** `at_raw_picks`, `rapid_signals`, `lm_signals`

---

### `at_raw_picks` - Aggregated Raw Picks

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | char | NO | PRI | None |
| aggregation_run_id | char | NO | MUL | None |
| source_system | varchar | NO | MUL | None |
| symbol | varchar | NO | MUL | None |
| asset_class | enum | NO | MUL | None |
| direction | enum | NO | | None |
| entry_price | decimal | NO | | None |
| take_profit | decimal | YES | | None |
| stop_loss | decimal | YES | | None |
| risk_reward | decimal | YES | | None |
| confidence | decimal | YES | | None |
| strategy | varchar | YES | | None |
| raw_payload | json | YES | | None |
| signal_timestamp | datetime | NO | MUL | None |
| recorded_at | datetime | YES | | None |
| dedup_hash | char | YES | UNI | None |
| was_stale | tinyint | YES | | None |
| was_banned | tinyint | YES | | None |
| was_demoted | tinyint | YES | | None |
| was_wr_suppressed | tinyint | YES | | None |
| status | enum | YES | MUL | None |
| exit_price | decimal | YES | | None |
| exit_reason | varchar | YES | | None |
| pnl_pct | decimal | YES | | None |
| closed_at | datetime | YES | | None |

**Purpose:** Raw picks from 60+ source systems before consensus/filtering.

**Data Quality:**
- **Rows:** 121,857
- **Date Range:** 2024 to 2026-05-08
- **Asset Classes:** CRYPTO (101,729), EQUITY (13,548), FOREX (7,469), UNKNOWN (4,326), MEMECOIN (3,155), FUTURES (2,508), PENNY_STOCK (707), ETF (152)
- **Top Source Systems:** incubator_gainer (21,351), AlphaEngine (13,498), quan_engine (13,260), alpha_engine (12,641), Predictions (12,539)
- **Deduplication:** Unique dedup_hash constraint

**Related Tables:** `at_aggregation_runs`, `at_consensus_picks`, `at_filter_log`

---

### `bt_backtest_trades` - Backtest Trade History

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| backtest_run_id | int | YES | MUL | None |
| source_db | varchar | YES | | None |
| source_table | varchar | YES | | None |
| symbol | varchar | YES | MUL | None |
| asset_class | varchar | YES | | None |
| direction | varchar | YES | | None |
| strategy | varchar | YES | MUL | None |
| entry_price | decimal | NO | | None |
| exit_price | decimal | YES | | None |
| ... | | | | |

**Purpose:** Massive historical backtest trade repository (1.3M+ trades).

**Data Quality:**
- **Rows:** 1,312,509
- **Storage:** 1.5 GB (largest table)
- **Top Strategies:** coinglass_strategies (5.4M), signal_recorder (3.3M), FearGreedReversal (2.2M)
- **Foreign Key:** backtest_run_id -> bt_backtest_runs.id

**Related Tables:** `bt_backtest_runs`

---

### `rapid_signals` - Rapid Signal Generation

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| signal_id | int | NO | PRI | auto |
| symbol | varchar | NO | MUL | None |
| direction | varchar | NO | | None |
| strategy | varchar | NO | | None |
| ... | | | | |

**Purpose:** Fast signal generation layer with high throughput.

**Data Quality:**
- **Rows:** 11,709

---

### `lm_signals` - Learning Machine Signals

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| signal_type | enum | NO | MUL | None |
| symbol | varchar | NO | MUL | None |
| ... | | | | |

**Purpose:** ML-processed signals with intelligent meta-labeling.

**Data Quality:**
- **Rows:** 33,557
- **Storage Engine:** MyISAM

---

### `goldmine_cursor_predictions` - AI Prediction Engine

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| prediction_id | char | NO | | None |
| asset_class | varchar | NO | | None |
| ticker | varchar | NO | MUL | None |
| algorithm | varchar | NO | | None |
| direction | varchar | NO | | None |
| entry_price | decimal | NO | | None |
| target_price | decimal | NO | | None |
| stop_loss | decimal | NO | | None |
| confidence_score | int | YES | | None |
| ... | | | | |

**Purpose:** Goldmine Cursor AI prediction outputs with position management.

**Data Quality:**
- **Rows:** 478
- **Asset Classes:** stocks, crypto

---

### `ml_feature_store` - ML Feature Vectors

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| pair | varchar | NO | MUL | None |
| asset_class | varchar | NO | | None |
| timestamp | datetime | NO | MUL | None |
| timeframe | varchar | NO | | None |
| close_price | double | YES | | None |
| return_1, return_5, return_20 | double | YES | | None |
| rsi_14, macd_value, macd_signal | double | YES | | None |
| stoch_k, stoch_d, williams_r | double | YES | | None |
| sma_20, sma_50, ema_9, ema_21 | double | YES | | None |
| adx_14, atr_14, bollinger_* | double | YES | | None |
| realized_vol_20, volume_sma_20 | double | YES | | None |
| hurst_exponent, autocorrelation_1 | double | YES | | None |
| engines_bullish, engines_bearish | int | YES | | None |
| target_1h, target_4h, target_24h | double | YES | | None |
| target_direction | varchar | YES | | None |

**Purpose:** Pre-computed ML feature vectors with 40+ technical indicators per instrument/timeframe combination.

**Data Quality:**
- **Rows:** 396
- **Features:** 40+ technical indicators plus target variables
- **Timeframes:** 4H primary
- **Asset Classes:** CRYPTO primary

---

### `stock_fundamentals` - Fundamental Financial Data

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| ticker | varchar | NO | MUL | None |
| trailing_eps | decimal | YES | | None |
| forward_eps | decimal | YES | | None |
| trailing_pe | decimal | YES | | None |
| forward_pe | decimal | YES | | None |
| peg_ratio | decimal | YES | | None |
| dividend_rate | decimal | YES | | None |
| dividend_yield | decimal | YES | | None |
| ... | | | | |

**Purpose:** Fundamental metrics from Yahoo Finance for stock analysis.

**Data Quality:**
- **Rows:** 119
- **Source:** yahoo_v10

**Related Tables:** `stocks`, `stock_earnings`, `stock_dividends`

---

### `portfolio_snapshots` - Portfolio Performance

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| portfolio_id | varchar | NO | | None |
| portfolio_name | varchar | YES | | None |
| methodology | varchar | YES | | None |
| category | varchar | YES | | None |
| status | enum | YES | | None |
| equity | decimal | YES | | None |
| initial_capital | decimal | YES | | None |
| pnl_pct | decimal | YES | | None |
| win_rate | decimal | YES | | None |
| total_trades | int | YES | | None |
| max_drawdown_pct | decimal | YES | | None |
| sharpe_ratio | decimal | YES | | None |

**Purpose:** Portfolio performance tracking with risk metrics.

**Data Quality:**
- **Rows:** 26
- **Portfolios:** Score Leaders, Proven Only, Momentum Riders, etc.

---

### `crypto_assets` - Crypto Asset Registry

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| symbol | varchar | NO | UNI | None |
| name | varchar | NO | | None |
| category | varchar | YES | | None |
| tier | varchar | YES | | None |
| ... | | | | |

**Purpose:** Registry of tracked crypto assets.

**Data Quality:**
- **Rows:** 14
- **Assets:** BTC, ETH, BNB, etc.

---

### `stock_earnings` - Earnings Data

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| ticker | varchar | NO | MUL | None |
| quarter_end | date | NO | | None |
| eps_actual | decimal | YES | | None |
| eps_estimate | decimal | YES | | None |
| eps_surprise | decimal | YES | | None |
| surprise_pct | decimal | YES | | None |
| source | varchar | YES | | None |

**Purpose:** Quarterly earnings with surprise analysis.

**Data Quality:**
- **Rows:** 381
- **Source:** yahoo_v10

---

### `stock_dividends` - Dividend History

**Schema:**
| Column | Type | Nullable | Key | Default |
|--------|------|----------|-----|---------|
| id | int | NO | PRI | auto |
| ticker | varchar | NO | MUL | None |
| ex_date | date | NO | | None |
| amount | decimal | NO | | None |
| frequency | varchar | YES | | None |

**Purpose:** Historical dividend payments with frequency tracking.

**Data Quality:**
- **Rows:** 831

---

## Key Relationships

```
stocks (153 tickers)
    ├── daily_prices (49,340 rows) - ticker FK
    ├── stock_picks (7,239 rows) - ticker + algorithm_id FK
    ├── alpha_picks (5,043 rows) - ticker FK
    ├── alpha_factor_scores (2,860 rows) - ticker FK
    ├── stock_fundamentals (119 rows) - ticker FK
    ├── stock_earnings (381 rows) - ticker FK
    └── stock_dividends (831 rows) - ticker FK

algorithms (142 algos)
    └── stock_picks - algorithm_id FK

at_aggregation_runs (1,847 runs)
    ├── at_raw_picks (121,857 rows) - aggregation_run_id FK
    └── at_consensus_picks (5,176 rows) - aggregation_run_id FK

bt_backtest_runs (285 runs)
    └── bt_backtest_trades (1,312,509 rows) - backtest_run_id FK

sp_batches
    └── sp_picks - batch_id FK

KIMI_GOLDMINE_PICKS
    └── KIMI_GOLDMINE_WINNERS - pick_uuid FK

trading_picks (live execution)
    └── References at_raw_picks (signal aggregation)
    └── References lm_signals (ML processing)
    └── References rapid_signals (signal generation)
```

## Data Flow Architecture

```
Multiple Signal Sources (60+)
    │  incubator_gainer, AlphaEngine, quan_engine, alpha_engine,
    │  Predictions, ml_crypto_pred, smart_money, battleground, ...
    ▼
at_raw_picks (aggregation layer)
    │  Deduplication, filtering, stale/banned/demoted flagging
    ▼
at_aggregation_runs (run orchestration)
    │
    ├──> at_consensus_picks (multi-system consensus)
    ├──> at_filter_log (filter audit trail)
    ├──> at_audit_events (pipeline events)
    └──> lm_signals (ML intelligence layer)
            │
            ├──> goldmine_cursor_predictions (AI predictions)
            ├──> rapid_signals (fast signals)
            ├──> trading_picks (live execution)
            └──> portfolio_snapshots (portfolio tracking)

Price Data:
    daily_prices ──> stock_picks, alpha_picks, backtest_trades
    crypto_ohlcv ──> crypto_signals, crypto_indicators
    fx_prices ──> fx_signals, fx_pairs

Fundamental Data:
    stock_fundamentals ──> alpha_factor_scores ──> alpha_picks
    stock_earnings ──> earnings strategies
    stock_dividends ──> dividend strategies

Backtest:
    bt_backtest_runs ──> bt_backtest_trades (1.3M+ trades)
```

---

## Key Insights

### 1. Multi-Asset Trading Platform
The database supports stocks, crypto, forex, futures, ETFs, and memecoins through a unified pipeline. ~77% of raw picks are crypto-related, with significant forex (7,469) and equity (13,548) activity.

### 2. Sophisticated Algorithm Ecosystem
142 algorithms across 40+ families including:
- **Academic research factors** (16 variants): BAB, QMJ, Piotroski F-Score, etc.
- **Technical strategies**: Momentum, breakout, mean reversion
- **Alternative data**: Insider flow, congressional trades, dark pool, ESG
- **ML/AI ensemble**: Meta-learners, ensemble arbitrators
- **Event-driven**: Merger arb, spin-offs, earnings drift

### 3. Signal Aggregation Pipeline
A multi-stage pipeline processes raw signals:
- 60+ source systems generate raw picks
- Aggregation runs consolidate signals
- Deduplication via hash-based uniqueness
- Filtering with stale/banned/demoted flagging
- ML intelligence layer (lm_signals) for meta-processing
- Consensus picks from multi-algorithm agreement

### 4. Prediction Market & Copy Trading Integration
Unique features include:
- Polymarket whale tracking (1,856 picks)
- Prediction market agents (1,920 picks)
- Multi-asset copy trading (28,918 picks from copytrader)
- CTA replication (7,866 picks)

### 5. Sports Betting Component
The `lm_sports_*` tables (~30 tables) indicate an integrated sports betting ML system with:
- Daily picks, odds tracking, bankroll management
- ML predictions for NBA, NFL, NHL, MLB
- Value bet detection and closing line value (CLV) analysis

### 6. Data Freshness
- **Daily prices:** Current through 2026-04-29
- **Trading picks:** Active through 2026-05-08
- **Alpha picks:** Current through 2026-04-27
- **Fundamentals:** Updated 2026-04-27
- System appears actively maintained with current data

### 7. Empty Tables (102 of 322)
Over 100 tables are completely empty, suggesting:
- Features under development
- Deprecated subsystems
- Seasonal/temporary tables
- Placeholder schemas for future modules

---

## Prediction-Related Tables Identified

### Core Prediction/Signal Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `alpha_picks` | 5,043 | Alpha factor model predictions |
| `rapid_signals` | 11,709 | Fast signal generation |
| `lm_signals` | 33,557 | ML-processed signals |
| `goldmine_cursor_predictions` | 478 | AI prediction engine |
| `ua_predictions` | 355 | Unauthenticated predictions |
| `at_raw_picks` | 121,857 | Raw pre-consensus predictions |
| `at_consensus_picks` | 5,176 | Multi-algorithm consensus picks |
| `at_signal_outcomes` | 121 | Signal outcome tracking |
| `crypto_signals` | 0 | Crypto-specific signals |
| `stock_signals` | 0 | Stock signal registry |

### Backtest & Simulation Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `bt_backtest_trades` | 1,312,509 | Historical backtest trades |
| `bt_backtest_runs` | 285 | Backtest run definitions |
| `backtest_results` | 2 | Backtest summary results |
| `backtest_trades` | 50 | Current backtest trades |
| `simulation_grid` | 6,000 | Parameter sweep simulations |
| `simulation_meta` | 3 | Simulation metadata |
| `at_incubator_backtest_results` | 1,210 | Strategy incubator backtests |
| `at_large_backtest_results` | 1,061 | Large-scale backtests |
| `whatif_scenarios` | 114 | What-if analysis scenarios |
| `cr_whatif_scenarios` | 3 | Crypto what-if scenarios |
| `fx_whatif_scenarios` | 0 | Forex what-if scenarios |
| `fxp_whatif_scenarios` | 3 | Forex portfolio what-if |
| `strategy_whatif_results` | 0 | Strategy what-if results |

### ML/Model Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `ml_feature_store` | 396 | ML feature vectors |
| `ml_model_registry` | 0 | Model registry |
| `ml_models` | 0 | Trained models |
| `ml_model_performance` | 0 | Model performance tracking |
| `ml_learning_curve` | 14 | Learning curve data |
| `ml_ensemble_weights` | 0 | Ensemble weights |
| `ml_platform_daily` | 3 | ML platform metrics |
| `ml_regime_snapshots` | 3 | Regime detection snapshots |
| `ml_calibration_log` | 0 | Prediction calibration |
| `ml_ab_tests` | 0 | A/B test results |
| `meme_ml_models` | 0 | Meme coin ML models |
| `meme_ml_predictions` | 0 | Meme coin predictions |
| `meme_ml_signals` | 50 | Meme coin ML signals |

### Forecast & Ensemble Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `consensus_tracked` | 318 | Consensus position tracking |
| `consensus_lessons` | 348 | Consensus learning records |
| `consensus_performance_daily` | 62 | Daily consensus performance |
| `lm_smart_consensus` | 552 | Smart consensus engine |
| `at_permutation_picks` | 1,514 | Permutation-based picks |
| `at_permutation_snapshots` | 28 | Permutation snapshots |
| `walk_forward_results` | 0 | Walk-forward analysis |
| `walk_forward_summary` | 10 | Walk-forward summaries |

### Prediction Market & Advanced Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `gm_unified_picks` | 1,846 | Goldmine unified predictions |
| `gm_sec_13f_holdings` | 2,084 | SEC 13F institutional holdings |
| `gm_sec_insider_trades` | 714 | SEC insider trading data |
| `gm_news_sentiment` | 140 | News sentiment scores |
| `goldmine_cursor_algo_scorecard` | 0 | Algorithm scorecards |
| `goldmine_cursor_predictions` | 478 | Cursor AI predictions |
| `goldmine_cursor_regime_log` | 0 | Market regime log |
| `goldmine_cursor_data_health` | 9 | Data health monitoring |

### Sports Prediction Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `lm_sports_daily_picks` | 222 | Daily sports picks |
| `lm_sports_ml_predictions` | 79 | Sports ML predictions |
| `lm_sports_odds` | 502 | Odds tracking |
| `lm_sports_value_bets` | 375 | Value bet identification |
| `lm_sports_bets` | 74 | Placed bets tracking |
| `lm_sports_clv` | 20,607 | Closing line value analysis |
| `lm_sports_bankroll` | 15 | Bankroll management |
| `lm_sports_ml_metrics` | 0 | Sports ML metrics |

---

## Database Assessment Summary

| Aspect | Assessment |
|--------|------------|
| **Overall Health** | Good - actively maintained with current data |
| **Data Freshness** | Current through May 2026 |
| **Data Consistency** | Good - FK constraints, unique hashes, no NULL prices |
| **Empty Tables** | 102/322 (32%) - many appear to be placeholders |
| **Largest Table** | bt_backtest_trades (1.3M rows, 1.5GB) |
| **Most Active Module** | Signal aggregation (at_* tables) |
| **Key Strength** | Multi-asset, multi-algorithm, ML-enhanced pipeline |
| **Key Gap** | Many empty tables indicate incomplete features |
| **Security** | Pick dedup hashes prevent duplicates |
| **Audit Trail** | Comprehensive (at_audit_events, at_filter_log, audit_log) |


---

## Appendix A: Complete Table List

| # | Table | Est. Rows | Engine |
|---|-------|-----------|--------|
| 1 | `bt_backtest_trades` | 1312509 | InnoDB |
| 2 | `at_filter_log` | 505080 | InnoDB |
| 3 | `at_raw_picks` | 121857 | InnoDB |
| 4 | `daily_prices` | 49340 | MyISAM |
| 5 | `lm_signals` | 33557 | MyISAM |
| 6 | `at_audit_events` | 27602 | InnoDB |
| 7 | `trading_picks` | 24644 | InnoDB |
| 8 | `now_history` | 23859 | InnoDB |
| 9 | `lm_sports_clv` | 20607 | MyISAM |
| 10 | `rapid_signals` | 11709 | InnoDB |
| 11 | `at_discord_gate_log` | 10640 | InnoDB |
| 12 | `stock_picks` | 7239 | MyISAM |
| 13 | `mf2_nav_history` | 6860 | MyISAM |
| 14 | `simulation_grid` | 6000 | MyISAM |
| 15 | `audit_log` | 5937 | MyISAM |
| 16 | `at_consensus_picks` | 5176 | InnoDB |
| 17 | `alpha_picks` | 5043 | MyISAM |
| 18 | `mf_nav_history` | 5000 | MyISAM |
| 19 | `cp_prices` | 4857 | MyISAM |
| 20 | `at_discord_notifications` | 4637 | InnoDB |
| 21 | `cr_price_history` | 4529 | MyISAM |
| 22 | `fx_prices` | 3855 | MyISAM |
| 23 | `algorithm_rolling_perf` | 3536 | MyISAM |
| 24 | `alpha_fundamentals` | 2964 | MyISAM |
| 25 | `alpha_factor_scores` | 2860 | MyISAM |
| 26 | `fxp_price_history` | 2658 | MyISAM |
| 27 | `at_local_picks` | 2103 | InnoDB |
| 28 | `lm_snapshots` | 2096 | MyISAM |
| 29 | `gm_sec_13f_holdings` | 2084 | MyISAM |
| 30 | `at_aggregation_runs` | 1847 | InnoDB |
| 31 | `gm_unified_picks` | 1846 | MyISAM |
| 32 | `kelly_sizing_log` | 1702 | MyISAM |
| 33 | `at_permutation_picks` | 1514 | InnoDB |
| 34 | `lm_position_sizing` | 1409 | MyISAM |
| 35 | `at_discord_sent` | 1305 | InnoDB |
| 36 | `at_incubator_backtest_results` | 1210 | InnoDB |
| 37 | `strategy_registry` | 1187 | InnoDB |
| 38 | `fxp_pair_picks` | 1184 | MyISAM |
| 39 | `at_large_backtest_results` | 1061 | InnoDB |
| 40 | `penny_picks` | 1029 | MyISAM |
| 41 | `cr_pair_picks` | 952 | MyISAM |
| 42 | `daytrader_sim_trades` | 838 | MyISAM |
| 43 | `stock_dividends` | 831 | MyISAM |
| 44 | `alpha_refresh_log` | 731 | MyISAM |
| 45 | `gm_sec_insider_trades` | 714 | MyISAM |
| 46 | `audit_trails` | 684 | MyISAM |
| 47 | `ps_history` | 684 | MyISAM |
| 48 | `cw_scan_log` | 666 | MyISAM |
| 49 | `miracle_audit2` | 659 | MyISAM |
| 50 | `miracle_picks3` | 644 | MyISAM |
| 51 | `challenge_200_trades` | 620 | MyISAM |
| 52 | `mf2_fund_picks` | 600 | MyISAM |
| 53 | `fx_signals` | 585 | MyISAM |
| 54 | `market_regimes` | 560 | MyISAM |
| 55 | `lm_smart_consensus` | 552 | MyISAM |
| 56 | `lm_sports_odds` | 502 | MyISAM |
| 57 | `goldmine_cursor_predictions` | 478 | MyISAM |
| 58 | `mf2_backtest_trades` | 450 | MyISAM |
| 59 | `gm_failure_alerts` | 414 | MyISAM |
| 60 | `miracle_audit3` | 412 | MyISAM |
| 61 | `at_strategy_symbol_performance` | 410 | InnoDB |
| 62 | `miracle_learning3` | 410 | MyISAM |
| 63 | `ml_feature_store` | 396 | MyISAM |
| 64 | `cr_audit_log` | 393 | MyISAM |
| 65 | `stock_earnings` | 381 | MyISAM |
| 66 | `fxp_audit_log` | 380 | MyISAM |
| 67 | `lm_sports_value_bets` | 375 | MyISAM |
| 68 | `ua_predictions` | 355 | MyISAM |
| 69 | `consensus_lessons` | 348 | MyISAM |
| 70 | `cw_winners` | 342 | MyISAM |
| 71 | `mf2_audit_log` | 328 | MyISAM |
| 72 | `consensus_tracked` | 318 | MyISAM |
| 73 | `at_raw_picks_anomaly_log` | 304 | InnoDB |
| 74 | `bt_backtest_runs` | 285 | InnoDB |
| 75 | `gm_system_health` | 272 | MyISAM |
| 76 | `mf_audit_log` | 260 | MyISAM |
| 77 | `miracle_picks2` | 249 | MyISAM |
| 78 | `alpha_earnings` | 242 | MyISAM |
| 79 | `lm_sports_daily_picks` | 222 | MyISAM |
| 80 | `lm_market_regime` | 213 | MyISAM |
| 81 | `lm_trades` | 200 | MyISAM |
| 82 | `lm_hour_learning` | 195 | MyISAM |
| 83 | `alpha_macro` | 181 | MyISAM |
| 84 | `daytrader_sim_days` | 176 | MyISAM |
| 85 | `at_incubator_strategies` | 174 | InnoDB |
| 86 | `cp_signals` | 174 | MyISAM |
| 87 | `lm_intelligence` | 169 | MyISAM |
| 88 | `eh_grade_history` | 168 | MyISAM |
| 89 | `stocks` | 153 | MyISAM |
| 90 | `algorithms` | 142 | MyISAM |
| 91 | `gm_news_sentiment` | 140 | MyISAM |
| 92 | `miracle_results2` | 140 | MyISAM |
| 93 | `lm_breaker_log` | 133 | MyISAM |
| 94 | `lm_sports_credit_usage` | 132 | MyISAM |
| 95 | `challenge_200_days` | 124 | MyISAM |
| 96 | `at_signal_outcomes` | 121 | InnoDB |
| 97 | `stock_fundamentals` | 119 | MyISAM |
| 98 | `whatif_scenarios` | 114 | MyISAM |
| 99 | `fx_audit_log` | 89 | MyISAM |
| 100 | `lm_analyst_ratings` | 84 | MyISAM |
| 101 | `ss_baselines` | 82 | MyISAM |
| 102 | `lm_sports_ml_predictions` | 79 | MyISAM |
| 103 | `miracle_results3` | 78 | MyISAM |
| 104 | `mf2_tracked_picks` | 75 | MyISAM |
| 105 | `lm_sports_bets` | 74 | MyISAM |
| 106 | `miracle_watchlist2` | 68 | MyISAM |
| 107 | `lm_price_cache` | 66 | MyISAM |
| 108 | `consensus_performance_daily` | 62 | MyISAM |
| 109 | `pf_challenge_positions` | 62 | InnoDB |
| 110 | `miracle_watchlist3` | 56 | MyISAM |
| 111 | `penny_picks_daily` | 54 | MyISAM |
| 112 | `strategy_health` | 54 | InnoDB |
| 113 | `alpha_universe` | 52 | MyISAM |
| 114 | `pf_pair_patterns` | 51 | MyISAM |
| 115 | `strategy_test_runs` | 51 | InnoDB |
| 116 | `backtest_trades` | 50 | MyISAM |
| 117 | `meme_ml_signals` | 50 | MyISAM |
| 118 | `meme_signal_results` | 50 | MyISAM |
| 119 | `meme_signals` | 50 | MyISAM |
| 120 | `pf_fingerprints` | 47 | MyISAM |
| 121 | `lm_challenger_showdown` | 46 | MyISAM |
| 122 | `portfolios` | 39 | MyISAM |
| 123 | `ps_scores` | 36 | MyISAM |
| 124 | `mf_selections` | 34 | MyISAM |
| 125 | `strategy_symbol_coverage` | 34 | InnoDB |
| 126 | `lm_nba_team_stats` | 30 | InnoDB |
| 127 | `at_permutation_snapshots` | 28 | InnoDB |
| 128 | `lm_algo_health` | 28 | MyISAM |
| 129 | `portfolio_snapshots` | 26 | InnoDB |
| 130 | `super_strategy_candidates` | 26 | InnoDB |
| 131 | `algorithm_performance` | 23 | MyISAM |
| 132 | `crypto_exchange_netflow` | 20 | MyISAM |
| 133 | `mf_funds` | 20 | MyISAM |
| 134 | `cp_audit_log` | 19 | MyISAM |
| 135 | `now_strategy_stats` | 17 | InnoDB |
| 136 | `fx_pair_picks` | 16 | MyISAM |
| 137 | `cp_pairs` | 15 | MyISAM |
| 138 | `fx_pairs` | 15 | MyISAM |
| 139 | `lm_discovered_movers` | 15 | MyISAM |
| 140 | `lm_ml_status` | 15 | InnoDB |
| 141 | `lm_sports_bankroll` | 15 | MyISAM |
| 142 | `mf2_funds` | 15 | MyISAM |
| 143 | `mf_fund_picks` | 15 | MyISAM |
| 144 | `KIMI_GOLDMINE_SOURCES` | 14 | InnoDB |
| 145 | `crypto_assets` | 14 | InnoDB |
| 146 | `lm_nba_games_today` | 14 | InnoDB |
| 147 | `ml_learning_curve` | 14 | MyISAM |
| 148 | `eh_alerts` | 13 | MyISAM |
| 149 | `eh_engine_grades` | 12 | MyISAM |
| 150 | `lm_bridge_options` | 12 | MyISAM |
| 151 | `lm_conviction_history` | 12 | MyISAM |
| 152 | `lm_conviction_performance` | 12 | MyISAM |
| 153 | `lm_multi_dimensional` | 12 | MyISAM |
| 154 | `lm_price_targets` | 12 | MyISAM |
| 155 | `lm_wsb_sentiment` | 12 | MyISAM |
| 156 | `mf2_portfolios` | 12 | MyISAM |
| 157 | `cp_strategies` | 10 | MyISAM |
| 158 | `cr_pairs` | 10 | MyISAM |
| 159 | `cr_portfolios` | 10 | MyISAM |
| 160 | `fx_portfolios` | 10 | MyISAM |
| 161 | `fxp_portfolios` | 10 | MyISAM |
| 162 | `lm_bridge_onchain` | 10 | MyISAM |
| 163 | `lm_insider_sentiment` | 10 | MyISAM |
| 164 | `mf2_algo_performance` | 10 | MyISAM |
| 165 | `mf2_algorithms` | 10 | MyISAM |
| 166 | `mf2_backtest_results` | 10 | MyISAM |
| 167 | `mf_algo_performance` | 10 | MyISAM |
| 168 | `mf_algorithms` | 10 | MyISAM |
| 169 | `mf_strategies` | 10 | MyISAM |
| 170 | `walk_forward_summary` | 10 | MyISAM |
| 171 | `goldmine_cursor_data_health` | 9 | MyISAM |
| 172 | `lm_conviction_stats` | 9 | MyISAM |
| 173 | `lm_kelly_fractions` | 9 | MyISAM |
| 174 | `mf2_tracking_lessons` | 9 | MyISAM |
| 175 | `cr_algo_performance` | 8 | MyISAM |
| 176 | `cr_algorithms` | 8 | MyISAM |
| 177 | `fx_algo_performance` | 8 | MyISAM |
| 178 | `fx_algorithms` | 8 | MyISAM |
| 179 | `fx_strategies` | 8 | MyISAM |
| 180 | `fxp_algo_performance` | 8 | MyISAM |
| 181 | `fxp_algorithms` | 8 | MyISAM |
| 182 | `fxp_pairs` | 8 | MyISAM |
| 183 | `lm_alert_configs` | 8 | MyISAM |
| 184 | `mf_portfolios` | 8 | MyISAM |
| 185 | `mf_whatif_scenarios` | 8 | MyISAM |
| 186 | `miracle_portfolios2` | 8 | MyISAM |
| 187 | `miracle_strategies2` | 8 | MyISAM |
| 188 | `miracle_strategies3` | 8 | MyISAM |
| 189 | `goldmine_cursor_algo_scorecard` | 7 | MyISAM |
| 190 | `lm_quant_bridge` | 6 | MyISAM |
| 191 | `mc_scan_log` | 6 | MyISAM |
| 192 | `miracle_portfolios3` | 6 | MyISAM |
| 193 | `at_futures_symbol_edge` | 4 | InnoDB |
| 194 | `lm_injury_intel_cache` | 4 | MyISAM |
| 195 | `lm_meta_labeler` | 4 | MyISAM |
| 196 | `lm_opportunities` | 4 | MyISAM |
| 197 | `stock_analyst_recs` | 4 | MyISAM |
| 198 | `cr_whatif_scenarios` | 3 | MyISAM |
| 199 | `fxp_whatif_scenarios` | 3 | MyISAM |
| 200 | `lm_conviction_alerts` | 3 | MyISAM |
| 201 | `lm_fear_greed` | 3 | MyISAM |
| 202 | `lm_schedule_intel_cache` | 3 | MyISAM |
| 203 | `lm_scraped_data` | 3 | MyISAM |
| 204 | `mf2_tracking_daily` | 3 | MyISAM |
| 205 | `ml_platform_daily` | 3 | MyISAM |
| 206 | `ml_regime_snapshots` | 3 | MyISAM |
| 207 | `report_cache` | 3 | MyISAM |
| 208 | `simulation_meta` | 3 | MyISAM |
| 209 | `backtest_results` | 2 | MyISAM |
| 210 | `lm_algo_performance` | 2 | InnoDB |
| 211 | `mf2_whatif_scenarios` | 2 | MyISAM |
| 212 | `mf_report_cache` | 2 | MyISAM |
| 213 | `alpha_status` | 1 | MyISAM |
| 214 | `lm_bridge_cusum` | 1 | MyISAM |
| 215 | `lm_mlb_stats_cache` | 1 | MyISAM |
| 216 | `lm_nba_stats_cache` | 1 | MyISAM |
| 217 | `lm_nfl_stats_cache` | 1 | MyISAM |
| 218 | `lm_nhl_stats_cache` | 1 | MyISAM |
| 219 | `lm_webhook_config` | 1 | MyISAM |
| 220 | `mc_daily_snapshots` | 1 | MyISAM |
| 221 | `KIMI_GOLDMINE_ALERTS` | 0 | InnoDB |
| 222 | `KIMI_GOLDMINE_DAILY_SNAPSHOT` | 0 | InnoDB |
| 223 | `KIMI_GOLDMINE_PERFORMANCE` | 0 | InnoDB |
| 224 | `KIMI_GOLDMINE_PICKS` | 0 | InnoDB |
| 225 | `KIMI_GOLDMINE_WINNERS` | 0 | InnoDB |
| 226 | `at_discord_gate_state` | 0 | InnoDB |
| 227 | `at_sqlite_imports` | 0 | InnoDB |
| 228 | `at_strategy_stats` | 0 | InnoDB |
| 229 | `circuit_breaker_log` | 0 | MyISAM |
| 230 | `consensus_history` | 0 | MyISAM |
| 231 | `consolidated_cache` | 0 | MyISAM |
| 232 | `cp_backtest_results` | 0 | MyISAM |
| 233 | `cp_report_cache` | 0 | MyISAM |
| 234 | `cr_backtest_results` | 0 | MyISAM |
| 235 | `cr_backtest_trades` | 0 | MyISAM |
| 236 | `cr_category_perf` | 0 | MyISAM |
| 237 | `cr_comparisons` | 0 | MyISAM |
| 238 | `crypto_indicators` | 0 | InnoDB |
| 239 | `crypto_ohlcv` | 0 | InnoDB |
| 240 | `crypto_patterns` | 0 | InnoDB |
| 241 | `crypto_signals` | 0 | InnoDB |
| 242 | `crypto_whale_movements` | 0 | MyISAM |
| 243 | `crypto_whale_wallets` | 0 | MyISAM |
| 244 | `fx_backtest_results` | 0 | MyISAM |
| 245 | `fx_backtest_trades` | 0 | MyISAM |
| 246 | `fx_category_perf` | 0 | MyISAM |
| 247 | `fx_comparisons` | 0 | MyISAM |
| 248 | `fx_price_history` | 0 | MyISAM |
| 249 | `fx_report_cache` | 0 | MyISAM |
| 250 | `fx_whatif_scenarios` | 0 | MyISAM |
| 251 | `fxp_backtest_results` | 0 | MyISAM |
| 252 | `fxp_backtest_trades` | 0 | MyISAM |
| 253 | `fxp_category_perf` | 0 | MyISAM |
| 254 | `fxp_comparisons` | 0 | MyISAM |
| 255 | `goldmine_cursor_benchmarks` | 0 | MyISAM |
| 256 | `goldmine_cursor_circuit_breaker` | 0 | MyISAM |
| 257 | `goldmine_cursor_correlation_matrix` | 0 | MyISAM |
| 258 | `goldmine_cursor_regime_log` | 0 | MyISAM |
| 259 | `lm_bridge_congress` | 0 | MyISAM |
| 260 | `lm_bridge_entropy` | 0 | MyISAM |
| 261 | `lm_bridge_portfolio` | 0 | MyISAM |
| 262 | `lm_bridge_sentiment` | 0 | MyISAM |
| 263 | `lm_cross_correlation` | 0 | InnoDB |
| 264 | `lm_daily_price_history` | 0 | MyISAM |
| 265 | `lm_ensemble_weights` | 0 | InnoDB |
| 266 | `lm_feature_importance` | 0 | InnoDB |
| 267 | `lm_guru_picks` | 0 | MyISAM |
| 268 | `lm_guru_tracker` | 0 | MyISAM |
| 269 | `lm_meta_labels` | 0 | MyISAM |
| 270 | `lm_model_versions` | 0 | InnoDB |
| 271 | `lm_picks_bridge` | 0 | InnoDB |
| 272 | `lm_prediction_calibration` | 0 | InnoDB |
| 273 | `lm_signal_performance` | 0 | MyISAM |
| 274 | `lm_sports_ml_metrics` | 0 | MyISAM |
| 275 | `lm_supplemental_dimensions` | 0 | MyISAM |
| 276 | `lm_virtual_comparison` | 0 | InnoDB |
| 277 | `lm_walk_forward` | 0 | InnoDB |
| 278 | `mc_winners` | 0 | MyISAM |
| 279 | `meme_ml_models` | 0 | MyISAM |
| 280 | `meme_ml_predictions` | 0 | MyISAM |
| 281 | `mf2_category_perf` | 0 | MyISAM |
| 282 | `mf2_comparisons` | 0 | MyISAM |
| 283 | `mf_backtest_results` | 0 | MyISAM |
| 284 | `mf_backtest_trades` | 0 | MyISAM |
| 285 | `mf_benchmarks` | 0 | MyISAM |
| 286 | `mf_category_perf` | 0 | MyISAM |
| 287 | `mf_comparisons` | 0 | MyISAM |
| 288 | `mf_simulation_grid` | 0 | MyISAM |
| 289 | `mf_simulation_meta` | 0 | MyISAM |
| 290 | `ml_ab_tests` | 0 | MyISAM |
| 291 | `ml_calibration_log` | 0 | MyISAM |
| 292 | `ml_ensemble_weights` | 0 | MyISAM |
| 293 | `ml_model_performance` | 0 | InnoDB |
| 294 | `ml_model_registry` | 0 | MyISAM |
| 295 | `ml_models` | 0 | InnoDB |
| 296 | `paper_portfolio_daily` | 0 | MyISAM |
| 297 | `paper_trades` | 0 | MyISAM |
| 298 | `penny_stocks` | 0 | InnoDB |
| 299 | `pf_alerts` | 0 | MyISAM |
| 300 | `portfolio_comparisons` | 0 | MyISAM |
| 301 | `portfolio_daily_equity` | 0 | MyISAM |
| 302 | `portfolio_positions` | 0 | MyISAM |
| 303 | `portfolio_resets` | 0 | InnoDB |
| 304 | `portfolio_strategy_stats` | 0 | InnoDB |
| 305 | `saved_portfolios` | 0 | MyISAM |
| 306 | `social_influencers` | 0 | MyISAM |
| 307 | `social_sentiment` | 0 | MyISAM |
| 308 | `sp_batches` | 0 | InnoDB |
| 309 | `sp_daily_performance` | 0 | InnoDB |
| 310 | `sp_picks` | 0 | InnoDB |
| 311 | `ss_spikes` | 0 | MyISAM |
| 312 | `stock_assets` | 0 | InnoDB |
| 313 | `stock_ohlcv` | 0 | InnoDB |
| 314 | `stock_signals` | 0 | InnoDB |
| 315 | `strategy_health_audit` | 0 | InnoDB |
| 316 | `strategy_status_history` | 0 | InnoDB |
| 317 | `strategy_whatif_results` | 0 | InnoDB |
| 318 | `test_portfolio_positions` | 0 | InnoDB |
| 319 | `tracked_portfolio_picks` | 0 | InnoDB |
| 320 | `tracked_portfolios` | 0 | InnoDB |
| 321 | `ua_engine_stats` | 0 | MyISAM |
| 322 | `walk_forward_results` | 0 | MyISAM |
