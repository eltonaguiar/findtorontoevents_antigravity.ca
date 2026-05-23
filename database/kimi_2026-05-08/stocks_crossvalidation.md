# Cross-Validation Report: ejaguiar1_stocks Database
## Generated: 2026-05-08

---

## 1. REFERENTIAL INTEGRITY CHECKS

### 1.1 daily_prices -> stocks
| Metric | Value |
|--------|-------|
| Orphan tickers | **0** |
| Orphan rows | **0** |
| Total distinct tickers in daily_prices | 153 |
| Total tickers in stocks | 153 |
| **Result** | **PASS** - All tickers in daily_prices exist in stocks table |

### 1.2 stock_picks -> stocks
| Metric | Value |
|--------|-------|
| Orphan tickers | **0** |
| Orphan rows | **0** |
| Total distinct tickers in stock_picks | 134 |
| **Result** | **PASS** - All tickers in stock_picks exist in stocks table |

### 1.3 alpha_picks -> stocks
| Metric | Value |
|--------|-------|
| Orphan tickers | **0** |
| Orphan rows | **0** |
| Total distinct tickers in alpha_picks | 48 |
| **Result** | **PASS** - All tickers in alpha_picks exist in stocks table |

### 1.4 stock_picks -> algorithms
| Metric | Value |
|--------|-------|
| Orphan algorithm_ids | **1** |
| Orphan rows | **63** |
| Distinct algorithm_ids in stock_picks | 26 |
| **Result** | **WARNING** - 63 rows reference non-existent algorithm_id=0 |

### 1.5 alpha_factor_scores -> stocks
| Metric | Value |
|--------|-------|
| Orphan tickers | **0** |
| Orphan rows | **0** |
| Total distinct tickers | 52 |
| **Result** | **PASS** - All tickers in alpha_factor_scores exist in stocks table |

**Severity: WARNING** - One orphan algorithm_id (id=0) with 63 rows in stock_picks.

---

## 2. ASSET CLASS DISTRIBUTION ANALYSIS

### 2.1 at_raw_picks (Total: 136,155)
| Asset Class | Count | Percentage |
|-------------|-------|------------|
| CRYPTO | 101,781 | 74.8% |
| EQUITY | 13,557 | 10.0% |
| FOREX | 7,472 | 5.5% |
| UNKNOWN | 4,326 | 3.2% |
| (empty) | 2,493 | 1.8% |
| FUTURES | 2,509 | 1.8% |
| MEMECOIN | 3,155 | 2.3% |
| PENNY_STOCK | 707 | 0.5% |
| ETF | 152 | 0.1% |

### 2.2 trading_picks (Total: 63,997)
| Inferred Asset Class | Count | Percentage |
|-------------|-------|------------|
| FOREX | 22,420 | 35.0% |
| CRYPTO | 16,801 | 26.3% |
| FUTURES | 17,815 | 27.8% |
| STOCK/ETF | 6,961 | 10.9% |

### 2.3 rapid_signals (Total: 35,328)
| Inferred Asset Class | Count | Percentage |
|-------------|-------|------------|
| STOCK/ETF | 19,438 | 55.0% |
| CRYPTO | 13,989 | 39.6% |
| FOREX | 1,901 | 5.4% |

### 2.4 lm_signals (Total: 33,576)
| Asset Class | Count | Percentage |
|-------------|-------|------------|
| CRYPTO | 30,440 | 90.7% |
| FOREX | 1,914 | 5.7% |
| STOCK | 1,222 | 3.6% |

### 2.5 goldmine_cursor_predictions (Total: 478)
| Asset Class | Count | Percentage |
|-------------|-------|------------|
| stocks | 478 | 100.0% |

### 2.6 alpha_picks (Total: 5,043)
- **All are EQUITY only** - covers 48 tickers (all large-cap stocks like AAPL, MSFT, GOOGL, etc.)
- 9 distinct strategies (Alpha Factor Momentum, Value, Quality, Growth, etc.)

### 2.7 stock_picks (Total: 7,239)
- **All are EQUITY only** - covers 134 tickers
- Top strategies: Alpha Factor Composite (563), Alpha Factor Growth (560), Alpha Factor Quality (560)

