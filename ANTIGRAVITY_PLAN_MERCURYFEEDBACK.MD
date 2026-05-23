# 🔴 ANTIGRAVITY PLAN — MERCURY AI FEEDBACK RESPONSE

> **Source:** Mercury AI (Inception Labs)
> **Date Received:** 2026-03-03 @ 18:27 EST
> **Date Documented:** 2026-03-03 @ 18:27 EST
> **Plan Author:** Antigravity Agent Fleet
> **Status:** 🟡 IN PROGRESS

---

## 📋 Executive Summary

Mercury AI / Inception Labs conducted a comprehensive audit of our crypto trading system ecosystem and provided a two-part report:

1. **Part 1 — Performance Audit & Pragmatic Blueprint**: Analysis of all system families (Mercury-2, Alpha Engine, Baby Battleground, Claws of Doom, FC-PRO, ATM Challenge, Kill List) with concrete code-level recommendations.
2. **Part 2 — Hedge Fund / Mutual Fund Grade Techniques**: A full road-map of statistical, ML, and operational techniques used by professional crypto-focused funds.

This plan documents every piece of feedback, maps it to our existing codebase, and assigns actionable implementation tasks.

---

## 📊 Part 1: Performance Audit Results

### 1.1 System-by-System Performance Snapshot

| System / Family | Closed Picks | Win Rate | Expectancy/Trade | Mercury AI Verdict |
|---|---|---|---|---|
| **Mercury-2** | 46 | 39% | +0.25% | Edge shows up only at RR ≥ 1.4 (WR ≈ 68%, E ≈ +1.87%) |
| **Alpha Engine** | 165 | 34% | -2.45% | **Strong directional asymmetry** — short works (WR 65%, E +3.4%), long drags (WR 26%, E -3.9%) |
| **Baby Battleground** | 128 | 65% | +0.53% | Good core performer |
| **Claws of Doom** | 25 | 56% | +0.78% | Small sample but solid |
| **FC-PRO (baby+claws)** | 153 | 63% | +0.57% | Current qualified mix |
| **ATM – funding_carry** | 39-51/variant | 74-95% | +1.61% (ELITE) | 🏆 **Most frequent & profitable family** |
| **ATM – ema_crossover/bollinger_squeeze** | ~30-35 each | 45-48% | Near breakeven | High-frequency but no edge |
| **KILL LIST** (smart_money_fvg, m2_liquidity_lag, etc.) | 8-9 each | 0-22% | Large negative PnL | ☠️ **Toxic — disable immediately** |

### 1.2 Key Take-Aways from Mercury AI

1. **Core edge lives in a handful of components:**
   - `funding_carry` (ATM) — high-frequency, high-WR, good RR
   - `autocorrelation_exploiter`, `hurst_regime_adaptive`, `volume_profile_value_area`, `adaptive_vr_confluence` (Alpha) — strong WR & expectancy when they fire

2. **Most Alpha strategies are dormant** (1-2 trades in 16 days) — overly restrictive thresholds or wrong timeframe

3. **Direction asymmetry is a real problem** — long side of Alpha Engine is a net drain

4. **Consensus routing is weak** — many "master picks" come from a single system (defeating multi-system filter purpose)

5. **Data quality issues** — conflicting exit-reason fields, mixed PnL units skew metrics

---

## 🏗️ Part 1: Implementation Plan

### PHASE 1: Immediate Safety (Priority: 🔴 CRITICAL)

#### Task 1.1: Enforce RR Gate Globally
- **Files:** `mercury2/config.py`, `crypto_signal_engine/risk_engine.py`, `cross_aggregation/fc_crypto_pro.py`
- **Current State:**
  - Mercury2 `MIN_RR = 2.0` ✅ (already above 1.5)
  - FC-PRO `MIN_RISK_REWARD = 1.5` ✅ (already at recommendation)
  - Signal Engine: Uses ATR-based TP/SL with R:R 1:2.67 ✅
- **Action:** Verify all entry points enforce RR ≥ 1.5. Already mostly done.
- **Status:** ✅ ALREADY IMPLEMENTED

#### Task 1.2: Kill/Disable Toxic Strategies
- **Files:** `kill_list.json`, `alpha_engine/auto_tuner.py`
- **Current State:**
  - `kill_list.json` — Contains: `smart_money_fvg`, `m2_liquidity_lag`, `ema_crossover`, `bollinger_squeeze`, `alpha_engine_long` ✅
  - `auto_tuner.py` — `HARD_DISABLED_STRATEGIES` set with 25+ toxic strategies ✅
  - `DIRECTION_RESTRICTED_STRATEGIES` — Alpha short-only enforced for key strategies ✅
