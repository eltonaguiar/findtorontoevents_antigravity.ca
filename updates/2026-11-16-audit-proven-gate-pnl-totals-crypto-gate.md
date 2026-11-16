# 2026-11-16 — /audit: PROVEN badge, P&L totals, crypto long-only gate

**Scope.** Fixes for three findings from `reports/audit_data_quality_2026-11-16.md`
(live payload `generated_at 2026-11-16T13:06:26Z`, 7,654 pick rows).

## 1. PROVEN badge was a name lookup, not a result

**Broken.** `dashboard_generator.py` wrote `pick["trust_tier"] =
get_tier(source_system)` — a lookup in `cross_aggregation/system_trust_registry`
— overwriting the empirical tier `stamp_pick_quality.py` had just computed from
closed-pick history. `ml_bg_system_f` aliases to `claws_of_doom`, which is a
PROVEN entry, so all 97 of its rows carried PROVEN regardless of results. The
frontend independently re-derives the tier from `_TRUST_PROVEN_STRATEGIES` /
`_TRUST_PROVEN_SYSTEMS` in `audit_dashboard/template.html` (the manifest calls
it "name-match, not a live closed-pick query").

**Changed.**
* New `audit_trail/proven_gate.py`: the published rule as code — PROVEN needs
  `n >= 20` resolved rows, `WR >= 50%`, `PF >= 1.5`. Stats come from the
  strategy-level `strat_fwd_wr` / `strat_fwd_trades` / `strat_fwd_pf` stamped
  before generation, so the check is forward-clean at generation time. A pick
  with no verifiable stats is demoted (`unverifiable:no_strategy_stats`).
* `dashboard_generator.py`: before writing the registry tier, a PROVEN result
  is re-checked; failures are demoted to WATCH (n>=5) or MONITOR and annotated
  with `trust_tier_demoted_from` / `trust_tier_demote_reason`. Summary gains a
  `proven_badge_audit` block (`rule`, `demoted_from_proven_this_run`, examples).
* `audit_dashboard/template.html`: `getTrustTier()` returns the payload's
  demoted tier when `trust_tier_demoted_from === 'PROVEN'`, so the name lookup
  cannot re-promote a pick the ledger rejected.

**Verified.** Running the gate over the live payload demotes **97 of 97**
PROVEN rows to WATCH — 86 on `wr_below_floor`, 11 on `insufficient_sample`.

## 2. Four P&L totals, none labelled, one silently floored

**Broken.** `total_pnl_pct` (−77.67), `total_pnl_pct_sum_raw` (−1356.44),
`total_pnl_pct_compounded_ew` (−99.0, clamped from −1356.44 with no record) and
`total_pnl_pct_geomean_annualized` (−99.9) appeared as four competing claims.
`zero_pnl_count` said 132 while 3,868 rows carried `pnl_pct: 0.0`.

**Changed.** New `audit_trail/pnl_totals_audit.py`:
* `build_pnl_headline()` emits one primary metric (rolling-100 compound) plus a
  `values` map and `basis_notes` for each alternative, and records
  `compounded_ew_floored` / `compounded_ew_pre_floor`.
* `compute_resolver_anomalies()` counts resolved rows whose outcome cannot
  follow from their own geometry.
* `dashboard_generator.py` captures `_compounded_ew_pre_floor` before the −99 /
  9999 display clamps and adds `pnl_headline` + `resolver_anomalies` to
  `summary`.

**Verified on the live payload:** `stale_exit_beyond_planned_stop=44`,
`clamped_loss_rows=2`, `expired_zero_pnl_rows=3204`,
`closed_rows_missing_closed_at=34`, `rows_scanned=7654`. The NEARUSDT row
(entry 1.356, SL 1.37973, exit 3.193, `EXPIRED`/"STALE >5809h",
`pnl_pct −99.0`, `pnl_pct_pre_clamp −135.472`) is detected by the stale-exit
and clamp counters.

## 3. Crypto long-only gate: stale calibration, and unmeasurable

**Broken.** `SMART_PICKS_CRYPTO_LONG_ONLY = True` was justified by a 7-day
April-2026 window where SHORT PF 1.54 trailed LONG 1.91. The full resolved
ledger says the opposite: LONG n=1,356 WR 32.7% PF 0.51 (Σ−1,514.8%) vs SHORT
n=608 WR 55.6% PF 1.89 (Σ+617.0%). The gate also left no trace of what it
rejected.

**Changed.** The flag is now env-overridable
(`SMART_PICKS_CRYPTO_LONG_ONLY=0`) with the ledger evidence in the comment, and
rejections set `pick["_smart_crypto_short_blocked"]=True` so the shadow cost is
visible in `smart_gate_failure_histogram`.

**Not flipped on by default.** Tested first: of 132 active crypto SHORTs, 5 pass
score>=65, 5 pass confidence, 4 pass R:R, and **0** pass `forward_validated`
(LONG: 5/3/3/0). The binding constraint is forward validation, not direction, so
flipping the flag today would admit nothing — the env var exists for the A/B.

## Files

* `audit_trail/proven_gate.py` (new)
* `audit_trail/pnl_totals_audit.py` (new)
* `audit_trail/dashboard_generator.py`
* `audit_trail/quality_gates.py`
* `audit_dashboard/template.html`
* `tests/test_audit_proven_gate_and_pnl_audit.py` (new, 14 tests)

## Verification run

```
python3 -m py_compile audit_trail/proven_gate.py audit_trail/pnl_totals_audit.py \
    audit_trail/dashboard_generator.py audit_trail/quality_gates.py   # OK
python3 -m pytest -q tests/test_audit_proven_gate_and_pnl_audit.py    # 14 passed
python3 -m pytest -q tests/test_compound_equal_weight_pnl.py          # 3 passed
```

No dashboard regeneration was run locally (it writes the deployed HTML).

## Still open (not fixed here)

* The frontend registries remain name-match for picks that were never PROVEN by
  name (`_TRUST_PROVEN_STRATEGIES` still lists strategies with 0 closed rows).
* Prediction-market rows (`polymarket_signals`, `pm_kalshi_signals`,
  `pm_whale_signals`, `prediction_market_consensus`) get synthetic stats in
  `stamp_pick_quality.py` (`n=max(source_count,5)`, `wr=max(...,0.50)`) when the
  ledger is empty — a fabricated-input path for trust scoring.
* `MUTUAL_FUND` is not a registered class: 0 payload rows, and the separate
  `ejaguiar1_mutual_funds` DB is unreachable (1045) per `SWARM_Nov162026/DB`.
