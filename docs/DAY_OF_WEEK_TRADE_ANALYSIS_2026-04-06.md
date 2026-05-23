# Day-of-Week Trade Analysis

Date: 2026-04-06

## Scope

Primary local dataset:

- `audit_dashboard/data/dashboard_data.json`
- field used: `picks.recent_closed`
- sample size: 3,500 closed picks
- crypto subset: 2,855 closed picks

Research context:

- Kenneth R. French, "Stock returns and the weekend effect", *Journal of Financial Economics* (1980), DOI: `10.1016/0304-405X(80)90021-5`
- Donglian Ma and Yutaka Kurihara, "The day-of-the-week effect on Bitcoin return and volatility", *Research in International Business and Finance* (2019)
- Nobuyoshi Yamori and Yutaka Kurihara, "The day-of-the-week effect in foreign exchange markets: multi-currency evidence", *Research in International Business and Finance* (2004), DOI: `10.1016/j.ribaf.2004.02.004`

## Scientific Caveat

This is an observational production-book study, not a randomized experiment.

Useful but limited:

- weekday buckets are not independent across strategies
- regime mix changes over time
- some weekday effects can be caused by one or two systems dominating volume
- large t-stats here indicate strong differences in this sample, not universal market laws

This is consistent with the literature: calendar effects are often real in-sample, but unstable across decades, asset classes, and market structures.

## What the literature says

### Stocks

French (1980) found a classic US stock-market weekend effect:

- Monday returns were significantly negative
- the effect persisted through multiple subperiods from 1953 to 1977

### Bitcoin / crypto

Ma and Kurihara (2019) found:

- a day-of-week effect in Bitcoin returns that varied by sample period
- higher volatility on Monday and Thursday
- Monday strength in Bitcoin was tied to higher volatility

### FX

Yamori and Kurihara (2004) found:

- some day-of-week effects existed in some currencies in the 1980s
- the anomaly mostly disappeared in the 1990s

Bottom line from research:

- weekday effects can exist
- they are not stable enough to treat as permanent laws
- they weaken or rotate over time
- asset class matters a lot

## Local Results

### Overall closed picks by weekday

| Day | N | WR | Avg PnL | PF |
|-----|---:|---:|--------:|---:|
| Monday | 501 | 52.9% | +0.809% | 2.37 |
| Tuesday | 192 | 53.6% | +0.652% | 1.87 |
| Wednesday | 422 | 46.9% | +0.249% | 1.38 |
| Thursday | 452 | 27.7% | -1.092% | 0.39 |
| Friday | 505 | 52.9% | +0.235% | 1.31 |
| Saturday | 549 | 54.6% | +0.276% | 1.71 |
| Sunday | 577 | 41.3% | +0.043% | 1.08 |

### Crypto-only closed picks by weekday

| Day | N | WR | Avg PnL | PF |
|-----|---:|---:|--------:|---:|
| Monday | 431 | 53.4% | +0.849% | 2.55 |
| Tuesday | 164 | 53.1% | +0.646% | 2.01 |
| Wednesday | 368 | 48.4% | +0.235% | 1.35 |
| Thursday | 369 | 27.1% | -1.131% | 0.37 |
| Friday | 399 | 62.7% | +0.772% | 3.16 |
| Saturday | 541 | 55.1% | +0.265% | 1.69 |
| Sunday | 573 | 41.2% | +0.033% | 1.06 |

## Significance Checks

Simple Welch-style comparisons on `pnl_pct`:

### All assets

- Thursday vs non-Thursday: difference `-1.431%`, t-stat `-10.20`
- Monday vs non-Monday: difference `+0.797%`, t-stat `+5.94`
- Thursday vs Friday WR: difference `-25.2 pts`, t-stat `-8.23`
- Sunday vs Friday WR: difference `-11.6 pts`, t-stat `-3.84`

### Crypto

