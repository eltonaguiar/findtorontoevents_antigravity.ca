# Financial Prediction System - Comprehensive Database Analysis Report

## Executive Summary

**Databases Analyzed:**
- `ejaguiar1_stocks` (mysql.50webs.com) - 322 tables
- `ejaguiar1_backtests` (mysql.50webs.com) - 6 tables

**Total Picks Analyzed:** 55,510 resolved trades with PnL data

**Date Range:** 2020-01-03 to 2026-05-11

**CRITICAL FINDING: NO asset class demonstrates statistically significant positive edge.**
The system as a whole produces negative returns across all asset classes, with significant
overfitting detected between backtest and live performance.

---

## 1. Schema Documentation

### Stocks Database (322 tables)

| Table | Rows | Description |
|-------|------|-------------|
| `at_raw_picks` | 143,514 | Main picks table with asset_class, direction, pnl_pct, confidence |
| `at_signal_outcomes` | 121 | Signal outcomes with PnL by asset class |
| `stock_picks` | 7,239 | Stock picks with algorithm scores |
| `cr_pair_picks` | 980 | Crypto pair picks (LONG/SHORT) |
| `fx_pair_picks` | 16 | Forex pair picks |
| `mf_fund_picks` | 15 | Mutual fund/ETF picks |
| `lm_trades` | 201 | Live trades with realized PnL (STOCK, FOREX, CRYPTO) |
| `algorithms` | 142 | Algorithm definitions and metadata |
| `algorithm_performance` | 23 | Algorithm performance summaries |
| `meme_signals` | 50 | Meme coin signals |
| `meme_signal_results` | 50 | Meme signal outcome results |
| `paper_trades` | 0 | Paper trading (EMPTY) |

### Backtests Database (6 tables)

| Table | Rows | Description |
|-------|------|-------------|
| `bt_backtest_runs` | 285 | Backtest run summaries with returns, win rates |
| `bt_backtest_trades` | 50,000 | Individual backtest trades with PnL |
| `at_incubator_backtest_results` | 1,285 | Strategy incubator results with Sharpe, Sortino, max DD |
| `at_large_backtest_results` | 1,105 | Large backtest results with equity curves |
| `backtest_results` | 2 | Portfolio-level backtest results |
| `backtest_trades` | 50 | Older backtest trades |

---

## 2. Performance Metrics by Asset Class

### Main Performance Table (from at_raw_picks - 55,510 resolved trades)

| Asset Class | Picks | Win% | Avg Return% | Cum PnL% | Sharpe | Sortino | Max DD% | PF | Expectancy% |
|-------------|-------|------|-------------|----------|--------|---------|---------|----|-------------|
| CRYPTO | 51,049 | 11.30 | -3.7306 | -190,442 | -2.890 | -2.309 | -190,442 | 0.456 | -3.731 |
| MEMECOIN | 1,869 | 15.73 | -3.5784 | -6,688 | -2.788 | -2.360 | -6,688 | 0.499 | -3.578 |
| EQUITY | 814 | 1.84 | +0.0197 | +16 | +0.667 | +0.373 | -9.4 | 2.177 | +0.020 |
| FOREX | 605 | 9.92 | -0.1907 | -115 | -0.513 | -0.254 | -179 | 0.628 | -0.191 |
| FUTURES | 172 | 17.44 | -0.3718 | -64 | -3.731 | -5.455 | -66 | 0.374 | -0.372 |
| PENNY_STOCK | 148 | 6.76 | -0.8659 | -128 | -3.379 | -1.802 | -129 | 0.194 | -0.866 |
| ETF | 39 | 0.00 | -0.0750 | -3 | -3.907 | -1.626 | -3 | 0.000 | -0.075 |
| **ALL** | **55,510** | **11.13** | **-3.5577** | **-197,487** | **-2.344** | **-1.834** | **-197,487** | **0.457** | **-3.558** |

### Directional Performance

| Asset Class | Long Picks | Long WR% | Short Picks | Short WR% |
|-------------|-----------|----------|------------|-----------|
| CRYPTO | 34,223 | 12.61% | 16,826 | 8.64% |
| MEMECOIN | 1,286 | 15.24% | 583 | 16.81% |
| EQUITY | 790 | 1.77% | 24 | 4.17% |
| FOREX | 460 | 7.39% | 145 | 17.93% |
| FUTURES | 78 | 6.41% | 94 | 26.60% |
| PENNY_STOCK | 133 | 3.76% | 15 | 33.33% |

---

## 3. Statistical Test Results (Edge Detection)

### Normality Tests

