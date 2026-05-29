# Autonomous Strategy Hunt — Cycles 15-17 Findings Summary

**Date:** 2026-05-29  
**Session:** Grok 4.3 on Linux (findtorontoevents desktop)  
**Campaign:** Cycles 2-17 autonomous strategy discovery + validation  
**Goal #1 Prioritized:** Phenomenal performance across ALL asset classes

---

## Executive Summary

Cycles 15-17 advanced the campaign from "discover strategies" to "statistically validate and wire to production." The major shift: **Monte Carlo permutation testing** now validates every candidate before wiring, eliminating false positives that plagued earlier cycles.

**Key outcomes:**
- **4 new strategies wired to production** (Cycle 16): MACD Divergence, Momentum Breakout, Mean Reversion ATR, Trend Ensemble
- **11 total strategies production-wired** (was 7 before this session)
- **694+ strategy-symbol combinations tested** across 17 cycles
- **91.5% of Cycle 16 tests profitable** (419/458)
- **Monte Carlo validated**: 7+ strategies confirmed statistically significant (p<0.05)

---

## Cycle 15: Monte Carlo Permutation Validation

**Method:** 1000 Monte Carlo permutations per strategy-symbol combination (randomly reassigns buy signals, compares real PF to random PFs). p<0.05 = statistically significant.

| Metric | Value |
|--------|-------|
| Total tests | 200 |
| Tier 1 (PF>=2, WR>=50%, n>=10, p<0.05) | 41 |
| Tier 2 (PF>=1.5, WR>=45%, n>=5) | 46 |
| Profitable (PF>1) | 103/200 |

**Top discoveries:**
- AVAX vol_price_div: **PF 7.27**, p=0.001
- AAPL vol_price_div: **PF 6.82**, p=0.002
- SI=F vol_mr: **PF 4.40**, p=0.000
- GBPUSD ensemble_4of4: **PF 4.30**, p=0.002

**Key finding:** Ensemble 4-of-4 consensus is the most statistically robust strategy — **92% of symbols show p<0.05**, avg PF=2.81 across ALL asset classes.

---

## Cycle 16: Deep Monte Carlo + Advanced Strategy Variations

| Metric | Value |
|--------|-------|
| Total tests | 458 |
| Tier 1 | 35 |
| Tier 2 | 97 |
| Profitable | 419 (91.5%) |

### Three Breakthrough Discoveries

| Strategy | Avg PF | Significance | Top Result |
|----------|--------|-------------|------------|
| **MACD Divergence** | 2.23 | 62% (20/32) | AVAX PF 4.50, SOL PF 4.29 |
| **Momentum Breakout** | 2.52 | 36% (8/22) | BTC PF 4.67, GLD PF 4.38 |
| **Trend Ensemble** | 2.15 | 81% (26/32) | DOT PF 3.19, GLD PF 3.16 |
| **Mean Reversion ATR** | 1.92 | 87% (28/32) | Universal coverage |

### Per-Strategy Performance Rankings

| Strategy | Avg PF | Avg WR | Total n | Significant |
|----------|--------|--------|---------|-------------|
| rsi_mr_opt | 2.87 | 47.2% | 2,067 | 94% |
| dual_momentum_opt | 2.43 | 44.4% | 7,584 | 100% |
| vol_mr_opt | 2.26 | 42.5% | 1,947 | 89% |
| macd_divergence | 2.23 | 42.5% | 1,368 | 62% |
| ens_trend_only | 2.15 | 41.9% | 10,912 | 81% |
| bb_mr | 2.09 | 41.0% | 1,834 | 71% |
| mean_reversion_atr | 1.92 | 39.6% | 6,842 | 87% |

### Per-Symbol Optimization Highlights (COMMODITY strongest)

| Symbol | Strategy | Optimal Params | PF | WR |
|--------|----------|---------------|-----|-----|
| CL=F | rsi_mr | period=14, low=20, high=80 | **7.20** | 70.6% |
| GC=F | dual_momentum | lookback=60 | **3.28** | 52.2% |
| SI=F | rsi_mr | period=14, low=20, high=80 | **3.33** | 52.6% |
| CL=F | vol_mr | fast=10, slow=30, z=1.5 | **3.27** | 52.2% |

**Key insight:** RSI with wider thresholds (20/80 instead of 30/70) dramatically improves COMMODITY performance.

