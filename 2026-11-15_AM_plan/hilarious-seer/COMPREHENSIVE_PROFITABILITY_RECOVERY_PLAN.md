# Comprehensive Profitability Recovery Plan
**Date:** 2026-11-15 AM  
**Worktree:** hilarious-seer  
**Status:** 0/9 asset classes money-ready; framework for finding genuine edge

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Asset Classes Attempted — Complete Inventory](#2-asset-classes-attempted--complete-inventory)
3. [Per-Asset-Class Profitability Recovery Plan](#3-per-asset-class-profitability-recovery-plan)
4. [Trading Style × Holding Period × Asset Class Matrix](#4-trading-style--holding-period--asset-class-matrix)
5. [Top Proven Algorithms & Contest Winners](#5-top-proven-algorithms--contest-winners)
6. [Why We Still Don't Have Winners](#6-why-we-still-dont-have-winners)
7. [Essential Questions We Must Answer](#7-essential-questions-we-must-answer)
8. [How Financial Firms Turned Struggle Into Trust](#8-how-financial-firms-turned-struggle-into-trust)
9. [Key Metrics by Investor Perspective](#9-key-metrics-by-investor-perspective)
10. [Parallel Agent Prompts](#10-parallel-agent-prompts)

---

## 1. Executive Summary

After **2,198 commits**, **7 peer worktree deliverables**, **15 bug reports**, and **4 shipped code fixes**, the verdict remains:

> **0/9 asset classes are money-ready today.**

The system is **anti-profitable on average** (4/170 ledgers pass at 95% confidence vs 8.5 expected by pure chance). Root cause: **data integrity and execution plumbing**, not missing theory.

**This document provides:**
- A recovery plan per asset class
- Analysis of trading styles vs holding periods
- Proven algorithms that have won contests
- Research on how real firms turned around
- Metrics from different professional perspectives
- Prompts for parallel AI agents to attack the problem

**Bottom line:** Fix measurement first. Then test one hypothesis at a time. Until then, deploy only passive beta.

---

## 2. Asset Classes Attempted — Complete Inventory

| Asset Class | Strategies | Status | PF (Live) | WR (Live) | Key Blocker |
|-------------|-----------|--------|-----------|-----------|-------------|
| **CRYPTO** | ~680+ | Active, highest volume | 0.74 | 33% | Stop-fill slippage (1.54× planned risk) |
| **EQUITY** (US) | ~12+ | Active | 0.70 | 43% | Fails SPY benchmark; mislabeling |
| **FOREX** | ~12+ | Active but poor | 0.85 | 36% | Contaminated data; JPY-cross drag |
| **ETF** | ~8 bundles | Sparse upstream | 0.02–1.84* | 2–73%* | *84× spread between surfaces; sync failure |
| **COMMODITY** | ~10+ | Active | 0.17 | 14% | COT contrarian failed 4/4 trials |
| **BOND** | ~5+ | Very sparse | 0.05 | 7.7% | Broken exit labels; insufficient n |
| **FUTURES** | ~5+ | Near-dead | 0.86 | 23% | No continuous-contract feed |
| **PENNY** | ~3+ | Dormant | 0.17 | 29% | 75+ days since last emission |
| **MEME** | Sub-class of crypto | Quarantined | 0.50 | — | Class-wide quarantine (29 strategies) |
| **MUTUAL FUNDS** | **Zero** | NOT_BUILT | N/A | N/A | No infrastructure; no live picks |
| **OPTIONS** | 6 variants | Paper only | N/A | N/A | 0DTE scalping untested live |

*ETF surfaces contradict each other by 84× — registry says PF 1.84, money_ready says PF 0.02.

---

## 3. Per-Asset-Class Profitability Recovery Plan

### 3.1 CRYPTO — Conditional Research Track (Slot 1)

**Current State:** PF 0.768, WR 33%, n=1,966. 98.8% of class loss from stop-fill slippage.

**Recovery Steps:**
1. **Fix stop-fill slippage** — Route `kimi_riseoftheclaw` through intrabar resolver with gap-aware fills
2. **Kill CRYPTO SWING emission** — PF 0.457, 39% of class loss
3. **Forward-test POSITION horizon only**, frozen rules, n ≥ 100
4. **Re-emit gates:** PF ≥ 1.3, WR ≥ 55%, stop-slippage < 10% of gross PnL

**Holding Periods:**
- **Scalping (1m–15m):** NOT RECOMMENDED — costs dominate, slippage kills edge
- **Day trading (1h–4h):** Conditional — only after fill fix
- **Swing (1d–7d):** KILL — PF 0.457, proven negative
- **Position (7d–30d):** RESEARCH TRACK — only horizon with any hope

**Probability Assessment:**
- 15% chance of PF ≥ 1.3 after fix
- 50% chance of breakeven only
- 35% chance of wind-down

---

### 3.2 EQUITY — Measurement Baseline (Slot 2)

**Current State:** PF 0.70, WR 43%, n=738. Fails SPY benchmark (median excess −0.57%).

**Recovery Steps:**
1. **Fix mislabeling** — 90% of EQUITY picks historically tagged as crypto (INCIDENT #7)
2. **Fix TIME_EXIT resolver** — 89% of closed rows have pnl=0 (mark-to-market bug)
3. **Unblock `stocks_rsi2_pullback`** — n=78, WR=44.9%, PF=1.11 (blocked by stale n=10 sample)
4. **Pre-registered benchmark test vs SPY** — require n≥500, PF≥1.15 after costs

**Holding Periods:**
- **Scalping:** NOT RECOMMENDED — VWAP scalping works on AAPL but fails on ETFs; costs dominate
- **Day trading:** Weak — no proven edge in repo
- **Swing (3d–14d):** BEST CANDIDATE — `stocks_rsi2_pullback` operates here
- **Long-term (months+):** PASSIVE ONLY — buy-and-hold quality names; no timing edge proven

**Key Strategy:** Connors RSI-2 pullback — historically 62.5% WR, Sharpe 2.35, p=0.009

---

### 3.3 ETF — Passive Control Arm Only

**Current State:** Contradictory surfaces (PF 0.02 vs 1.84). Zero live picks currently.

**Recovery Steps:**
1. **Fix mysql-trading-sync.yml** — ETF never synced into pf_registry
2. **Force-resolve 134 TIME_EXIT zero-pnl rows** with mark-to-market
3. **Add `etf_200dma_trend`** (Faber 10-month SMA) — strongest documented academic edge
4. **Use only as benchmark/control arm** — VTI, BND, SGOV

**Holding Periods:**
- **Scalping/Day trading:** FORBIDDEN — costs make it impossible
- **Swing:** Weak — no proven tactical edge
- **Long-term (monthly rebalance):** PASSIVE ONLY — dual momentum, sector rotation failed gates

**Recommended Allocation (Not Alpha):**
- VTI (Total Market): 60%
- BND (Aggregate Bonds): 30%
- SGOV (T-Bills): 10%

---

### 3.4 MUTUAL FUNDS — The Only Deployable Sleeve

**Current State:** NOT_BUILT. No infrastructure. No live picks.

**Immediate Action:**
1. **Build `alpha_engine/passive_fund_screener.py`** — Screen FXAIX, FSKAX, SWPPX, FXNAX, FSGGX
2. **No prediction claims** — This is beta capture, not alpha
3. **Deploy immediately** while research continues

**Recommended Core:**
| Ticker | Fund | ER | Allocation |
|--------|------|-----|------------|
| FXAIX | Fidelity 500 Index | 0.015% | 50% |
| FSKAX | Fidelity Total Market | 0.015% | 20% |
| FXNAX | Fidelity US Bond Index | 0.025% | 20% |
| FSGGX | Fidelity Global ex-US | 0.055% | 10% |

**Expected Return:** ~6.5% blended nominal, ~10–12% vol, Sharpe ~0.5

---

### 3.5 FOREX — Quarantine Until Fixed

**Current State:** PF 0.85, WR 36%. Hard-BLOCKED by PR #6 yet still emitting.

**Recovery Steps:**
1. **KILL `multi_asset_scanner` FOREX emission** — 39% of cohort at PF 0.21
2. **Fix resolver TIME_EXIT mislabels** — 76% of rows contaminated
3. **Scrub 6 bad TP_HIT rows** — decimal-shift bugs (CADJPY exit=611 vs entry=115)
4. **Watchlist `cta_cross_asset_tsmom`** — all-time n=189, WR=53.4%, PF~2.0–2.5 after scrub

**Holding Periods:**
- **Scalping:** FORBIDDEN — spreads kill retail
- **Day trading:** Weak — London breakout 62% WR but thin
- **Swing (1w–4w):** BEST CANDIDATE — carry + momentum
- **Long-term:** Not applicable

---

### 3.6 COMMODITY — Blocked Pending New Trial

**Current State:** PF 0.17, WR 14%. COT contrarian failed 4/4 pre-registered trials.

**Recovery Steps:**
1. **Fix TIME_EXIT resolver** — 72.5% of rows pnl=0
2. **Quarantine `multi_asset_copytrader / futures_momentum`** — 75% of clean closures, PF 0.25
3. **New pre-registered COT trial required** — old edge dead
4. **Add copper inventory mean-reversion sidecar**

**Holding Periods:**
- **Scalping:** FORBIDDEN — too volatile
- **Swing:** Weak — COT failed
- **Position (weeks–months):** Only hope — seasonal + COT

---

### 3.7 BOND — Dead-But-Displayed

**Current State:** PF 0.05, WR 7.7%. n effectively zero.

**Recovery Steps:**
1. **Fix TIME_EXIT exit_price forgery** — 71% of rows have exit_price = entry_price
2. **Wire FRED_API_KEY** — unblock macro signal sourcing
3. **Build real emitter** — currently daily cron emits picks that never resolve
4. **Accumulate n≥50** before any claim

**Holding Periods:**
- **All horizons:** NOT VIABLE — insufficient data

---

### 3.8 FUTURES — Merge or Rebuild

**Current State:** PF 0.86, WR 23%. 95% of rows are resolver bugs.

**Recovery Steps:**
1. **Fix mark-to-market for `*=F` symbols**
2. **KILL `futures_connors_rsi2`** — 87% of class, random walk
3. **Add `futures_vix_term_structure_v1`** — short VIX futures when contango >5%
4. **Merge into COMMODITY** or unblock with genuine feed

---

### 3.9 PENNY — Formally Dormant

**Current State:** PF 0.17, WR 29%. 75+ days since last emission.

**Recovery Steps:**
1. **Label as DORMANT** on dashboard
2. **KILL `penny_deep_oversold`** under ALL labels
3. **Add price-cap enforcement** — entry_price < $5
4. **Wire up or retire orphan code**

---

## 4. Trading Style × Holding Period × Asset Class Matrix

| Style | Horizon | Best Asset Class | Worst Asset Class | Why |
|-------|---------|------------------|-------------------|-----|
| **Scalping** | 1m–15m | NONE | CRYPTO, FOREX, EQUITY | Costs + slippage > edge for all |
| **Day Trading** | 1h–4h | EQUITY (conditional) | FOREX, COMMODITY | VWAP mean-reversion on trending stocks only |
| **Swing** | 1d–7d | EQUITY (`stocks_rsi2_pullback`) | CRYPTO, FOREX | CRYPTO SWING PF 0.457; FOREX regime drag |
| **Position** | 7d–30d | CRYPTO (conditional) | BOND, FUTURES | Only horizon where crypto fill fix might work |
| **Long-term** | Months+ | ETF, MF (passive) | CRYPTO, PENNY | Beta capture wins; prediction fails |

**Key Insight:** The shorter the horizon, the more costs dominate. The longer the horizon, the more beta dominates. There is a "valley of death" in the middle (swing/position) where neither beta nor edge reliably works.

---

## 5. Top Proven Algorithms & Contest Winners

### 5.1 Contest-Winning & Research-Backed Strategies

| Strategy | Source | Asset Class | Horizon | Claimed WR | Verified? | Notes |
|----------|--------|-------------|---------|------------|-----------|-------|
| **Connors RSI-2** | Larry Connors | EQUITY, ETF | Swing (2d) | 75.7% | Partial | `stocks_rsi2_pullback` live: 44.9% WR, PF 1.11 |
| **Hoffman EMA-9 / IRB** | Gemini Championship (Hoffman) | CRYPTO, FOREX | Day/Swing | 60–70% | Unverified in repo | `hoffman_ema_irb` exists but no live data |
| **VWAP Mean Reversion** | Berkowitz (1988) | CRYPTO, FUTURES | Day | 70–75% | Unverified | `vwap_sd_mean_reversion` in alpha_engine |
| **Hash Ribbon Buy** | Charles Edwards (2019) | CRYPTO | Position | 78% | Unverified | `hash_ribbon_buy` in onchain_strategies |
| **TSMOM (12M)** | Moskowitz et al. (2012) | MULTI-ASSET | Position | Sharpe ~0.5–0.8 | Failed in repo | ETF TSMOM walk-forward Sharpe 0.37 |
| **COT Positioning** | CFTC data | COMMODITY | Position | 86.5% | FAILED 4/4 trials | CT=F sub-cohort was promising but dead |
| **Funding Rate Carry** | Kraken Research | CRYPTO | Position | 60% | Unverified | `funding_rate_carry` in crypto_strategies |
| **Kalman Filter Trend** | Academic | MULTI-ASSET | Swing | 65–72% | Unverified | `kalman_filter_trend` exists |

### 5.2 Why These Haven't Won For Us

1. **Connors RSI-2:** Blocked by stale n=10 sample. Live n=78 shows PF 1.11 but suppression prevents accumulation.
2. **Hoffman IRB:** Exists in repo as `hoffman_ema_irb` but never wired to production scanner. No live picks.
3. **VWAP MR:** Requires intraday data. Repo uses daily/4h. Gap between theory and data.
4. **Hash Ribbon:** On-chain only, no live integration with pick resolver.
5. **TSMOM:** Academic Sharpe assumes perfect execution, no costs, no slippage. Repo reality adds 0.5–1.5% cost drag.
6. **COT:** Failed pre-registered trials. Edge may have existed in 2020–2024 but regime shifted.

### 5.3 Lessons from TradingView & Contest Winners

- **Hoffman (Gemini Championship):** EMA-9 + Inventory Retracement Bar + ADX filter. Key insight: **trend direction first, entry precision second.**
- **Bellet (Gemini):** Fibonacci + RSI Divergence. Key insight: **confluence of structure + momentum.**
- **Triton (Gemini):** Multi-Factor Momentum. Key insight: **no single indicator; ensemble of uncorrelated factors.**
- **Kimi Claw Pro (TradingView):** 61 plots + 2 bgcolor (63/64 limit). Key insight: **institutional flow detection via VWAP + RSI.**

**Common thread:** All winners use **multiple uncorrelated confirmations** and **strict risk management**. None use a single indicator. All have a "no-trade" filter for ~60–70% of bars.

---

## 6. Why We Still Don't Have Winners

### 6.1 The Brutal Math

- **658 strategies tested.** ~33 false positives expected by chance at p=5%.
- **Only 21 "survivors."** All are single-source artifacts.
- **90,523 of 143,156 picks (63%) never resolve.** Survivorship bias is severe.
- **Fleet policy-clean PF: 0.2657.** The system loses money on average.

### 6.2 Root Causes (In Order of Impact)

1. **Stop-fill slippage (CRYPTO)** — 1.54× planned risk. 703/773 rows show exit_price ≠ stop_loss.
2. **Resolver bugs (ALL CLASSES)** — TIME_EXIT writes pnl=0 instead of mark-to-market. TP_HIT/SL_HIT not promoted to WON/LOST.
3. **Stale blocklists** — `stocks_rsi2_pullback` killed at n=10; live n=78 shows PF 1.11.
4. **Unenforced cost gates** — Cost ≥ edge for ETF (267% cost drag).
5. **Overfitting** — 69/80 strategies flagged OVERFIT_LIKELY (86%).
6. **Multiple testing** — 658 strategies × 9 asset classes = ~5,922 combinations. Bonferroni correction means p < 0.000008 required for significance.
7. **Copy-trader failure** — Copying others' trades adds latency. By the time a signal reaches us, the edge is gone.
8. **Prediction markets (Kalshi/Polymarket)** — These price events, not asset directions. Different skill set. Our alpha_engine is not designed for binary event pricing.

### 6.3 Why Copy Trading Failed

- **Latency:** Our copy-trader pipeline adds 5–30 minutes vs the original entry.
- **Selection bias:** We copy traders AFTER they've had a good run. Regression to mean hits.
- **No edge aggregation:** Copying 10 traders with 52% WR each gives ~52% WR, not 70%.
- **Risk mismatch:** Prop traders use 0.5% risk/trade. Our system uses 2%. Their 3% drawdown is our 12%.

### 6.4 Why Prediction Markets Didn't Help

- Kalshi/Polymarket price **binary events** ("Will X happen by Y date?").
- Our system predicts **continuous price directions** ("Will BTC go up?").
- These are different domains. Event pricing requires information edge; price prediction requires statistical edge.
- We tried to use prediction market consensus as a signal, but the correlation to price direction is near zero.

---

## 7. Essential Questions We Must Answer

### 7.1 Data Integrity
1. What percentage of our closed-pick PnL is recomputed vs stored? If <100%, we don't trust the numbers.
2. How many rows have `exit_price = entry_price` (fabricated flat closes)?
3. What is the true slippage on CRYPTO stop fills vs planned risk?
4. How many "active" picks are actually zombies (EXPIRED, pnl=0, age >30d)?

### 7.2 Strategy Validation
5. Has ANY strategy passed a pre-registered, out-of-sample test with n≥100?
6. What is the Bonferroni-corrected p-value of our best strategy?
7. How many strategies were killed at n<30 that might have recovered?
8. What is the correlation between our "best" strategies and SPY/beta?

### 7.3 Cost & Execution
9. What is all-in cost per trade (spread + commission + slippage + borrow) for each asset class?
10. Does our backtest include realistic costs? If not, add 0.5% per trade and recompute.
11. What is the capacity of our best strategy? Can it handle $10K? $100K? $1M?
12. How does stop-fill slippage scale with position size?

### 7.4 Regime & Robustness
13. What happens to each strategy in bear markets? VIX >30? Fed hiking?
14. How many strategies work in both high-vol and low-vol regimes?
15. What is the half-life of our edges? (How many months until decay?)
16. Have we tested walk-forward with EXPANDING windows (not fixed)?

### 7.5 Benchmarking
17. Does ANY strategy beat buy-and-hold SPY after costs?
18. Does ANY strategy beat a simple 60/40 portfolio?
19. What is the information coefficient (IC) of our best predictor?
20. What is the probability that our "best" result is a false positive?

### 7.6 Mutual Funds (The User's Intuition)
21. Can we build a NAV-based momentum screener for mutual funds?
22. What is the tax efficiency of MF vs ETF for our target holding period?
23. Can we identify factor-tilted MFs (value, momentum, quality) that outperform vanilla index?
24. What is the minimum AUM threshold where MF expenses stop mattering?

---

## 8. How Financial Firms Turned Struggle Into Trust

### 8.1 Renaissance Technologies (Jim Simons)

**The Struggle:** Early 1980s. Simons hired mathematicians with no finance background. First fund (Monemetrics) lost money for 2 years. Early Medallion had 30% drawdowns.

**The Turnaround:**
1. **Hired for signal-processing expertise, not finance.** The team included Lenny Baum (Baum-Welch algorithm) and James Ax (algebraic geometry).
2. **Built proprietary data infrastructure.** They cleaned and aligned data themselves. No vendor trust.
3. **Short holding periods.** Medallion holds positions for hours to days. This reduces exposure to regime shifts.
4. **Ensemble of hundreds of weak signals.** No single strategy dominates. Edge comes from aggregation.
5. **Ruthless culling.** Strategies that underperform for 3 months are killed. No emotional attachment.
6. **Capacity discipline.** Medallion is capped at ~$10B. They return capital rather than degrade edge.

**Lesson for us:** We have 658 strategies but no ensemble discipline. We need to aggregate weak signals, not chase strong ones.

### 8.2 D.E. Shaw & Two Sigma

**The Turnaround:**
1. **Systematic research pipeline.** Every idea goes through: hypothesis → backtest → paper trade → small live → scale.
2. **No backtest without out-of-sample.** They use 50/30/20 splits (train/validation/test).
3. **Cost models are mandatory.** Every backtest includes realistic market-impact estimates.
4. **Red teams.** Dedicated teams try to break strategies. If they can, the strategy dies.
5. **Continuous monitoring.** Strategies are checked daily against expectation. Drift = death.

**Lesson for us:** Our "paper trading" is not systematic. We need a formal promotion pipeline with gates.

### 8.3 Bridgewater (Ray Dalio)

**The Turnaround:**
1. **Radical transparency.** All meetings recorded. All data shared. No one hides bad results.
2. **Principles over personalities.** Decisions are made by algorithms, not committees.
3. **All-weather framework.** They don't predict; they allocate. Risk parity works across regimes.
4. **Pain + reflection = progress.** Every loss is analyzed. The system learns.

**Lesson for us:** Our system hides bad results (pnl=0 rows, zombie picks). We need transparency.

### 8.4 AQR (Cliff Asness)

**The Turnaround:**
1. **Factor investing.** Value, momentum, quality, carry. These are well-documented academic factors.
2. **Long/short construction.** Capture factor premium without market beta.
3. **Risk management first.** Position sizing based on volatility, not conviction.
4. **Academic rigor.** Every strategy has a published paper behind it.

**Lesson for us:** Our strategies lack theoretical grounding. Most are technical indicators, not factors.

### 8.5 What We Must Adopt

| Practice | Our Current State | Target State |
|----------|-------------------|--------------|
| **Data cleaning** | Pnl=0 rows, forged exits | 100% recomputed vs market data |
| **Out-of-sample testing** | In-sample optimization | 50/30/20 split minimum |
| **Cost modeling** | Ignored or underestimated | Realistic spread + slippage + impact |
| **Red teams** | None | Dedicated agent to break strategies |
| **Ensemble discipline** | 658 strategies, no aggregation | Top 20 weak signals, weighted by IC |
| **Capacity discipline** | No limits | Hard cap per strategy |
| **Promotion pipeline** | Ad hoc | Hypothesis → paper → small live → scale |
| **Transparency** | Zombie rows hidden | All picks auditable in real-time |

---

## 9. Key Metrics by Investor Perspective

### 9.1 Quantitative Hedge Fund (Renaissance-style)

| Metric | Good | Acceptable | Poor | Our Best |
|--------|------|------------|------|----------|
| Sharpe | >2.0 | 1.0–2.0 | <1.0 | ~0.5 (MF passive) |
| Sortino | >2.5 | 1.5–2.5 | <1.5 | N/A |
| Calmar | >3.0 | 1.5–3.0 | <1.5 | N/A |
| Information Ratio | >0.5 | 0.2–0.5 | <0.2 | ~0 (IC ≈ 0) |
| DSR | >0.95 | 0.5–0.95 | <0.5 | 0.603 (ETF RSI-2) |
| Max Drawdown | <10% | 10–20% | >20% | 178% (CRYPTO) |
| Capacity | >$100M | $10M–$100M | <$10M | Unknown |

**Verdict:** We are far below minimum thresholds for any professional fund.

### 9.2 Mutual Fund Manager

| Metric | Good | Acceptable | Poor | Our Best |
|--------|------|------------|------|----------|
| Alpha vs benchmark | >2% | 0–2% | <0% | Negative (all classes) |
| Tracking Error | <2% | 2–5% | >5% | N/A |
| Upside Capture | >100% | 90–100% | <90% | N/A |
| Downside Capture | <90% | 90–100% | >100% | N/A |
| Expense Ratio | <0.20% | 0.20–0.75% | >0.75% | 0.015% (FXAIX) |
| Turnover | <20% | 20–50% | >50% | N/A |

**Verdict:** Only our passive MF sleeve meets professional standards.

### 9.3 Bank Prop Trader

| Metric | Good | Acceptable | Poor | Our Best |
|--------|------|------------|------|----------|
| Daily PnL Volatility | <1% | 1–2% | >2% | Unknown |
| Hit Ratio | >55% | 50–55% | <50% | 44.9% (EQUITY RSI-2) |
| Average Win/Loss | >1.5 | 1.0–1.5 | <1.0 | 1.11 (EQUITY RSI-2) |
| VaR (95%, 1d) | <2% | 2–5% | >5% | Unknown |
| CVaR (95%, 1d) | <3% | 3–7% | >7% | Unknown |
| Kelly Fraction | 0.25–0.5 | 0.1–0.25 | <0.1 or >0.5 | N/A |

**Verdict:** No strategy meets prop-trading standards.

### 9.4 Crypto Fund

| Metric | Good | Acceptable | Poor | Our Best |
|--------|------|------------|------|----------|
| Beta to BTC | 0.3–0.7 | 0–0.3 or 0.7–1.0 | >1.0 or <0 | Unknown |
| Alpha generation | >10% ann. | 0–10% | <0% | Negative |
| Downside Deviation | <15% | 15–30% | >30% | Unknown |
| Recovery Time | <3 months | 3–6 months | >6 months | Unknown |
| Slippage-Adjusted Return | Within 0.5% of gross | 0.5–2% | >2% | 1.54× planned risk |

**Verdict:** CRYPTO is the most broken class due to execution, not signal.

### 9.5 CTA / Trend Follower

| Metric | Good | Acceptable | Poor | Our Best |
|--------|------|------------|------|----------|
| MAR Ratio | >1.5 | 0.5–1.5 | <0.5 | N/A |
| Profit Factor | >1.5 | 1.2–1.5 | <1.2 | 1.11 (EQUITY RSI-2) |
| Win Rate | >45% | 35–45% | <35% | 44.9% (EQUITY RSI-2) |
| Expectancy | >0.5% | 0–0.5% | <0% | ~0% (EQUITY RSI-2) |
| Regime-Adjusted Sharpe | >0.8 | 0.3–0.8 | <0.3 | N/A |

**Verdict:** Only EQUITY RSI-2 is in "acceptable" range for one metric (PF). All others are poor.

---

## 10. Parallel Agent Prompts

### 10.1 Agent 1: CRYPTO Stop-Fill Fix Specialist

```
You are a crypto execution specialist. Your task is to fix the stop-fill slippage that is consuming 98.8% of CRYPTO class losses.

CONTEXT:
- Current slippage: 1.54× planned risk (703/773 rows show exit_price ≠ stop_loss)
- Primary leak: `kimi_riseoftheclaw` (n=174)
- CRYPTO SWING emission has PF 0.457 and must be killed
- POSITION horizon is the only research track

YOUR TASK:
1. Review `audit_trail/stop_fill.py` (shipped PR #771) and verify gap-aware fill logic
2. Review `KIMI_RISEOFTHECLAW/live_scanner.py` exit booking
3. Propose a fix that ensures SL_HIT exits at stop level, not polled price
4. Write tests in `tests/test_kimi_exit_fill.py` covering gap opens, wicks, and partial fills
5. Estimate the PF uplift from the fix

DELIVERABLE:
- Working code + tests
- PF uplift estimate
- Risk assessment of the change
```

### 10.2 Agent 2: EQUITY Benchmark Test Designer

```
You are a systematic equity researcher. Your task is to design and run a pre-registered benchmark test for EQUITY strategies vs SPY.

CONTEXT:
- Best candidate: `stocks_rsi2_pullback` (n=78, WR=44.9%, PF=1.11)
- Currently BLOCKED by stale n=10 sample
- 90% of EQUITY picks historically mislabeled as crypto
- TIME_EXIT resolver bug: 89% of closed rows have pnl=0

YOUR TASK:
1. Unblock `stocks_rsi2_pullback` — remove from BLOCKED_SOURCE_SYSTEMS
2. Fix TIME_EXIT mark-to-market for EQUITY rows
3. Design a 90-day forward test vs SPY total return
4. Define pre-registered gates: PF≥1.15, WR≥50%, n≥500, excess return >0%
5. Write the test harness in `tests/test_equity_spy_benchmark.py`

DELIVERABLE:
- Test harness code
- Pre-registered hypothesis document
- 90-day measurement plan
```

### 10.3 Agent 3: Mutual Fund & ETF Infrastructure Builder

```
You are a passive investing infrastructure engineer. Your task is to build the missing mutual fund and ETF baseline infrastructure.

CONTEXT:
- Mutual funds: ZERO coverage. Infrastructure does not exist.
- ETFs: Contradictory surfaces (PF 0.02 vs 1.84). mysql-trading-sync.yml never synced ETF.
- Only deployable sleeve: passive beta (FXAIX, FSKAX, FXNAX, FSGGX)

YOUR TASK:
1. Create `alpha_engine/passive_fund_screener.py` that screens MFs/ETFs by:
   - ER ≤ 0.20%, no load, AUM ≥ $1B, turnover ≤ 20%, age ≥ 5y
2. Fix `mysql-trading-sync.yml` to include ETF in pf_registry sync
3. Create `audit_dashboard/mf_etf_baseline.html` showing allocation, drift, rebalance alerts
4. Wire `portfolio_defs.py` tactical_fund_rotation to monthly cron (rebalance only)

DELIVERABLE:
- Working screener + dashboard + cron wiring
- Documentation of screening criteria
```

### 10.4 Agent 4: Data Integrity Auditor

```
You are a data integrity auditor. Your task is to find and fix all data quality issues across all asset classes.

CONTEXT:
- 53 rows at pnl_pct=0 with FORCE_CLOSED status
- resolution_method is NULL on all 3,500 rows
- 90,523 of 143,156 picks (63%) never resolve
- 22,947 ghost rows in db_health.json
- CRYPTO: 79% of active_raw are zombie picks (EXPIRED, pnl=0, median age 89d)
- EQUITY: 89% of closed rows have pnl=0 (TIME_EXIT bug)
- FOREX: 76% of rows contaminated by TIME_EXIT mislabels
- BOND: 71% of rows have exit_price = entry_price (forgery)

YOUR TASK:
1. Add `decisive` boolean column to closed-picks schema
2. Add `pnl_source` unit column to all PnL write paths
3. Write a daily reconciliation job that diffs money_ready_verdict vs pf_registry vs payload
4. Create freshness gates: CRYPTO ≤6h, EQUITY ≤24h, COT ≤9d, dashboard ≤2h
5. Write CI assertions for blank fields, stale prices, and forged exits

DELIVERABLE:
- Schema migration scripts
- Reconciliation job code
- CI assertions
- Audit report of current data quality
```

### 10.5 Agent 5: FOREX & COMMODITY Recovery Specialist

```
You are a macro/FX/commodity researcher. Your task is to assess whether FOREX and COMMODITY can be recovered.

CONTEXT:
- FOREX: PF 0.85, WR 36%, hard-BLOCKED yet still emitting 277 active rows
- COMMODITY: PF 0.17, WR 14%, COT contrarian failed 4/4 trials
- Best FOREX candidate: `cta_cross_asset_tsmom` (n=189, WR=53.4%, PF~2.0–2.5 after scrub)
- COMMODITY best candidate was CT=COT but edge is dead

YOUR TASK:
1. KILL `multi_asset_scanner` FOREX emission (39% of cohort, PF 0.21)
2. Fix 6 bad FOREX TP_HIT rows (decimal-shift bugs)
3. Scrub `cta_cross_asset_tsmom` and verify true PF
4. Design a new pre-registered COMMODITY trial (copper inventory + seasonal)
5. Assess whether FOREX should remain blocked or graduated to watchlist

DELIVERABLE:
- Kill/mutate recommendations for each strategy
- Scrubbed PF for `cta_cross_asset_tsmom`
- New COMMODITY trial design
- GO/NO-GO verdict for each class
```

### 10.6 Agent 6: Risk Management & Position Sizing Engineer

```
You are a risk management engineer. Your task is to build a comprehensive risk overlay that protects capital while research continues.

CONTEXT:
- Current system has no enforced daily/weekly/monthly loss caps
- Max concurrent positions: unenforced
- Correlation limits: unenforced
- Kelly criterion: not calculated
- Drawdown: CRYPTO hit 178% in April 2026

YOUR TASK:
1. Implement per-class position sizing: 1–2% risk per trade, quarter-Kelly max
2. Implement drawdown circuit breakers: daily -5%, monthly -20%
3. Implement correlation limits: max 1 position per correlated group
4. Implement losing streak halt: 3 consecutive losses → stop session
5. Build `RISK_MANAGEMENT.html` dashboard showing real-time risk metrics
6. Add regime filters: BTC > 200-EMA, SPY > 200-SMA, data freshness < TTL

DELIVERABLE:
- Risk engine code
- Dashboard HTML/JS
- Circuit breaker logic
- Regime filter integration
```

### 10.7 Agent 7: Overfitting & Statistical Validation Specialist

```
You are a statistical validation specialist. Your task is to fix the overfitting epidemic and implement rigorous statistical testing.

CONTEXT:
- 69/80 strategies flagged OVERFIT_LIKELY (86%)
- 658 strategies × 9 asset classes = ~5,922 combinations
- Bonferroni-corrected p < 0.000008 required for significance
- Only 4/170 ledgers pass at 95% confidence (vs 8.5 expected by chance)
- DSR (Deflated Sharpe Ratio) is our best anti-overfit metric

YOUR TASK:
1. Implement Bonferroni correction across all strategy × asset-class tests
2. Require DSR ≥ 0.95 for any strategy to graduate from paper to live
3. Implement walk-forward analysis with EXPANDING windows (not fixed)
4. Add CPCV (Combinatorial Purged Cross-Validation) for time-series
5. Build a "red team" agent that tries to break strategies via data snooping
6. Create a trial registry: every hypothesis must be pre-registered before testing

DELIVERABLE:
- Statistical testing framework code
- DSR calculator
- Trial registry system
- Red team test harness
```

### 10.8 Agent 8: Prediction Market Integration Specialist

```
You are a prediction market researcher. Your task is to determine why Kalshi/Polymarket integration failed and whether it can be fixed.

CONTEXT:
- Kalshi/Polymarket price binary events, not continuous price directions
- Our alpha_engine is designed for price prediction, not event pricing
- Prediction market consensus showed near-zero correlation to price direction
- Copy-trader attempts also failed due to latency and selection bias

YOUR TASK:
1. Analyze the structural mismatch between prediction markets and our alpha engine
2. Design a NEW module (`alpha_engine/prediction_market_signals.py`) that:
   - Reads Kalshi/Polymarket event probabilities
   - Converts event probabilities into asset-class regime signals (bull/bear/neutral)
   - Uses event probabilities as a FILTER, not a primary signal
3. Example: "Will SPY close above $600 by Dec 31?" at 65% → mild bullish filter for EQUITY
4. Test correlation between prediction market consensus and 30-day forward returns
5. If correlation < 0.1, recommend abandoning prediction market integration

DELIVERABLE:
- Structural analysis document
- New module code (if viable)
- Correlation test results
- GO/NO-GO recommendation
```

---

## Appendix A: Recommended Reading for Parallel Agents

| Document | Location | Relevance |
|----------|----------|-----------|
| `docs/ALL_STRATEGIES.md` | GitHub main | Complete strategy inventory |
| `updates/2026-05-13-money-maker-action-plan.md` | GitHub main | Original action plan with per-class baseline |
| `hilarious-seer-final-plan-2026-11-14/FINAL_PLAN_2026_11_14.md` | Local | Final plan with data-quality blockers |
| `hilarious-seer-final-plan-2026-11-14/QA_PLAN.md` | Local | Comprehensive QA validation rules |
| `hilarious-seer-final-plan-2026-11-14/RISK_MANAGEMENT.html` | Local | Interactive risk dashboard |
| `hilarious-seer-final-plan-2026-11-14/PROPOSED_EDITS.md` | Local | 20 prioritized code edits |
| `2026-11-14/inspect-wt_20261114_1058/reports_live_audit_2026-11-14/summary_*.md` | Local | Per-class live audit summaries |
| `TRUE_PROFITABILITY_VALIDATED.md` | Local | Only one statistically valid edge found |
| `NONCRYPTO_PF_TRUST_INVESTIGATION_openclaw-mimo_2026-04-17T1239CST.md` | Local | Non-crypto profit factors cannot be trusted |

---

## Appendix B: API Keys Available for Research

| Provider | Key Status | Use Case |
|----------|-----------|----------|
| Google Gemini | Active | General research, fact-checking |
| Groq | Active | Fast inference |
| Together AI | Active | Model inference |
| Mistral | Active | Model inference |
| Cohere | Active | Embeddings, classification |
| DeepSeek | Active | Reasoning models |
| OpenRouter | Active | Multi-model routing |
| SubQ | $5 + $20 credit | Sub-question decomposition |
| Novita AI | Active | Inference |
| Pollinations | Keyless (rate-limited) | Free anonymous inference |

**Recommendation:** Use Gemini or DeepSeek for deep reasoning about strategy design. Use Groq for fast iteration. Use SubQ for decomposing complex research questions.

---

*Document compiled from: peer reviews (flaxen-hair, finpredict, scratch-hippodraco, childlike-airport, quant-audit), live audit data (2026-11-14), and research on quantitative finance best practices.*
