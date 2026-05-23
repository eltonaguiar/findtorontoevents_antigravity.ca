# Closed Picks Scoring Tweaks

Date: 2026-04-06

## Dataset Used

Primary source: `audit_dashboard/data/dashboard_data.json`

- `picks.recent_closed`: 3,500 closed picks
- Crypto subset: 2,855 closed picks

Why this dataset:

- it carries `score`, `elite_score`, `confidence`, `trust_score`, `rr_ratio`, `has_conflict`, and `asset_class`
- it is the right place to judge whether the live scoring layer is actually ranking winners better than losers

## Core Findings

### Overall closed-pick baseline

- All assets: 44.6% WR, average PnL `-0.061%`, PF `0.938`
- Crypto only: 47.0% WR, average PnL `+0.075%`, PF `1.096`

Crypto is the only major bucket with a usable aggregate edge right now.

### Score is predictive, but not linearly

Crypto score bands:

- `0-29`: 37.3% WR, PF `0.50`
- `30-39`: 46.8% WR, PF `1.13`
- `40-49`: 40.0% WR, PF `0.69`
- `50-59`: 51.4% WR, PF `1.34`
- `60-69`: 63.6% WR, PF `4.78`
- `70+`: 63.5% WR, PF `2.80`

Takeaway:

- `60-69` is the best live crypto band in this sample.
- `70+` is still good, but it is not better than `60-69`.
- `40-49` is a dead zone and underperforms even `30-39`.

### Confidence is useful only up to a point

Crypto confidence bands:

- `<0.55`: 39.6% WR, PF `0.87`
- `0.55-0.69`: 43.8% WR, PF `1.21`
- `0.70-0.79`: 57.7% WR, PF `1.49`
- `0.80-0.89`: 76.5% WR, PF `9.13` on small sample
- `0.90+`: 26.7% WR, PF `0.20`

Takeaway:

- high-but-not-max confidence works
- extreme confidence is a red flag, not a green flag
- the current system is still letting too many `0.90+` picks look elite

### Trust is the cleanest filter in the file

Crypto trust bands:

- `0-2.9`: 38.9% WR, PF `0.69`
- `3-4.9`: 43.9% WR, PF `1.30`
- `5-6.9`: 71.7% WR, PF `3.02`
- `7+`: 83.3% WR, PF `13.47` on tiny sample

Takeaway:

- `trust_score >= 5` is a real regime change
- trust is doing more useful ranking work than raw confidence

### Direction conflict is not the villain

Crypto closed picks:

- `has_conflict = false`: 46.6% WR, PF `1.08`
- `has_conflict = true`: 47.8% WR, PF `1.14`

Takeaway:

- the blanket direction-conflict penalty is too aggressive
- conflict is not inherently bad in crypto; it often reflects active two-sided opportunity or multi-system disagreement that still resolves profitably

### Strong picks deserve more weight

All assets:

- `strong = false`: 43.9% WR, PF `0.89`
- `strong = true`: 49.4% WR, PF `1.78`

Takeaway:

- the strong flag is a real positive feature and should matter more in final score

### R:R floor matters

All assets:

- `RR < 1.0`: 29.1% WR, PF `0.25`
- `RR 1.0-1.24`: 43.8% WR, PF `1.01`
- `RR 1.25-1.49`: 48.8% WR, PF `1.07`
- `RR 1.5-1.99`: 41.2% WR, PF `0.86`
- `RR 2.0+`: 48.2% WR, PF `1.27`

Takeaway:

- sub-1.0 R:R should be hit much harder
- the old intuition that `1.5-2.0` is always ideal does not hold uniformly in the live closed book
- `2.0+` is better than `1.5-1.99` here because many of those picks also come from cleaner crypto setups

### Asset-class lesson

Closed-pick PF by asset:

- Crypto: `1.096`
- Equity: `0.667`
- Forex: `0.515`
- Commodity: `0.489`
- ETF: `0.338`

Takeaway:

- the current scoring stack should stay crypto-first
- non-crypto should face materially tougher gates until their closed-book quality improves

## Recommended Scoring Tweaks

### 1. Keep crypto Smart Picks floor at 60

Do not raise crypto back to `70`.

Reason:

- `60-69` is currently the best closed-pick band
- raising to `70` would throw away the strongest PF cohort

### 2. Increase trust weight and hard-gate low trust

Recommendations:

- add a hard penalty when `trust_score < 3`
- add a meaningful bonus when `trust_score >= 5`
- consider `trust_score >= 5` as a Smart Picks requirement for crypto
- consider `trust_score >= 6` for paper-trading-ready crypto picks

Reason:

- trust is the strongest clean separator in the closed book

### 3. Replace blanket extreme-confidence handling with a targeted trap rule

Recommendations:

- penalize `confidence >= 0.90` unless trust is high and the system is proven
- preferred safe zone: `0.70-0.89`
- treat `0.90+` as suspicious by default, not premium

Reason:

- `0.90+` crypto picks were terrible in the closed set

### 4. Reduce the direction-conflict penalty in crypto

Recommendations:

- remove or halve the penalty for crypto
- keep a stronger penalty only for non-crypto or for same-system self-hedging spam

Reason:

- conflicted crypto picks slightly outperformed non-conflicted ones

### 5. Boost `strong` picks more

Recommendations:

- add a larger score bonus for `strong = true`
- if `strong` and `trust >= 5`, let that combo push a pick into the top tier faster

Reason:

- strong picks had far better PF than non-strong picks

### 6. Penalize the `40-49` score band until recalibrated

Recommendations:

- audit which components most commonly land picks in `40-49`
- apply a slight dead-zone penalty or require stronger trust to escape that band

Reason:

- the `40-49` cohort is one of the worst crypto bands and likely contains score inflation from bad components

### 7. Make asset-specific floors stricter outside crypto

Recommendations:

- equities: raise effective floor and trust requirement further
- forex: stay very restrictive
- commodities and ETFs: keep in probation unless backed by stronger closed-book evidence

Reason:

- non-crypto PF is not competitive with crypto

## Suggested Priority Order

1. Trust up, low-trust down
2. Keep crypto floor at `60`
3. Penalize `0.90+` confidence unless proven/trusted
4. Remove most crypto direction-conflict penalty
5. Reward `strong` picks more
6. Audit the `40-49` dead zone

## Operational Recommendation

Before changing more weights, run a simple before/after replay on `picks.recent_closed` with these four rule changes only:

- `trust_score >= 5` bonus
- `confidence >= 0.90` penalty unless trust high
- reduced crypto conflict penalty
- unchanged crypto floor at `60`

This is the smallest high-signal experiment and should tell us quickly whether the live book improves without a full scorer rewrite.