| Asset Class | N | Jarque-Bera | p-value | Normal? |
|-------------|---|-------------|---------|---------|
| CRYPTO | 51,049 | 118,221.76 | < 0.001 | NO |
| MEMECOIN | 1,869 | 1,590.83 | < 0.001 | NO |
| EQUITY | 814 | 2,072,231.38 | < 0.001 | NO |
| FOREX | 605 | 277,052.21 | < 0.001 | NO |
| FUTURES | 172 | 62.83 | < 0.001 | NO |

### T-Tests (Mean Return > 0)

| Asset Class | T-statistic | p-value | Has Edge? |
|-------------|-------------|---------|-----------|
| CRYPTO | -34.18 | 1.000 | NO |
| MEMECOIN | -6.31 | 1.000 | NO |
| EQUITY | +1.20 | 0.115 | NO (not significant) |
| FOREX | -0.80 | 0.787 | NO |
| FUTURES | -3.08 | 0.999 | NO |

**Conclusion:** No asset class has statistically significant positive edge.

### Distribution Characteristics

| Asset Class | Skewness | Direction | Excess Kurtosis | Tail Type |
|-------------|----------|-----------|-----------------|-----------|
| CRYPTO | -0.66 | Left-skewed | +7.34 | Fat tails |
| MEMECOIN | -0.46 | Left-skewed | +4.42 | Fat tails |
| EQUITY | +13.14 | Right-skewed | +245.78 | Extreme fat tails |
| FOREX | +2.86 | Right-skewed | +104.68 | Extreme fat tails |
| FUTURES | +0.41 | Right-skewed | +2.85 | Fat tails |

---

## 4. ML Performance Analysis

| Metric | CRYPTO | MEMECOIN | EQUITY | FOREX | FUTURES | ALL |
|--------|--------|----------|--------|-------|---------|-----|
| Samples | 49,540 | 1,644 | 810 | 605 | 172 | 53,758 |
| Accuracy% | 31.46 | 35.40 | 83.83 | 59.17 | 23.26 | 32.60 |
| Precision% | 11.56 | 14.51 | 1.67 | 18.52 | 18.52 | 11.52 |
| Recall% | 84.15 | 90.31 | 13.33 | 91.67 | 100.00 | 84.38 |
| F1% | 20.33 | 25.00 | 2.96 | 30.81 | 31.25 | 20.27 |
| Specificity% | 25.35 | 27.97 | 85.16 | 55.60 | 7.04 | 26.74 |
| Brier Score | 0.374 | 0.377 | 0.312 | 0.368 | 0.414 | 0.374 |

### Calibration Analysis
**CRITICAL ISSUE:** Model confidence scores are severely miscalibrated.
- Predicted confidence of 96% corresponds to actual win rate of only 0.9%
- Predicted confidence of 85% corresponds to actual win rate of only 3.4%
- Predicted confidence of 74% corresponds to actual win rate of only 13.0%
- Predicted confidence of 61% corresponds to actual win rate of only 13.4%

The model systematically overestimates win probabilities by an enormous margin.

---

## 5. Backtest vs Live Comparison

| Asset Class | BT Avg Ret% | Live Avg Ret% | BT WR% | Live WR% | Gap% | Overfitting? |
|-------------|-------------|---------------|--------|----------|------|-------------|
| CRYPTO | -1.05 | -3.73 | 42.42 | 11.30 | -2.68 | YES |
| MEMECOIN | 0.00 | -3.58 | 0.00 | 15.73 | -3.58 | YES |
| FOREX | 0.00 | -0.19 | 0.00 | 9.92 | -0.19 | No |
| EQUITY | 0.00 | +0.02 | 0.00 | 1.84 | +0.02 | No |
| ALL | -1.05 | -3.56 | 42.42 | 11.13 | -2.51 | YES |

**CRITICAL:** Severe overfitting detected. Backtest win rate (42%) is nearly 4x the live win rate (11%).
The gap of -2.51% in average return represents a massive degradation from backtest to live.

---

## 6. Algorithm Performance Summary

All 23 algorithms have **negative average returns**. Best performers:

| Algorithm | Picks | Win% | Avg Return% |
|-----------|-------|------|-------------|
| CAN SLIM | 4 | 50.00 | -0.35 |
| Alpha Predator | 19 | 47.37 | -0.70 |
| PEAD Earnings Drift | 147 | 30.61 | -2.98 |
| 13F Hedge Fund Clone | 153 | 29.41 | -2.84 |
| Cursor Genius | 292 | 25.34 | -2.64 |

Worst performers:

| Algorithm | Picks | Win% | Avg Return% |
|-----------|-------|------|-------------|
| Regime-Aware Reversion (V2) | 8 | 0.00 | -6.70 |
| Alpha Factor Low Vol | 360 | 3.06 | -9.76 |
| Alpha Factor Safe Bets | 314 | 3.82 | -8.07 |
| Alpha Factor Composite | 333 | 3.90 | -10.00 |
| Alpha Factor Value | 266 | 4.51 | -6.82 |

