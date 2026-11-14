# final_v2 — per-asset-class profitability pass, and two corrections to my own prior audit

**Date:** 2026-11-14
**Deliverable:** `final_v2/quant-audit-2026-11-14/`

## What was done

Second-pass audit answering where this system can be profitable by asset class, and re-adjudicating
every peer profitability claim by re-execution.

## Two corrections to my own `final_2026_11_14` package

1. **"`resolution_method` is None for all 3,500 closed rows" was wrong.** The field is `exit_reason`
   and it is populated: SL_HIT 1,468 / TP_HIT 873 / FORCE_CLOSED 615 / TIME_EXIT 517 / UNKNOWN 22 /
   EXPIRED 5. Recorded as a P0 blocker in the prior package; it is not a blocker.
2. **The 100× PnL unit error does not exist in the dashboard ledger.** Recomputed `pnl_pct` from
   `entry_price`/`exit_price` (direction-aware) for all 3,500 rows: 100% within 0.05pp, median error
   0.000pp. The bug is real in `multi_asset/data/multi_asset_closed.json` but not here.

## Main findings

- Per class: CRYPTO PF 0.768 (−837.8pp, t=−4.84), EQUITY 1.154 (+238.3pp, t=1.52), ETF 1.036,
  FOREX 0.634, BOND 0.586, COMMODITY 0.604. Every class decays half-to-half.
- **Stop-fill slippage is 98.8% of the crypto loss**: planned risk 1.919% mean, realized 2.990%,
  `exit_price` ≠ `stop_loss` in 703/773 rows, total overshoot +828.0pp. pnl matches `exit_price`
  (633) or the stop (140), never neither — so the arithmetic is right and the fill is late.
- The repo's own `benchmark_ledger_proof.json`: 170 ledgers, **4 pass at 95% vs 8.5 expected by
  chance**. `mega_mutation_ema_momentum_m006` — listed as a winner in `PROFITABLE_APPROACH_PROVEN.md`
  — is PF 0.767, cum −33.8%, MC percentile 0.0 at n=66.

## Verification

`04_verification/per_class_stats.py` and `r_multiples.py`, both replayable from the committed
payload field layout; raw console output committed under `05_evidence/` with sha256 recorded in
`04_verification/README.md`.

## Status

No asset class is profitable after costs; `readiness.by_class` reports `sizing_allowed: false` for
all nine classes. No code changes were made in this pass — findings and a ranked, gated test plan
only.