**Severity: INFO** - Multi-asset database with clear asset class separation across tables.

---

## 3. SIGNAL PIPELINE VALIDATION

### 3.1 Pipeline Flow
| Stage | Record Count |
|-------|-------------|
| at_raw_picks | 136,155 |
| at_consensus_picks | 11,437 (8.4% of raw) |
| trading_picks | 63,997 |

### 3.2 at_consensus_picks Tiers
| Tier | Count |
|------|-------|
| MODERATE | 6,201 |
| STRONG | 3,955 |
| SUPER | 1,112 |
| high_conviction | 116 |
| medium_conviction | 28 |
| speculative | 25 |

### 3.3 at_signal_outcomes
- **Total tracked outcomes: 121** (very low relative to raw picks)
- Outcomes: LOSS (49), OPEN (38), EXPIRED (13), WIN (13), SL_HIT (2), CLOSED (6)

### 3.4 Deduplication Pipeline (at_raw_picks flags)
| Flag | Count | Percentage |
|------|-------|------------|
| was_stale | 0 | 0.0% |
| was_banned | 0 | 0.0% |
| was_demoted | 0 | 0.0% |
| was_wr_suppressed | 0 | 0.0% |

**CRITICAL**: Deduplication flags are entirely unused in at_raw_picks. The deduplication happens via at_filter_log (793,809 filter events) instead.

### 3.5 Filter Log (Total: 793,809 events)
| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| staleness | 631,669 | 79.6% |
| no_consensus | 115,725 | 14.6% |
| demoted_system | 19,497 | 2.5% |
| incubator_strategy | 13,722 | 1.7% |
| concentration_cap | 4,993 | 0.6% |
| wr_suppressed | 4,216 | 0.5% |
| banned_purge | 2,001 | 0.3% |
| regime_mismatch | 1,986 | 0.3% |

**Severity: CRITICAL** - Only 121 tracked outcomes for 136K+ raw picks. Outcome tracking coverage is severely inadequate. The deduplication flags in at_raw_picks are unused; all filtering happens post-hoc in at_filter_log.

---

## 4. PREDICTION QUALITY METRICS

### 4.1 trading_picks Closed Trades
| Status | Count | Avg PnL % | Min PnL % | Max PnL % |
|--------|-------|-----------|-----------|-----------|
| WON | 2,549 | -40.82 | -106,700.68 | 99.67 |
| LOST | 3,072 | -3.59 | -2,305.15 | 0.80 |
| TP_HIT | 629 | 2.90 | 0.30 | 13.87 |
| SL_HIT | 818 | -2.17 | -99.26 | -0.42 |

- **Overall win rate**: 3,178 / 7,068 = **44.96%**
- **CRITICAL**: WON trades have negative average PnL (-40.82%) - contradictory data
- **WARNING**: 8 trades with PnL < -100% (extreme outliers, max -106,700.68%)
- **WARNING**: WON status with min PnL of -106,700.68% suggests data integrity issues

### 4.2 at_raw_picks Closed Picks
| Status | Count | Avg PnL % |
|--------|-------|-----------|
| WON | 2,188 | -19.93 |
| LOST | 2,929 | -10.75 |

- Same contradictory pattern: WON picks have negative average PnL
- 3 records with negative stop_loss or take_profit prices

### 4.3 alpha_picks
- **5,043 total picks** with **NO outcome tracking** (no exit_price, pnl_pct columns)
- Cannot calculate win rates or realized returns

### 4.4 stock_picks
- **7,239 total picks** with **NO realized PnL tracking**
- Only has stop_loss_price; no exit tracking
- 534 unverified (verified=0), 6,705 verified (verified=1)

### 4.5 rapid_signals
- Closed/Win: 17,710 (avg PnL: +0.0464)
- Closed/Loss: 17,618 (avg PnL: -0.0254)
- **Win rate ~50%** for closed signals
- All PnL values are very small (fractional)

### 4.6 lm_signals
- Expired: 33,334 (avg PnL: -0.00%)
- Only 10 resolved with meaningful PnL (avg 5.61%)
- Most signals expire with near-zero PnL

