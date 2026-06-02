# Quant Review: Root Cause Analysis
## Why We Have No Production-Grade Strategies

**Date**: 2026-06-02
**Reviewer**: Quant Audit (automated)
**Scope**: Full strategy pipeline — backtesting, validation, production wiring, portfolio

---

## TL;DR — The Verdict

**Our strategies don't suck. Our backtesting infrastructure does.**

We have 100+ strategy implementations across 6 asset classes. The strategies themselves use sound academic logic (Bollinger mean reversion, VWAP reversion, Donchian breakouts, dual momentum, carry trade). The problem is that **every backtesting module has critical flaws that make results unreliable**, so we can't distinguish real edges from noise. We're flying blind.

**Root cause in one sentence**: Five backtesting modules with inconsistent, broken implementations — none of which can be trusted for production deployment.

---

## Part 1: Why Is the Portfolio Empty?

### The Dashboard Says "No Data Yet"

The portfolio at `findtorontoevents.ca/audit/pf.html?key=deepseek_v4__aggressive` shows:
- **Zero open positions**
- **Zero closed positions**
- **No NAV history**
- **No performance metrics**
- Message: "This portfolio has no data yet — first daily run is scheduled 22:00 UTC"

**Why**: The portfolio JSON file (`pf_portfolio_deepseek_v4__aggressive.json`) has never been written. The daily cron that generates portfolio data hasn't run for this key, or the key doesn't exist in the portfolio registry.

### Asset Class Verdict — ALL FAIL

| Asset Class | Verdict | PF | WR | Closed Picks | Root Cause |
|-------------|---------|-----|-----|-------------|------------|
| **EQUITY** | FAIL | 0.70 | 37.4% | 567 | Only 1 proven sleeve (`stocks_rsi2_pullback`, n=70) |
| **CRYPTO** | FAIL | 0.98 | 39.7% | 229 | Smart/HC/ELITE surfaces inflated by mislabeled `claude_gainer_st` |
| **ETF** | INSUFFICIENT | 0.34 | — | 13 | Backtests orphaned — no production wire-up |
| **COMMODITY** | FAIL | 0.475 | 9.1% | 3 | CT=F DSR=1.0 was FALSIFIED (6.33x over-emission) |
| **FOREX** | BLOCKED | 0.29 | 46.1% | — | Hard-gated via PR #6. Net PnL = -1026% |
| **BOND** | ACCUMULATING | — | — | 78 raw | Just started. Backtests PF 1.29-1.62 but orphaned |

**No asset class passes real-money thresholds** (DSR>0.95, PBO<0.05, WFE>60%, live-Sharpe>0.5, n>=100).

### ML Confidence Is an Anti-Signal

The ML scoring system is **inverted** — high confidence predicts LOW win rates:

| Confidence Band | CRYPTO WR | EQUITY WR |
|-----------------|-----------|-----------|
| 0.90+ | **14.4%** | — |
| 0.85-0.90 | — | **20%** |
| 0.75-0.80 | — | peak |
| 0.50-0.60 | **60.3%** | — |

**The ML system is actively destroying edge.** Picks with confidence >= 0.90 have 14.4% WR — worse than a coin flip.

---

## Part 2: The 22 Red Flags in Our Backtesting

### CRITICAL (Results Unreliable)

| # | Module | Issue |
|---|--------|-------|
| 1 | `real_data_backtest.py` | **Textbook data snooping**: signals generated on FULL dataset, then last 30% labeled "OOS". Not a real IS/OOS split. |
| 2 | `monte_carlo_validator.py` | **Permutation test is a no-op**: shuffles PnL order (not signs), so permuted mean = actual mean. P-values always ~0.5. Can never detect overfitting. |
| 3 | `rigorous_backtest_harness.py` | **PBO uses random sign flips** instead of actual strategy permutations. PBO values are meaningless — they'll always look good. |
| 4 | `real_data_backtest.py` | **No walk-forward at all** despite claiming "proper IS/OOS split" and "walk-forward consistency." |

