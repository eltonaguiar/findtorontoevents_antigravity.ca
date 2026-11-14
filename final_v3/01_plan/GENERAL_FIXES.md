# General fixes — the full todo list

Grouped by subsystem, ordered by (money moved) ÷ (cost to build). Each item has an acceptance test so
"done" is checkable rather than asserted. Items marked **DONE TODAY** have code in this branch.

---

## Group 1 — Measurement integrity (do first; nothing else is trustworthy without it)

**G1. Stop-fill provenance on every closed row** — **DONE TODAY**
`audit_trail/stop_fill.py`: classifies each SL row `stop | gap_through | late_polled | unmeasured`,
adds `planned_risk_pct`, `realized_risk_pct`, `stop_slippage_pct`, `pnl_pct_at_stop`. Never rewrites
`pnl_pct`.
*Accept:* `python3 -m audit_trail.stop_fill --payload <p>` prints per-class planned vs realized risk.
*Current output:* CRYPTO 1.919% → 2.956% (1.54×); EQUITY 4.984% → 4.551% (0.91×).

**G2. Gap-aware fills in the resolver** — **DONE TODAY**
`_check_tp_sl_intrabar` now fills at the bar open when a bar gaps through the level, at the level
otherwise. `RESOLVER_GAP_AWARE_FILL=0` restores legacy.
*Accept:* `tests/test_stop_fill.py` covers span/gap/both-sides; resolver compiles; flag round-trips.

**G3. Verdict artifact invalidation** (fixes B1)
Every verdict/`VALIDATED` document carries `evidence_hash` + `generated_at`; a consumer refuses stale
hashes; CI greps `VALIDATED|PROVEN` and requires a registry match.
*Accept:* renaming a source artifact makes the dependent verdict fail CI.

**G4. Canonical cohort per class** (fixes B2)
One query per class producing `{cohort_id, n, filter_hash}`; reconciliation job diffs
`money_ready_verdict` vs `pf_registry` vs payload and fails on disagreement for the same cohort.
*Accept:* the ETF 2.22% vs 68.42% gap resolves to two named cohorts, or CI fails.

**G5. Field contract + population assertion** (fixes B5)
Adopt `finpredict-v2`'s `DATA_CONTRACT.md`; assert `exit_reason` populated on ≥95% of closed rows and
that `resolution_method` (SQL) and `exit_reason` (payload) are explicitly mapped.
*Accept:* dropping `exit_reason` from a payload fails the build.

**G6. Unit canonicalization at every write path** (fixes B6)
Percent-only storage; read-side guard rejecting `|pnl| > 100` without a declared `unit`; one-off
migration for the 17,632 percent-style MySQL rows.
*Accept:* a mixed-unit fixture cannot be written; the dashboard ledger still reproduces 3,500/3,500.

**G7. Symbol/class hygiene at ingest** (fixes B7)
Enforce the currency allowlist; route currency ETFs to ETF; reject unparseable timestamps instead of
coercing them.
*Accept:* FOREX row count drops by the 49 known non-FX rows and no `EURUSDT` remains in FOREX.

**G8. Trial registry + corrected thresholds** (fixes B8)
`trials.json`; BH-FDR q=0.10 across the real count; |t| ≥ 3.5 for promotion; every result carries its
trial ID.
*Accept:* promotion without trial ID fails; the 170-ledger run reports its count automatically.

---

## Group 2 — Gates that can actually block (fixes B12)

**G9. Per-class cost gate** — **DONE TODAY**
`tools/per_class_cost_gate.py`: class may emit only while `mean_pnl_pct ≥ 3 × round-trip cost` and
`n ≥ 30`; fail-open on unknown/thin/stale. Wired into `tools/hc_gates_python.passes_high_conviction_pick`
(default ON, `PER_CLASS_COST_GATE_ENABLED=0` disables) and as a stamping fallback in
`dashboard_generator.stamp_after_cost_fields`.
*Accept:* `tests/test_per_class_cost_gate.py` (18 tests) passes; index builds from the live payload.
*Current verdict:* EQUITY ALLOW (3.23×), CRYPTO/ETF/FOREX/BOND BLOCK, COMMODITY thin-sample BLOCK.