### 4.7 at_signal_outcomes
| Outcome | Count | Avg PnL % |
|---------|-------|-----------|
| WIN | 13 | 5.86 |
| LOSS | 49 | -6.42 |
| EXPIRED | 13 | 0.22 |
| SL_HIT | 2 | -5.93 |
| OPEN | 38 | -0.38 |
| CLOSED | 6 | NULL |

### 4.8 goldmine_cursor_predictions
- Won: 99 (avg PnL: 5.0%, min=max=5.0 - suspiciously uniform)
- Lost: 86 (avg PnL: -3.0%, min=max=-3.0 - suspiciously uniform)
- Expired: 38
- Open: 255

**Severity: CRITICAL** - trading_picks shows contradictory data where WON trades have negative average PnL. This indicates a data integrity issue. Alpha_picks and stock_picks lack any outcome tracking infrastructure.

---

## 5. DATA FRESHNESS & CONSISTENCY

### 5.1 Latest Dates by Table
| Table | Date Column | Latest Date |
|-------|-------------|-------------|
| daily_prices | trade_date | 2026-04-29 |
| trading_picks | created_at | **2026-05-08 14:58:07** |
| alpha_picks | pick_date | 2026-04-27 |
| stock_picks | pick_date | 2026-04-27 |
| at_raw_picks | signal_timestamp | **2026-05-08 15:29:01** |
| lm_signals | signal_time | **2026-05-08 15:09:36** |
| rapid_signals | created_at | 2026-05-06 22:20:54 |
| goldmine_cursor_predictions | logged_at | 2026-02-10 |
| at_consensus_picks | generated_at | **2026-05-08 14:49:52** |
| at_signal_outcomes | opened_at | 2026-03-05 |
| ml_feature_store | timestamp | 2026-02-16 |

### 5.2 Future Date Check (>= 2026-05-09)
| Table | Future Records |
|-------|---------------|
| daily_prices | 0 |
| trading_picks | 0 |
| stock_picks | 0 |
| at_raw_picks | 0 |
| lm_signals | 0 |

**Result**: No future dates detected.

### 5.3 Stale Data Check (< 2026-04-08, older than 30 days)
| Table | Stale Records | Total | Percentage |
|-------|--------------|-------|------------|
| daily_prices | 48,466 | 49,340 | 98.2% |
| rapid_signals | 34,559 | 35,328 | 97.8% |
| ml_feature_store | 396 | 396 | 100.0% |
| lm_signals | 20,023 | 33,576 | 59.6% |
| at_raw_picks | 47,805 | 136,155 | 35.1% |
| trading_picks | 18,353 | 63,997 | 28.7% |

**Severity: WARNING** - daily_prices and rapid_signals are mostly stale (>97%). ml_feature_store is 100% stale (last update 2026-02-16). Active prediction tables (trading_picks, at_raw_picks, lm_signals) have recent data.

---

## 6. ML/FEATURE STORE VALIDATION

### 6.1 Summary
| Metric | Value |
|--------|-------|
| Total rows | 396 |
| Unique pairs | 36 (all crypto) |
| Unique timeframes | 1 (4H) |
| Unique timestamps | 11 |

### 6.2 Pairs (all crypto)
AAVEUSD, ADAUSD, APTUSD, ATOMUSD, AVAXUSD, BCHUSD, BONKUSD, COMPUSD, CRVUSD, DOTUSD, DYDXUSD, FARTCOINUSD, FETUSD, FLOKIUSD, INJUSD, LINKUSD, LTCUSD, NEARUSD, OPUSD, PENGUUSD, PEPEUSD, SHIBUSD, SOLUSD, SPXUSD, SUIUSD, TRUMPUSD, TURBOUSD, VIRTUALUSD, WIFUSD, XDGUSD, XETHZUSD, XXBTZUSD, XXLMZUSD, XXMRZUSD, XXRPZUSD, XZECZUSD

