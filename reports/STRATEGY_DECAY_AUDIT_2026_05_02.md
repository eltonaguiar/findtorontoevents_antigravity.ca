# Strategy Decay Audit — H1/H2 Chronological Split

**Date:** 2026-05-02
**Source:** `alpha_engine/data/closed_picks.json` (7,445 closed picks)
**Mode:** READ-ONLY analysis. No production code modified.

## Methodology

Loaded 7,445 closed picks. For each pick extracted `strategy`, `pnl_pct`, and a timestamp (first available of `timestamp` -> `closed_at` -> `exit_date`, with `None` coerced to `""` before sorting per Issue #638 lesson). Grouped by `strategy`, filtered to strategies with **n>=20** closed picks (statistical floor), sorted each group's picks by timestamp ascending, and split at the midpoint (H1 = first half, H2 = second half). WR = wins / total where a win is `pnl_pct > 0`. Delta = H2_WR - H1_WR (negative = decaying). 175 total strategies, 35 qualified at n>=20.

**Status thresholds:**
- `DECAY_SEVERE` — H2_WR < 45% (retire candidate)
- `DECAY_MODERATE` — delta < -10pp but H2_WR >= 45%
- `STABLE` — abs(delta) <= 10pp
- `IMPROVING` — delta > 10pp

## All n>=20 Strategies (sorted by delta ascending — most-decaying first)

| strategy | n_total | n_h1 | n_h2 | h1_wr | h2_wr | delta_pp | status |
|---|---:|---:|---:|---:|---:|---:|---|
| `ml_enhanced_APEUSDT_1d_D_ensemble_stack` | 30 | 15 | 15 | 66.7% | 0.0% | -66.7 | DECAY_SEVERE |
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | 22 | 22 | 86.4% | 27.3% | -59.1 | DECAY_SEVERE |
| `quan_engine_swing` | 109 | 54 | 55 | 50.0% | 5.5% | -44.5 | DECAY_SEVERE |
| `ml_enhanced_AVAXUSDT_15m_D_ensemble_stack` | 30 | 15 | 15 | 60.0% | 20.0% | -40.0 | DECAY_SEVERE |
| `ml_enhanced_DOGEUSDT_15m_D_ensemble_stack` | 27 | 13 | 14 | 69.2% | 35.7% | -33.5 | DECAY_SEVERE |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 47 | 23 | 24 | 78.3% | 45.8% | -32.4 | DECAY_MODERATE |
| `cta_cross_asset_tsmom` | 83 | 41 | 42 | 61.0% | 33.3% | -27.6 | DECAY_SEVERE |
| `rsi_bounce` | 25 | 12 | 13 | 41.7% | 15.4% | -26.3 | DECAY_SEVERE |
| `ml_enhanced_ALGOUSDT_15m_B_lightgbm` | 26 | 13 | 13 | 61.5% | 38.5% | -23.1 | DECAY_SEVERE |
| `ml_enhanced_ADAUSDT_15m_B_lightgbm` | 28 | 14 | 14 | 71.4% | 50.0% | -21.4 | DECAY_MODERATE |
| `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` | 29 | 14 | 15 | 100.0% | 80.0% | -20.0 | DECAY_MODERATE |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 37 | 18 | 19 | 66.7% | 47.4% | -19.3 | DECAY_MODERATE |
| `myfxbook_retail_contrarian` | 81 | 40 | 41 | 27.5% | 9.8% | -17.7 | DECAY_SEVERE |
| `ig_contrarian_sentiment` | 123 | 61 | 62 | 45.9% | 30.6% | -15.3 | DECAY_SEVERE |
| `macd_rsi_confluence` | 66 | 33 | 33 | 42.4% | 30.3% | -12.1 | DECAY_SEVERE |
| `ml_enhanced_AVAXUSDT_1d_B_lightgbm` | 25 | 12 | 13 | 50.0% | 38.5% | -11.5 | DECAY_SEVERE |
| `unknown` | 468 | 234 | 234 | 42.7% | 32.5% | -10.3 | DECAY_SEVERE |
| `ml_enhanced_INJUSDT_15m_D_ensemble_stack` | 26 | 13 | 13 | 7.7% | 0.0% | -7.7 | DECAY_SEVERE |
| `forex_rsi2_mean_reversion` | 53 | 26 | 27 | 11.5% | 7.4% | -4.1 | DECAY_SEVERE |
| `forex_carry_momentum` | 70 | 35 | 35 | 2.9% | 0.0% | -2.9 | DECAY_SEVERE |
| `quan_engine_position` | 26 | 13 | 13 | 0.0% | 0.0% | +0.0 | DECAY_SEVERE |
| `futures_momentum` | 31 | 15 | 16 | 0.0% | 0.0% | +0.0 | DECAY_SEVERE |
| `ml_enhanced_FETUSDT_15m_B_lightgbm` | 29 | 14 | 15 | 64.3% | 66.7% | +2.4 | STABLE |
| `quan_engine_scalp` | 5293 | 2646 | 2647 | 28.3% | 31.6% | +3.3 | DECAY_SEVERE |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | 15 | 16 | 93.3% | 100.0% | +6.7 | STABLE |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 28 | 14 | 14 | 92.9% | 100.0% | +7.1 | STABLE |
| `volume_spike_breakout` | 78 | 39 | 39 | 10.3% | 23.1% | +12.8 | DECAY_SEVERE |
| `stocks_rsi2_pullback` | 28 | 14 | 14 | 35.7% | 50.0% | +14.3 | IMPROVING |
| `ml_enhanced_JTOUSDT_1d_B_lightgbm` | 30 | 15 | 15 | 26.7% | 46.7% | +20.0 | IMPROVING |
| `ml_enhanced_TRXUSDT_1d_B_lightgbm` | 26 | 13 | 13 | 0.0% | 23.1% | +23.1 | DECAY_SEVERE |
| `ml_enhanced_HBARUSDT_1d_D_ensemble_stack` | 28 | 14 | 14 | 28.6% | 57.1% | +28.6 | IMPROVING |
| `cot_positioning` | 43 | 21 | 22 | 66.7% | 95.5% | +28.8 | IMPROVING |
| `cftc_cot_commercial_signal` | 31 | 15 | 16 | 66.7% | 100.0% | +33.3 | IMPROVING |
| `ml_enhanced_POLUSDT_1d_B_lightgbm` | 27 | 13 | 14 | 23.1% | 71.4% | +48.4 | IMPROVING |
| `ml_enhanced_XRPUSDT_1d_D_ensemble_stack` | 28 | 14 | 14 | 35.7% | 85.7% | +50.0 | IMPROVING |

## Top 5 KILL Candidates (DECAY_SEVERE, sorted by delta asc)

> **REHAB GATE — TESTING_PROTOCOL.MD §7:** Try DNA mutation / inverse / symbol rotation BEFORE killing. Do not expand `BLOCKED_SOURCE_SYSTEMS` without `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` and `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (export closed CSV -> `python tools/mutation_analysis.py`). Also check `feedback_noncrypto_resolver_live_close_bug.md` — non-crypto strategies may be polluted by `outcome_resolver.py:97` (1bp WIN threshold) + `:384-405` (live yfinance close on every run) before any retirement decision.

| rank | strategy | n | h1_wr | h2_wr | delta_pp |
|---:|---|---:|---:|---:|---:|
| 1 | `ml_enhanced_APEUSDT_1d_D_ensemble_stack` | 30 | 66.7% | 0.0% | -66.7 |
| 2 | `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | 86.4% | 27.3% | -59.1 |
| 3 | `quan_engine_swing` | 109 | 50.0% | 5.5% | -44.5 |
| 4 | `ml_enhanced_AVAXUSDT_15m_D_ensemble_stack` | 30 | 60.0% | 20.0% | -40.0 |
| 5 | `ml_enhanced_DOGEUSDT_15m_D_ensemble_stack` | 27 | 69.2% | 35.7% | -33.5 |

## Bottom 5 — Candidate Workhorses (most stable / improving)

> Note: only 1 IMPROVING strategy (`cot_positioning`, n=43) and 0 STABLE strategies hit the preferred n>=50 floor. List below is padded with the highest-n IMPROVING/STABLE entries from the n>=20 cohort — treat as candidates pending more closed-trade evidence.

| rank | strategy | n | h1_wr | h2_wr | delta_pp | status |
|---:|---|---:|---:|---:|---:|---|
| 1 | `cot_positioning` | 43 | 66.7% | 95.5% | +28.8 | IMPROVING |
| 2 | `cftc_cot_commercial_signal` | 31 | 66.7% | 100.0% | +33.3 | IMPROVING |
| 3 | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | 93.3% | 100.0% | +6.7 | STABLE |
| 4 | `ml_enhanced_JTOUSDT_1d_B_lightgbm` | 30 | 26.7% | 46.7% | +20.0 | IMPROVING |
| 5 | `ml_enhanced_FETUSDT_15m_B_lightgbm` | 29 | 64.3% | 66.7% | +2.4 | STABLE |

## Operator Summary

Of **35 strategies** with n>=20 closed picks, **21 are DECAY_SEVERE** (H2_WR < 45%), **4 are DECAY_MODERATE** (delta < -10pp but H2_WR still >=45%), **3 are STABLE** (abs(delta) <= 10pp), and **7 are IMPROVING** (delta > +10pp). The decay pile dominates: 60% of the qualifying universe is in severe decay, including the system's two highest-volume buckets — `quan_engine_scalp` (n=5293, H1 28.3% -> H2 31.6%, classified SEVERE because H2_WR is still <45% even though delta is slightly positive) and the `unknown`-strategy bucket (n=468, H1 42.7% -> H2 32.5%). The five sharpest cliffs (`ml_enhanced_APEUSDT_1d_D_ensemble_stack`, `ml_enhanced_FETUSDT_1d_B_lightgbm`, `quan_engine_swing`, `ml_enhanced_AVAXUSDT_15m_D_ensemble_stack`, `ml_enhanced_DOGEUSDT_15m_D_ensemble_stack`) all dropped 30-67pp between halves.

Repo-wide message: edge is degrading faster than the rehab pipeline is replacing it. The strongest improvers are the COT/CFTC positioning signals (`cftc_cot_commercial_signal` H2 100%, `cot_positioning` H2 95.5%) and a handful of daily-bar ML ensembles on alt-coins (`POLUSDT_1d`, `XRPUSDT_1d`, `HBARUSDT_1d`, `JTOUSDT_1d`) — these deserve capital re-allocation study before any kills are executed. Also flagged: every `forex_*` and `futures_*` strategy in the table sits at single-digit H2_WR, which is the exact signature of the non-crypto resolver live-close bug (`outcome_resolver.py:97` 0.1bp WIN threshold + `:384-405` live yfinance close on every run); these picks should be re-resolved with the resolver fix before retirement, per `feedback_noncrypto_resolver_live_close_bug.md`. Mandatory next step before any `BLOCKED_SOURCE_SYSTEMS` expansion: run `tools/mutation_analysis.py` and `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` per TESTING_PROTOCOL.MD §7.
