# What is blocked, exactly why, and what would unblock it

**Date:** 2026-11-22 · **Owner:** buffy · **Programme:** `plans/2026-11-22-50-action-items.md`

Seven of the fifty items cannot be completed from this machine, and one more is answered only
in part. They are listed here with the **specific** missing artifact rather than a general
"needs data", because a vague blocker is indistinguishable from an excuse.

| # | Item | What is missing | Evidence it is missing | What would unblock it | Cost to unblock |
|---|---|---|---|---|---|
| 6 | Execution realism: stored fills vs modelled slippage | Realised fill prices from the live system | The stored rows carry `entry_price` but no `fill_price`/`slippage` column, so modelled and realised cost cannot be paired per trade | A DB export with per-fill executed price, or enabling fill logging on the emitter | Requires DB access + an emitter change; not an analysis task |
| 12 | Crypto CME calendar basis vs perp basis | CME BTC/ETH futures series (front + second month) | Only one continuous front-month series exists on disk, same defect that blocks commodity term structure | CME or Databento subscription | Paid feed |
| 14 | Buy-write (BXM-style) vs SPY | An options or BXM total-return series | No options chain, no BXM index in the cache; synthesising an option book from VIX would invent the premium | A CBOE BXM series or an options history | Paid feed (BXM itself is free from CBOE but not fetched here) |
| 19 | Penny-stock liquidity haircut from ADV | Per-symbol average daily volume for the penny universe | The penny universe is a seed list (`data/penny_universe_seed.json`) with no volume series attached | A volume history join for those tickers | Fetchable, but the penny universe itself is survivorship-contaminated, so the haircut would refine a number that cannot be trusted |
| 20 | MUTUAL_FUND NAV execution lag | Fund NAV publication timestamps | Cost field is configured at `0.08` and never populated; no NAV series with publication dates exists | A fund NAV source with as-of dates | Paid/labelled data |
| 26 | PBO / CSCV block-length sensitivity | The T×N per-cell return matrix | `reports/per_class_edge_2026-11-22.json` stores only the scalar `pbo_cscv`, not the matrix it was computed from | A one-line harness change to persist the matrix, then re-run with `s_blocks ∈ {8,16,24}` | Cheap, but requires re-running the 40-cell harness |
| 27 | White's Reality Check across the 40-cell family | Per-cell daily return series | Same root cause as 26: only summary statistics are stored, and a family-wide p-value cannot be computed from summaries | Persist each cell's daily excess-return vector, then bootstrap the max statistic across all 40 | Same harness change as 26 — the two should be done together |

## The one partial

**15 — vol-scaled cross-sectional momentum.** The *strategy-to-benchmark* vol match is already
computed and it does **not** rescue H-201: matched excess **+1.94 bp/day** but
**matched CI-LB −0.533**, i.e. once the cell is scaled to SPY's volatility the lower bound is
negative and the raw +7.246 is largely volatility rather than selection.

What remains genuinely untested is the *position-level* variant — weighting each name by inverse
realised vol inside the top-3 basket — which is a different rule and is not answered by the
above. It is recorded as partial rather than closed, because "the vol match says no" and
"inverse-vol position sizing says no" are different claims and only the first was measured.

## The pattern worth noticing

**23 of the 50 items needed nothing but arithmetic on data already on disk** — cost floors,
required-n, DSR margins, portfolio construction, seasonality. The blocked ones are almost all
blocked on the same two things: a **measured transaction cost** (11 of 12 classes) and a
**point-in-time universe** (every class). Neither is an analysis problem; both are procurement
problems, and no amount of further backtesting substitutes for them.

That is the honest reason this programme stops where it does: the remaining questions are
answered by buying data or by waiting for forward days, not by thinking harder.
