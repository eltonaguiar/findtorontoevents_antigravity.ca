# Strategy Summary — Rigorous Backtest Report

- **Generated:** 2026-05-29 02:22:21 EDT
- **Database:** ejaguiar1_stocks (mysql.50webs.com)
- **Backtest Harness:** `alpha_engine/rigorous_backtest_harness.py` (Purged WF, DSR, PBO, Costs)
- **Reference:** Lopez de Prado, "Advances in Financial Machine Learning" (2018)

---

## 1. System Overview

| Metric | Value |
|---|---|
| Strategies tracked | 81 |
| Strategies with DSR/PBO | 40 |
| Strategies sized (T1/T2/T3) | 0 |
| Pick dimension snapshots | 3,000 |
| Edge discovery combos (n≥30) | 15 |
| Funnel views tracked | 6 |

### Backtest Methodology
- **Purged Walk-Forward:** 8-fold with 5% purge + 2% embargo to prevent lookahead leakage
- **Deflated Sharpe Ratio (DSR):** Adjusts observed Sharpe for number of trials tested (null hypothesis Sharpe = 0)
- **Probability of Backtest Overfitting (PBO):** Fraction of times best IS strategy ranks in bottom half OS (lower = better, < 0.05 = good)
- **Costs:** Per-class taker fees + slippage (CRYPTO 0.1%, EQUITY 0.05%, FOREX 0.03%, etc.)
- **Sizing Tiers:** T1 (PF>2/WR>55%/n≥30/DSR>0.95/PBO<0.05/MDD<10%), T2, T3 with relaxed thresholds

---

## 2. Key Finding: No Strategies Yet Meet Real-Money Thresholds

**All 0 strategies remain at "shadow" sizing.** While several strategies show positive PF, the rigorous statistical validation reveals:

1. **High PBO values** (> 0.4 for most) indicate high probability of backtest overfitting
2. **Walk-forward consistency** is low — most strategies fail to reproduce IS performance OOS
3. **Cost-adjusted Sharpe** is often negative after fees/slippage

This confirms the broader system finding: `money_ready_verdict.json` shows `money_ready: []` — no asset class is investable yet.

---

## 3. Top Strategies Per Asset Class (by DSR)

### CRYPTO
| Rank | Strategy | PF (costed) | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | unknown | 1.294 | 100.0% | 408 | 15.34 | 0.416 | 71.4% | shadow |
| 2 | luxalgo_confluence | 0.000 | 0.0% | 12 | 5.57 | 0.486 | 57.1% | shadow |
| 3 | ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | 10.417 | 100.0% | 34 | 5.18 | 0.987 | 0.0% | shadow |
| 4 | ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 6.833 | 100.0% | 30 | 4.60 | 0.621 | 0.0% | shadow |
| 5 | ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 3.094 | 100.0% | 26 | 4.00 | 0.602 | 0.0% | shadow |

### EQUITY
| Rank | Strategy | PF (costed) | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | stocks_rsi2_pullback | 21.508 | 100.0% | 64 | 7.69 | 0.645 | 0.0% | shadow |
| 2 | bond_yield_momentum | 0.000 | 0.0% | 3 | 0.00 | 0.000 | 0.0% | shadow |

### FOREX
| Rank | Strategy | PF (costed) | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | fx_smart_carry_trade_momentum | 6.213 | 100.0% | 53 | 6.88 | 0.593 | 0.0% | shadow |
| 2 | fx_smart_forex_rsi2_mean_reversion | 15.742 | 100.0% | 12 | 1.64 | 0.411 | 0.0% | shadow |
| 3 | unknown | 1.392 | 100.0% | 22 | 1.17 | 0.568 | 0.0% | shadow |
| 4 | ig_contrarian_sentiment | 0.000 | 0.0% | 6 | -10.11 | 0.762 | 14.3% | shadow |
| 5 | forex_carry_momentum | 0.000 | 0.0% | 4 | -17.25 | 0.653 | 0.0% | shadow |

### ETF
*No strategies with ≥ 3 resolved picks.*

### COMMODITY
| Rank | Strategy | PF (costed) | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | futures_momentum | 0.000 | 0.0% | 3 | -2.99 | 0.545 | 28.6% | shadow |
| 2 | cta_cross_asset_tsmom | 0.000 | 0.0% | 3 | -9.17 | 0.852 | 14.3% | shadow |
| 3 | cta_commodity_momentum_term | 0.000 | 0.0% | 5 | -11.81 | 0.978 | 0.0% | shadow |
| 4 | commodity_tsmom_12m | 0.000 | 0.0% | 3 | 0.00 | 0.000 | 0.0% | shadow |

