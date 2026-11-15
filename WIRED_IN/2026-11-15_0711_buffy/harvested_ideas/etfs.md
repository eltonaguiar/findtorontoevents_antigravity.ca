# ETFs

**Scan footprint:** 1,052 flagged files.

**Closed-ledger measurement:**

| n | mean | median | WR | PF |
|---:|---:|---:|---:|---:|
| 503 | +0.08% | −0.68% | 44.3% | 1.07 |

**Verdict: REJECT (as currently traded).** PF 1.07 at n=503 is the null result of this audit:
with this sample, an edge below ~0.1% per trade is statistically invisible, and 1.07 is inside
that band. The median is negative.

**What has been tried:** sector rotation (`etf_sector_rotation_backtest`), dual momentum with
cross-validation (`etf_dual_momentum_cv_2026-06-03`), VIX gate for ETFs, Faber tactical
(`peer_claude-strategy-build-faber-tactical`), ABC backtest, economic backtest.

**Important nuance:** ETF strategies are the ones where a *real* edge is most plausible in
principle (sector momentum is a documented factor), but this repo trades them on a daily-pick
cadence instead of a monthly rotation cadence, which is where the literature's edge lives. The
PF 1.07 is evidence about the cadence, not necessarily about the idea.

**Next experiment:** one monthly (not daily) sector-rotation test on a fixed 11-sector universe,
measured vs SPY with block bootstrap, n ≥ 60 monthly observations. If it fails, ETF is closed
for good; if it works, the cadence was the bug.
