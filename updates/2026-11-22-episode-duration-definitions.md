# Funding-carry median episode duration: 0.67 d vs 1.93–2.33 d are DIFFERENT DEFINITIONS, not a conflict

**Date:** 2026-11-22 · **Programme:** 12-asset-class profitability research, funding-carry row
**Purpose:** record a numerical discrepancy between documents rather than silently overwriting the older figure.

## The two numbers

| Figure | Where it came from | What it measures |
|---|---|---|
| **1.93–2.33 d** (per-symbol 1.3–2.3 d) | Earlier analysis in [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](../docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:97) (1.93 d), [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](../docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:35) (2.33 d), and [`06_FUNDING_CARRY_2026-11-22.md`](../docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:216-222) (per-symbol 2.3 / 2.0 / 1.3 / 2.3 / 1.7 d). The spread across the three was already flagged in [`19_HONEST_VERDICT_2026-11-22.md`](../docs/edge_research/19_HONEST_VERDICT_2026-11-22.md:150-157) §8.2. | The carry backtest's `positive_trailing_episodes` block — a *trailing-positive* episode notion, essentially the mask in rule B below. |
| **0.67 d** (headline) | [`updates/2026-11-22-funding-carry-opportunity-frequency.md`](2026-11-22-funding-carry-opportunity-frequency.md) §1.1, artifact [`reports/funding_carry_opportunity_frequency_20261122.json`](../reports/funding_carry_opportunity_frequency_20261122.json), tool [`tools/funding_carry_opportunity_frequency.py`](../tools/funding_carry_opportunity_frequency.py). Rule A was pre-declared before any duration was computed. | **Rule A:** maximal contiguous run of settled 8h intervals where funding is *strictly positive at every interval* (`f > 0`) and records are contiguous. Duration = `(index_end − index_start + 1)/3` days. |

## Why rule B reproduces the old figure

Rule B (also pre-declared, in the same §0.3) is the carry backtest's own entry condition: hold while
the **trailing 24h funding sum** over 3 settled intervals is `> 0`. Under rule B the aggregate
median is **2.000 d** ([`updates/2026-11-22-funding-carry-opportunity-frequency.md`](2026-11-22-funding-carry-opportunity-frequency.md:143)) —
which lands inside the old 1.93–2.33 d range. The old figure is therefore **reproducible under a
different, also-reasonable definition**. Rule A is stricter: it ends an episode at the first
interval with non-positive funding, so it produces many short episodes (median 0.667 d, p75 2.000 d);
rule B stays in the trade through brief negative intervals as long as the 24h sum is positive, so it
produces fewer, longer episodes (n 1,253 vs 2,838).

So: not in conflict, but differently defined. The difference is the episode-termination rule.

## The verdict-relevant conclusion is robust across all three definitions

| Rule | Definition | n | median | ≥16.398 d (cost amortised) |
|---|---|---|---|---|
| A | contiguous `f > 0` | 2,838 | 0.667 d | **2.89%** |
| B | trailing-24h sum > 0 | 1,253 | 2.000 d | **9.18%** |
| C | `f > 1 bp` per 8h | 975 | 0.667 d | **1.03%** |

The fraction of episodes that can amortise the measured 45.524 bp round trip **never exceeds
9.18%** under any of the three definitions, and the median episode is 0.7–2.0 d against a 16.398 d
break-even in every case. The NOT_INVESTABLE verdict for lack of tradeable opportunity holds under
all three.

## What a future reader should do

Quote the median **with its rule name**. Do not replace 1.93–2.33 d with 0.67 d, or vice versa:
they are answers to slightly different questions about the same data. The old figures in docs 6,
15, 18, 19 and 22 are left as written and are not wrong under their own definition.
