# Elimination Rationale — Why the Other Classes/Strategies Were Removed

**Package:** WIRED_IN/2026-11-15_0125/finpredict-v4
**Author:** finpredict-v4
**Date:** 2026-11-15

---

## The elimination principle

> *A class/strategy is eliminated unless it (a) has a standing economic mechanism, (b) beats its buy-and-hold benchmark after costs out-of-sample, (c) has effective N ≥ 100, and (d) survives a 90-day paper forward test.* Everything that fails any of these is removed.

---

## Per-class elimination log

| Class/Strategy | Why eliminated | Evidence |
|----------------|----------------|----------|
| **Intraday scalping/day-trading (all)** | Cost-fragile; overfit; structural losses | Every audit; phase-10b; famous-strategy reality-check |
| **EQUITY intraday RSI-2** | SPY gate FAILED (median excess -0.57%, beat-SPY 45.5%, t=1.05) | `tools/equity_vs_spy.py` |
| **CRYPTO scalping / short-hold** | Fill bugs + cost drag; PF ~0.80 after fixes | kimi leak correction |
| **FOREX intraday session** | 96.6% null PnL; breakeven gap -16pp | peer reports |
| **FOREX contrarian sentiment** | Anti-skill (SHORT 21% WR vs LONG 57% on wrong axis) | audit |
| **BOND intraday** | n ~18-26 << 60 floor; contaminated | peer reports |
| **COMMODITY COT contrarian** | Gate failed 4/4 pre-registered checks (OOS PF 0.861) | `tools/cot_contrarian_backtest.py` |
| **COMMODITY crypto-proxy** | Conceptually broken (RNDRUSDT as "silver") | audit |
| **FUTURES momentum (original)** | Plumbing-blocked; no real feed; HHI 0.76 concentration | audit |
| **ETF intraday** | WR 2.2% conclusive | audit |
| **Prediction-market copy-trading** | Zero-sum + fees + adverse selection (structural) | analysis |
| **Meta/multi-asset permutations** | Overfit; 170 ledgers → 4 pass vs 8.5 expected by chance | M8 |
| **VWAP mean reversion** | Fatal annualization error; real Sharpe ~1.18; PBO 0.489 | peer adjudication |
| **Mutual funds as a prediction edge** | They are beta, not alpha — kept only as allocation core | unanimous peer conclusion |

---

## What we kept (and why)

| Kept | Why |
|------|-----|
| Mutual funds / broad ETF allocation core | Beta + low cost = highest-probability lower-risk path |
| Faber 200-day MA trend filter | Only backtest-proven, grounded, reproducible risk-adjusted edge |
| Dual-momentum (as diversifier) | Risk reduction; not primary engine |
| Defensive sleeve (TLT/SGOV/BND) | Flight-to-safety; keeps capital deployed in bad regimes |
| CRYPTO POSITION horizon (conditional) | Only positive sub-bucket; shadow forward-test pending |

---

## Summary

We eliminated every class/strategy that could not clear the four gates. What remains is a single, grounded, backtest-proven allocation logic (trend-aware index beta) plus one conditional research pilot (CRYPTO POSITION). That is the entire, honest, deployable surface.
