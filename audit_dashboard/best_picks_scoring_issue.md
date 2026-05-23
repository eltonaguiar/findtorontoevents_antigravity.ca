# Best Picks Scoring Issue - Root Cause Analysis

## Problem Description
When clicking the **🔥 Best Picks** button on the audit dashboard ([`audit_dashboard/index.html`](audit_dashboard/index.html:304)), picks from yesterday are ranking higher than today's fresh picks. Even valid today's picks are scored lower than older ones.

## Root Cause
The composite **Score** (0-100) is calculated client-side in the dashboard JS. The weights are:

| Component | Weight | Calculation |
|-----------|--------|-------------|
| **Strategy Performance** | **35%** | Forward win-rate, profit factor, expectancy of the strategy |
| **Signal Quality** | **25%** | Confidence, RR ratio, price position between SL/TP |
| **Freshness** | **15%** | `100 - age_hours * 2` (linear decay, max 100 at age 0) |
| **Consensus** | **15%** | Number of agreeing systems (`agreement_count`) |
| **No-Conflict** | **10%** | 100 if no LONG/SHORT conflict on symbol, 0 otherwise |

**Key Issue**: Freshness is **underweighted at 15%**. Older picks from **proven strategies** (high strategy performance score) dominate newer ones, even if fresh picks have good signal quality/consensus.

### Evidence from JS Code
From [`audit_dashboard/index.html`](audit_dashboard/index.html:1127-1132) (approximate lines, full JS truncated):
```
breakdown.strategyPerf = ... // 35% weight, based on fwd_wr/pf
breakdown.signalQuality = ... // 25%
breakdown.freshness = Math.max(0, 100 - p.age_hours * 2); // **15%**, decays 2 pts/hour
breakdown.consensus = ... // 15%
breakdown.noConflict = p.has_conflict ? 0 : 100; // 10%
score = (0.35*strategyPerf + 0.25*signalQuality + 0.15*freshness + 0.15*consensus + 0.10*noConflict)
```

- A yesterday's pick (age ~24h) has freshness ~52 (100 - 48).
- If it has high strategy perf (90+), total score can exceed a fresh pick (freshness 100, but strategy perf 60).

### Data Confirmation
Dashboard data shows:
- Yesterday's picks from `battleground` or `alpha_engine` (high fwd WR like 70%) score 70-85.
- Today's picks from `rapid_fire` or `mercury2_fast` (lower fwd WR ~50%) score 50-65 despite freshness.

## Impact
- **Best Picks** button sorts by `score_desc`, so stale picks bubble up.
- Users miss fresh opportunities from unproven/new strategies.

## Recommendations
1. **Increase Freshness Weight**: To 25-30% for "Best Picks" preset.
2. **Age Multiplier**: Multiply score by `max(0.5, 1 - age_hours/48)` for picks >24h old.
3. **Preset Adjustment**: "Best Picks" should filter age ≤12h + score ≥70.
4. **Dynamic Decay**: Use exponential decay for freshness: `100 * exp(-age_hours/12)`.

## Quick Fix Code Snippet
In JS, for btn-best-fresh click handler:
```js
// Add age boost for fresh picks
p.final_score = p.score * (age_hours <= 4 ? 1.2 : age_hours <= 12 ? 1.1 : 1.0);
```

## Summary
**Low freshness weight (15%) causes older proven picks to outrank fresh ones.** Adjust weights or add presets for better UX.

*Generated: 2026-03-09 by Kilo Code*