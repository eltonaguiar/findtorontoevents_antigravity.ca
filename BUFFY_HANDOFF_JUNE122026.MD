# BUFFY HANDOFF — June 12 2026 (Full Session)

**From:** Buffy (deepseek-v4-pro) — Codebuff session  
**To:** Freebuff / Operator / Next agent  
**Files changed:** `alpha_engine/config.py`, `audit_trail/quality_gates.py`, `tools/backtest_new_strategies_june2026.py` (NEW), `FREEBUFF_JUNE122026.MD`  
**Evidence:** `reports/new_strategies_june2026_20260612_0400.json`

---

## 0. TL;DR

Three workstreams completed this session:

1. **Forensic autopsy hardening** — M-110 direction gating, M-111 monkey-test P95 gate, STRATEGY_WEIGHT_OVERRIDES reset, BLACKLISTED_STRATEGIES + MIN_ELITE_SCORE floor reversal
2. **10 new strategies designed & backtested** — 4 beat class baselines, 0 pass monkey-test P95 (consistent with 0/9 money-ready), 4 registered as MONITORED
3. **picks-now.html methodology swarm-reviewed** — council of Skeptic/Pragmatist/Critic produced 7 ranked enhancements, top 2 are one-position-per-ticker + universal ATR trailing stop

**Cross-reference with P0/P1 plans:** Our work is consistent with all 5 plans. The only risk is P0B/P0C potentially duplicating gate infrastructure we already hardened in `quality_gates.py`.

---

## 1. Code Changes

### config.py
- `MONKEY_TEST_P95_PF` dict added (CRYPTO=1.19, EQUITY=1.38, FOREX=1.45, COMMODITY=1.38)
- `STRATEGY_WEIGHT_OVERRIDES` — all 30 reset to 1.0 (0 passed n≥20+PF≥1.0 gate)
- `BLACKLISTED_STRATEGIES` — 6 PF<0.5 proven losers added
- `MIN_ELITE_SCORE` — all 6 eroded floors restored

### quality_gates.py
- M-110: `BLOCKED_DIRECTION_TRIPLES` — `(FUTURES, futures_momentum, LONG)` added; futures_momentum removed from `BLOCKED_SOURCE_SYSTEMS` and `BLOCKED_ASSET_STRATEGY_PAIRS`
- M-111: `_passes_monkey_test_p95_gate()` function + wiring in `passes_active_gate()`
- Baseline-beater monitor: `_BASELINE_BEATER_MONITORED_STRATS` set + `tag_baseline_beater_monitor()` function + wiring in `passes_active_gate()` after `tag_baby_monitor(pick)`
- Syntax: clean compile ✅

### tools/backtest_new_strategies_june2026.py (NEW)
- Full backtest harness: DB OHLCV pull → indicators → trade simulation → metrics
- 10 strategies across 5 classes, vectorized numpy, TP/SL walk-forward
- Cost model: CRYPTO=16bp RT, EQUITY/ETF/COMMODITY=4bp, FOREX=2bp

---

## 2. New Strategy Backtest Results

| Strategy | Class | Trades | WR% | PF | vs Baseline | vs P95 |
|---|---|---|---|---|---|---|
| `etf_rsi2_pullback_uptrend` | ETF | 53 | 37.7 | **1.145** | ✅ beats 0.148 | ❌ |
| `commodity_bb_squeeze` | COMMODITY | 11 | 45.5 | **1.108** | ❌ | ❌ |
| `forex_rsi14_oversold` | FOREX | 57 | 35.1 | **1.004** | ❌ | ❌ |
| `crypto_funding_contrarian` | CRYPTO | 1,481 | 34.2 | **0.825** | ✅ beats 0.728 | ❌ |
| `equity_gap_fade` | EQUITY | 26 | 57.7 | **0.787** | ✅ beats 0.509 | ❌ |
| `equity_rsi2_sma200` | EQUITY | 71 | 32.4 | **0.744** | ✅ beats 0.509 | ❌ |
| `commodity_momentum_atr` | COMMODITY | 232 | 33.2 | **0.882** | ❌ | ❌ |
| 3 strategies | — | 0 | — | — | need tuning | — |

**4/10 beat class baselines. 0/10 pass P95. 3 need parameter tuning.**

### 4 MONITORED strategies registered:
- `crypto_funding_contrarian` (CRYPTO, PF=0.825)
- `equity_gap_fade` (EQUITY, PF=0.787, WR=57.7% — highest WR)
- `equity_rsi2_sma200` (EQUITY, PF=0.744)
- `etf_rsi2_pullback_uptrend` (ETF, PF=1.145 — highest PF)

All tagged `_monitor_mode=True`, `_monitor_tag="BASELINE_BEATER_SHADOW"`, `_sizing_override="zero"`.

### 3 zero-trade strategies — tuning needed:
- `crypto_atr_compression_breakout`: relax ATR ratio 0.7→0.85
- `forex_london_breakout`: relax ATR expansion 1.2→1.1
- `etf_dual_momentum`: reduce min_bars 300→200

---

## 3. picks-now.html Methodology Council Review

Convened Skeptic/Pragmatist/Critic council to swarm-review the 5-factor scoring system.

### Council verdict — 7 ranked enhancements:

