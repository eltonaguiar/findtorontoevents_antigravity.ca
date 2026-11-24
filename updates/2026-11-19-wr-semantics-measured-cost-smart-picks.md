# `wr` semantics, measured cost, one smart-picks definition (2026-11-19)

Three follow-ups from the merged denominator work.

## 1. Why `money_ready_verdict` returned `wr=0.4052` for a 47%-WR fixture

**Root cause.** The emitted field named `wr` was assigned `_sizing_wr`, the
honest-intrabar overlay, not the win rate of the class rows it sat beside:

```python
"n_resolved": _sizing_n,
"wr": round(_sizing_wr, 4),     # <- overlay, different row set
```

`audit_dashboard/data/money_ready_verdict.json` proved it in the wild:
`COMMODITY wr=0.4052, sizing_source=intrabar_truth`. Any unit test that patched
`_load_picks` therefore still read a number from a static intrabar artifact — which
is why two unrelated fixtures (`80/20` and `47/53`) both produced exactly 0.4052.
`wr` never described the fixture at all.

This is structurally the same defect as ETF on `/audit` (n=52/WR 1.9% vs n=584/WR
43.1%): two metrics, different denominators, one label.

**Fix.** `wr` / `wr_pct` / `pf` / `n` now describe the class's own resolved rows.
The overlay is published as `sizing_wr`, `sizing_pf`, `sizing_wr_ok`, and
`verdict_basis` names which metric actually gated the verdict (`policy_clean` vs
`intrabar_truth`). `wr_ok` follows `wr`; `sizing_wr_ok` is the gate.

**Second fix.** `MONEY_READY_INTRABAR_TRUTH=0` disables the overlay, so a
policy-only run (and any unit test) is judged on the rows it was handed instead of
on a live artifact.

## 2. One cost model: audit3 adopts measured slippage

`alpha_engine/audit3_tribunal.py` carried flat class constants that were above
measured for CRYPTO (0.15 vs 0.0997), EQUITY (0.10 vs 0.05), ETF (0.08 vs 0.05)
and FOREX (0.05 vs 0.02) — conservative — and **below** measured for FUTURES
(0.10 vs 0.15) and COMMODITY (0.12 vs 0.15), i.e. optimistic. A commodities cell
could clear a cost gate at a cost it never paid.

`load_rows` now calls `_apply_measured_costs(payload)`, which adopts
`slippage_validation.asset_class_stats[name].avg_slippage_pct` when that class has
at least `MIN_COST_SAMPLE` (30) measured closes, and per-strategy
`flagged_strategies[name].avg_slippage_pct` (78 strategies in the current payload)
with the per-strategy value taking precedence. Classes below the sample floor keep
the flat fallback. The report's `conventions.cost_basis` records `model`
(`measured` / `flat_fallback`), the class table actually used, and how many
per-strategy costs were applied — so a reader can tell which prices a verdict used.

Both surfaces now price from the same payload block, and the canonical view's
`CLASS_COST_BPS` matches what audit3 lands on for CRYPTO/EQUITY/ETF/FOREX/BOND.

## 3. One smart-picks definition

The page carried `smart_picks_feed` (0 picks, `total_scored` 0) and
`smart_picks_snapshot_summary` (45 batches, 95 picks, 68.4% WR, `metric_type:
snapshot`). Both are true; they answer different questions, and no reader could
tell. The payload now also publishes a single `smart_picks` object:

* `definition` — Smart Picks = picks clearing `SMART_PICKS_MIN_SCORE` in the
  current feed;
* `now` — `n_picks`, `total_scored`, `metric_type: live_feed`;
* `history` — `n_picks`, `resolved_batches`, `win_rate_pct`,
  `metric_type: snapshot`, **`comparable_to_live_feed: false`**, and the caveat
  "batch-resolution pricing, not execution fills".

The legacy keys stay for compatibility; nothing has to guess which is which.

## Verification

* `tests/test_money_ready_wr_semantics.py` — `wr` = class rows (0.7 for a 70/100
  fixture) while `sizing_wr` = 0.4052 from the injected overlay, and the overlay
  switch is honoured.
* `tests/test_audit3_cost_basis.py` — measured class cost replaces the constant
  (CRYPTO 0.0997), thin samples keep the fallback (BOND n=5), per-strategy beats
  class, and a payload with no block reports `flat_fallback`.
* Existing audit3 suites re-run green.
* `tests/test_money_ready_verdict.py`: see the commit message for the count before
  and after — the overlay leak explains the 10 pre-existing failures documented in
  `updates/2026-11-19-canonical-denominator-gates-on-dead-tiles.md`.

## Still open

The 68.4% tile itself lives in generated markup I could not attribute to a single
template element; the data layer now labels it `comparable_to_live_feed: false`, but
the tile should also be relabelled in the UI rather than only in the payload.
