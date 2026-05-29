# Comprehensive Strategy Roadmap

- **Generated:** 2026-05-29 02:32:02 EDT
- **Total Strategies Tracked:** 81
- **Database:** ejaguiar1_stocks (mysql.50webs.com)
- **Backtest Harness:** Purged WF + DSR + PBO + Costs (`alpha_engine/rigorous_backtest_harness.py`)

---

## 1. Executive Summary

### Current State: No World-Class Strategies Yet

**0 strategies meet T1/T2/T3 sizing thresholds.** While 81 strategies are tracked across 7 asset classes, rigorous statistical validation reveals systemic overfitting:

| Metric | Value |
|---|---|
| Strategies with DSR/PBO computed | 2 |
| Average DSR (all sized) | -3.13 |
| Average PBO (all sized) | 0.613 |
| Strategies passing T3+ | 0 |

**Root Cause:** High PBO (0.3–0.7) indicates most strategies were data-mined (many parameter trials), inflating in-sample performance but failing out-of-sample. The solution: fewer parameters + economic rationale + purged walk-forward during development.

---

## 2. Per-Asset-Class Overview

### CRYPTO (50 strategies)
| Metric | Value |
|---|---|
| Avg PF | 478.123 |
| Avg WR | 100.0% |
| Avg DSR | 1.59 |
| Avg PBO | 0.580 |
| Strategies sized (T1/T2/T3) | 0 |

**Top 3 by DSR:**
| Rank | Strategy | PF | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | unknown | 1.294 | 100.0% | 408 | 15.34 | 0.416 | 71.4% |  |
| 2 | luxalgo_confluence | 0.000 | 0.0% | 12 | 5.57 | 0.486 | 57.1% | shadow |
| 3 | ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | 10.417 | 100.0% | 34 | 5.18 | 0.987 | 0.0% |  |

### EQUITY (5 strategies)
| Metric | Value |
|---|---|
| Avg PF | 21.508 |
| Avg WR | 100.0% |
| Avg DSR | 7.69 |
| Avg PBO | 0.645 |
| Strategies sized (T1/T2/T3) | 0 |

**Top 3 by DSR:**
| Rank | Strategy | PF | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | stocks_rsi2_pullback | 21.508 | 100.0% | 64 | 7.69 | 0.645 | 0.0% |  |
| 2 | bond_yield_momentum | 0.000 | 0.0% | 3 | 0.00 | 0.000 | 0.0% | shadow |

### FOREX (8 strategies)
| Metric | Value |
|---|---|
| Avg PF | 7.782 |
| Avg WR | 100.0% |
| Avg DSR | -8.51 |
| Avg PBO | 0.623 |
| Strategies sized (T1/T2/T3) | 0 |

**Top 3 by DSR:**
| Rank | Strategy | PF | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | fx_smart_carry_trade_momentum | 6.213 | 100.0% | 53 | 6.88 | 0.593 | 0.0% |  |
| 2 | fx_smart_forex_rsi2_mean_reversion | 15.742 | 100.0% | 12 | 1.64 | 0.411 | 0.0% |  |
| 3 | unknown | 1.392 | 100.0% | 22 | 1.17 | 0.568 | 0.0% |  |

### ETF
*No strategies with sufficient data yet.*

### COMMODITY (8 strategies)
| Metric | Value |
|---|---|
| Avg PF | 0.000 |
| Avg WR | 0.0% |
| Avg DSR | -9.09 |
| Avg PBO | 0.714 |
| Strategies sized (T1/T2/T3) | 0 |

**Top 3 by DSR:**
| Rank | Strategy | PF | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | futures_momentum | 0.000 | 0.0% | 3 | -2.99 | 0.545 | 28.6% | shadow |
| 2 | cta_cross_asset_tsmom | 0.000 | 0.0% | 3 | -9.17 | 0.852 | 14.3% | shadow |
| 3 | cta_commodity_momentum_term | 0.000 | 0.0% | 5 | -11.81 | 0.978 | 0.0% | shadow |

