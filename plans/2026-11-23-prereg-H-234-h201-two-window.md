# PRE-REGISTRATION — H-234: which half does H-201's +7.246 bp/day come from?

**Filed:** 2026-11-23, before the run. **Rule:** M-107. **Status at filing:** REGISTERED.

## Why

H-201 (`xsmom_top3_6m`, EQUITY) is the only cell of 29 declared that clears every gate, with
CI-LB **+7.246 bp/day** over **3,744 days**, and it is `NOT_PROVEN` on arithmetic margins only
(C-019: DSR holds to N=28 of 29; needs 76.7 more trading days). H-233 showed the same treatment
applied to the vol-target claim flipped sign between sub-periods, so before anyone spends 77
forward days waiting for H-201, it is worth knowing whether its edge is present in both halves of
its own history or concentrated in one.

## The construction (copied from the artifact, not retuned)

From `tools/per_class_edge_harness.py`:
- Universe: `AAPL MSFT NVDA AMZN GOOGL META JPM XOM UNH JNJ` (the EQUITY list).
- `xsmom(closes, lookback=126, top_k=3, cost_bps=10, rebal_days=21)` — 6-month momentum, monthly
  rebalance, top 3 equal-weighted, 10 bp per unit turnover.
- Benchmark leg: SPY (`BENCH_SYMBOL["EQUITY"]`).
- Sample: `START=2012-01-01` to the last available bar.
- **No parameter is changed.** This is the artifact's own cell.

## Split (fixed now)

Temporal midpoint of the available sample, because it is the least discretionary choice:
- Window A: 2012-01-01 .. 2019-06-30
- Window B: 2019-07-01 .. last bar

## Test statistic

Mean net daily return in **bp**, with the harness's own block bootstrap (block 5, 2,000 resamples,
5% lower quantile), plus mean excess versus SPY and its CI. Reported per window and full-sample.

## Acceptance

H-201 is `ROBUST` iff in BOTH windows: mean net > 0, CI lower bound > 0, and excess vs SPY > 0.
`HALF_DEPENDENT` if exactly one window satisfies all three. `FRAGILE` if neither does.
Full-sample reproduction of +7.246 bp/day is a validation check, not an acceptance criterion.

## Kill rule

If the verdict is `FRAGILE` or `HALF_DEPENDENT`, the claim that H-201 is "the one candidate worth
77 forward days" is downgraded to "period-specific until replicated forward", and that downgrade is
published. No re-splitting, no alternative lookback, no benchmark swap.

## Family note

One additional trial on an existing claim, not a new family. N declared becomes 30; the DSR bar
moves and that is disclosed rather than hidden.