### FUTURES
*No strategies with ≥ 3 resolved picks.*

### BOND
| Rank | Strategy | PF (costed) | WR | n | DSR | PBO | WF Consistency | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | futures_momentum | 362.631 | 100.0% | 4 | 0.00 | 0.000 | 0.0% | shadow |

---

## 4. Sizing Thresholds (Not Yet Met by Any Strategy)

| Tier | Min PF | Min WR | Min n | Min DSR | Max PBO | Max MDD |
|---|---|---|---|---|---|---|
| T1 (Renaissance) | > 2.0 | > 55% | ≥ 30 | > 0.95 | < 0.05 | < 10% |
| T2 (Institutional) | > 1.5 | > 50% | ≥ 30 | > 0.90 | < 0.10 | < 20% |
| T3 (Retail-OK) | > 1.2 | > 48% | ≥ 20 | > 0.80 | < 0.20 | < 30% |

### Closest Candidates (by DSR, but PBO too high)
- **unknown (CRYPTO):** DSR=15.34, PBO=0.416 — catch-all for unclassified picks, not a real strategy
- **stocks_rsi2_pullback (EQUITY):** DSR=7.69, PBO=0.645 — promising but high overfit risk
- **fx_smart_carry_trade_momentum (FOREX):** DSR=6.88, PBO=0.593 — same issue

---

## 5. Path to Investable Strategies

1. **Fix data integrity first** — resolve the 62% TIME_EXIT phantom-closes diluting WR/PF
2. **Increase sample sizes** — most strategies have n < 30 resolved picks
3. **Reduce overfitting** — simplify strategy logic, add regularization, use purged WF during development
4. **Lower costs** — negotiate fee tiers, improve execution timing
5. **Re-run backtests monthly** — use `alpha_engine/rigorous_backtest_harness.py --batch`

### Re-run Backtests
```bash
# All strategies for one asset class
python3 alpha_engine/rigorous_backtest_harness.py --batch --class CRYPTO

# Single strategy
python3 alpha_engine/rigorous_backtest_harness.py --strategy stocks_rsi2_pullback --class EQUITY

# Custom parameters
python3 alpha_engine/rigorous_backtest_harness.py --batch --class FOREX --n-trials 200 --n-bootstrap 2000
```

---

## 6. Database Tables

| Table | Purpose | Rows |
|---|---|---|
| `strategy_summary` | Canonical strategy catalog with PF/WR/DSR/PBO/time-windows/traceability | 81 |
| `pick_dimension_snapshot` | Per-pick Score/Trust/AGV/Regime/Edge sub-tags | 3,000 |
| `pick_funnel_views` | Performance by nav-surface (Smart Picks button vs tab, etc.) | 6 |
| `edge_discovery` | Pre-computed edge significance with Bonferroni correction | 15 |
| `metric_dimensions` | Dictionary of all dimension values | 41 |
| `view_definition_catalog` | Documents every dashboard button/filter | 10 |

### Live Dashboard
- **Strategy Funnel section:** https://findtorontoevents.ca/audit/pick_funnel.html (Strategy Funnel section)
- **Data source:** https://findtorontoevents.ca/audit/data/strategy_funnel_data.json

---

## 7. Backtest Harness Reference

**File:** `alpha_engine/rigorous_backtest_harness.py`

**Key functions:**
- `run_backtest(pnl_series, asset_class)` — full rigorous backtest with DSR/PBO/WF/costs
- `purged_walkforward(pnl_series)` — purged k-fold walk-forward validation
- `compute_deflated_sharpe(sharpe, n_trials, n_obs)` — DSR per Bailey & Lopez de Prado (2014)
- `compute_pbo(pnl_matrix, n_splits, n_bootstrap)` — PBO per Bailey & Lopez de Prado (2015)
- `apply_costs(pnl_series, asset_class)` — cost/slippage adjustment

**Backtest result files:** `backtest_results/rigorous_backtest_*.json`

---

*Report generated from ejaguiar1_stocks database. All metrics computed from resolved picks with pnl_pct IS NOT NULL.
Data populated from 3,000 pick dimension snapshots + rigorous backtest harness with purged walk-forward, DSR, PBO, and cost modeling.*