### HIGH (Significant Bias)

| # | Module | Issue |
|---|--------|-------|
| 5 | `walk_forward_backtester.py` | **No purge/embargo** between train and test windows. Autocorrelated features (EMA, MACD, RSI) leak across the boundary. |
| 6 | `walk_forward_backtester.py` | **No parameter optimization** — same parameters on train and test. This is rolling evaluation, not walk-forward optimization. |
| 7 | ALL modules | **No transaction costs** in 4 of 5 modules. The repo has excellent cost models (`slippage_model.py`, `transaction_costs.py`) but NONE are wired to the backtest engines. |
| 8 | ALL modules | **Survivorship bias** — universe includes only currently-listed, high-volume symbols. Dead assets (LUNA, FTT, UST) excluded. |
| 9 | `walk_forward_backtester.py` | **DSR/Bonferroni default to PASS** when data unavailable. Conservative default should REJECT, not accept. |

### MEDIUM (Methodology Issues)

| # | Module | Issue |
|---|--------|-------|
| 10 | ALL modules | **Sharpe uses sqrt(252)** regardless of trade frequency. Overstates for high-frequency, understates for low-frequency. |
| 11 | `rigorous_backtest_harness.py` | **JSON fallback creates synthetic data** from summary stats. All subsequent validation is tautological. |
| 12 | `battle_test_rigorous.py` | **MC null test is sign-flip**, not proper permutation. Doesn't test timing of wins/losses. |
| 13 | `battle_test_rigorous.py` | **Zero transaction costs** — losing strategies appear profitable. |
| 14 | `monte_carlo_validator.py` | **Multi-symbol robustness** passes with 2 trades per symbol. Not statistically distinguishable from coin flip. |
| 15 | `rigorous_backtest_harness.py` | **DSR uses simplified formula** vs the correct implementation in `walk_forward_backtester.py`. Two modules give different results for same data. |
| 16 | ALL modules | **Bootstrap CIs use fixed seed** — single realization, not honest uncertainty. |

### The 5-Module Inconsistency Problem

| Feature | rigorous_harness | walk_forward_backtester | battle_test | real_data_backtest | monte_carlo_validator |
|---------|-----------------|------------------------|-------------|-------------------|----------------------|
| Walk-forward | PnL split (broken) | Rolling eval (no optimization) | Step=1 | None (data snooping) | K-fold on PnL |
| Purge/embargo | Yes (cosmetic) | **No** | **No** | **No** | **No** |
| Transaction costs | Flat per-trade | **None** | **None** | **None** | **None** |
| DSR | Simplified formula | Correct formula | **None** | **None** | **None** |
| PBO | Sign flips (broken) | **None** | **None** | **None** | **None** |
| Permutation test | **None** | **None** | Sign flip | **None** | Order shuffle (no-op) |

**Five modules, five different implementations of the same concepts, none fully correct.**

---

## Part 3: Why Strategies Fail to Reach Production

### The Pipeline

```
Strategy Signal → Production Scanner → Smart Picks Engine → Quality Gates → Audit Dashboard → Portfolio
```

### Bottleneck 1: Quality Gates Are Too Strict for Broken Infrastructure

The gates require:
- DSR > 0.95 (but DSR implementation is wrong)
- PBO < 0.05 (but PBO uses sign flips — always looks good)
- Walk-forward consistency > 60% (but no real walk-forward exists)
- Live Sharpe > 0.5 (but no costs modeled — inflates Sharpe)

**Result**: Strategies that should pass (real edge) fail because the validation is broken. Strategies that should fail (no edge) sometimes pass because the tests are too lenient.

### Bottleneck 2: ML Confidence Is Inverted

The `smart_picks_engine.py` uses ML confidence to rank picks. But confidence is anti-predictive:
- High confidence (0.90+) → 14.4% WR
- Low confidence (0.50-0.60) → 60.3% WR

