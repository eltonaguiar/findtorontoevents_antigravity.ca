# First denylist shadow review — measured (2026-11-19T21:04Z)

**Scope:** documentation only. Produced with
`python3 -m alpha_engine.audit3_denylist_hits` against the CI-persisted
`alpha_engine/data/audit3_denylist_hits.jsonl` (10,591 B, 27 rows).

## What the gate actually blocked

```
27 denials   2026-11-19T21:04:52Z
by class   : CRYPTO 23, COMMODITY 4
by strategy: atr_percentile_gate_scanner 9, luxalgo_confluence 7,
             prediction_market_consensus 6, commodity_momentum 2,
             commodity_rsi_divergence 1, commodity_term_cot 1,
             B_flip_PriceRocMeanReversion 1
by symbol  : BTCUSDT, WIFUSDT, ADAUSDT, DOTUSDT, SOLUSDT, ETHUSDT,
             XRPUSDT (2 each), HE=F 1
reasons    : "audit3 KILL: CRYPTO (class aggregate) n=6740 net=-0.3089%/trade"
             "audit3 KILL: COMMODITY (class aggregate) n=51 net=-3.5066%/trade"
```

## Reading it

1. **The gate is doing what the tribunal says.** Every denial cites a class
   aggregate whose net expectancy CI is negative — CRYPTO −0.309%/trade over
   6,740 trades, COMMODITY −3.507% over 51. Nothing here is a false positive on
   a class the ledger calls profitable.
2. **The class gate is the dominant kill, not per-strategy.** 27/27 denials come
   from the two KILL class aggregates. That is intentional (a class with proven
   negative expectancy should not emit), but it means class-level repair — not
   strategy tuning — is the lever for these strategies.
3. **`atr_percentile_gate_scanner` and `luxalgo_confluence` are the biggest
   blocked emitters.** They are not "good strategies being suppressed": the
   ledger scores them inside a losing class. They are candidates for
   **retirement or mutation**, which the kill tribunal already records.
4. **Paper / forward-shadow is unaffected.** The denylist gates
   `is_valid_active_pick` (live/active emission); the paper sim writes CLOSE rows
   straight into `reports/forward_observations.jsonl` through
   `tools/pilot_forward_bridge.py`. So the observe pods can still accrue evidence
   while their class is KILL — the intended separation.

## Operating procedure (now automated)

- **Automatic:** `audit3-health.yml` prints this summary every run (warn-only;
  says "no denylist hits committed yet" when empty).
- **On demand:** `python3 -m alpha_engine.audit3_denylist_hits [--json]`.
  Exit code `1` means "no data", so a scheduled check cannot mistake absence for
  cleanliness.
- **Cadence:** review weekly, and after any class verdict change. Watch for a
  strategy that suddenly dominates denials — that is a signal to retire it, not
  to loosen the gate.

## Caveats

- This is a **single snapshot** (one minute of denials), not a week. Re-run after
  several scanner cycles before drawing trend conclusions.
- Denials are counted per pick attempt; the same symbol/strategy appears
  repeatedly, so row counts are not distinct-signal counts.