- **Action:** Verify kill list matches Mercury AI recommendations. Already implemented.
- **Status:** ✅ ALREADY IMPLEMENTED

#### Task 1.3: Enforce Short-Only for Alpha Strategies
- **Files:** `alpha_engine/auto_tuner.py`
- **Current State:**
  - `DIRECTION_RESTRICTED_STRATEGIES` already contains: `autocorrelation_exploiter: SELL`, `adaptive_vr_confluence: SELL`, `multi_sigma_reversal: SELL`, etc. ✅
  - `core_whitelist.json` notes: "All Alpha Engine strategies have short-only override for long signals due to negative long expectancy" ✅
- **Action:** Verify direction gate is checked in the scanner hot path.
- **Status:** ✅ ALREADY IMPLEMENTED

#### Task 1.4: Freshness SLA (15-min signal decay)
- **Files:** `signal_aggregator/picks_router.py`, `signal_aggregator/aggregator_fixed.py`, `scripts/send_top_picks_now.py`
- **Current State:**
  - `picks_router.py` — `SIGNAL_FRESHNESS_MAX_SECONDS = 900` (15 min) ✅
  - `aggregator_fixed.py` — `SIGNAL_FRESHNESS_MAX_SECONDS = 900` (15 min) ✅
  - `send_top_picks_now.py` — `SIGNAL_FRESHNESS_MAX_SECONDS = 900` (15 min) ✅
  - `_is_signal_fresh()` method implemented in router ✅
- **Action:** Already implemented across all entry points.
- **Status:** ✅ ALREADY IMPLEMENTED

#### Task 1.5: Consensus Gate (≥ 2 Unique Systems for Master Picks)
- **Files:** `signal_aggregator/picks_router.py`
- **Current State:**
  - `_passes_master_consensus_gate()` method exists ✅
  - Requires `min_master_unique_systems` (default 2) ✅
  - `consensus_score` threshold enforced (default 0.55) ✅
  - `send_signal()` method also calls this gate ✅
- **Action:** Already implemented. Verify gate cannot be bypassed.
- **Status:** ✅ ALREADY IMPLEMENTED

### PHASE 2: Core/Incubator Split (Priority: 🟡 HIGH)

#### Task 2.1: Core Whitelist Configuration
- **File:** `core_whitelist.json`
- **Current State:** Already exists with 8 core strategies ✅
  - `funding_carry` (weight: 0.25)
  - `funding_carry_elite` (weight: 0.20)
  - `autocorrelation_exploiter` (weight: 0.15)
  - `hurst_regime_adaptive` (weight: 0.15)
  - `volume_profile_value_area` (weight: 0.10)
  - `adaptive_vr_confluence` (weight: 0.10)
  - `baby_battleground` (weight: 0.03)
  - `claws_of_doom` (weight: 0.02)
- **Mercury AI Recommendation:** Matches exactly ✅
- **Status:** ✅ ALREADY IMPLEMENTED

#### Task 2.2: Picks Router Core/Incubator Routing
- **File:** `signal_aggregator/picks_router.py`
- **Current State:**
  - `_load_core_whitelist()` — loads from `trading/data/core_whitelist.json` ✅
  - `_get_strategy_tier()` — classifies as 'core', 'incubator', 'kill', or 'unknown' ✅
  - `route_signal()` — routes to 'master_picks', 'freshpicks', 'sandbox', or 'incubator' ✅
- **Action:** Already implemented.
- **Status:** ✅ ALREADY IMPLEMENTED

#### Task 2.3: Position Sizing & Draw-Down Controls
- **Files:** `mercury2/config.py`, `mercury2/risk_engine.py`
- **Current State:**
  - Fixed 1% risk per trade (`RISK_PER_TRADE = 0.01`) ✅
  - High-ATR guard: halves position when ATR > 1.5× avg ✅
  - Max concurrent picks capped at 5 ✅
- **Mercury AI Recommendation:** 2% per Core pick, 0.5% per Incubator
- **Action Required:** 🟡 Consider raising Core to 2% and adding Incubator sizing at 0.5%
- **Status:** 🟡 NEEDS REVIEW — current 1% is more conservative than recommended