**G10. Populate `after_cost_net_per_trade`**
Was `null` on 3,500/3,500 rows — the field the existing HC after-cost gate reads was dead. Class-level
fallback now fills it. Next step: restore the strategy-level B16 index by generating
`reports/forward_edge_audit_*.json` on a schedule.
*Accept:* ≥ 90% of closed rows carry a non-null value.

**G11. Wire `sizing_allowed` to emission**
`readiness.by_class` returns `false` for all nine classes and blocks nothing. Either connect it to the
scanner's emit path or delete it.
*Accept:* emitting while `sizing_allowed=false` is impossible without an explicit override that is
logged.

**G12. Maker/taker reality check**
All cost figures assume taker fills. If any strategy is intended maker, its cost model must say so and
its assumed fill rate must be measured.
*Accept:* every strategy declares `liquidity_role`; cost is derived from it.

---

## Group 3 — Exit semantics and lifecycle

**G13. Resolve B4 (exits inside the stop)** (see `../00_common_themes/DEEP_INVESTIGATION.md` D1)
Record `stop_loss_initial` and `stop_loss_at_exit`; if a trail moved the level, label the row
`TRAIL_HIT`, not `SL_HIT`.
*Accept:* for each class, ≥95% of `SL_HIT` rows have `exit_price` on the correct side of
`stop_loss_at_exit`.

**G14. Make `FORCE_CLOSED` a real reason** (n=615, mean +0.019 — pure noise today)
Split into: `MAX_HOLD`, `SIGNAL_FLIP`, `MISSING_PRICE`, `MANUAL`, `ZOMBIE_CLEANUP`.
*Accept:* no row carries bare `FORCE_CLOSED`; each bucket has n and mean PnL reported.

**G15. Decisive flag stored, not inferred** (fixes B10)
`decisive: true|false` written at close; the 53 zero-PnL rows excluded from every cohort by the flag,
not by a filter each consumer re-implements.
*Accept:* screener totals equal payload totals minus decisive-false, with a printed reconciliation.

**G16. Relabel audit trail**
Any `EXPIRED→WON` style relabel writes before/after counts and a reason to an audit table.
*Accept:* relabeling without an audit row is impossible.

---

## Group 4 — ML model quality

**G17. Purged walk-forward as the only evaluation**
Replace random K-fold anywhere it appears with purged, embargoed walk-forward; embargo ≥ the max
holding period.
*Accept:* no `train_test_split`/`KFold` without `purge`/`embargo` in strategy evaluation code.

**G18. Feature-set freeze per forward test**
Every model records the exact feature list and hash at train time; a changed feature set starts a new
trial ID.
*Accept:* two runs with different features cannot share a trial ID.

**G19. Calibration, not just ranking**
Report reliability curves per class; the HC gate's confidence bands (0.85–0.95) were removed for being
non-predictive — replace the assumption with a measured curve.
*Accept:* each promoting model ships a calibration plot + Brier score.

**G20. Leakage canaries**
Synthetic features with known zero information in every training set; if the model finds signal in them,
the pipeline leaks.
*Accept:* canary feature importance ≈ 0 on a clean run.

**G21. Label the horizon**
Every pick declares its intended holding period and is evaluated at exactly that horizon. Today a
48h-horizon pick can be scored by a 4-week outcome.
*Accept:* evaluation filters on `intended_horizon == evaluation_horizon`.

---

## Group 5 — Repo hygiene

**G22. One writer per generated file** (see A8)
**G23. Kill dead scanners** — the 683-strategy zoo produces 0/166 passing cells; archive anything that
has not emitted a passing cell in 90 days.
**G24. Docs match code** — the AGENTS.md path registry is documentation-only since the push trigger was
removed; say so or restore enforcement.

---

## Sequencing

| Phase | Items | Why this order |
|---|---|---|
| 0 (done) | G1, G2, G9 | measurement + the two gates that need no new data |
| 1 (1 week) | G3, G5, G13, G14, G15 | cheap, unblocks correct interpretation |
| 2 (2 weeks) | G4, G6, G7, G10, G11 | reconciliation + real enforcement |
| 3 (1 month) | G8, G17–G21 | statistics plumbing before any new model |
| 4 (ongoing) | G16, G22–G24 | hygiene |

**Do not start Group 4 before Group 1 is green.** Fitting models to a ledger whose exits are mislabelled
and whose classes disagree on denominators produces confident numbers about nothing.
