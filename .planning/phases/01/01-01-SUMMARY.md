---
phase: 1
plan: 1
subsystem: audit
tags: [audit, ml, backtest, forward-test, validation]
dependency_graph:
  requires: []
  provides: [audit-findings, reuse-decisions, failure-root-cause]
  affects: [phase-2-data, phase-3-training, phase-4-gainer]
tech_stack:
  added: []
  patterns: [deflated-sharpe-ratio, triple-barrier-labeling, walk-forward-efficiency, CPCV-PBO]
key_files:
  created:
    - crypto_ml_edge/AUDIT.md
  modified: []
key_decisions:
  - "All existing ML crypto models have no OOS edge — discard all .joblib files"
  - "Root cause of v1.2 failure: validation code existed but was never enforced as gate before picks"
  - "Label construction is broken: adaptive positive rate produced 45-50% positive rates (coin flip targets)"
  - "Connors RSI-2 on SPY/QQQ is the only proven signal (p=6e-06); BTC adaptation is borderline"
  - "Reuse: advanced_validation.py, feature_engine.py helpers, realistic_backtester.py, slippage map"
  - "Rebuild: label construction (fixed threshold), pick generation gate (DSR+CPCV required), timeframes (drop 15m, use 1h/4h)"
metrics:
  duration: "~15 minutes"
  completed: "2026-02-23"
  tasks_completed: 5
  files_created: 1
---

# Phase 1 Plan 1: Audit Existing Systems for OOS Edge Patterns Summary

## One-Liner

Systematic audit of all crypto ML systems confirming no existing model has OOS edge; root cause isolated to validation-production gap and broken label construction; reuse/rebuild decisions documented.

## What Was Built

A comprehensive 386-line audit report at `crypto_ml_edge/AUDIT.md` covering:

1. **v1.2 Forward Test Analysis** — 34 picks, 23.5% WR, Sharpe -2.799. Root causes: near-random model probabilities (AUC 0.27), tight SL wiped out by crypto volatility, adaptive positive rate producing coin-flip labels.

2. **v4 Supertrend Analysis** — 6 "passing" models all had 5–11 trade samples. Statistical analysis showed these are not significant: at 7 trades with 71.4% WR the binomial p-value is 0.164 (not 0.039 as reported). DSR confirmed: HBARUSDT DSR = 4.4e-47.

3. **v1.5 Training Analysis** — 355 models all had positive rates 0.41–0.50 (near coin-flip targets). This explains why all AUC scores clustered at 0.25–0.28.

4. **Gainer ML Analysis** — AUC 0.537. No edge. Top feature (consolidation_range) is conceptually valid but not actionable at 0.537 AUC.

5. **Connors RSI-2 Analysis** — The only proven signal: SPY Sharpe 4.84 (p=6e-06), QQQ Sharpe 6.55 (p=8e-06). BTC Sharpe 2.35 (p=0.009) is borderline. Not directly portable to crypto but methodology is adaptable.

## Key Findings

### No existing crypto ML model has genuine OOS edge

Every system audited showed negative or near-zero live performance. The Simpleton naive benchmark (Sharpe 0.567, 51.3% WR) outperformed the ML system (Sharpe -2.799, 23.5% WR) by a wide margin.

### Root cause: The validation-production gap

`advanced_validation.py` has correct DSR, CPCV, PBO, and Monte Carlo CI implementations. But picks were generated based on `probability > 0.55` alone — the validation results were computed but never gated pick generation. A model with AUC 0.27 could output probability 0.58 and generate a pick that would fail in production.

### Label construction was broken at the foundation

The adaptive positive rate target (15-30% in v3, resulting in 45-50% in v1.5) meant the label for the same price action could change depending on surrounding context. Near-50% positive rates make the classification problem trivially easy for a model to "solve" (predict 50/50) while appearing to have learned something.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Discard all existing .joblib models | AUC 0.27–0.54, no OOS edge |
| Reuse `advanced_validation.py` | Correctly implements DSR, CPCV, PBO |
| Reuse `feature_engine.py` helpers | Good technical indicators |
| Reuse `realistic_backtester.py` | ATR-based TP/SL, cost model sound |
| Rebuild label construction | Adaptive positive rate = coin flip |
| Rebuild pick generation gate | Must enforce DSR + CPCV + WFE |
| Drop 15m timeframe | Even worse in OOS (-3.28 Sharpe); 1h/4h only |
| Reduce to top-10 pairs | Fewer pairs = less multiple testing inflation |
| Test RSI-2 adaptation first | Only proven signal in codebase |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `crypto_ml_edge/AUDIT.md` created and committed (90f6834e)
- [x] All 5 tasks executed (v1.2 forward test, v4 proof, Alpha Engine, gainer ML, write audit)
- [x] Commit exists: `90f6834e`