#### Task 2.4: Portfolio-Wide Max Draw-Down
- **Mercury AI Recommendation:** Hard stop at 10% equity loss
- **Current State:** Not implemented as a portfolio-wide circuit breaker
- **File to create/modify:** `risk_management/portfolio_circuit_breaker.py`
- **Action Required:** 🔴 Implement portfolio-wide DD cap
- **Status:** 🔴 NOT YET IMPLEMENTED

### PHASE 3: Data Quality & Attribution (Priority: 🟡 HIGH)

#### Task 3.1: Normalize PnL Units
- **Mercury AI Issue:** Mixed PnL units (%, USDT, raw) skew metrics
- **Current State:** Various systems store PnL differently
- **Action Required:** Create a normalization layer in aggregator
- **Status:** 🔴 NOT YET IMPLEMENTED

#### Task 3.2: Add Status Field to Closed Picks
- **Mercury AI Recommendation:** Add `status` field (`closed`, `canceled`, `stale`)
- **Current State:** Most systems only have implicit status
- **Action Required:** Standardize across all `closed_picks.json` files
- **Status:** 🔴 NOT YET IMPLEMENTED

#### Task 3.3: Post-Trade Attribution Script
- **Mercury AI Recommendation:** Run after every close to recompute WR/expectancy per component → `component_perf_daily.json`
- **Current State:** No automated daily attribution
- **Action Required:** Create `scripts/post_trade_attribution.py`
- **Status:** 🔴 NOT YET IMPLEMENTED

### PHASE 4: Weekly PM Dashboard (Priority: 🟢 MEDIUM)

#### Task 4.1: Component Metrics Tracking
- **Mercury AI Metrics:**
  
  | Metric | Frequency | Alert Condition |
  |---|---|---|
  | Component expectancy | Weekly | < 0% → demote |
  | Win Rate | Weekly | < 30% → demote |
  | Max Draw-Down | Weekly | > 5% of allocation → demote |
  | Turnover | Weekly | > 30% of allocation → review |
  | Slippage drift | Weekly | > 0.2% per trade → tighten RR |
  | Regime decay | Real-time | Regime flag flip → pause |

- **Action Required:** Create weekly automated report generator
- **Status:** 🔴 NOT YET IMPLEMENTED

### PHASE 5: Edge Preservation (Priority: 🟢 MEDIUM)

#### Task 5.1: Loosen Dormant Alpha Thresholds
- **Mercury AI Issue:** Most Alpha strategies fire 1-2 times in 16 days — insufficient data to prove/kill
- **Action:** Reduce RSI-divergence from 3σ to 2σ on select strategies
- **Status:** 🟡 NEEDS RESEARCH

#### Task 5.2: Regime-Aware Filter
- **Mercury AI Recommendation:** Gate `hurst_regime_adaptive` when Hurst > 0.6
- **Current State:** `core_whitelist.json` has `regime_sensitive: true` and `preferred_regime: "trending"` ✅
- **Action:** Verify runtime enforcement
- **Status:** 🟡 PARTIALLY IMPLEMENTED

#### Task 5.3: Vol-Adjusted Position Sizing
- **Mercury AI Recommendation:** Scale size by `1/σ_price`
- **Current State:** Mercury2 has high-ATR guard (halves on ATR > 1.5× avg) ✅
- **Action:** Extend to all systems
- **Status:** 🟡 PARTIALLY IMPLEMENTED

#### Task 5.4: Signal Decay Metric
- **Mercury AI Recommendation:** Auto-retire component if no trigger > 7 days
- **Current State:** `fc_crypto_pro.py` has `check_signal_staleness()` with `STALE_THRESHOLD_DAYS = 7` ✅
- **Action:** Already implemented.
- **Status:** ✅ ALREADY IMPLEMENTED

---

## 📊 Part 2: Hedge Fund / Mutual Fund Grade Techniques

### 2.1 Data & Feature Foundations

| Technique | Mercury AI Recommendation | Our Current State | Gap |
|---|---|---|---|
| **Clean price series** | Tick-by-tick from multiple exchanges | Binance 1h candles only | 🔴 Major gap |
| **Feature engineering** | Technical + on-chain + macro + sentiment | RSI, MACD, ATR, BB, vol, F&G, funding | 🟡 Partial |
| **Label generation** | Risk-adjusted forward return | Binary win/loss + raw PnL | 🟡 Can improve |
| **Transaction cost model** | Micro-structure: `TC = a + b·√(size/ADV) + c·spread` | Simple fee + slippage map | 🟡 Adequate for current scale |
| **Data quality** | Rule-based filters, imputation, versioned lake | Basic outlier handling | 🟡 Needs improvement |

