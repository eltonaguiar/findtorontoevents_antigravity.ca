# ___GROUNDBREAKING — register — buffy — 2026-11-22T10:00Z

**Status: NO BREAKTHROUGH CLAIMED.** No asset class, strategy cell or pod has
passed every gate. This file exists so that a breakthrough has a place to be
recorded, and so that "nothing yet" is itself on the record rather than implied
by silence.

The rule for adding an entry here: a genuine breakthrough needs forward rows and
a gate pass (2x cost CI-LB > 0, benchmark-relative IR, split-half stable), not a
lab result. Nothing in this repository meets that bar today.

## Notable findings, not breakthroughs

These are worth a peer's time; none of them is an investable edge.

1. **"Volatility scaling is free alpha (+0.3 Sharpe)" is false on our own data.**
   Same TSMOM signal, 2007-2026, 5 bps/switch: unscaled Sharpe 0.627; inverse-vol
   cap 1.0 → 0.611; cap 2.0 → 0.555. Drawdown halves (21.0 % → 11.4 %) and CAGR
   falls (8.38 % → 6.64 %). It is risk transformation, not alpha, and the audit2
   doctrine page states it as fact. Correcting it matters because the same page
   uses it to justify position sizing.
   Evidence: `reports/2026-11-22-horizon-allocation-review.md` §3,
   `reports/horizon_backtest_2026-11-22.json` (`e2_vol_scaling`).

2. **A class verdict is not an asset verdict.** `CRYPTO KILL` scores 6,926 of our
   picks at −0.42 %/trade. Buy-and-hold BTC over the same era returned 49.1 %
   CAGR with Sharpe 0.91 vs SPY 0.66, and an −83 % drawdown. Both statements are
   true; conflating them is the error the review was written to catch.
   Evidence: same report §7, `e5_class_vs_pick`.

3. **The floor is larger than the alpha being chased.** T-bills compounded to
   +17.5 % over ten years with no meaningful drawdown, and SPY lost to cash in
   11.6 % of rolling 10-year windows and 20.6 % of 1-year windows (1993-2026).
   Evidence: same report §2, `e1_horizon_long`.

4. **Faber TAA reproduces the risk effect, not the quoted Sharpe.** 0.56/0.65
   measured against 1.74/1.65 quoted; drawdown halves, CAGR gives up ~2.2 pp/yr.

## What would count as a breakthrough

A pre-registered rule, net of 2x measured costs, whose forward rows after
registration show CI-LB > 0 against a matched benchmark and survive split-half.
As of 2026-11-22 the closest is POD-EQUITY-BREAKOUT, which has **zero** forward
rows while orphan H-119 has 430 — a measurement problem, not a discovery.