### FUTURES (4 strategies)
| Metric | Value |
|---|---|
| Avg PF | 0.000 |
| Avg WR | 0.0% |
| Avg DSR | 0.00 |
| Avg PBO | 0.000 |
| Strategies sized (T1/T2/T3) | 0 |

**Top 3 by DSR:**
| Rank | Strategy | PF | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|

### BOND (1 strategies)
| Metric | Value |
|---|---|
| Avg PF | 362.631 |
| Avg WR | 100.0% |
| Avg DSR | 0.00 |
| Avg PBO | 0.000 |
| Strategies sized (T1/T2/T3) | 0 |

**Top 3 by DSR:**
| Rank | Strategy | PF | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | futures_momentum | 362.631 | 100.0% | 4 | 0.00 | 0.000 | 0.0% | shadow |

---

## 3. World-Class Thresholds (Not Yet Met)

| Tier | Min PF | Min WR | Min n | Min DSR | Max PBO | Max MDD | Description |
|---|---|---|---|---|---|---|---|
| T1 | > 2.0 | > 55% | ≥ 30 | > 0.95 | < 0.05 | < 10% | Renaissance-grade |
| T2 | > 1.5 | > 50% | ≥ 30 | > 0.90 | < 0.10 | < 20% | Institutional |
| T3 | > 1.2 | > 48% | ≥ 20 | > 0.80 | < 0.20 | < 30% | Retail-OK |

### Closest Candidates (Still Shadow)

| Strategy | Class | PF | WR | n | DSR | PBO | Gap to T3 |
|---|---|---|---|---|---|---|---|
| unknown | CRYPTO | 1.294 | 100.0% | 408 | 15.34 | 0.416 | PBO 0.42>0.20 |
| stocks_rsi2_pullback | EQUITY | 21.508 | 100.0% | 64 | 7.69 | 0.645 | PBO 0.64>0.20 |
| fx_smart_carry_trade_momentum | FOREX | 6.213 | 100.0% | 53 | 6.88 | 0.593 | PBO 0.59>0.20 |
| luxalgo_confluence | CRYPTO | 0.000 | 0.0% | 12 | 5.57 | 0.486 | PF 0.00<1.2; WR 0%<48%; n 12<20; PBO 0.49>0.20 |
| ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | CRYPTO | 10.417 | 100.0% | 34 | 5.18 | 0.987 | PBO 0.99>0.20 |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | CRYPTO | 6.833 | 100.0% | 30 | 4.60 | 0.621 | PBO 0.62>0.20 |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | CRYPTO | 3.094 | 100.0% | 26 | 4.00 | 0.602 | PBO 0.60>0.20 |
| ml_enhanced_STRKUSDT_15m_D_ensemble_stack | CRYPTO | 2.132 | 100.0% | 28 | 3.98 | 0.528 | PBO 0.53>0.20 |
| ml_enhanced_TONUSDT | CRYPTO | 5209.101 | 100.0% | 23 | 3.62 | 0.964 | PBO 0.96>0.20 |
| ml_enhanced_AVAXUSDT_15m_D_ensemble_stack | CRYPTO | 19.331 | 100.0% | 25 | 3.38 | 0.518 | PBO 0.52>0.20 |
| crypto_keltner_compression_expansion_v1 | CRYPTO | 3.734 | 100.0% | 21 | 3.33 | 0.434 | PBO 0.43>0.20 |
| ml_enhanced_INJUSDT_15m_D_ensemble_stack | CRYPTO | 4.242 | 100.0% | 28 | 3.26 | 0.526 | PBO 0.53>0.20 |
| ml_enhanced_FETUSDT_15m_B_lightgbm | CRYPTO | 19.083 | 100.0% | 23 | 3.21 | 0.287 | PBO 0.29>0.20 |
| ml_enhanced_ALGOUSDT_15m_B_lightgbm | CRYPTO | 11.764 | 100.0% | 23 | 3.14 | 0.326 | PBO 0.33>0.20 |
| ml_enhanced_ADAUSDT_15m_B_lightgbm | CRYPTO | 33.035 | 100.0% | 21 | 2.97 | 0.501 | PBO 0.50>0.20 |

---

## 4. Path to World-Class Strategies