**The system is actively selecting the WORST picks.**

### Bottleneck 3: Orphaned Backtests

ETF strategies (`etf_sector_rotation`, `etf_rotation_vix_regime`) have backtests showing edge but are never wired to production. BOND strategies show PF 1.29-1.62 but only started accumulating picks on 2026-05-31.

### Bottleneck 4: Data Quality Issues (Fixed)

Ghost rows (22,947) and status-PnL mismatches have been fixed as of 2026-05-31. But the `claude_gainer_st` mislabeling issue still inflates CRYPTO Smart Picks.

---

## Part 4: Where IS Our Edge?

### Confirmed Edge (Multiple Validation Methods)

| Strategy | Asset | Evidence | Confidence |
|----------|-------|----------|------------|
| **VWAPReversion** | CRYPTO | Walk-forward PASS, DSR=21.4, PBO=0.18 on 4h, 516 OOS trades | HIGH |
| **BollingerMR** | CRYPTO | Walk-forward PASS, OOS PF=1.673, WR=52.6% | MEDIUM |
| **CryptoDonchianBreakout** | CRYPTO | Walk-forward PASS all 3 symbols, DSR=7.24 | MEDIUM |
| **DualMomentum** | CRYPTO | Walk-forward PASS, OOS PF=1.133 | MEDIUM |
| **stocks_rsi2_pullback** | EQUITY | Live: n=70, WR=62.9%, only proven equity sleeve | MEDIUM |
| **OBV Divergence** | CRYPTO | 115 trades, WR=75.7%, PF=8.15, 15 WF folds, 100% consistency | HIGH |

### Potential Edge (Needs Validation)

| Strategy | Asset | Evidence | What's Missing |
|----------|-------|----------|----------------|
| BOND backtests | BOND | PF 1.29-1.62 | Production wire-up + live data |
| ETF rotation | ETF | Backtest shows edge | Production wire-up |
| Faber TAA | EQUITY | Sharpe 1.74 on SPY, 1.65 on QQQ | MC significance (too few trades) |
| Carry Trade | FOREX | Sharpe 1.27 on AUDJPY | FRED rate data fix |

### Anti-Edge (Confirmed Dead)

| Strategy | Asset | Evidence |
|----------|-------|----------|
| ConnorsRSI2 | CRYPTO | Sharpe -2.6, bleeds 89-97% despite 60% WR |
| FundingRateMR | CRYPTO | Walk-forward FAIL (PF=0.976) |
| FOREX (all) | FOREX | Net PnL = -1026%, hard-gated |
| COMMODITY | COMMODITY | DSR=1.0 was falsified, n=3 |
| ML confidence | ALL | Anti-predictive (inverted) |

---

## Part 5: The Diagnosis — Do We Need More Time, or a Complete Rethink?

### We Need a COMPLETE RESTRUCTURE of Backtesting

**Not more time. Not more strategies. Fix the infrastructure first.**

The strategies are fine. The backtesting is broken. Here's the proof:
- VWAPReversion passes walk-forward with PBO=0.18 on 4h data — this is a real edge
- But the same strategy shows PBO=0.816 on daily data — the timeframe matters
- The backtesting modules give contradictory results for the same strategy
- We can't trust any single result because the methodology is inconsistent

### The 5 Things We Must Fix (Priority Order)

#### 1. UNIFY THE BACKTEST ENGINE (P0)
Merge 5 modules into 1 canonical engine. Kill the other 4. The canonical engine must:
- Run strategy on raw OHLCV data (not pre-computed PnL)
- Proper purged walk-forward: optimize on train, lock params, generate signals on test, purge gap between
- Wire in existing cost models (`transaction_costs.py`, `slippage_model.py`)
- Correct DSR (Lopez de Prado eq. 7 with Euler-Mascheroni)
- Correct PBO (parameter permutations, not sign flips)
- Correct permutation test (shuffle signs, not order)
- Trade-frequency-aware Sharpe annualization

