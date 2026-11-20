# H-147 — Is the resolved book's edge selection, or beta?

Date: 2026-11-20
Author: freebuff (deepseek-v4-flash)
Tool: `tools/h147_beta_hedge_picks.py` · Output: `reports/h147_beta_hedge_2026-11-20.json`
Benchmark: SPY · Sample: `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed`

## Question

Every promotion argument in this program rests on realised pick returns. If those
returns are mostly directional exposure to the market, then the "edge" is a long
position with extra steps, and hedging it away should leave nothing.

## Method

For each resolved pick that carries both an entry timestamp and a close:

1. β from daily returns over the last 60 **shared** calendar dates before entry
   (symbol vs SPY, intersected — crypto trades 7 days a week, SPY 5).
2. Benchmark return over the trade's own window, entry bar → exit bar.
3. Hedged return = `pnl − β · r_SPY`.

## Coverage (the binding limit)

| bucket | n |
|---|---|
| Resolved picks with entry **and** exit timestamps | 1,909 / 3,500 (54.5%) |
| Hedgeable at daily resolution | **331 (17.3% of timestamped, 9.5% of book)** |
| Entry and exit on the same daily bar | 626 |
| No usable price bar for the symbol | 796 |
| Fewer than 30 shared returns for β | 16 |

So this answers the question for ~9.5% of the book, not the book.

## Result (robust estimator)

| | unhedged | hedged |
|---|---|---|
| mean per trade | +0.5088% | **+0.5358%** |
| trimmed mean (10%) | +0.3498% | +0.3498% |
| median | −0.5000% | −0.4769% |
| 95% bootstrap CI of mean | [+0.086%, +0.946%] | [+0.100%, +0.991%] |
| hit rate | 47.7% | 48.3% |
| t-stat | 2.40 | 2.44 |

Mean β = 1.09, 90.9% of betas positive. Decomposition: mean benchmark return over
these windows −0.012%, mean `β·r_SPY` −0.027%. The windows were essentially flat,
so there was little exposure to remove.

**Verdict: H-147's strong form is refuted on this subsample — the edge is not beta.**
Hedging changes the mean by +0.027 percentage points, i.e. it moves the wrong way
and is statistically indistinguishable from zero. CRYPTO alone (n=308):
+0.5136% unhedged → +0.5802% hedged.

## Why this is a weaker result than it looks

1. **The mean is tail-driven.** Median is **negative** in both columns and the hit
   rate is below 50%. The positive mean comes from a right tail, not from
   consistent wins — the same shape that made the headline win rate misleading.
2. **I chose the estimator after seeing it fail.** The first run used raw betas and
   returned a hedged mean of **−5.12%** with a mean β of **−64.5** — a handful of
   outlier crypto symbols dominating the covariance. Winsorising daily returns at
   ±20% and clipping β to [−3, 3] flipped the sign of the result. That contrast is
   the real finding: **per-trade β on this book is not reliably estimable**, and
   the robust version is sensitivity-selected, not pre-registered. Neither number
   should be read as a settled estimate.
3. **Flat windows.** `β·r_SPY` averaged −0.03%, so this sample barely tests the
   beta hypothesis. A book of mostly short crypto holds happened to avoid the
   benchmark. The test has power only for the periods it covers.

## Consequence for the program

- Do **not** cite this as proof of selection alpha. Cite it as: *on the 9.5% of the
  book that is hedgeable, the mean is not explained by beta; the sample is too
  small, too tail-driven, and too flat in the benchmark to promote anything.*
- The actionable defect it exposes is **data**, not statistics: 54.5% of resolved
  picks lack an entry timestamp and 42% of those lack a price bar. No hedge,
  regime, or path-dependent analysis can cover the book until entry timestamps and
  entry prices are populated for every pick at write time.
- Follow-up that would actually decide H-147: aggregate **portfolio-level** daily
  returns (equal-weight, one unit per open pick) and regress the *series* on SPY.
  Portfolio β is estimable even when per-trade β is not, and it uses same-day and
  missing-bar picks.

## Reproduction

```
python3 tools/h147_beta_hedge_picks.py --out reports/h147_beta_hedge_2026-11-20.json
```
