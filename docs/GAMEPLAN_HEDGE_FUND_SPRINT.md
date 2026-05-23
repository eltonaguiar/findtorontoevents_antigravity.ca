# GAMEPLAN: 46% → 60% WR Sprint
**Date:** 2026-03-25 | **Consensus from:** 5 Claude Code agents, Mercury 2, Grok, GitHub Copilot

---

## The Diagnosis (All Models Agree)

> "You already HAVE hedge-fund-level signals. You just buried them under 130+ strategies of dirt."

- **7 strategies** carry the entire book (85-94% WR)
- **2 copy traders** are profitable (NMTD 81%, whale_123M 100%)
- **~90% of the system dilutes the 10% that works**

---

## Phase 1: Stop the Bleeding (0-2 hours)

### 1.1 Kill binance_smart_money at generator level
- **Why:** NOT copy trading — reads Binance L/S ratios (sentiment indicator). 44% of copy volume, 45.8% WR, picks illiquid alts
- **How:** Add to HARD_KILL_STRATEGIES in scanner.py AND crypto_risk_gates.py
- **Impact:** +5pp WR

### 1.2 Block equity/commodity cold
- **Why:** 0-19% WR = guaranteed losers bleeding capital
- **How:** Hard category filter in production_scanner.py quality gates
- **Impact:** Remove 100+ guaranteed losers per cycle

### 1.3 Restore ml_score as primary weight
- **Why:** Strongest predictor (+0.337 correlation) was incorrectly zeroed based on biased IC sample
- **How:** Un-zero ml_score component in elite_scorer.py, weight at 15-18 pts (was 0)
- **Impact:** +10pp scoring discrimination

---

## Phase 2: Concentrate & Calibrate (2-5 hours)

### 2.1 Concentrate copy trading on 2 proven traders
- **NMTD_25M:** 81.2% WR, 16 trades — PRIMARY allocation (60% of copy capital)
- **whale_123M_87roi:** 100% WR, 4 trades — SECONDARY (30% of copy capital)
- **Everything else:** Paper-only until 20+ trades at WR>60%
- **Impact:** CT WR: 53% → 85%

### 2.2 Widen whale TP/SL
- **From:** 3% TP / 2% SL
- **To:** 8% TP / 4% SL
- **Why:** Whales use 10-40x leverage. Our 2% SL = noise stop. 35% of picks hit SL prematurely
- **Impact:** Fewer premature exits, better PnL per trade

### 2.3 Separate execution pipelines (the "3 Alphas Rule")
- **Pipeline A — ML Scalping:** Tight SL (2-3%), high turnover, score-driven
- **Pipeline B — Whale Swing:** Wide SL (4-8%), low frequency, copy-only
- **Pipeline C — Experimental:** Paper only, new traders/strategies
- **Impact:** +5-8pp WR from removing cross-contamination

### 2.4 Add score minimum threshold (55)
- **Why:** Score 0-20 and 21-40 are noise. Only 60+ shows real signal
- **How:** Hard filter in production_scanner.py
- **Impact:** +2-3pp WR

### 2.5 FETUSDT concentration cap (30%)
- **Why:** 52% of all profits from one symbol = unacceptable risk
- **How:** Max 2 active picks per symbol
- **Impact:** Risk reduction, not WR improvement

---

## Phase 3: Rebuild the Engine (5-8 hours)

### 3.1 Restart ml_crypto_predictor
- **Status:** Dead since March 8 (17 days). 62% of ML features offline
- **How:** Check if Docker container/workflow is running, restart, verify health_score >= 0.8
- **Impact:** Recovers 85-94% WR ML strategies to full strength

### 3.2 Hard-kill enforcement at generator level
- **Why:** 160+ picks generated from strategies marked as killed
- **How:** Check HARD_KILL_STRATEGIES at pick GENERATION, not just filtering
- **Impact:** +5-7pp WR from eliminating junk at source

### 3.3 Fix gate cascade calibration
- **Why:** Only 2/68 picks pass current gates (too restrictive)
- **How:** Audit each gate's rejection rate, loosen the overaggressive ones
- **Impact:** Surfaces 10-15 good picks instead of 2

### 3.4 Fix PnL unit inconsistency
- **Why:** FETUSDT has pnl_pct=4.2006, JTOUSDT has 0.049475 in same file
- **How:** Normalize all PnL to decimal (0.042 = 4.2%)
- **Impact:** Correct downstream calculations

---

## Expected Outcome

| Metric | Now | After Sprint | Hedge Fund Target |
|--------|-----|-------------|-------------------|
| Win Rate | 46% | 58-62% | >55% |
| Profit Factor | 1.52 | 1.9-2.3 | >2.0 |
| Sharpe Ratio | ~0.3 | 0.9-1.4 | >1.0 |
| Active Strategies | 130+ | 5-8 | 5-20 |
| Copy Traders | 1,325 | 2-4 | 2-10 |
| Trades/Day | 128 | 20-40 | 10-50 |

---

## What to Protect (DO NOT TOUCH)

1. **ml_enhanced_BNBUSDT** (94.1% WR) — crown jewel
2. **ml_enhanced_FETUSDT** (93.8% WR) — biggest PnL contributor
3. **ml_enhanced_RENDERUSDT** (87.5% WR) — high but cap exposure
4. **copy_hl_NMTD_25M** (81.2% WR) — most reliable non-ML signal
5. **Polymarket integration** — correctly bearish on BTC
6. **Alpha engine** — fixed and running 3+ consecutive successes

---

## The 2 Core Principles

### 1. "Garbage Multiplies Faster Than Alpha"
Bad trades execute more often, have higher variance, and destroy Sharpe exponentially.
Removing losers > adding winners.

### 2. "Edge > Coverage"
More trades ≠ better. Better trades = better.
Every dollar on a bad strategy = opportunity cost from a great one.

---

## Assignment Matrix

| Task | Assigned To | Priority |
|------|-------------|----------|
| Kill binance_smart_money | Coordinator (this agent) | P0 |
| Block equity/commodity | Coordinator | P0 |
| Restore ml_score | 5zajmzss (has ML-composite deployed) | P0 |
| Widen whale TP/SL | i8mbe7tv (working on adaptive TP/SL) | P1 |
| Concentrate copy traders | i8mbe7tv (researching traders) | P1 |
| Separate pipelines | 5zajmzss (regime router ready) | P1 |
| Restart ml_crypto_predictor | 314emojt (infrastructure) | P2 |
| Hard-kill at generator | 314emojt (quality assurance) | P2 |
| Gate cascade calibration | ms6wyhav (scoring expert) | P2 |
| Score threshold (55) | Coordinator | P1 |

---

*"You're not far off. Your edge exists. Your problem is system design, not signal discovery."*
*— Consensus from 7 AI models analyzing the same data*
