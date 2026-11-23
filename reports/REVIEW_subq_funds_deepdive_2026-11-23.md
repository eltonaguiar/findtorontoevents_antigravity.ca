# Review of subq's review — fund deep-dive (FXAIX/SPY, 60/40, cash)

**Date:** 2026-11-23 · **Reviewer:** buffy · **Subject:** subq's 12-point critique of the
"what should a human buy" fund analysis
**Method:** read both versions of `tools/fund_deep_dive.py` (v1 `5660b25`, v2 `5a3fdbab` in the
`vanilla-handsaw` worktree), recomputed every disputed number independently from
`market_prices.csv` (1,254 daily returns, 2021-11-16→2026-11-13), and checked the published doc
against the JSON the tool actually emitted at 10:26Z.
Paper only. Zero capital. Not investment advice.

## Verdict

**subq's review was substantially right about v1, is now mostly history, and contains one arithmetic
error that the correction copied.** Seven of its twelve points were fixed within ~90 minutes of it
being written; two are stale (the code exists, compiles, and reproduces its own numbers); one is
wrong in direction and has propagated into the fixed tool's docstring; one is still open. It also
missed the most consequential remaining bug.

## Point by point

| # | subq's point | Status | Evidence |
|---|---|---|---|
| 1 | Sharpe/Sortino never subtract the risk-free rate | **Right about v1, fixed in v2** | v1 line 41: `sharpe=(mu*ann-mer)/(sd*math.sqrt(ann))` — a fee-adjusted return/vol ratio. v2 uses daily excess over SGOV. Recomputed: FXAIX 0.506, SPY 0.498 — matches v2 to 3 dp. |
| 2 | SGOV's 15.886 Sharpe sits in an equity table | **Right, fixed** | v2 sets `use_rf=None` for `SGOV_adj` and prints `n/a`. |
| 3 | `portfolio(rebal=21)` never rebalances | **Right about v1, fixed** | v1 had `def portfolio(ret, weights, rebal=21, ...)` and ignored it; v2 has a real sleeve-drift reset. Recomputed 60/40: 6.85% monthly vs 6.98% daily → −0.14pp (doc says 0.13; rounding). |
| 4 | The FXAIX-vs-SPY fee explanation "doesn't add up"; fee gap **over**-predicts | **WRONG DIRECTION** | Net gap **+0.167 pp/yr** (FXAIX 11.657 net vs SPY 11.490 net), fee gap **0.0795 pp/yr**. The fee gap *under*-predicts by ~0.09 pp/yr: 5-yr cumulative gap +0.83pp vs fee 0.40pp. subq also compared a 5-year cumulative (0.40pp) to an annual gap (0.17pp) — a units mismatch. |
| 5 | No uncertainty on any number | **Right, fixed** | Block bootstrap 21d/2000 added; every equity CI spans ~0→25%, and the doc correctly stops ranking on it. |
| 6 | One window, one regime | **Right, fixed** | Split added: FXAIX − SPY = +0.18pp first 3y, +0.14pp last 2y. |
| 7 | No futures | **Right, scoped out** | Doc §5: "Out of scope: futures (needs contract/roll data)". |
| 8 | No tax drag (VTSAX vs VTI) | **Largely closed** | Decision table has a tax column: MFs "cap-gains distributions possible", ETFs "most tax-efficient". Terse, but the point is made. |
| 9 | Final verification command truncated | **Stale** | The tool runs end-to-end and wrote `reports/fund_deep_dive.json` at 10:26Z; the JSON matches the doc. |
| 10 | Code in the transcript is markdown-mangled | **Stale as diagnosed, valid in substance** | `py_compile` passes; the mangling was rendering. **But** the doc cites `tools/fund_deep_dive.py`, which lives in the `vanilla-handsaw` worktree — a reader of the review repo cannot find it. Fix the citation, not the code. |
| 11 | Bonds judged only by trailing return | **Open, acknowledged** | Doc says "BND judged by trailing only (forward YTM is the right forward input — not available here)". Acceptable scope call, but the −0.648 Sharpe row still reads as a verdict on bonds. |
| 12 | No costs, spreads, minimums | **Right, fixed** | Decision table has minimums ($0 / $3,000 / 1 share) and a fractional-shares note. |

## What subq missed

**1. The Sortino convention understates the ratio by ~30%.** v2 computes downside deviation as
`sqrt(sum(x² for x<0) / len(negatives))` — dividing by the count of negative days rather than by n.
Recomputed both ways on the same excess series:

| fund | excess Sharpe | Sortino (tool, ÷n_neg) | Sortino (standard, ÷n) | share of negative days |
|---|---:|---:|---:|---:|
| FXAIX | 0.506 | **0.501** | **0.722** | 48.2% |
| SPY | 0.498 | **0.491** | **0.714** | 47.3% |
| BND | −0.648 | **−0.634** | **−0.889** | 50.9% |

The published 0.501 is not "Sortino ≈ Sharpe because the distribution is symmetric" — it is the
wrong denominator. With the standard convention Sortino is ~1.43× Sharpe, which is the expected
relationship. The fix is one expression, and it is the only published number that changes materially
without changing any conclusion.

**2. "True monthly rebalancing" is every 21 trading days, not month start.** The docstring says
"reset at month start"; the code does `if (i+1)%21==0`. Over 1,254 days that is 59 rebalances against
~60 calendar months — close enough that the CAGR effect is negligible, but the label overstates the
method. Rename to "21-trading-day rebalance" or key the reset to the date column.

**3. The tool's own docstring repeats subq's arithmetic error.** Line 11 says "fee gap
*over*-predicts; magnitude within noise", while the doc body correctly says the observed magnitude
**exceeds** the fee gap. 0.0795 < 0.167, so the docstring is wrong and self-contradicting. It is the
first thing a reader of the tool sees.

**4. The CAGR CI is a sampling interval presented next to forecast language.** [0.1, 25.4] is the
dispersion of a 5-year CAGR under block resampling of *this* path — not a forward range. The doc's
"read the CIs first" framing is right; one clause saying "sampling interval, not a forecast" would
prevent the obvious misreading.

## Bottom line

The corrected analysis is sound *as a buying-cost analysis*: same-index comparison, net-of-MER
reporting, CIs that honestly kill the fund ranking, and 60/40 drawdown control. Three edits remain,
all small:

1. Divide downside deviation by `n`, not by the count of negative days (changes Sortino 0.501 → 0.722).
2. Fix the tool docstring's "over-predicts" → "under-predicts" and cite the tool's real path.
3. Relabel "monthly" as 21-trading-day rebalancing, or key it to the date column.

None of them changes the recommendation, which is the point: the recommendation rests on expense
ratios and tax treatment, and those are deterministic.
