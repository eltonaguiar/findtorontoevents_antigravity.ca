# Performance Issues & Root Cause Analysis
**Date:** 2026-05-31  
**Tool:** `tools/monte_carlo_edge_audit.py` (10,000-sample bootstrap, 95% CI)  
**Data Source:** `ejaguiar1_stocks.trading_picks` (all-time, all resolved statuses)

---

## Executive Summary

After running Monte Carlo bootstrap significance testing (N=10,000 resamples) across ALL asset classes with n≥12, **zero asset classes pass industry-standard thresholds at the class level.** The system has exactly **1 proven TIER-1 strategy** (`mega_mutation` CRYPTO, PF 3.33, 95% CI low 2.57) and **5 promising small-n candidates.** Every other strategy with PF>5.0 achieves it through outlier concentration (WR<15%), not repeatable edge.

---

## Per-Asset-Class Reality

| Class | Total n | WR | PF | PF 95% CI low | Verdict |
|-------|---------|-----|------|---------------|---------|
| CRYPTO | 7,764 | 52.3% | 1.41 | 1.20 | Only class with positive PF CI — driven by mega_mutation |
| FUTURES | 378 | 0.3% | 10.28 | 0.95 | Outlier-driven, unexecutable (wins 1 in 333 trades) |
| EQUITY | 8,655 | 27.4% | 0.62 | 0.58 | No strategy has PF>1.0 at class level |
| FOREX | 8,814 | 46.1% | 0.29 | 0.26 | 3 of 4 top strategies have WR<6% |
| COMMODITY | 3,507 | 7.8% | 0.17 | 0.15 | Every single strategy is a DESTROYER |
| ETF | 75 | 42.7% | 1.41 | 0.68 | CI includes <1.0 — too few trades |
| BOND | 24 | 62.5% | 2.11 | 0.82 | CI includes <1.0 — too few trades |
| MEMECOIN | 19 | 5.3% | 0.89 | 0.42 | Nearly unexecutable |

---

## Root Cause #1: Outlier-Driven Profit Factor (The "High PF, Terrible WR" Trap)

The most pervasive problem: strategies showing PF>5.0 achieve it through 1-3 massive wins, not consistent edge.

| Strategy | Dir | n | WR | PF | Reality |
|----------|-----|----|-----|------|---------|
| prediction_market_consensus | SHORT | 1,526 | **2.8%** | 36.8 | Wins 1 in 36 trades |
| non_crypto_consensus | SHORT | 1,322 | **4.2%** | 24.0 | Wins 1 in 24 trades |
| ig_contrarian_sentiment | SHORT | 2,475 | **5.2%** | 13.6 | Wins 1 in 19 trades |
| combined_confidence | SHORT | 36 | **13.9%** | 51.2 | Wins 1 in 7 trades |
| cta_golden_cross_200 | LONG | 232 | **10.3%** | 17.4 | Wins 1 in 10 trades |

**Root Cause:** These strategies use fixed TP/SL ratios (e.g., 3:1, 5:1) and rely on rare outsized moves hitting TP. The high PF is a mathematical artifact of asymmetric R:R, not predictive edge. A strategy with WR<15% is unexecutable in live trading — you'd quit after 10 consecutive losses.