### 2.2 Model-Building & Validation

| Technique | Mercury AI Recommendation | Our Current State | Gap |
|---|---|---|---|
| **Factor regression** | Ridge/Lasso on factor returns | XGBoost ensembles | 🟡 Different approach, valid |
| **Cointegration** | Johansen + Kalman filter | Not implemented | 🔴 Future opportunity |
| **GARCH volatility** | Rolling-window vol forecasting | ATR-based (simpler) | 🟡 Adequate |
| **Regime detection** | Markov-Regime-Switching (MRS) | Hurst + clustering | ✅ Similar approach |
| **Tree ensembles** | XGBoost/LightGBM with SHAP | XGBoost ensemble (3 variants) + LightGBM | ✅ Implemented |
| **Deep learning** | LSTM/Transformer | Not yet | 🔴 Future phase |
| **Reinforcement learning** | RL position sizing | Not yet | 🔴 Future phase |
| **Walk-forward backtest** | Rolling-origin, 30d train / 7d test | Some back-testing infra exists | 🟡 Needs formalization |
| **Monte Carlo stress test** | Block bootstrap + synthetic shocks | Not implemented | 🔴 Future phase |
| **Paper trading period** | 30-day minimum before real capital | Incubator concept exists | 🟡 Formalize |
| **Feature drift monitoring** | K-S distance, auto-retrain | Not implemented | 🔴 Future phase |
| **Model registry** | MLflow or Git-backed | Not implemented | 🔴 Future phase |

### 2.3 Risk-Budgeting & Governance

| Technique | Mercury AI Recommendation | Our Current State | Gap |
|---|---|---|---|
| **Risk budgeting** | Fixed % of portfolio volatility per sleeve | Fixed 1% per trade | 🟡 Simpler but functional |
| **Portfolio DD limits** | Hard stop at 8% from peak | Not implemented | 🔴 Critical gap |
| **Diversification (PCA)** | Max eigenvalue < 0.5 for core book | Not measured | 🟡 Future |
| **Smart order routing** | Multi-exchange, TWAP/VWAP | Not applicable (signal-only) | N/A |
| **SLA dashboards** | Latency < 200ms, freshness < 5s | 15-min freshness SLA | 🟡 Different timeframe |
| **Model governance** | Committee review, sign-off | Not implemented | 🟢 Nice-to-have |
| **Weekly attribution** | By factor, regime, exchange | Not implemented | 🔴 Needed |
| **Audit logs** | Tamper-proof, append-only JSON | JSON files exist, not tamper-proof | 🟡 Adequate |

---

## 📈 Mercury AI's Sample Workflow vs. Our Implementation

| Step | Mercury AI Recommendation | Our Current Implementation | Match |
|---|---|---|---|
| 1. Data Ingestion | tick → cleaned → feature store | Binance API → 1h candles → features | 🟡 |
| 2. Feature Generation | technical + on-chain + macro | RSI/MACD/ATR/BB + F&G + funding | 🟡 |
| 3. Regime Detector | Hurst + clustering → regime ID | `hurst_regime_adaptive` strategy | ✅ |
| 4. Model Ensemble | Tree + cointegration + RL | 3× XGBoost + LightGBM | 🟡 |
| 5. Signal Gate | RR ≥ 1.5 + ≥ 2 models + freshness | RR gate + consensus gate + freshness | ✅ |
| 6. Risk Budget | Fractional Kelly, 2% cap | 1% fixed per trade | 🟡 |
| 7. Smart Order Router | Multi-exchange, slippage control | Discord signal only | N/A |
| 8. Post-Trade Attribution | `closed_picks.json` → weekly PM | Partial attribution | 🟡 |
| 9. Model Risk Review | Monthly expectancy check | Auto-tuner continuous | ✅ |

---

## 🎯 Investor-Readiness Checklist (from Mercury AI)

| ✅ Item | Our Status | Action Needed |
|---|---|---|
| Statistically significant edge | 🟡 Some strategies show edge | Formalize OOS Sharpe > 1.0 proof |
| Robust TCM | ✅ Fee + slippage map per symbol | Document as report |
| Risk-budget transparency | 🟡 1% per trade, core/incubator split | Add allocation table |
| Model governance | 🔴 No formal registry | Future phase |
| Explainability | ✅ `pick_reason` field with full guard docs | Already strong |
| Regime awareness | ✅ Hurst regime + preferred regime in whitelist | Documented |
| Operational reliability | 🟡 15-min freshness SLA | Add latency monitoring |
| Independent audit | 🔴 Not available | External engagement needed |
| Investor reporting | 🔴 No formal cadence | Create weekly report generator |

