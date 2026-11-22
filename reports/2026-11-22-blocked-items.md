# What is blocked, exactly why, and what would unblock it

**Date:** 2026-11-22 · **Owner:** buffy · **Programme:** `plans/2026-11-22-50-action-items.md`

**Updated 2026-11-22 (status log 5):** items **26**, **27** and the partial **15** are now closed —
the harness change persisted the T×N matrices, and the inverse-vol variant was pre-registered as
H-232 and run. See `reports/2026-11-22-pbo-and-family-tests.md`. Five items remain blocked, listed
with the **specific** missing artifact rather than a general "needs data", because a vague blocker
is indistinguishable from an excuse.

| # | Item | What is missing | Evidence it is missing | What would unblock it | Cost to unblock |
|---|---|---|---|---|---|
| 6 | Execution realism: stored fills vs modelled slippage | Realised fill prices from the live system | The stored rows carry `entry_price` but no `fill_price`/`slippage` column, so modelled and realised cost cannot be paired per trade | A DB export with per-fill executed price, or enabling fill logging on the emitter | Requires DB access + an emitter change; not an analysis task |
| 12 | Crypto CME calendar basis vs perp basis | CME BTC/ETH futures series (front + second month) | Only one continuous front-month series exists on disk, same defect that blocks commodity term structure | CME or Databento subscription | Paid feed |
| 14 | Buy-write (BXM-style) vs SPY | An options or BXM total-return series | No options chain, no BXM index in the cache; synthesising an option book from VIX would invent the premium | A CBOE BXM series or an options history | Paid feed (BXM itself is free from CBOE but not fetched here) |
| 19 | Penny-stock liquidity haircut from ADV | Per-symbol average daily volume for the penny universe | The penny universe is a seed list (`data/penny_universe_seed.json`) with no volume series attached | A volume history join for those tickers | Fetchable, but the penny universe itself is survivorship-contaminated, so the haircut would refine a number that cannot be trusted |
| 20 | MUTUAL_FUND NAV execution lag | Fund NAV publication timestamps | Cost field is configured at `0.08` and never populated; no NAV series with publication dates exists | A fund NAV source with as-of dates | Paid/labelled data |
| 6b | ~~26, 27~~ | **CLOSED 2026-11-22.** The harness now persists `reports/per_class_edge_series_2026-11-22.csv` (5157×39 net) and `..._excess_...csv`. PBO is block-length robust but **convention-fragile** (0.345 → 0.53 on the honest matrix); the registered Reality Check does not reject (p = 0.144–0.479) while studentised/SPA do (p ≈ 0.015). Full write-up in `reports/2026-11-22-pbo-and-family-tests.md`. |

## The former partial, now closed

**15 — vol-scaled cross-sectional momentum. CLOSED 2026-11-22.** Both claims are now measured:

- *Strategy-to-benchmark* vol matching does not rescue H-201 — matched excess **+1.94 bp/day**,
  **matched CI-LB −0.533**.
- *Position-level* inverse-vol sizing (H-232, pre-registered in commit `b9ff7faab3e` before its
  first run) is **significantly worse than equal weight**: paired difference **−1.826 bp/day**,
  95% CI **[−2.754, −0.922]**, t = −4.23. DSR 0.8491 at n_trials = 30 (raised, not lowered).

So the answer is no twice, and the second answer is stronger than "no": reallocating weight
inside a fixed basket destroys 1.83 bp/day. See `reports/h232_invvol_2026-11-22.md`.

## The pattern worth noticing

**26 of the 50 items needed nothing but arithmetic on data already on disk** — cost floors,
required-n, DSR margins, portfolio construction, seasonality, PBO sensitivity, the family-wide
tests, the sizing variant. **45 of 50 are now complete; 5 remain blocked**, almost all on the same
two things: a **measured transaction cost** (11 of 12 classes) and a **point-in-time universe**
(every class). Neither is an analysis problem; both are procurement problems, and no amount of
further backtesting substitutes for them.

That is the honest reason this programme stops where it does: the remaining questions are
answered by buying data or by waiting for forward days, not by thinking harder.