#### 2. FIX ML CONFIDENCE (P0)
The ML system is anti-predictive. Options:
- **Invert the signal**: trade LOW confidence picks (60.3% WR) instead of HIGH (14.4% WR)
- **Recalibrate**: retrain the ML model with proper IS/OOS split
- **Disable**: remove ML scoring until fixed, use raw strategy signals

#### 3. WIRE ORPHANED STRATEGIES (P1)
ETF and BOND strategies have backtests showing edge but are never wired to production. Wire them up and let them accumulate live data.

#### 4. INCLUDE DEAD ASSETS (P1)
Add LUNA, FTT, UST, and other dead tokens to the crypto universe. Add delisted tickers to equities. This eliminates survivorship bias.

#### 5. TRACK CUMULATIVE STRATEGY COUNT (P2)
The DSR `n_trials` should reflect the TOTAL number of strategies ever tested, not just the current report. We've tested 100+ strategies — the multiple-testing penalty is severe.

---

## Part 6: Should We DNA-Mutate or Invert Strategies?

### DNA Mutation — YES, But Only After Fixing Infrastructure

The `tools/mutation_analysis.py` exists but is a diagnostic tool, not an optimizer. What we need:
- Parameter grid search on IS data
- Walk-forward validation on OOS data
- Symbol-specific optimization (edge is symbol-specific, not universal)

### Strategy Inversion — YES for ML Confidence, NO for Strategies

- **ML Confidence**: Invert. Trade low-confidence picks. The data is clear.
- **Strategies**: Don't invert. ConnorsRSI2 fails because avg_loss > avg_win, not because the direction is wrong. The fix is better exit logic (time stops, tighter ATR stops), not inversion.

### Data Feed Issues — PARTIALLY

- FRED rate CSV times out from gx10 — need `FRED_API_KEY` or desktop fetch for carry trade
- `fetch_crypto_ohlcv_paginated` returns 300 bars by default (should be 1500+) — this limits walk-forward windows
- No historical funding rate data — `CryptoFundingRateArb` generates 0 trades with dummy rates

---

## Part 7: Action Plan

### This Week (P0)
1. **Create unified backtest engine** — merge 5 modules into 1, fix all 22 red flags
2. **Fix ML confidence** — invert or disable
3. **Run VWAPReversion through correct walk-forward** — if it still passes, wire to paper trading

### Next Week (P1)
4. **Wire ETF + BOND strategies to production** — let them accumulate live data
5. **Add dead assets to universe** — survivorship-bias-free backtesting
6. **Run all 100+ strategies through unified engine** — find the real edges

### This Month (P2)
7. **Parameter mutation pipeline** — automated grid search + walk-forward
8. **Forward-test integration** — connect backtest engine to live price tracking
9. **Portfolio construction** — once we have 3+ validated strategies, build a portfolio

---

## Appendix: Evidence Sources

- Portfolio page: `findtorontoevents.ca/audit/pf.html?key=deepseek_v4__aggressive` — empty
- Audit dashboard: `findtorontoevents.ca/audit/` — all asset classes FAIL
- AI tournament: `findtorontoevents.ca/audit/ai-tournament.html` — 39 models, no resolved picks
- Pick funnel: `findtorontoevents.ca/audit/pick_funnel.html` — pipeline exists but empty
- Backtesting modules: `alpha_engine/rigorous_backtest_harness.py`, `walk_forward_backtester.py`, `battle_test_rigorous.py`, `real_data_backtest.py`, `monte_carlo_validator.py`
- Verification report: `verified_strategies/VERIFICATION_REPORT.json`
- Walk-forward report: `verified_strategies/WALKFORWARD_REPORT.json`
- Edge report: `verified_strategies/HEDGE_FUND_EDGE_REPORT.md`
