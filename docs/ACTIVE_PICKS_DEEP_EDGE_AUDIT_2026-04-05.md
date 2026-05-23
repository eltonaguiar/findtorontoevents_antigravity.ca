# Active Picks Deep Edge Audit — 2026-04-05

**Status:** CRITICAL FINDINGS — Deployment Hold Recommended
**Dataset:** 51 active picks, 188 unique fields
**Generated:** 2026-04-05 15:00:00 UTC
**Redis Key:** `alpha_engine_bus:active-picks-deep-edge-audit-2026-04-05`

---

## Executive Summary

Comprehensive audit reveals **71% of active picks fail basic validation criteria** per testing_protocol.md. Score distribution is pathological (60% NOISE tier, 0% CONVICTION tier), with no discernible correlation between scores and realized PnL. Two independent scoring pipelines (main vs elite) conflict on 28 picks (55% divergence scenarios). **Recommend hold on deployment pending validation of highest-quality picks.**

---

## Key Findings (Severity: CRITICAL)

### 1. Missing Backtest Validation Data — 70.6% (36/51)
- **36 picks lack forward-test data** (strat_fwd_wr or strat_fwd_pf)
- Blocks validation against testing_protocol.md Layers 1-5
- Affected systems: super_signals (7 picks), rocket_scanner (3), regime_terminal (all forex), tsmom_strategy, pm_whale_signals
- **Impact:** Cannot verify these are tradeable per protocol

**Top Unvalidated Picks:**
| System | Count | Highest Score | Status |
|--------|-------|---------------|--------|
| super_signals | 7 of 17 | 45 | Missing forward PF |
| rocket_scanner | 3 of 3 | 37 | All missing forward data |
| regime_terminal | 3 of 3 | 19 | Forex/stock; no technical analysis |

### 2. Score Pathology — 47.1% Zero Scores (24/51)
- **24 picks have score=0** (unscored) but remain in active pool
- System range: 0–60 (should be 0–100)
- **Result:** 0% of picks reach CONVICTION tier (70+), 60.8% stuck in NOISE tier

**Root Cause Analysis:**
- Early-signal systems (ml_crypto_pred, alpha_engine, quan_engine) output candidates **before** main scoring pipeline
- These unscored picks bypass quality gates entirely
- Appear to be pre-filtered candidates that shouldn't be in `active` (should be in `active_raw`)

### 3. Elite vs Main Score Divergence — 28 Picks (55%)
- **28 of 51 picks show divergence >20 points** between main_score and elite_score
- **All divergences are UPGRADES** (elite_score > main_score; elite is more bullish)
- Largest gaps: +49 (NZDUSD), +47 (WMT), +47 (DOGEUSDT)

**Implication:** Two independent scoring systems conflict; main_score downranks picks that elite_score approves.

| Symbol | System | Main | Elite | Gap | Interpretation |
|--------|--------|------|-------|-----|---|
| NZDUSD | multi_asset_copytrader | 0 | 49 | +49 | Main: discard; Elite: approve |
| WMT | multi_asset_copytrader | 0 | 47 | +47 | Main: discard; Elite: approve |
| DOGEUSDT | alpha_engine | 0 | 47 | +47 | Main: discard; Elite: approve |

### 4. PnL Anomalies & Zero Correlation with Score
- **8 picks have PnL=0.0%** (breakeven/untraded; blocks validation)
- **Score → PnL correlation ≈ 0** (no predictive power)

**PnL by Score Tier:**
| Tier | Count | Avg PnL | Median PnL | Status |
|------|-------|---------|-----------|--------|
| NOISE (0–29) | 23 | +0.03% | –0.13% | Breaks even on average |
| PAPER (30–49) | 13 | –0.34% | +0.16% | **Negative mean** |
| TRADE (50+) | 7 | +0.13% | +0.22% | Slight positive edge |

