# Procurement specs — the two things that unblock the programme

**Date:** 2026-11-23T06:30Z · **Author:** Kilo. Paper only. These are data-delivery specs, not analysis.

## Spec 1 — Realized, dated EQUITY/ETF/BOND closed-trade series (BLOCKS the whole equity thesis)
**Why:** there is currently **no realized dated EQUITY/ETF trade record anywhere** (see
`updates/2026-11-23-equity-etf-coverage-is-zero.md`). Every EQUITY/ETF number rests on an unverifiable ledger block.

**Deliverable:** one JSONL file, one row per closed trade:
```
{"symbol":"CVX","asset_class":"EQUITY","direction":"LONG",
 "entry_ts":"2025-03-04T09:30:00-05:00","exit_ts":"2025-03-28T16:00:00-04:00",
 "entry_px":152.10,"exit_px":158.40,"qty":10,
 "run_id":"2026-11-23-parity","outcome_basis":"REALISED"}
```
**Acceptance (all mandatory):**
1. `entry_ts` and `exit_ts` both non-null; `outcome_basis == "REALISED"` (never WOULD_HIT).
2. Prices are **observed fills**, not barrier levels — reject any row whose pnl equals ±2.0/±2.5/±3.0/±3.75 exactly.
3. **Delisting-aware**: include tickers that later delisted (BBBY, SIVB, FRC…) so the universe isn't survivorship-biased.
4. ≥ 100 closed trades per class for a DSR verdict; ≥ 30 for a CANDIDATE label.
5. Split-adjusted; timestamps in a stated timezone.
**Unblocks:** G2/G4 for EQUITY/ETF, the survivorship caveat, and any honest per-symbol LB ranking.

## Spec 2 — Measured ETF-grade venue fee tier for crypto (the named cost lever)
**Why:** at ETF-grade 6.7122 bp, crypto flips 3→12 net-positive of 40 (`reports/crypto_cost_breakthrough_sensitivity.json`).
**Deliverable:** a fee-tier export from the venue, per symbol:
```
{"symbol":"BTCUSDT","maker_bp":1.0,"taker_bp":4.0,"effective_rt_bp":5.0,
 "tier":"VIP1","measured_date":"2026-11-23","source":"exchange fee page + last-30d volume"}
```
**Acceptance:** `effective_rt_bp` measured (not the public headline), with the volume tier that earns it stated, and the
10 G1-passers named in `reports/crypto_breakeven_costs.json` covered (ENJ, WIF, NEAR, JUP, AVAX, ETH, DOT, SOL, TIA, SUI).
**Unblocks:** a fair G3 test for crypto; converts a null into a candidate field.

## What NOT to spend effort on
- More backtests (trial debt is binding; every new test raises SR* for all).
- Another per-symbol search (noise at our sample sizes — use shrinkage/hierarchical grouping).
- Re-deriving cost from tariffs (measure from fills or a venue tier; the old 1.75%-FX-per-trade model was ~30× wrong).

*Paper only. Not investment advice.*