---

## 7. Data Quality Issues

| # | Issue | Severity |
|---|-------|----------|
| 1 | **38,312 resolved trades have zero PnL** | CRITICAL |
| 2 | **814 records with unknown/empty asset class** | HIGH |
| 3 | **4 extreme PnL outliers (-43,939% to -1,038%)** | HIGH |
| 4 | **All meme signals marked as "win" (suspicious)** | HIGH |
| 5 | **Zero paper trading data** | MEDIUM |
| 6 | **Only 1 record with zero confidence score** | LOW |
| 7 | **Only 1 record missing exit price** | LOW |
| 8 | **Meme signal returns range from -35.6% to +55.8%** | MEDIUM |
| 9 | **No pick_hash deduplication in extracted data** | MEDIUM |

---

## 8. Day of Week Performance

| Day | CRYPTO Avg% | CRYPTO WR% | EQUITY Avg% | FOREX Avg% |
|-----|-------------|-----------|-------------|-----------|
| Monday | -16.92 | 30.8% | N/A | -4.83 |
| Tuesday | -3.37 | 48.8% | +2.03 | -0.95 |
| Wednesday | -13.85 | 28.5% | +0.33 | -8.15 |
| Thursday | -12.51 | 37.3% | N/A | -0.26 |
| Friday | -9.42 | 36.9% | 0.00 | +0.72 |
| Saturday | -12.17 | 35.4% | -0.67 | -0.02 |
| Sunday | -12.75 | 35.8% | N/A | N/A |

**Observation:** Tuesday shows the highest win rate for crypto (~49%), while Monday shows the deepest losses.

---

## 9. Key Conclusions

### Which Asset Classes Have Genuine Edge?
**NONE.** Statistical testing confirms no asset class has a statistically significant positive edge.

The closest is **EQUITY** (p=0.115, Sharpe=+0.67), but it fails to reach significance and has an extremely low win rate (1.84%).

### Overfitting Assessment: **SEVERE**
- Backtest win rate (42%) is ~4x live win rate (11%)
- Live average return (-3.56%) is 3.4x worse than backtest (-1.05%)
- This represents catastrophic overfitting

### ML Model Quality: **POOR**
- Accuracy is 32.6% (worse than random guessing for binary outcomes)
- Calibration is fundamentally broken - high confidence = low actual win rate
- Brier score of 0.37 indicates very poor probability calibration

### Data Quality: **CONCERNING**
- 69% of resolved trades have zero PnL (38,312 / 55,510)
- Missing asset classification for 1.5% of records
- Extreme outliers suggesting data pipeline issues

### Overall System Assessment: **NOT PROFITABLE**
The financial prediction system, across all asset classes, strategies, and algorithms, does not
produce profitable results. The combination of negative expected returns, poor model calibration,
severe backtest overfitting, and data quality issues indicates fundamental problems requiring
significant redevelopment.

---

## 10. Output Files Generated

| File | Description |
|------|-------------|
| `/mnt/agents/output/db_analysis.py` | Complete analysis script |
| `/mnt/agents/output/metrics_by_asset_class.csv` | Per-asset-class metrics |
| `/mnt/agents/output/edge_detection.csv` | Statistical test results |
| `/mnt/agents/output/ml_performance.csv` | ML model performance |
| `/mnt/agents/output/backtest_vs_live.csv` | Backtest vs live comparison |
| `/mnt/agents/output/day_of_week_performance.csv` | Day-of-week analysis |
| `/mnt/agents/output/algorithm_performance.csv` | Algorithm rankings |
| `/mnt/agents/output/raw_picks_clean.csv` | Cleaned picks data |
| `/mnt/agents/output/schema_documentation.json` | Schema documentation |
| `/mnt/agents/output/comprehensive_summary.png` | Summary dashboard |
| `/mnt/agents/output/rolling_CRYPTO.png` | CRYPTO rolling performance |
| `/mnt/agents/output/rolling_MEMECOIN.png` | MEMECOIN rolling performance |
| `/mnt/agents/output/rolling_EQUITY.png` | EQUITY rolling performance |
| `/mnt/agents/output/rolling_FOREX.png` | FOREX rolling performance |
| `/mnt/agents/output/rolling_FUTURES.png` | FUTURES rolling performance |
| `/mnt/agents/output/rolling_PENNY_STOCK.png` | PENNY STOCK rolling performance |
| `/mnt/agents/output/rolling_ALL.png` | ALL rolling performance |
| `/mnt/agents/output/day_of_week_performance.png` | Day-of-week chart |

---

*Report generated: 2025-06-10*
*Analyst: Financial Database Analysis System*
