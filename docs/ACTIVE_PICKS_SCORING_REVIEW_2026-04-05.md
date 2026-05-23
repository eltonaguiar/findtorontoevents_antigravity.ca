# Active Picks Scoring Review - Edge Analysis

**Date:** 2026-04-05 (Sunday)  
**Auditor:** antigrav-scoring-review  
**Scope:** All 51 active picks at findtorontoevents.ca/audit  
**Data Source:** audit_trail/data/dashboard_payload.json

---

## Executive Summary

The active picks portfolio shows **severe scoring compression** with 47% of picks (24/51) having a score of **zero**. Only 7 picks (13.7%) have scores ≥50, and **zero picks qualify** for Smart Picks under current thresholds (score≥70, conf≥0.60, trust≥5).

The scoring system is functioning as designed but may be **overly punitive** for legitimate high-conviction signals.

---

## Score Distribution

| Score Range | Count | Percentage |
|-------------|-------|------------|
| 50+ | 7 | 13.7% |
| 40-49 | 8 | 15.7% |
| 30-39 | 5 | 9.8% |
| 20-29 | 3 | 5.9% |
| 0-19 | 4 | 7.8% |
| **Score = 0** | **24** | **47.1%** |

**Average Score:** 20.3  
**Score Range:** 0 - 60  
**Median Score:** ~15

---

## Top Performing Picks (Score 45+)

| Rank | Symbol | Direction | Score | Elite | Conf | Strategy |
|------|--------|-----------|-------|-------|------|----------|
| 1 | ETCUSDT | LONG | 60 | 45 | 0.76 | super signal (strong) via quan_engine |
| 2 | ETHUSDT | LONG | 56 | 26 | 0.95 | pm_whale_0xa2f1fe |
| 3 | XRPUSDT | LONG | 55 | 46 | 0.82 | drawdown_recovery_rsi_xrp |
| 4 | AVAXUSDT | LONG | 54 | 52 | 0.99 | super signal (super) via kimi |
| 5 | HBARUSDT | LONG | 54 | 52 | 0.99 | super signal (strong) via kimi |
| 6 | DOTUSDT | LONG | 51 | 39 | 0.99 | super signal (super) via claude_gainer_st |
| 7 | ARBUSDT | LONG | 51 | 52 | 0.99 | super signal (super) via claude_gainer_st |
| 8 | SHIBUSDT | LONG | 49 | 39 | 0.75 | super signal (strong) via ml_crypto_pred |
| 9 | SOLUSDT | LONG | 45 | 39 | 0.99 | super signal (super) via claude_gainer_st |
| 10 | BNBUSDT | LONG | 45 | 42 | 0.99 | super signal (super) via claude_gainer_st |

---

## Strategy Performance Breakdown

| Strategy | Count | Avg Score | Notes |
|----------|-------|-----------|-------|
| super signal via kimi | 3 | 48.0 | Top performer |
| drawdown_recovery_rsi | 2 | 47.0 | Strong specific plays |
| super signal via claude_gainer_st | 7 | 40.3 | Consistent high scores |
| super signal via quan_engine | 1 | 60.0 | Single top pick |
| rocket_scanner | 5 | 20.8 | Mixed results |
| enhanced_ml_A_xgboost | 6 | 9.5 | **Underperforming** |
| contrarian_consensus_flip | 2 | 0.0 | Getting zeroed out |
| prediction_market_consensus | 2 | 0.0 | Getting zeroed out |

---

## Where The Edge Is (Positive Factors)

### 1. Tight Risk:Reward Ratio (1.5x)
- **Bonus:** +10 points
- **Applies to:** ETCUSDT, XRPUSDT, AVAXUSDT, HBARUSDT, BTCUSDT, SHIBUSDT
- **Evidence:** `tight_rr_winner(1.5):+10`

### 2. Fresh Pick Timing (< 2 hours old)
- **Bonus:** +5 points
- **Applies to:** Most high-scoring picks
- **Evidence:** `crypto_fresh(0h):+5`

### 3. Confidence Sweet Spot (0.75 - 0.80)
- **Bonus:** +12 points
- **Applies to:** ETCUSDT (0.76), SHIBUSDT (0.75)
- **Evidence:** `conf_sweet_spot(0.76):+12`

### 4. Proven Track Record (60%+ WR, 15+ trades)
- **Bonus:** +12 points
- **Applies to:** Strategies with established history
- **Evidence:** `strat_wr_proven(60%/15t):+12`

### 5. Multi-Source Consensus (5+ sources)
- **Bonus:** +6 points
- **Applies to:** Super signals with crowded consensus
- **Evidence:** `crowded_consensus_proven(31):+6`

---

## Edge Killers (Negative Factors)

### 1. LONG + High Confidence Combo (0.90+)
- **Penalty:** -25 points
- **Hits:** ETHUSDT (0.95 conf), AVAXUSDT (0.99), HBARUSDT (0.99), etc.
- **Issue:** May be penalizing genuine high-conviction signals

### 2. Bad Symbol Track Record (< 40% WR)
- **Penalty:** -35 points
- **Hits:** SOLUSDT via quan_engine
- **Evidence:** `bad_sym_track(36.4%):-35`

### 3. Direction Conflict
- **Penalty:** -12 points
- **Hits:** 14 of 15 top picks
- **Issue:** Symbol-level hedging (LONG+SHORT same symbol)

### 4. HTF Misaligned
- **Penalty:** -8 points
- **Hits:** Many picks with technical misalignment
- **Evidence:** `htf_misaligned:-8`