### 6.3 NULL Checks
| Indicator | NULL Count | Percentage |
|-----------|-----------|------------|
| rsi_14 | 0 | 0.0% |
| macd_value | 0 | 0.0% |
| macd_signal | 0 | 0.0% |
| sma_20 | 0 | 0.0% |
| sma_50 | 0 | 0.0% |
| atr_14 | 0 | 0.0% |
| volume | 0 | 0.0% |
| adx_14 | 0 | 0.0% |
| close_price | 0 | 0.0% |

### 6.4 Target Variable
| Target | Count |
|--------|-------|
| target_direction | 396 (ALL NULL) |
| target_1h | 396 (ALL NULL) |
| target_4h | 396 (ALL NULL) |
| target_24h | 396 (ALL NULL) |

**Severity: CRITICAL** - The ML feature store has NO labeled target data. All 396 rows have NULL targets, making this table unsuitable for supervised learning.

---

## 7. KEY CORE TABLES PER ASSET CLASS

### 7.1 STOCKS/EQUITY
| Table | Role | Records |
|-------|------|---------|
| stocks | Master symbol reference | 153 |
| daily_prices | End-of-day prices | 49,340 |
| stock_picks | Algorithm picks | 7,239 |
| alpha_picks | Alpha factor strategies | 5,043 |
| alpha_factor_scores | Factor scoring | 52 tickers |
| goldmine_cursor_predictions | Cursor-based predictions | 478 |
| rapid_signals | Mixed (stocks included) | 19,438 stock signals |

### 7.2 CRYPTO
| Table | Role | Records |
|-------|------|---------|
| at_raw_picks | Primary raw signals (74.8%) | 101,781 |
| lm_signals | ML-based signals (90.7% crypto) | 30,440 |
| rapid_signals | Rapid signals (39.6% crypto) | 13,989 |
| trading_picks | Executed trades (26.3% crypto) | 16,801 |
| at_consensus_picks | Consensus signals (84.6% crypto) | 9,680 |
| ml_feature_store | ML features (100% crypto) | 396 |
| crypto_assets | Asset metadata | 14 |
| crypto_signals | Alternative crypto signals | 0 |
| crypto_ohlcv | OHLCV data | 0 |
| cp_signals | Crypto pairs signals | 174 |

### 7.3 FOREX
| Table | Role | Records |
|-------|------|---------|
| fx_prices | Price data | 3,855 |
| fx_signals | Signal data | 585 |
| lm_signals | ML signals (5.7% forex) | 1,914 |
| trading_picks | Executed trades (35% forex) | 22,420 |
| at_raw_picks | Raw picks (5.5% forex) | 7,472 |

### 7.4 FUTURES
| Table | Role | Records |
|-------|------|---------|
| at_raw_picks | Raw picks (1.8%) | 2,509 |
| trading_picks | Executed trades (27.8%) | 17,815 |
| at_futures_symbol_edge | Symbol edge data | 4 |

### 7.5 ETFs
| Table | Role | Records |
|-------|------|---------|
| at_raw_picks | Raw picks (0.1%) | 152 |
| goldmine_cursor_predictions | ETF picks via ETF Masters | 51 |
| trading_picks | ETF trades | 57 |

### 7.6 MEMECOINS
| Table | Role | Records |
|-------|------|---------|
| at_raw_picks | Raw picks (2.3%) | 3,155 |
| at_consensus_picks | Consensus (6.2%) | 707 |
| meme_signals | Meme signal scoring | 50 |
| meme_signal_results | Meme signal results | 50 |
| meme_ml_predictions | ML predictions | 0 |

**Severity: INFO** - Clear asset class separation. CRYPTO is the dominant asset class in raw signals.

---

## 8. ANOMALY DETECTION

### 8.1 NULL Prices
| Table | NULL Prices Found |
|-------|-----------------|
| daily_prices | 0 |

### 8.2 Negative Prices
| Table | Negative Prices |
|-------|----------------|
| daily_prices | 0 |
| at_raw_picks | 3 records (HYPEUSDT, STOUSDT, STRKUSDT with negative stop_loss) |
| trading_picks | 0 |

### 8.3 Negative Volumes
| Table | Negative Volumes |
|-------|-----------------|
| daily_prices | 0 |

