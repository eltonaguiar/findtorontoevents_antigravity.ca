# Prediction-market dossier (Block 49)

## Why the class was missing

The 12-class dossier set published in Block 48 covers the classes that have a verdict surface
on `/audit`, `/audit2` or `/audit3`. PREDICTION_MARKET is not one of them. It is referenced by
live code (`prediction_market_agents/`, `alpha_engine/polymarket_signals.py`,
`alpha_engine/kalshi_signals.py`, `alpha_engine/prediction_market_consensus.py`,
`copy_trader_intel/polymarket_scraper.py`) but has no bucket on any surface, so it never
appeared in a class list and no dossier was written for it. This one fills that gap and
records that the gap is structural, not an oversight.

## What was measured, and what is UNMEASURED

Measured, from files on `origin/main`:

- The only picks tagged `asset_class` PREDICTION_MARKET: `alpha_engine/data/pm_macro_expansion_picks.json`,
  4 rows, all OPEN, all contract-side YES, `pnl_pct` null on all four.
- Kalshi market inventory: 9054 market rows across 16 snapshots, all `status` active, with
  yes_bid, volume, last_price and open_interest null on every row.
- The PM odds history: 27573 rows over 202 market ids, no outcome field.
- The one PM number on an audit surface: the ledger's `prediction_market` source family at n 2,
  WR 1.0 CI [0.3424, 1.0], PF n/a, verdict INSUFFICIENT_N.
- The spot-derived proxy under the label (`prediction_market_consensus`): paper log 110 rows
  (WR 84.47 pct, PF 13.198, one +80.37 pct outlier is 29 pct of gross wins), pilot 1016 picks
  (published wr 64.76, pf 2.0242, max drawdown 69.17), forward replay REFUTED at 38.2 pct true WR.
- Cost: no venue fee is modelled anywhere; the only PM cost constant is a 110 bp framework
  placeholder; the ledger costs the family at 0.1 pct with no PM-specific key.

UNMEASURED, and why:

- **Any prediction-market win rate.** No file on main carries a settled binary contract.
  `data/pm_market_outcomes.json`, the feed `pm_contract_resolver` reads and `pm_outcome_ingest`
  writes, is not committed (and not gitignored). The contracts in
  `pm_macro_expansion_picks.json` are all OPEN.
- **Venue fees, spreads, settlement fees.** Nothing in the four generators models them. On a
  0.97 contract the gross win is 3.09 pct, so a fee of that size flips the sign; this is
  decisive, not cosmetic.

## Contradiction found

`verified_strategies/paper_pilot/prediction_market_consensus_pilot.json` says
`promotion_ready: true` with `min_forward_n: 50`, while
`prediction_market_consensus_state.json` and `..._dashboard.json` say `promotion_ready: false`
with `min_forward_n: 150` and a kill-switch WR floor of 55. One strategy, two promotion
verdicts. Separately, `audit_trail/quality_gates.py` RETIRES the strategy for corrupted exit
labels, and `alpha_engine/config.py` kills it for "WR 26%, -29% intrabar".

## What would convert it to a measured verdict

Run `pm_outcome_ingest`, commit `data/pm_market_outcomes.json`, and settle the macro contracts
against it. Gate: at least 100 settled contracts with payout-honest P&L and net PF CI-LB above
1.0. Falsifier: fewer than 100 settlements, or a CI that includes 1.0, leaves it UNMEASURED.