### Problem: Overfitting (High PBO)
The primary blocker is PBO > 0.20 for nearly all strategies. This means the strategies were likely discovered through extensive parameter searching, which inflates in-sample performance but fails out-of-sample.

### Solution: The 7 New Strategy Designs
See `alpha_engine/new_strategies/strategy_designs.py` for 7 economically-motivated strategies (one per asset class) designed with:
- **≤2 parameters each** (reduces trial count → lowers PBO)
- **Strong economic rationale** (not data-mined patterns)
- **Simple threshold rules** (no ML, no complex interactions)
- **Cost-aware design** (survives realistic fees/slippage)

| Asset Class | Strategy Name | Params | Expected Sharpe | Economic Basis |
|---|---|---|---|---|
| CRYPTO | crypto_funding_carry_reversion | 2 | 0.8 | Funding rate structural carry + RSI mean-reversion |
| EQUITY | equity_earnings_momentum_quality | 2 | 0.6 | PEAD anomaly (35+ years literature) + quality filter |
| FOREX | forex_carry_term_structure | 2 | 0.7 | Currency carry risk premium + term structure timing |
| ETF | etf_sector_rotation_momentum | 2 | 0.6 | Sector momentum (Jegadeesh & Titman 1993) |
| COMMODITY | commodity_term_structure_carry | 2 | 0.5 | Contango/backwardation → supply/demand signal |
| FUTURES | futures_trend_volatility_target | 2 | 0.8 | Time-series momentum (100+ years data) + vol targeting |
| BOND | bond_yield_curve_steepener | 2 | 0.5 | 2s10s slope predicts duration returns |

### Implementation Priority
1. **FUTURES trend + vol target** — simplest, most documented (Moskowitz et al. 2012)
2. **COMMODITY term structure carry** — economically clean, few params
3. **BOND yield curve steepener** — single macro signal, well-documented
4. **FOREX carry + term structure** — established risk premium
5. **ETF sector rotation** — requires sector ETF data
6. **EQUITY PEAD** — requires earnings data pipeline
7. **CRYPTO funding carry** — requires funding rate data

### Data Integrity Prerequisites
Before any strategy can be validated:
1. **Fix TIME_EXIT phantom-closes** — 62% of trading_picks are zero-PnL exits diluting metrics
2. **Resolve EXPIRED→WON mislabels** — inflates WR artificially
3. **Dedup signal timestamps** — prevents double-counting into WR/PF
4. **Increase sample sizes** — most strategies have n < 30

---

## 5. Database Schema Reference

| Table | Rows | Purpose |
|---|---|---|
| `strategy_summary` | 81 | Canonical catalog with PF/WR/DSR/PBO/time-windows/traceability |
| `pick_dimension_snapshot` | 3,000 | Per-pick Score/Trust/AGV/Regime/Edge sub-tags |
| `pick_funnel_views` | 6 | Performance by nav-surface (button vs tab comparison) |
| `edge_discovery` | 7 | Pre-computed edge significance (Bonferroni-corrected) |
| `metric_dimensions` | 41 | Dictionary of all dimension values |
| `view_definition_catalog` | 10 | Documents every dashboard button/filter |

### Live Dashboard
- **Strategy Funnel section:** https://findtorontoevents.ca/audit/pick_funnel.html
- **Data source:** https://findtorontoevents.ca/audit/data/strategy_funnel_data.json

---

## 6. Re-Run Backtests

```bash
# All strategies for one asset class
python3 alpha_engine/rigorous_backtest_harness.py --batch --class CRYPTO

# Single strategy
python3 alpha_engine/rigorous_backtest_harness.py --strategy stocks_rsi2_pullback --class EQUITY

# With more trials for better DSR/PBO estimates
python3 alpha_engine/rigorous_backtest_harness.py --batch --class FOREX --n-trials 200 --n-bootstrap 2000
```

---

*Report generated from ejaguiar1_stocks. All metrics from resolved picks with pnl_pct IS NOT NULL.
Backtest harness implements purged walk-forward, DSR (Bailey & Lopez de Prado 2014), PBO (2015), and cost modeling.*