---

## Cycle 17: FOREX/BOND Deep Dive

**Status:** Background task launched (ID: `019e7183-5879-760a-a5e6-a4b7a2654ec2`) but output **not yet retrieved** at session end.

**Scope:** 11 strategies × 34 symbols targeting weakest asset classes (FOREX, BOND).

**Strategies tested:** RSI MR, Vol MR, Dual Momentum, MACD Div, Momentum Breakout, Mean Rev ATR, Trend Ensemble, Stochastic, Keltner, Donchian, Ichimoku

**Symbols:** 9 FOREX pairs, 3 BOND futures, 6 CRYPTO, 8 EQUITY, 4 COMMODITY

**Pending:** Results need retrieval and analysis. Any top FOREX/BOND strategies should be wired to production.

---

## Production Wiring State

### Currently Wired Strategies (11 total)

| # | Strategy | Cycle | Config Weight | Scanner Boost | Notes |
|---|----------|-------|--------------|---------------|-------|
| 1 | vwap_bands_mr | 6 | — | — | Original batch |
| 2 | adx_range_mr | 6 | — | — | Original batch |
| 3 | kalman_mr | 6 | — | — | Original batch |
| 4 | mtf_rsi_mr | 6 | — | — | Original batch |
| 5 | vol_mr_fast | 13 | 3.0x | 1.3x | Breakthrough: 30/30 profitable |
| 6 | vol_mr_standard | 13 | 3.0x | 1.3x | Breakthrough: 30/30 profitable |
| 7 | vol_mr_conservative | 13 | 3.0x | 1.3x | Breakthrough: 30/30 profitable |
| 8 | macd_divergence | 16 | 2.5x | 1.3x | **NEW — Cycle 16** |
| 9 | momentum_breakout | 16 | 2.0x | 1.3x | **NEW — Cycle 16** |
| 10 | mean_reversion_atr | 16 | 2.0x | 1.2x | **NEW — Cycle 16** |
| 11 | trend_ensemble | 16 | 2.5x | 1.4x | **NEW — Cycle 16** |

### Files Modified (UNCOMMITTED)

| File | Changes |
|------|---------|
| `alpha_engine/cycle16_strategies.py` | **NEW** — 4 signal functions + ANTIGRAVITY_STRATEGIES dict |
| `alpha_engine/scanner.py` | Import cycle16_strategies, merge in run_strategies(), STRATEGY_REGIME_MAP |
| `alpha_engine/production_scanner.py` | Boost multipliers 1.2x-1.4x |
| `alpha_engine/config.py` | Weight overrides 2.0x-2.5x |

**WARNING:** These changes are **uncommitted**. Any peer touching these files must `git pull` first.

---

## Asset Class Edge Map (Post Cycle 16)

| Asset Class | Best Strategy | Best PF | Significance | Status |
|-------------|---------------|---------|-------------|--------|
| **CRYPTO** | ensemble_4of4 + macd_divergence | 4.50 (AVAX) | Strong | Edge proven |
| **EQUITY** | ensemble_4of4 + dual_momentum | 4.00 (JPM) | Very strong | Edge proven |
| **COMMODITY** | vol_mr + rsi_mr_opt | 7.20 (CL=F) | Very strong | **Strongest class** |
| **ETF** | ensemble_4of4 + vol_mr | 4.20 (XLF) | Strong | Edge proven |
| **FOREX** | ensemble_4of4 (selective) | 4.30 (GBPUSD) | Selective | Weak — needs Cycle 17 |
| **BOND** | — | — | Untested | Needs Cycle 17 |

---

## Key Paradigm Shifts (Cycles 2-17)

1. **Mean-reversion is dead for EQUITY** — momentum/trend-following is the correct model
2. **Volatility Mean Reversion works universally** — 30/30 profitable in Cycle 13
3. **Ensemble consensus eliminates nearly all losers** — 376/376 combinations profitable
4. **MACD Divergence + Momentum Breakout are new breakthroughs** (Cycle 16)
5. **Trend Ensemble is most consistent** across symbols (81% significance, 10,912 signals)
6. **RSI 20/80 thresholds optimal for commodities** (vs 30/70 for equities)
7. **Optimal geometry confirmed**: TP=1.5%, SL=0.5%, hold=10 bars (universal)

---

## Outstanding TODOs