**Fix Applied (PR #6):** FOREX strategies now blocked except `cta_cross_asset_tsmom` SHORT.

---

## Root Cause #2: COMMODITY — Universal Destructive Edge

Every COMMODITY strategy with n≥30 is a DESTROYER (PF 95% CI < 1.0):

| Strategy | Dir | n | WR | PF | PF CI low |
|----------|-----|----|-----|------|-----------|
| futures_momentum | LONG | 698 | 21.1% | **0.17** | 0.12 |
| cta_cross_asset_tsmom | SHORT | 715 | 2.4% | **0.37** | 0.25 |
| cta_commodity_momentum_term | LONG | 1,026 | 1.9% | **0.36** | 0.26 |
| futures_momentum | SHORT | 1,055 | 7.9% | **0.34** | 0.27 |

**Root Cause:** Commodity TP distances average 5.47% vs realistic ATR-reach of 0.72% at 24h hold. Picks sit dead until expiry, producing 92%+ LOST/EXPIRED outcomes. The `ATR_REACH_GATE` exists but defaults OFF (`ATR_REACH_GATE=0`).

**Status:** ❌ NOT YET HARD-DISABLED. Strategies still listed in `NON_CRYPTO_STRATEGY_POLICY` with probation thresholds.

---

## Root Cause #3: FOREX — LONG Is Systematically Destructive

Every FOREX LONG strategy is a destroyer:

| Strategy | Dir | n | WR | PF |
|----------|-----|----|-----|------|
| forex_rsi2_mean_reversion | SHORT | 1,372 | 14.2% | 0.26 |
| ig_contrarian_sentiment | LONG | 1,609 | 3.7% | 0.24 |
| non_crypto_consensus | LONG | 907 | 2.1% | 0.22 |
| myfxbook_retail_contrarian | LONG | 1,141 | 5.7% | 0.29 |

**Root Cause:** FOREX mean-reversion strategies generate LONG signals when price is below mean, but in trending markets these become momentum trades in the wrong direction. The carry-trade bias (long high-yield, short low-yield) structurally favors SHORT on funding currencies (JPY, CHF, EUR).

**Fix Applied (PR #6):** FOREX strategy consolidation gate blocks all FOREX strategies except `cta_cross_asset_tsmom` SHORT. `FOREX_HARD_DISABLE` env var defaults ON.

---

## Root Cause #4: EQUITY — Negative Expectancy at Class Level

Class PF 0.62, WR 27.4%. No EQUITY strategy has PF>1.0 at n≥30.

**Root Cause:** EQUITY picks are dominated by penny/meme stocks (GME, AMC, NIO, LCID) that gap against the signal direction. The `LARGE_CAP_EQUITY_SYMBOLS` filter exists but is not enforced at the emission gate — `quality-momentum-scout` and `post-earnings-rev-scout` still emit on speculative names.

**Status:** ❌ NOT YET HARD-DISABLED. Equity strategies remain in policy with probation thresholds.

---

## Root Cause #5: No Per-Class Hard-Disable Mechanism

The system lacks a clean pattern to hard-disable an entire asset class at the emission gate. The `FOREX_HARD_DISABLE` flag exists in `config.py` but:
- It's env-var gated (flips OFF on restart without `.env`)
- It only exists for FOREX — no COMMODITY or EQUITY equivalent
- The `evaluate_non_crypto_candidate` function in `non_crypto_policy.py` doesn't check it

**Fix Needed:** Add `COMMODITY_HARD_DISABLE` and `EQUITY_HARD_DISABLE` flags, enforce them in `evaluate_non_crypto_candidate` before the strategy policy check.

---

## The Only Proven Edge

| # | Class | Strategy (source) | Dir | n | WR | PF | PF 95% CI low |
|---|-------|-------------------|-----|----|-----|------|---------------|
| 1 | CRYPTO | **mega_mutation** (NULL-strat) | — | 283 | **65.4%** | **3.33** | **2.57** |

Source system: `source_system='mega_mutation'`. Heavily LONG-biased (425 LONG, 27 SHORT). Top symbols: BTC, ETH, SOL — major caps only. This is the only strategy passing both WR (>50%) and PF significance (CI low > 2.0) with adequate sample size.

**Problem:** The strategy name is NULL in `trading_picks` — it's tracked only by `source_system`. It needs a formal strategy name, policy entry, and monitoring.

---

## Promising Small-n Candidates (Need n≥50)

| Strategy | n | WR | PF | CI low | Note |
|----------|----|-----|------|--------|------|
| ml_enhanced_DYDXUSDT LONG | 34 | 94.1% | 10.36 | 3.04 | Per-symbol ML ensemble |
| ml_enhanced_INJUSDT LONG | 26 | 92.3% | 35.64 | 8.57 | Per-symbol ML ensemble |
| luxalgo_confluence LONG | 24 | 91.7% | 40.62 | 11.30 | LuxAlgo community signals |
| ml_enhanced_RENDERUSDT LONG | 39 | 64.1% | 4.34 | 1.64 | CI low < 2.0 |
| ml_enhanced_FETUSDT LONG | 29 | 48.3% | 6.02 | 2.06 | Borderline WR |

**Pattern:** Per-symbol ML ensembles (DYDX, INJ, RENDER, FET) consistently outperform generic strategies. The ML model learns symbol-specific microstructure, which generic strategies cannot.

---

## P0 Action Items (Not Yet Implemented)

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| **P0** | Hard-disable COMMODITY at emission gate | Stops 3,507 destructive picks | 5 lines |
| **P0** | Hard-disable EQUITY at emission gate | Stops 8,655 negative-expectancy picks | 5 lines |
| **P0** | Add COMMODITY_HARD_DISABLE + EQUITY_HARD_DISABLE env flags | Prevent restart-undo | 10 lines |
| **P1** | Document & name mega_mutation strategy | Track the only proven edge properly | 30 lines |
| **P1** | Remove outlier-PF strategies from TIER classification | Stop classifying WR<15% as "edge" | 20 lines |
| **P2** | Deploy undeployed backtested strategies (bond_*, futures_tsmom, gold_safe_haven) | Build forward records on probation | Deploy only |
| **P2** | Enable ATR_REACH_GATE for COMMODITY | Block TP>5% picks (92% of losses) | Flip env var |

---

## What's Already Been Fixed (This Session)

| Fix | File | Status |
|-----|------|--------|
| PR #6: FOREX strategy consolidation gate | `alpha_engine/non_crypto_policy.py` | ✅ Committed (`0b94451bc`) |
| `dxy_trend_filter` probation policy entry | `alpha_engine/non_crypto_policy.py` | ✅ Committed (`0b94451bc`) |
| `tools/monte_carlo_edge_audit.py` (bootstrap tool) | `tools/monte_carlo_edge_audit.py` | ✅ Committed (`6fca7d786`) |
| `reports/money_maker_ready_v2_deep_dive_2026-05-31.md` | `reports/` | ✅ Committed (`6fca7d786`) |
| FOREX strategies blacklisted in config | `alpha_engine/config.py` | ✅ Committed (`0b94451bc`) |
| `forex_rsi2_mean_reversion`, `inverse_carry_contrarian`, `carry_trade_momentum`, `forex_carry_ppp` removed from policy | `alpha_engine/non_crypto_policy.py` | ✅ Committed (`0b94451bc`) |

---

## Methodology

All findings backed by `tools/monte_carlo_edge_audit.py`:
- **10,000 bootstrap resamples** with replacement from `trading_picks` (all-time resolved)
- **95% confidence interval** via `np.percentile` on resampled PF distribution
- **TIER classification:** TIER-1 (PF CI low > 2.0, WR > 50%, n > 50), EDGE (PF CI low > 1.0, n > 30), DESTROYER (PF CI high < 1.0)
- **RANDOM_SEED = 42** for reproducibility
- **Status filter:** WON, LOST, SL_HIT, TP_HIT, EXPIRED, TIME_EXIT (all resolved)

---

## Next Steps

1. Run `python3 tools/monte_carlo_edge_audit.py --min-n 15` weekly to track per-class PF trajectory
2. After COMMODITY/EQUITY hard-disable, re-run to measure class-level PF improvement
3. At n≥50 on ml_enhanced_DYDXUSDT/INJUSDT, re-audit for TIER-1 promotion
4. After 30 days of FOREX SHORT-only, re-audit FOREX class metrics