---

## 🚀 Immediate Action Items (Agent Fleet Assignments)

### Agent 1: Portfolio Circuit Breaker 🔴
**File:** `risk_management/portfolio_circuit_breaker.py`
**Task:** Implement portfolio-wide max draw-down at 10% equity + per-component DD at 5%
**Priority:** CRITICAL

### Agent 2: Post-Trade Attribution Engine 🔴
**File:** `scripts/post_trade_attribution.py`
**Task:** Daily script that normalizes PnL to USDT, computes WR/expectancy per component, writes `component_perf_daily.json`
**Priority:** HIGH

### Agent 3: Weekly PM Dashboard Data Generator 🟡
**File:** `scripts/weekly_pm_report.py`
**Task:** Generate weekly performance attribution with all Mercury AI metrics (expectancy, WR, max DD, turnover, slippage)
**Priority:** HIGH

### Agent 4: Data Quality Standardization 🟡
**File:** `scripts/normalize_closed_picks.py`
**Task:** Add `status` field, normalize PnL units, standardize exit reasons across all systems
**Priority:** HIGH

### Agent 5: Monte Carlo Stress Tester 🟢
**File:** `scripts/monte_carlo_stress_test.py`
**Task:** Block bootstrap + synthetic shocks on core book, estimate tail risk
**Priority:** MEDIUM (Phase 2)

---

## 📁 Files Referenced in This Plan

| File | Status | Notes |
|---|---|---|
| [`core_whitelist.json`](file:///e:/findtorontoevents_antigravity.ca/core_whitelist.json) | ✅ Implemented | 8 core strategies with weights |
| [`kill_list.json`](file:///e:/findtorontoevents_antigravity.ca/kill_list.json) | ✅ Implemented | 5 toxic strategies + auto-kill rules |
| [`signal_aggregator/picks_router.py`](file:///e:/findtorontoevents_antigravity.ca/signal_aggregator/picks_router.py) | ✅ Implemented | Freshness SLA, consensus gate, core/incubator routing |
| [`cross_aggregation/fc_crypto_pro.py`](file:///e:/findtorontoevents_antigravity.ca/cross_aggregation/fc_crypto_pro.py) | ✅ Implemented | RR gate (1.5), kill list, signal staleness |
| [`alpha_engine/auto_tuner.py`](file:///e:/findtorontoevents_antigravity.ca/alpha_engine/auto_tuner.py) | ✅ Implemented | 25+ hard-disabled, direction restrictions |
| [`mercury2/config.py`](file:///e:/findtorontoevents_antigravity.ca/mercury2/config.py) | ✅ Implemented | MIN_RR=2.0, symbol blacklist, cost model |
| [`mercury2/risk_engine.py`](file:///e:/findtorontoevents_antigravity.ca/mercury2/risk_engine.py) | ✅ Implemented | 7 guards, ATR-based TP/SL, high-ATR guard |
| [`scripts/send_top_picks_now.py`](file:///e:/findtorontoevents_antigravity.ca/scripts/send_top_picks_now.py) | ✅ Implemented | Safety filters (RR + freshness) |
| [`signal_aggregator/aggregator_fixed.py`](file:///e:/findtorontoevents_antigravity.ca/signal_aggregator/aggregator_fixed.py) | ✅ Implemented | 15-min freshness, consensus calculation |
| `risk_management/portfolio_circuit_breaker.py` | 🔴 Not yet | To be created by Agent 1 |
| `scripts/post_trade_attribution.py` | 🔴 Not yet | To be created by Agent 2 |
| `scripts/weekly_pm_report.py` | 🔴 Not yet | To be created by Agent 3 |
| `scripts/normalize_closed_picks.py` | 🔴 Not yet | To be created by Agent 4 |

---

## 📝 Version History

| Date | Author | Changes |
|---|---|---|
| 2026-03-03 18:27 EST | Antigravity Agent Fleet | Initial plan created from Mercury AI / Inception Labs feedback |

---

> **Bottom Line:** Our system has already implemented ~70% of Mercury AI's pragmatic recommendations (RR gates, freshness SLA, consensus gate, kill list, direction restrictions, core whitelist). The remaining 30% focuses on portfolio-level risk management (circuit breakers, DD caps), data quality normalization, post-trade attribution, and investor-grade reporting. The more advanced hedge-fund techniques (RL, deep learning, Monte Carlo, model registry) are future phases.