| # | Enhancement | Impact | Effort |
|---|---|---|---|
| 1 | **One-position-per-ticker hard limit** | Eliminates MU×8, AVGO×3, AMT×5 concentration | Low |
| 2 | **Universal ATR-trailing stop-loss** | Cuts catastrophic tail from -35.86% → ~-5% | Low |
| 3 | **Bridge AI panel → quant score** (-20pts per reject vote) | META 7/7 reject shouldn't still show as a top pick | Medium |
| 4 | **Factor correlation penalty** (momentum+MR+analyst = diminishing returns) | Reduces echo-chamber scoring | Medium |
| 5 | **Factor 4 → veto gate** (skip if RVOL extreme without analyst upgrade) | Prevents catching falling knives | Low |
| 6 | **DB Edge Overlay 10%→25%** — anchor scoring to real outcomes | Only factor grounded in YOUR data | Low |
| 7 | **Expose trimmed-mean PnL** on dashboard (-0.04% vs raw -35.86%) | Shows the real story to users | Low |

### Core insight:
> Your entry logic works — 288/157 positive open (+1.66% avg unrealized). The problem is what happens after entry: no exposure limits, no hard stop-loss, and ignoring your own AI panel's rejection warnings.

### Factor echo chamber problem:
The Skeptic identified that Momentum (30%) + Mean Reversion (20%) + Analyst Consensus (25%) = 75% of score all saying "buy large-caps that are dropping." They're highly correlated — not three independent signals.

---

## 4. DB Deep-Dive Findings

### The -35.86% mean is an outlier mirage:
| Metric | Value |
|---|---|
| Mean PnL (all closed) | -35.86% |
| Standard deviation | 296.01% |
| Mean (trimmed ±20% outliers) | **-0.04%** |
| Bulk of trades (0-5% loss) | 1,079 trades |
| Bulk of trades (0-5% win) | 588 trades |

The vast majority of trades are small ± a few percent. A tiny number of catastrophic outliers (-200%, -500%) drag the mean into the abyss. The trimmed mean is essentially breakeven.

### Signal clustering is the #1 allocation flaw:
- MU: 8 identical +15.26% entries
- AVGO: 3x in top losers
- AMT: 5x in top losers
- 445 open picks, only 209 unique symbols: **2.1 picks per symbol on average**

### Live vs closed gap:
- Live mark-to-market: +1.66% avg, 288/157 positive (64.7%)
- Closed resolved: -35.86% mean, 21% WR
- **Winners stay open, losers resolve fast** = survivorship bias in live data

---

## 5. Cross-Reference: Our Work vs. P0/P1 Plans

### 🔴 Conflicts to watch:
| Plan | Risk | Our coverage |
|---|---|---|
| P0C (M-036 CRYPTO LONG block) | May duplicate logic in `production_scanner.py` | We already have `BLOCKED_DIRECTION_TRIPLES` in `quality_gates.py` — P0C should route through this |
| P0B (unified kill list) | May duplicate `BLACKLISTED_STRATEGIES` | We already added 6 to `config.py` — P0B should read from centralized configs |
| P0A cap 500/hr | 15-day backlog catch-up | Our 4 MONITORED strategies need n≥20 — expect 2-3 weeks before actionable data |

### ✅ Alignment:
- Our monkey-test P95 gate feeds P1A (intrabar-only verdict UI)
- Our 4 MONITORED strategies feed master loop Addendum E
- Our direction gating (M-110) is the same pattern P0C needs for CRYPTO LONG
- Our picks-now enhancements (7 items) complement the master loop's exit-management focus

---

## 6. Open Action Items

1. **Tune 3 zero-trade strategies** — relax parameters, re-run
2. **Add SHORT variants** — forensic report shows SHORT PF=7.40 for futures_momentum, PF=6.13 for forex_rsi2
3. **Pre-register 4 strategies in M-107** hypothesis registry
4. **Implement picks-now enhancements #1 + #2** — one-position-per-ticker + ATR trailing stop
5. **Ensure P0B/P0C route through quality_gates.py** — don't duplicate blocks in production_scanner.py
6. **One-time P0A bootstrap batch** — 177K unresolved rows needs faster than 500/hr to seed intrabar data
7. **Apply stress matrix (cost×0.5/1/2/4) before promoting** any MONITORED strategy to real capital

---

## 7. Files Manifest

| File | Change |
|---|---|
| `alpha_engine/config.py` | MONKEY_TEST_P95_PF, STRATEGY_WEIGHT_OVERRIDES reset, BLACKLISTED_STRATEGIES, MIN_ELITE_SCORE floors |
| `audit_trail/quality_gates.py` | M-110 direction gating, M-111 monkey P95 gate, baseline-beater monitor set/function/wiring |
| `tools/backtest_new_strategies_june2026.py` | **NEW** — 10-strategy backtest harness |
| `FREEBUFF_JUNE122026.MD` | **NEW** — forensic autopsy handoff |
| `BUFFY_HANDOFF_JUNE122026.MD` | **NEW** — this file, full session handoff |
| `reports/new_strategies_june2026_20260612_0400.json` | **NEW** — backtest results JSON |

---

*Generated 2026-06-12 by Buffy (deepseek-v4-pro). Evidence: reports/new_strategies_june2026_20260612_0400.json*
