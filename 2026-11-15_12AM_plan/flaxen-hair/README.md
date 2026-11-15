# 2026-11-15 PM Plan — Flattened Profitability Framework

**Worktree:** flaxen-hair_2026-11-15T0038 | **Date:** 2026-11-15T00:38Z | **Repo:** findtorontoevents_antigravity.ca

---

## Executive Summary

**No asset class is proven profitable.** 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. All 9 classes return `sizing_allowed: false`.

**Only ETF Tactical Asset Allocation shows validated risk-adjusted performance:**
- Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51%, Calmar 0.48 vs 0.21
- Validated 2007-2026 including 2008 GFC
- Smart-beta (better risk-adjusted return, NOT alpha)

**EQUITY** is the only class with positive cost margin (3.23×, mean +0.323%, n=738) but not statistically significant (t=1.52, p=0.12).

**CRYPTO** is conditional — fill bug (`kimi_riseoftheclaw`) must be fixed first, then forward-test n≥100.

---

## Backtest Results — 42 Combinations Tested, 0 Passed P0 Gates

| Metric | Value |
|--------|-------|
| Total combinations tested | 42 |
| Strategies tested | 6 |
| Symbols tested | 10 |
| Strategies passing P0 gates | **0** |
| Strategies with n ≥ 50 trades | **0** |
| Best Sharpe | 1.14 (SPY connors_rsi2, n=6) |
| Best PF | 76.92 (SPY connors_rsi2, n=6 — inflated by tiny n) |

**Bottom line: No strategy is ready for live capital.** All have n < 10 trades — statistically insignificant.

### Top 5 by Profit Factor (min 5 trades):
| Symbol | Strategy | PF | WR | Sharpe | n |
|--------|----------|-----|-----|--------|---|
| SPY | connors_rsi2 | 76.92 | 83.3% | 1.14 | 6 |
| XLF | keltner_compression_v2 | 10.00 | 100.0% | 0.74 | 5 |
| GLD | ema_stack | 4.51 | 80.0% | 0.62 | 10 |
| GLD | funding_sentiment | 4.15 | 83.3% | 0.66 | 6 |
| SPY | funding_sentiment | 3.09 | 83.3% | 0.43 | 6 |

### Top 5 by Sharpe (min 5 trades):
| Symbol | Strategy | Sharpe | PF | WR | n |
|--------|----------|---------|-----|-----|---|
| SPY | connors_rsi2 | 1.14 | 76.92 | 83.3% | 6 |
| XLF | keltner_compression_v2 | 0.74 | 10.00 | 100.0% | 5 |
| GLD | funding_sentiment | 0.66 | 4.15 | 83.3% | 6 |
| GLD | ema_stack | 0.62 | 4.51 | 80.0% | 10 |
| SPY | funding_sentiment | 0.43 | 3.09 | 83.3% | 6 |

---

## Forward-Test Picks — 5 Active Paper Tests

| # | Symbol | Strategy | Direction | Entry | TP | SL | R:R | Status |
|---|--------|----------|-----------|-------|-----|-----|-----|--------|
| 1 | SPY | connors_rsi2 | LONG | 450.00 | 463.50 | 441.00 | 1.5 | PAPER TEST |
| 2 | XLF | keltner_compression_v2 | LONG | 42.00 | 43.26 | 41.16 | 1.5 | PAPER TEST |
| 3 | GLD | ema_stack | LONG | 2650.00 | 2729.50 | 2597.00 | 1.5 | PAPER TEST |
| 4 | GLD | funding_sentiment | LONG | 2650.00 | 2729.50 | 2597.00 | 1.5 | PAPER TEST |
| 5 | SPY | funding_sentiment | LONG | 450.00 | 463.50 | 441.00 | 1.5 | PAPER TEST |

All 5 picks written to `dashboard/live_picks.json` and `multi_asset/data/multi_asset_picks.json` with QA validation passed (0 critical flags).

---

## Forward-Test Tracking Protocol

### Kill Fast (Tier 1)
| Condition | Threshold | Action |
|-----------|-----------|--------|
| PnL = 0% with price movement | exit ≠ entry but pnl_pct = 0 | Kill immediately |
| Non-unique pick ID | Duplicate ID detected | Kill immediately |
| ml_score == confidence (>90% of picks) | Coupling detected | Kill immediately |
| Blank required fields | entry_price, direction, symbol missing | Kill immediately |
| Stale open position | > 72 hours with no price update | Mark EXPIRED |

### Hold Longer (Tier 2)
| Condition | Threshold | Action |
|-----------|-----------|--------|
| n < 50 trades | | Keep tracking, no capital |
| PF between 0.8-1.5 | | Watch, no capital |
| WR between 40-50% | | Watch, no capital |
| Sharpe between 0-0.5 | | Watch, no capital |

### Promote to Paper Trading (Tier 3)
| Condition | Threshold | Action |
|-----------|-----------|--------|
| n ≥ 50 trades | | Eligible for paper trading |
| PF ≥ 1.5 | | Eligible for paper trading |
| WR ≥ 50% | | Eligible for paper trading |
| Sharpe ≥ 0.5 | | Eligible for paper trading |
| MaxDD < 15% | | Eligible for paper trading |

### Promote to Live Capital (Tier 4)
| Condition | Threshold | Action |
|-----------|-----------|--------|
| n ≥ 100 forward picks | | Eligible for live capital |
| PF ≥ 1.5 forward | | Eligible for live capital |
| WR ≥ 55% forward | | Eligible for live capital |
| DSR ≥ 0.95 forward | | Eligible for live capital |
| 3+ months clean forward | | Eligible for live capital |

---

## Folder Structure

| Folder | Contents |
|--------|----------|
| `01_asset_class_plans/` | Per-class profitability plans ranked by probability |
| `02_holding_period_analysis/` | Per-class analysis by holding period vs trading style + backtest results + tracking protocol |
| `03_proven_algorithms/` | Top algorithms from TradingView contests |
| `04_subq_decision_support/` | Agent prompts, prediction markets analysis, SubQ fact-checking protocol |
| `05_framework_answers/` | Answers to all 6 detailed framework questions |
| `06_essential_questions/` | Essential questions for finding profitable algorithms |
| `07_company_turnarounds/` | Financial prediction/risk management company turnarounds |
| `08_key_metrics/` | Key metrics from different perspectives |

---

## Go/No-Go Decision

**NO-GO for live capital deployment today.**

**Conditions to revisit:**
1. Measurement gates pass (cohort_id, filter hash, source timestamp, row-level denominator reconciled)
2. Promotion gates fail closed (MONEY_READY_FDR_GATE and MONEY_READY_SINGLE_SOURCE_GATE enabled)
3. EQUITY pre-registered test: vs SPY total return, n≥500, OOS Sharpe ≥ SPY Sharpe AND PF ≥ 1.15, stability both halves
4. CRYPTO post-fix forward test: POSITION horizon n≥100, PF ≥ 1.3, WR ≥ 55%, after fill fix for kimi_riseoftheclaw
5. CI failure resolved (Python 3.11/3.12 test failures diagnosed and fixed)

If both EQUITY and CRYPTO fail pre-registered tests, keep both blocked and preserve passive benchmark sleeve (ETF TAA).

---

**Commit:** a83f635ea7c on `origin/main` — verified local and remote in sync.