- Thursday vs non-Thursday: difference `-1.546%`, t-stat `-10.11`
- Friday vs non-Friday: difference `+0.648%`, t-stat `+5.42`
- Monday vs non-Monday: difference `+0.748%`, t-stat `+5.55`
- Sunday vs non-Sunday: difference `-0.228%`, t-stat `-2.82`
- Thursday vs Friday WR: difference `-35.6 pts`, t-stat `-10.60`
- Sunday vs Friday WR: difference `-21.5 pts`, t-stat `-6.75`

Interpretation:

- Thursday weakness is not subtle in this sample
- Friday strength in crypto is also real in this sample
- Sunday is weaker than Friday in crypto, but not nearly as toxic as Thursday

## Important Caution: Thursday weakness is partly system-specific

The Thursday drawdown is not a pure market weekday law. It is heavily amplified by certain systems.

Largest crypto Thursday contributors:

- `claude_gainer_st`: 117 trades, 9.4% WR, avg `-3.15%`
- `alpha_engine`: 67 trades, 29.9% WR, avg `+0.03%`
- `rapid_fire`: 38 trades, 29.0% WR, avg `-0.61%`
- `baby_strats_forward`: 37 trades, 43.2% WR, avg `-0.19%`
- `luxalgo_filters`: 35 trades, 40.0% WR, avg `+0.00%`

So the local Thursday effect is a mix of:

- genuine weekday pattern
- system mix / deployment pattern
- strategy-specific overexposure on that day

## Lessons Learned

### 1. Do not add a blunt global "Thursday penalty" without context

Reason:

- Thursday weakness is real, but it is not evenly distributed
- a large part of the damage is concentrated in a few systems

### 2. Crypto Friday deserves a positive bias

Reason:

- crypto Friday is the best large-sample day in the closed book: 62.7% WR, PF 3.16

### 3. Monday is better than the old stock-market literature would suggest

Reason:

- our book is crypto-heavy, not S&P 1953-1977
- Monday is positive in both overall and crypto samples here
- that lines up more with the modern Bitcoin literature than with old US equity findings

### 4. Sunday is mediocre, not catastrophic

Reason:

- Sunday crypto is clearly weaker than Friday
- but it is still roughly breakeven/slightly positive on average, not an automatic reject

## Recommendations

### A. Use weekday adjustments at the system level, not globally

Recommended approach:

- compute each system's weekday profile from closed picks
- only apply a weekday penalty when:
  - system has enough sample on that day
  - the day is meaningfully worse than the system's own baseline

Example:

- penalize `claude_gainer_st` on Thursday
- do not penalize every crypto system equally on Thursday

### B. Add a mild crypto Friday bonus

Suggested first pass:

- small positive score adjustment on Friday for crypto
- only when trust and score are already above minimum thresholds

Reason:

- avoid boosting garbage Friday picks
- reward already-credible Friday setups

### C. Replace the old Sunday heuristic with measured day-aware logic

Reason:

- a blanket Sunday penalty is too crude
- the real local outlier is Thursday, not Sunday

### D. Add a minimum sample guard before any weekday rule fires

Suggested rule:

- no weekday multiplier unless system has at least 20-30 closed picks on that weekday

Reason:

- avoid overfitting noise

### E. Recompute weekday effects monthly

Reason:

- literature says these anomalies drift or disappear
- our own book likely changes as the strategy mix changes

## Suggested Implementation Sequence

1. Build per-system weekday stats from closed picks.
2. Penalize only systems with strongly negative Thursday history.
3. Add a mild Friday boost for qualified crypto picks.
4. Remove or reduce any blanket Sunday penalty if it still exists.
5. Revalidate after one month of new closed picks.

## Bottom Line

Our production book does show a day-of-week pattern, but it is not the classic stock-market Monday effect.

The local pattern is:

- strong Monday
- strong Friday crypto
- weak Sunday
- very bad Thursday

The most important lesson is not "weekday anomalies are universal." It is:

- weekday effects in our book are real enough to use
- but they should be applied as system-specific, sample-aware adjustments
- not as blunt market folklore rules
