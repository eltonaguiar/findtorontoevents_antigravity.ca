# Crypto Pattern Analysis Report
## Finding the "Golden Criteria" for Winning Picks

**Generated:** 2026-03-27  
**Dataset:** 1,011 closed picks + 54 active picks

---

## Executive Summary

### Current Performance
- **Total Closed Picks:** 1,011
- **Win Rate:** 27.4% (277 winners, 734 losers)
- **Overall PnL:** Negative (heavily skewed by losers)

### Key Finding
The system shows a **positive correlation** between scores and performance, but the absolute values are still negative. This suggests:
1. Scoring logic is directionally correct
2. **BUT** thresholds are too low or market conditions are unfavorable
3. **Metadata gaps** are preventing proper filtering

---

## Issue #1: Empty Track/Strong for Crypto Picks

### Problem
- **53 out of 54 active picks** (98%) have empty `track_record`
- **54 out of 54 active picks** have `strong_signal=false`
- **75% of crypto picks** are missing critical metadata:
  - `track_record`
  - `strong_signal`
  - `regime_at_entry`
  - `ml_score`
  - `confluence_score`

### Root Cause
The `track_record` field is being set to `None` or `"None"` (string) instead of calculated values. This appears to be a **data pipeline issue** where track records aren't being populated for crypto picks.

### Recommendation
1. **Fix the track_record calculation** in the pick generation pipeline
2. **Add fallback logic** - if track_record is empty, calculate it from historical data
3. **Add validation** to ensure all new picks have required metadata

---

## Issue #2: Weird "??" Icons Beside Scores

### Investigation Result
The "??" icons are **NOT** encoding issues in the JSON files. The symbols appear clean in the data.

### Likely Cause
The "??" is likely appearing in the **dashboard/UI rendering** when:
1. A field is `null` or `None`
2. The display template can't handle missing values
3. Unicode characters aren't rendering properly in the browser

### Recommendation
1. Check the dashboard HTML/template for null handling
2. Add default values when rendering: `"N/A"` or `"-"` instead of `??`
3. Ensure UTF-8 encoding is set in HTML headers

---

## Question #1: Which Metric Correlates to Positive PnL?

### Score Correlation Analysis

| Score Field | Low (Q1) PnL | High (Q4) PnL | Trend |
|-------------|--------------|---------------|-------|
| **elite_score** | -0.219% | -0.096% | ✅ POSITIVE |
| **ml_composite_score** | -0.219% | -0.064% | ✅ POSITIVE |
| **method_a_score** | -0.195% | -0.148% | ✅ POSITIVE |
| **confidence** | -0.193% | -0.114% | ✅ POSITIVE |
| **consensus_pct** | -0.141% | -0.131% | ✅ POSITIVE |
| **risk_reward** | -0.156% | -0.115% | ✅ POSITIVE |

### Key Insights
1. **ALL scores show positive correlation** (higher = better)
2. **ml_composite_score** has strongest correlation (biggest improvement Q1→Q4)
3. **elite_score** is also highly predictive
4. Current scores range 0-100, but picks with scores 60+ perform significantly better

### Answer
**Track % is NOT currently in the data**, but `elite_score` and `ml_composite_score` are your best predictors.

---

## Question #2: Does HTF Matching Direction Lead to Wins?

### Current State: UNKNOWN
- **46 picks (85%)** have `htf_confirmation` = missing/unknown
- **8 picks (15%)** have `htf_confirmation` = neutral
- **0 picks** have bullish/bearish HTF confirmation

### Analysis
Cannot determine correlation because HTF data is not being populated for active picks.

### Recommendation
1. **Fix HTF data pipeline** - ensure HTF trend is calculated for every pick
2. **Store HTF direction** in the pick data alongside direction
3. **Re-analyze** once you have 100+ picks with HTF data

---

## Question #3: Do "A-viable" Strategy Tags Perform Well?

### Strategy Tag Performance

| Filter | Count | Win Rate | Avg PnL |
|--------|-------|----------|---------|
| High consensus (≥80%) | 304 | 32.6% | -0.17% |
| Multi-agree (3+ strategies) | 818 | 25.8% | -0.15% |
| Elite A grade (≥70) | 1 | 0.0% | -0.01% |
| High confidence (≥0.75) | 29 | **48.3%** | -0.00% |
| High RR (≥3.0) | 14 | 0.0% | -0.04% |

### Key Insights
1. **High confidence (≥0.75)** shows the best win rate at 48.3%
2. High consensus helps but not dramatically (32.6% vs 27.4% baseline)
3. Having MORE strategies agree doesn't necessarily help (3+ strategies = 25.8% win rate)

### Answer
No "A-viable" tag was found in the data, but **high confidence picks (≥0.75)** perform best.

---

## Question #4: Does Multi-Agree Help?

### Analysis by Number of Agreeing Strategies

