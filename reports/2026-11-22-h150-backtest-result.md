# H-150 backtest — NOT_PROVEN, and the reason is size beta, not quality

**Date:** 2026-11-22 · run under the frozen `data_sample_lock` · artifact
`reports/h150_gpa_backtest_2026-11-22.json` · module `tools/h150_gpa_backtest.py`

## Headline

Quarterly TTM gross profitability, traded exactly as the H-150 spec was registered —
top quintile, next-open entry, first month-end 20–60 calendar days later — produces
**no cross-sectional edge** in the $2B–$10B SEC-filer universe from 2016 to 2025.

| Gate (pre-registered) | Result | Pass |
|---|---|---|
| harness admissible and positive | `UNTESTED` — 0 windows reach the 80-record floor | ✗ |
| ≥ 100 forward book records | 817 | ✓ |
| net IR vs FF4 ≥ 0.5 | **−0.00** | ✗ |
| FF4 alpha t ≥ 2.0 | **−1.41** (alpha −0.6903 %/mo) | ✗ |
| cost survival ≥ 0.60 | 0.783 | ✓ |

Verdict: **NOT_PROVEN**. Three of five gates fail, and the two that pass are the two that do
not measure an edge (sample size, and the fact that gross returns exceed costs).

## What was actually run

| Stage | Number |
|---|---|
| CIKs attempted (seed 149, frozen sample) | 2,600 |
| names with quarterly GP + Assets + shares | 636 |
| names with both open and close history | 584 |
| in-band records (cap $2B–$10B, GP/A available) | 4,753 |
| formations (month-end, 2016-01…2025-12) | 119 |
| book records (top quintile) | 817 over 94 formations |
| delisted exits inside the holding window | 0 |

~40 records per formation. That number matters for the harness and is the first honest
finding of the run (see below).

## Finding 1 — the harness cannot score this, and that is a data fact, not a pass

`edge_stability_harness` needs ≥80 records per window *and* ≥15 winners and ≥15 losers inside
it. At ~40 records per month, a 14-day window holds ~18 records: 0 windows qualify, so the
harness returns `UNTESTED` rather than a verdict. H-149 could be scored because the annual-10-K
signal put ~87 names per formation in band; requiring quarterly facts and shares cuts the
universe to 584 names, which halves the density.

Reporting `UNTESTED` as though it were `ADMISSIBLE` would be the exact substitution this repo
keeps punishing. It is reported as untestable at the frozen window.

## Finding 2 — the book is not better than the universe, and the bottom quintile is better

| | net mean per 20–60 day hold |
|---|---|
| top quintile (the book) | **+0.7318 %**, WR 52.14 % |
| whole in-band universe | +0.7217 % |
| bottom quintile | **+1.1894 %** |
| long/short (top − bottom) | **−0.4576 %** |

The book beats the universe by 0.010 pp before any cost of running a 17-name portfolio, and
the *worst* GP/A names did better than the best. The monotonic ordering the quality story
predicts is absent: this is flat-to-inverted, which is what a noise signal looks like.

## Finding 3 — what the book actually holds is small-cap beta

Fama-French 4-factor fit on the net book return, factor month = the month held:

| | overlapping (n=94) | every-2nd formation (n=47) |
|---|---|---|
| alpha | **−0.6903 %/mo**, t = **−1.41** | +0.3372 %/mo, t = 0.49 |
| R² | 0.721 | — |
| MKT | **1.280** | — |
| SMB | **1.004** | — |
| HML | −0.470 | — |
| RMW | 0.147 | — |

A market beta of 1.28 and an SMB loading of **1.00**: the "quality" book is a levered
small-cap position. R² of 0.72 says most of its return is those four factors, and the
intercept is not distinguishable from zero in either specification. The one positive
every-2nd-formation alpha (t=0.49) is not evidence — it is the half-sample that happened to be
positive.

Cost survival 0.783 and the 2× cost stress (net +0.5217 % at 40 bp) both say the *trading* is
viable; there is simply no alpha to trade.

## What this does and does not establish

**Establishes:** in this universe and this rendering, the signal does not rank future 20–60 day
returns, and its top quintile is compensation for size and market exposure. H-150 therefore does
not advance to forward testing — there is nothing to paper-trade, and `/audit3`'s promotion gate
should not be fed rows from a strategy that failed its own backtest.

**Does not establish:** that gross profitability has no premium anywhere. The universe is 584
names with quarterly XBRL GrossProfit (firms that tag it), pricing is survivor-biased (48
never-priceable names in H-149; 0 delisted exits here), and the cap band excludes the large caps
where Novy-Marx's original result is strongest. This is a narrow, honest test of one rendering.

## Combined with H-149

Both renderings of gross profitability are now closed on evidence, not on opinion:
H-149 (annual, 40 trading days, close entry) → REJECTED, 4 strong + vs 11 strong −, alpha t=0.04.
H-150 (quarterly, next open, 20–60 calendar days) → NOT_PROVEN, alpha t=−1.41, L/S negative.

The shared failure mode is the same in both: the top quintile is a small-cap/market-beta book,
and the ranking carries no incremental information.

## Sensitivity: the harness at a coarser window (post-hoc, disclosed)

The 14-day window is untestable at this density, so one extra run was made at
`--window-days 60` (`reports/h150_gpa_backtest_2026-11-22_w60.json`). This window was chosen
**after** seeing the 14-day floor fail, so it is a sensitivity check, not the pre-registered
test.

| window | windows scored | strong | signs | verdict |
|---|---|---|---|---|
| 14 days (registered) | 0 | 0 | — | `UNTESTED` |
| 60 days (sensitivity) | 38 | 2 | **0 positive / 2 negative** | `REJECTED` |

At 60 days the harness can score and finds no admissible positive: the only two strong windows
are negative, which is not enough (needs ≥3 same-sign) to reject on the harness alone, but it
points the same way as the book (L/S −0.46 pp) and the factor fit (alpha t = −1.41). All three
independent views agree, and none of them supports the quality story.
