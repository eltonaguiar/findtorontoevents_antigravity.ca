# PRE-REGISTRATION — H-236: does H-201's momentum survive a 44-name PIT universe?

**Filed:** 2026-11-23, before the run. **Rule:** M-107. **Status at filing:** REGISTERED.

## Why

H-234 made H-201 `ROBUST` across both halves of its own sample — but both halves used the same 10
mega caps (`AAPL MSFT NVDA AMZN GOOGL META JPM XOM UNH JNJ`). That tests period stability, not
universe stability, and the universe is 10 surviving mega caps chosen with hindsight. H-236 is the
universe stress that H-234's limitation note named.

## Construction

- Universe: the 44-name PIT artifact `reports/pit_equity_universe_20261122.json` (`universe` list,
  membership constant at 44 across all 61 monthly rebalance dates).
- Rule unchanged: `xsmom(lookback=126, top_k=3, cost_bps=10, rebal_days=21)`, SPY benchmark.
- Window: the artifact's own window (2021-11-30 .. 2026-11-20), because that is where the PIT
  membership is defined. Everything outside it would reintroduce the hindsight the artifact removes.

## Test statistic

Mean net daily return in bp on the 44-name book, block bootstrap 95% CI (block 5, 2,000 resamples),
plus mean excess vs SPY and its CI. Secondary: the same rule on the 10-name mega-cap book **over the
identical window**, so the comparison isolates universe breadth rather than period.

## Acceptance

`REPLICATED` iff mean > 0, CI lower bound > 0 and excess vs SPY > 0 on the 44-name book.
`REFUTED` otherwise. No re-splitting, no lookback change, no cost change.

## Known limits, stated in advance

- ~5 years, so the test is far weaker than H-234's 15.  Failure to replicate here does not overturn
  H-234; it bounds how much of H-201 depends on the mega-cap universe.
- The PIT artifact is `PARTIAL_NON_DELISTING_AWARE` (residual bias upward), so a *pass* here is
  still not survivorship-free evidence.
- This adds a trial; N declared rises again and the deflation bar moves.