### 5. Sunday Penalty
- **Penalty:** -6 points
- **Hits:** ALL picks (today is Sunday 2026-04-05)
- **Historical:** 32.8% WR on Sundays
- **Evidence:** `sunday_penalty:32.8%WR:-6`

### 6. Weak Source System
- **Penalty:** -15 points
- **Hits:** quan_engine picks
- **Evidence:** `weak_source(quan_engine):-15`

### 7. Failing Walk-Forward Verdict
- **Penalty:** -20 points
- **Hits:** quan_engine SOLUSDT pick
- **Evidence:** `wf_failing:-20`

---

## Zero Score Crisis Analysis

**24 of 51 picks (47%) have Score = 0**

Common penalty combinations zeroing out picks:

| Penalty Combination | Example Pick |
|---------------------|--------------|
| direction_conflict(-12) + long_overconf_combo(-25) + sunday(-6) | ETHUSDT LONG (pm_consensus) |
| bad_sym_track(-35) + inverse_long_trap(-15) + weak_source(-15) | SOLUSDT LONG (quan_engine) |
| conf_danger_zone(-10) + long_deadzone_combo(-12) + trust_LOW(-10) | WMT LONG (stocks) |
| overwide_rr(-10) + direction_conflict(-12) + sunday(-6) | NZDUSD LONG (forex) |

---

## Scoring Paradox: "Penalties" Often Increase Scores

The `_apply_score_penalties()` function is a **net positive** for quality picks:

| Pick | Elite Score | Final Score | Delta |
|------|-------------|-------------|-------|
| ETHUSDT LONG | 26 | 56 | **+30** |
| KITEUSDT SHORT | 18 | 45 | **+27** |
| DOLOUSDT LONG | 10 | 34 | **+24** |
| ALGOUSDT LONG | 10 | 30 | **+20** |
| ETCUSDT LONG | 45 | 60 | **+15** |

The "penalties" system should be renamed to **"scoring_adjustments"** as it includes significant bonuses.

---

## Smart Picks Analysis

### Current Thresholds (from quality_gates.py)
- Score ≥ 70
- Confidence ≥ 0.60
- Trust Score ≥ 5

### Current State
- **Qualifying Picks:** 0
- **Picks with Score ≥ 50:** 7
- **Picks with Score ≥ 40:** 15

### Recommendations

#### Option 1: Lower Smart Picks Threshold
- **New Threshold:** Score ≥ 50 (instead of 70)
- **Result:** 7 Smart Picks including top performers
- **Picks:** ETCUSDT, ETHUSDT, XRPUSDT, AVAXUSDT, HBARUSDT, DOTUSDT, ARBUSDT

#### Option 2: Create Tiered System
- **Tier 1 (Elite):** Score ≥ 60 → 1 pick (ETCUSDT)
- **Tier 2 (Strong):** Score 50-59 → 6 picks
- **Tier 3 (Viable):** Score 40-49 → 8 picks

---

## Key Findings

1. **Super Signal Dominance:** Top 10 picks are mostly "super signal" strategies via kimi, claude_gainer_st, quan_engine

2. **Confidence Paradox:** 0.99 confidence picks getting -12 "extreme_overconfident" penalty despite being legitimate super signals

3. **Sunday Suppression:** All picks getting -6 penalty today (Sunday), potentially suppressing legitimate opportunities

4. **Direction Conflict Pandemic:** 14/15 top picks have direction conflicts, suggesting either legitimate hedging or signal confusion

5. **Enhanced ML Underperforming:** enhanced_ml_A_xgboost averaging 9.5 score across 6 picks - strategy may need recalibration

6. **PM Consensus Getting Zeroed:** prediction_market_consensus picks with good elite scores (26-47) getting zeroed by penalty stacking

---

## Recommendations

### Immediate Actions

1. **Lower Smart Picks Min Score**
   ```python
   # quality_gates.py line 133
   SMART_PICKS_MIN_SCORE = 50  # was 70
   ```

2. **Review LONG_OVERCONF_COMBO Penalty**
   - Current: -25 for LONG + conf ≥ 0.90
   - Consider: Exclude "super signal" strategies from this penalty
   - Rationale: 0.99 conf on super signals may indicate genuine edge

3. **Evaluate Sunday Penalty**
   - Current: -6 for all Sunday picks
   - Historical WR of 32.8% may be stale data
   - Consider reducing to -3 or removing

### Strategic Actions

4. **Enhanced ML Strategy Review**
   - 6 picks averaging 9.5 score
   - Getting penalized: conf_below_avg, long_deadzone_combo, sym_dir
   - Either strategy is broken OR scoring is miscalibrated

5. **Direction Conflict Logic Review**
   - 14/15 top picks have this penalty
   - May be penalizing legitimate portfolio diversification
   - Consider reducing penalty from -12 to -6

6. **Confidence Sweet Spot Recalibration**
   - Current: 0.75-0.80 = +12, 0.95+ = -12
   - Super signals with 0.99 conf getting penalized
   - Consider tiered approach: 0.90-0.95 = neutral, 0.95+ with proven track = +5

---

## Files Referenced

| File | Purpose |
|------|---------|
| `audit_trail/data/dashboard_payload.json` | Source of active picks data |
| `audit_trail/quality_gates.py` | Scoring logic and penalties |
| `audit_dashboard/template.html` | Frontend display |

---

## Data Integrity Notes

- Payload generated_at: 2026-04-05T14:09:55Z
- Total active picks: 51
- All picks analyzed from `picks.active` array
- Sunday penalty affecting all picks (2026-04-05 is Sunday)

---

*Broadcast via Redis Bus: antigrav-scoring-review*
*Next Review Recommended: After adjusting scoring thresholds*