### 8.4 Win Rate Validity
| Table | Invalid Win Rates (>100% or <0%) |
|-------|-------------------------------|
| algorithm_rolling_perf | 0 (range: 0-100%, avg=22.85%) |

### 8.5 Confidence Score Validity
| Metric | Value |
|--------|-------|
| at_raw_picks confidence outside [0,1] | **11 records** |
| Minimum confidence | -0.80 |
| Maximum confidence | 1.00 |
| Average confidence | 0.63 |

11 records have negative confidence (-0.8 or -0.6), all from source_systems `sandbox_opposite` and `audit_trail_local`.

### 8.6 Extreme PnL Values
| Table | |PnL| > 1000% | PnL < -100% |
|-------|---------|-------------|
| trading_picks | 5 | 8 |
| at_raw_picks | Not checked | Not checked |

**Extreme trading_picks cases:**
- DOGEUSDT: NULL% (OPEN) - no exit price
- WON trades with PnL as low as -106,700.68% - **data integrity issue**

### 8.7 Other Anomalies
- **449 trading_picks with empty/NULL direction** out of 63,997 (0.7%)
- **3 at_raw_picks with negative stop_loss values** (HYPEUSDT: -0.38, STOUSDT: -0.028, STRKUSDT: -0.028)
- **goldmine_cursor_predictions**: Won PnL is uniformly 5.0%, Lost PnL is uniformly -3.0% (suspicious hardcoded values)

**Severity: WARNING** - 11 records with invalid negative confidence scores; 3 records with negative stop_loss; goldmine cursor PnL values appear hardcoded.

---

## SUMMARY OF KEY FINDINGS

| # | Finding | Severity |
|---|---------|----------|
| 1 | 63 orphan rows in stock_picks referencing non-existent algorithm_id=0 | WARNING |
| 2 | at_raw_picks deduplication flags (was_stale, was_banned, etc.) are entirely unused - all 0 | WARNING |
| 3 | Only 121 tracked outcomes for 136K+ raw picks - outcome tracking severely inadequate | CRITICAL |
| 4 | trading_picks: WON trades have negative average PnL (-40.82%) - contradictory data integrity issue | CRITICAL |
| 5 | alpha_picks (5,043) and stock_picks (7,239) have NO outcome tracking columns | CRITICAL |
| 6 | ml_feature_store has 396 rows with ALL targets NULL - not usable for ML training | CRITICAL |
| 7 | daily_prices is 98.2% stale; rapid_signals is 97.8% stale; ml_feature_store 100% stale | WARNING |
| 8 | 11 records with negative confidence scores in at_raw_picks | WARNING |
| 3 records with negative stop_loss prices in at_raw_picks | WARNING |
| 10 | goldmine_cursor_predictions PnL values appear hardcoded (uniform 5.0% / -3.0%) | WARNING |
| 11 | No future dates detected in any table | INFO |
| 12 | Referential integrity is mostly clean (only 1 orphan algorithm_id) | INFO |
| 13 | CRYPTO dominates raw signals (74.8%) and consensus (84.6%) | INFO |
| 14 | trading_picks overall win rate: 44.96% (3,178 wins / 7,068 closed) | INFO |

---

## RECOMMENDATIONS

1. **Fix outcome tracking**: Add exit_price and pnl_pct columns to alpha_picks and stock_picks tables
2. **Fix contradictory PnL data**: Investigate why WON trades in trading_picks show negative average PnL
3. **Populate ML targets**: The ml_feature_store needs labeled target_direction data for supervised learning
4. **Remove or fix orphan algorithm_id=0**: Either create algorithm id=0 in algorithms table or reassign those 63 rows
5. **Fix negative stop_loss values**: 3 records in at_raw_picks have negative stop_loss prices
6. **Investigate hardcoded PnL**: goldmine_cursor_predictions has uniform PnL values suggesting hardcoding
7. **Enable dedup flags**: The was_stale/banned/demoted flags in at_raw_picks should be populated during ingestion
8. **Refresh stale price data**: daily_prices and rapid_signals are heavily stale
