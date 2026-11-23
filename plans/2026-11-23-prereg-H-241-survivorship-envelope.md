# PRE-REGISTRATION — H-241: can H-201 be re-read without the delisting flag?

**Filed:** 2026-11-23, before the run. **Rule:** M-107. **Status at filing:** REGISTERED, UNTESTED.

## The problem this must solve

H-201's universe (`reports/pit_equity_universe_20261122.json`, 44 names) is stamped
`PARTIAL_NON_DELISTING_AWARE`. Every name in it trades on the final day of the window — i.e. the
universe contains **additions** (names listed after the window start) but **zero removals**. The
missing removals are the survivorship bias: names that died are exactly the ones a momentum book
would have held, and their returns are absent.

A delisting-aware universe would fix this by *procuring delisted prices*. That procurement was
attempted on 2026-11-23 and failed (evidence in `reports/h241_survivorship_envelope_2026-11-23.md`):

- Yahoo/yfinance: 30 of 37 known dead tickers (TWTR, ATVI, SGEN, PXD, SIVB, FRC, XLNX, DISH, …)
  return **no data at all**; the 7 that do return data are *recycled* live tickers, not delisted
  histories.
- Stooq (the usual free fallback for delisted US series): returns an HTTP 200 but the body is a
  JavaScript proof-of-work challenge, not CSV.

So H-241 is the second-best question, asked honestly: **instead of removing the bias, bound it.**
If the edge survives the pessimistic corner of a synthetic-delisting envelope, the flag stops being
decisive and H-201 can be re-read. If it does not, we have the number that kills it, and the flag
was decisive.

## Construction

- **Base book:** H-201's own rule on the 44-name PIT artifact — `xsmom(lookback=126, top_k=3,
  rebal_days=21, cost_bps=10/side)`, benchmark SPY, window 2021-11-30 .. 2026-11-20.
- **Injection:** at each 21-session rebalance, with probability `hazard_period = hazard_annual × 21/252`,
  one of the **selected holdings** is replaced for that holding period by a synthetic delisted name
  whose return is `haircut` instead of the observed return. Rationale: a name that dies after being
  bought is the only version of survivorship bias that can hurt a long-only top-3 book, and momentum
  selection is precisely what puts doomed names into a top-3.
- **Grid, fixed now:** annual hazard ∈ {0.00, 0.02, 0.04, 0.06, 0.10} × haircut ∈ {−0.30, −0.50, −0.70}.
  Baseline US delisting hazard for liquid large caps is ≈1–2%/yr; 6% and 10% are deliberately
  pessimistic stress corners, not estimates.
- **Paths:** 200 seeded paths per cell (seed = 241), each path the same rule and the same dates.
  Reported: mean net bp/day, block-bootstrap 95% CI (block 5, 2,000 resamples), and the fraction of
  paths whose own CI lower bound is > 0.

## Test statistic

Mean net daily return in bp on the 44-name book **at the cell's hazard and haircut**, with the CI
recomputed per cell (not reused from the baseline).

## Acceptance (fixed before the run)

- **SURVIVES_SURVIVORSHIP_STRESS** iff the CI lower bound stays > 0 at the pessimistic corner
  (hazard 6%/yr, haircut −50%) — i.e. twice the realistic hazard and a haircut beyond a typical
  takeover discount.
- **NOT_SURVIVES** iff the CI lower bound goes ≤ 0 before that corner; the report must name the
  exact (hazard, haircut) at which it breaks.
- **The baseline (0% hazard) cell must reproduce the previously published 44-name result.** If it
  does not, the run is `INVALID` and nothing else in it counts.

## What this is, and is not

- It **is** a bounded robustness statement: "the edge tolerates up to X% annual delisting at a Y%
  terminal haircut and still has a positive lower bound."
- It is **not** delisting-aware data, and it does not turn the flag into `CLEAN`. The flag becomes
  `BOUNDED` at best, with the tested envelope written into the artifact.
- It adds one trial. N declared rises; the deflation bar for every cell in the sweep moves up by
  the same amount as it would for any other trial, and that cost is accepted here rather than hidden.