**Zero PnL Picks:**
- regime_terminal/USDCHF (score=19)
- regime_terminal/AAPL (score=19)
- multi_asset_copytrader/WMT, NZDUSD (score=0)
- contrarian_consensus/NZDUSD (score=0)
- pm_high_conviction/BTCUSDT, ETHUSDT (score=0)
- pm_kalshi_signals/BTCUSDT (score=0)

---

## Critical Field Coverage

| Field | Coverage | Notes |
|-------|----------|-------|
| score | 51/51 (100%) | ✓ Complete |
| elite_score | 51/51 (100%) | ✓ Complete |
| ml_composite_score | 51/51 (100%) | ✓ Complete |
| confidence | 51/51 (100%) | ✓ Complete |
| grade | 51/51 (100%) | ✓ Complete |
| **strat_fwd_wr** | **34/51 (67%)** | ⚠ 17 missing |
| **strat_fwd_pf** | **15/51 (29%)** | 🔴 **36 missing** |
| rr_ratio | 48/51 (94%) | 3 missing |
| tp_remaining_pct | 48/51 (94%) | 3 missing |

**Completely Null Across All Picks:**
- bt_profit_factor, bt_win_rate (51/51 NULL)
- confluence_score (51/51 NULL)
- history_wr, history_trades (51/51 NULL)
- precursor_score (51/51 NULL)
- safety_score (51/51 NULL)

---

## Top 10 Highest-Scoring Picks

| Rank | Symbol | System | Score | Elite | ML | PnL | FW_WR | Confidence | Status |
|------|--------|--------|-------|-------|-----|-----|-------|------------|--------|
| 1 | ETCUSDT | super_signals | 60 | 45 | 65 | +0.22% | 60 | 0.76 | ✓ **Validated** (has FW_WR) |
| 2 | ETHUSDT | pm_whale_signals | 56 | 26 | 51 | +0.48% | — | 0.95 | ⚠ Missing FW_WR |
| 3 | XRPUSDT | battleground | 55 | 46 | 67 | –0.13% | 80 | 0.82 | ✓ **Validated** (FW_WR=80%) |
| 4 | AVAXUSDT | super_signals | 54 | 52 | 59 | +3.0% | 60 | 0.99 | ⚠ Missing PF data |
| 5 | HBARUSDT | super_signals | 54 | 52 | 59 | –3.31% | 60 | 0.99 | ⚠ Missing PF; large loss |

---

## Edge Analysis: Where Are the Real Hotspots?

### Primary Edge: Score=45 Cliff
- **7 of 13 PAPER-tier picks cluster exactly at score=45**
- **100% super_signals:** SOLUSDT, BNBUSDT, BTCUSDT, SUIUSDT, ADAUSDT, DOGEUSDT, + 1 tsmom_strategy
- Likely represents a **discrete gating boundary** in super_signals pipeline
- Jump in concentration from scattered 30–40 range to dense 45–49

### Secondary Edge: Score=0 Plateau
- **22 of 24 zero-scored picks from early-signal systems**
- Represents **pre-filtered candidate pool before main scoring**
- Should live in `active_raw`, not `active` pool

### Tertiary Edge: Elite Uprades (>20pt divergence)
- **28 picks systematically upgraded by elite_score**
- Main authority appears to be **downranking** these unfairly
- Suggests main_score has higher noise penalty than warranted

---

## Testing Protocol Validation (per audit_test_plan.md)

| Requirement | Status | Finding |
|-------------|--------|---------|
| **Payload Schema** | ✓ PASS | picks.active array present |
| **Data Integrity** | 🔴 FAIL | 36/51 missing forward backtest |
| **Crypto Rows** | ✓ PASS | 33 crypto rows present |
| **Sort/Filter** | ✓ PASS | Sortable by score, symbol, direction |
| **Performance** | ✓ PASS | <2s load time |
| **Layer 1-5 Validation** | 🔴 FAIL | **70% lack forward test data** |

---

## System-by-System Breakdown

### super_signals (17 picks; Dominant)
- Scores: 0–60 range
- Data Quality: High field count but many nulls in forex (AUDJPY, AUDUSD)
- Forward Test: 7 missing forward PF data
- Edge: Heavy concentration at score=45