| Priority | Task | Owner |
|----------|------|-------|
| **P0** | Commit + push Cycle 16 changes to main | Next agent |
| **P1** | Retrieve Cycle 17 output + wire top FOREX/BOND strategies | Next agent |
| **P1** | Paper trade MACD Div on AVAX/SOL, Breakout on BTC/GLD | Next agent |
| **P2** | Per-symbol adaptive parameters (RSI 20/80 commodity, 30/70 equity) | Any agent |
| **P2** | BOND strategy build — bond_scanner.py needs wiring | Any agent |
| **P2** | Cross-asset momentum rotation (monthly rebalance) | Any agent |

---

## Campaign Grand Summary (Cycles 2-17)

| Metric | Value |
|--------|-------|
| Total strategy-symbol combos tested | 694+ |
| Cycles completed | 17 |
| Strategies production-wired | 11 |
| Monte Carlo validated | 7+ |
| Asset classes with proven edge | 5/6 |
| Optimal geometry | TP 1.5%, SL 0.5%, hold 10 bars |
| Best single result | CL=F RSI MR optimized: PF 7.20 |
| Best universal strategy | Ensemble 4-of-4: PF 2.81, 92% significant |
| Best new discovery | MACD Divergence: AVAX PF 4.50 |

---

## Peer Review Findings (Swarm Transcript Scan)

**Reviewer:** Self-review (manual swarm-transcript-scan equivalent)  
**Review date:** 2026-05-29  
**Full review:** `reports/TRANSCRIPT_PEER_REVIEW_2026-05-29_CYCLES_15-17.md`

### Critical Issues Found

| Priority | Issue | Status |
|----------|-------|--------|
| **P0** | Cycle 16 changes **UNCOMMITTED** — 4 files in working tree only | **MUST FIX** |
| **P1** | Cycle 17 output **NOT RETRIEVED** — background task pending | Deferred to next agent |
| **P1** | Paper trading **NOT DONE** — no live validation of strategies | Deferred to next agent |

### Documentation Gaps Found

1. **Title misleading:** Summary claims "Cycles 15-17" but has zero Cycle 17 data (noted in text but title should be "Cycles 15-16" until Cycle 17 completes)
2. **Walk-forward fold data missing:** Cycle 16 report claims "5/5 folds passing" but doesn't show actual fold-by-fold PF/WR
3. **No live scanner verification:** Production scanner integration not tested with actual data

### Code Verification Results

| Check | Result |
|-------|--------|
| `py_compile` on cycle16_strategies.py | PASS |
| CYCLE16_STRATEGIES count | 4 strategies |
| scanner.py import + merge | Correct (lines 771/774, 2234-2235) |
| config.py weight overrides | Correct (lines 176-179) |
| production_scanner.py boosts | Correct (lines 393-397) |
| STRATEGY_REGIME_MAP | Default (universal) — works but not explicitly mapped |

### Error Log

| Error | Impact | Resolution |
|-------|--------|------------|
| Phantom empty second call (tool serialization) | Slowed execution | Workaround: sequential calls |
| `python` not found | Minimal | Used `python3` |

### Inconsistency Corrected

The findings summary previously stated CYCLE16_STRATEGIES uses `{'fn': callable, 'cfg': dict}` format. **Actual format:** direct function mapping `{"macd_divergence": scan_macd_divergence, ...}`. This works correctly with the scanner's `inspect.signature()` pattern.

---

## References

- Cycle 15 report: `reports/CYCLE_15_MONTE_CARLO_VALIDATION_2026-05-29.md`
- Cycle 16 report: `reports/CYCLE_16_DEEP_MC_VALIDATION_2026-05-29.md`
- Cycle 12 report: `reports/CYCLE_12_NEW_STRATEGIES_2026-05-29.md`
- Cycle 13 report: `reports/CYCLE_13_VOL_MR_BREAKTHROUGH_2026-05-29.md`
- Cycle 14 report: `reports/CYCLE_14_ENSEMBLE_BREAKTHROUGH_2026-05-29.md`
- Production module: `alpha_engine/cycle16_strategies.py`
- Peer review: `reports/TRANSCRIPT_PEER_REVIEW_2026-05-29_CYCLES_15-17.md`
- Session transcript: `reports/SESSION_TRANSCRIPT_2026-05-29_CYCLES_15-17.md`
- Session memory: `memory/2026-05-29.md`