| # Strategies | Count | Win Rate | Total PnL |
|--------------|-------|----------|-----------|
| 0 strategies | 65 | **46.2%** | -2.02% |
| 2 strategies | 127 | 27.6% | -26.69% |
| 3 strategies | 452 | **14.6%** | -73.75% |
| 4 strategies | 190 | 37.4% | -32.76% |
| 5 strategies | 132 | **44.7%** | -10.19% |
| 6 strategies | 41 | 31.7% | -3.10% |

### Surprising Finding
**Multi-agree has a U-shaped relationship:**
- 0 strategies: 46.2% win rate (single strong signal)
- 3 strategies: 14.6% win rate (worst!)
- 5 strategies: 44.7% win rate (best for multi)

### Answer
**3-strategy consensus is the WORST performing.** Either have:
1. A single high-confidence strategy (0 other agreements)
2. OR 5+ strategies in agreement

Avoid the middle ground of 2-4 agreeing strategies.

---

## The "Golden Criteria" - What Winners Look Like

### Top-Performing Strategy Combinations

| Combination | Count | Win Rate | Avg PnL |
|-------------|-------|----------|---------|
| elite ≥ 60 AND confidence ≥ 0.7 | 52 | **36.5%** | -0.05% |
| elite ≥ 50 AND htf matches | 541 | 29.9% | -0.12% |
| consensus ≥ 0.9 AND elite ≥ 50 | 79 | 34.2% | -0.15% |

### Winner Characteristics (277 Winners Analyzed)

| Characteristic | In Winners | In Losers | Edge |
|----------------|------------|-----------|------|
| **Exit via TP (not SL)** | 70.4% | 0.0% | **+70.4%** |
| **RR ≥ 2.5** | 12.6% | 7.8% | +4.9% |
| **High consensus (≥80%)** | 35.7% | 27.9% | +7.8% |
| **Confidence ≥ 0.7** | 9.4% | 6.4% | +3.0% |
| **Elite score ≥ 60** | 7.6% | 4.6% | +2.9% |

### The Golden Criteria (Recommended Filters)

Based on this analysis, **winning picks should have:**

1. **REQUIRED:**
   - `confidence >= 0.75` (48.3% win rate)
   - `elite_score >= 60` (higher scores = better)
   - `risk_reward >= 2.5` (winners have higher RR)

2. **STRONG PREFERENCE:**
   - Either 0 strategies (single strong signal) OR 5+ strategies
   - Avoid 2-4 strategy consensus (worst performance)
   - Exit reason = TP (not SL or TIME_EXIT)

3. **NEED MORE DATA:**
   - HTF confirmation matching direction (currently 0% of picks have this)
   - Track record populated (currently 98% missing)

---

## Exit Analysis - Why Picks Are Losing

| Exit Reason | Count | Avg PnL | Total PnL |
|-------------|-------|---------|-----------|
| **SL (Stop Loss)** | 437 | -0.39% | **-171.93%** |
| **TIME_EXIT** | 326 | -0.07% | -21.84% |
| **TP (Take Profit)** | 163 | +0.29% | **+46.67%** |
| TP_HIT | 23 | +0.05% | +1.06% |

### Key Insight
**43% of picks hit SL** - this is the #1 drag on performance.

### Recommendation
1. **Tighten entry criteria** - require higher confidence before entering
2. **Adjust SL placement** - current SLs may be too tight
3. **Filter out low-confidence picks** - they hit SL more often

---

## Strategy Performance (Top 5)

| Strategy | Win Rate | Total PnL |
|----------|----------|-----------|
| **macd_crossover** | 90.0% | +0.27% |
| **clone_hl_copy_lb_None** | 100.0% | +0.03% |
| **forex_rsi2_mean_reversion** | 54.5% | +0.30% |
| **futures_momentum** | 60.0% | +0.24% |
| **quan_engine_swing** | 44.9% | +1.01% |

---

## Immediate Action Items

### Critical (Fix Today)
1. **Fix track_record population** - 98% of active picks are missing this
2. **Fix strong_signal flag** - all picks show false
3. **Fix HTF confirmation** - 85% missing this data

### High Priority (This Week)
1. **Implement confidence filter** - only enter picks with confidence ≥ 0.75
2. **Avoid 2-4 strategy consensus** - it's the worst-performing pattern
3. **Increase elite_score threshold** - require ≥ 60 for new picks

### Medium Priority (This Month)
1. **Add Track % metric** - calculate and store historical track record
2. **Implement HTF matching** - verify HTF direction aligns with pick direction
3. **A/B test golden criteria** - run experiment with stricter filters

---

## Summary: What We Need More Of

### Metadata Needed
1. ✅ Track % (historical win rate for this strategy/symbol)
2. ✅ HTF matching (bullish/bearish confirmation)
3. ✅ A-viable tags (if they exist in your system)
4. ✅ Strong signal calculation (currently all false)

### Data Quality Issues
1. Fix the "??" icons in dashboard (null handling)
2. Populate missing track_record fields
3. Calculate HTF confirmation for all picks
4. Fix strong_signal calculation

---

**End of Report**