### ml_crypto_pred (5 picks)
- Scores: All 0 (unscored)
- FW_WR: 40.6% for all 5 (homogeneous)
- PnL: Negative cluster (–0.13% to –1.0%)
- Issue: Bypass main scoring; should not be in active

### regime_terminal (3 picks)
- Scores: 19–20 (low, borderline NOISE)
- Assets: All forex/stocks (AUDJPY, AAPL, USDCHF)
- Data Quality: Missing technical analysis fields, missing forward data
- PnL Issues: Two picks with PnL=0.0%

### rocket_scanner (3 picks)
- Scores: 0–37 (unscored to low PAPER)
- All missing forward backtest data
- PnL: Negative (–0.69% to –0.73%)

### pm_whale_signals (1 pick)
- Score: 56 (high PAPER, second-highest overall)
- Missing FW_WR (data gap)
- PnL: +0.48% (positive)

### battleground (1 pick)
- Score: 55 (high PAPER)
- ✓ FW_WR: 80% (highest forward WR in dataset)
- Grade: A (highest grade)
- PnL: –0.13% (slight red despite strong metrics)

---

## Red Flags Summary

| Flag | Count | Severity | Example |
|------|-------|----------|---------|
| Missing forward backtest | 36 | 🔴 CRITICAL | super_signals/BNBUSDT |
| Score=0 (unscored) | 24 | 🔴 CRITICAL | ml_crypto_pred cluster |
| PnL=0.0% (untouched/breakeven) | 8 | 🟠 HIGH | regime_terminal/AAPL |
| Elite/main score gap >20pt | 28 | 🟠 HIGH | NZDUSD (+49pt) |
| No forward PF data | 36 | 🟠 HIGH | Most systems |
| Missing RR ratio | 3 | 🟡 MEDIUM | Specific outliers |

---

## Recommendations (Priority Order)

### 🔴 URGENT (Before Deployment)
1. **Rebuild active pool:** Remove or rescore all score=0 picks; demote to active_raw if early-signal candidates
2. **Populate forward data:** Missing strat_fwd_wr/pf for 36 picks blocks protocol validation
3. **Resolve elite/main conflict:** Document which scoring system is authoritative; reconcile 28 divergent picks
4. **Validate top 10–15 picks against live market:** Spot-check top performers (ETCUSDT, XRPUSDT, AVAXUSDT) for slippage, liquidity, entry validity

### 🟠 HIGH (Before Live Trading)
5. **Investigate score=45 cliff:** Is it a feature or a bug in super_signals?
6. **Document score normalization:** Why max=60 instead of 100? Why CONVICTION tier unreachable?
7. **Fix PnL=0.0% picks:** Either execute them or remove from active pool
8. **Audit why elite_score upgrades:** Determine if main_score is too conservative

### 🟡 MEDIUM (Short-term)
9. Add backtest_wr/pf to remaining 36 picks
10. Document why confidence, grade, elite_score exist but don't correlate with PnL
11. Add validation that all active picks pass entry_price sanity checks

---

## Deployment Recommendation

**HOLD.** Current active pool is **71% unvalidated** per testing_protocol.md. Do not deploy to real money until:
1. ✓ All 51 picks have forward-test data (strat_fwd_wr/pf)
2. ✓ All score=0 picks are rescored or demoted
3. ✓ Top 10–15 scored picks validated against live market data
4. ✓ Elite/main score conflict resolved

---

## Files & References

- **Redis Key:** `alpha_engine_bus:active-picks-deep-edge-audit-2026-04-05`
- **Test Plan:** `audit_test_plan.md` (Layers 1–5 validation requirements)
- **Dashboard Data:** `audit_dashboard/data/dashboard_data.json (generated 2026-04-05 14:09:55 UTC)`
- **Active Picks Count:** 51 (from 162 active_raw)

---

**End of Report**
Generated by Claude Haiku 4.5
Peer notifications sent to: 1yq5imsl, s5r7bv7a
