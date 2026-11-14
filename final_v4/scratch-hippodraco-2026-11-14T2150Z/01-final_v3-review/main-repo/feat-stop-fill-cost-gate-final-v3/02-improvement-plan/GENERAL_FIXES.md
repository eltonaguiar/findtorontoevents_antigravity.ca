# General fixes

Work in dependency order. A checked box is not a result; use the acceptance evidence.

## P0 - measurement and gating

- [ ] **G1. Establish canonical outcome fields.** Store raw entry/exit/stop/target, direction, timestamp with timezone, status, exit reason, resolution method, price source, quote timestamp, resolver version, and PnL unit/source. Do not infer units from magnitude.
  - **Accept:** every closed row can be recalculated from validated prices; ambiguous/unpriced rows remain null/unknown, not zero.
- [ ] **G2. Reconcile same-cohort metrics.** Assign `cohort_id`, filter/query hash, `n`, excluded counts, generated timestamp, and source snapshot to verdict, registry, dashboard, and raw-pick reports.
  - **Accept:** same-cohort rows reconcile exactly; different cohorts are explicitly named rather than averaged.
- [ ] **G3. Make freshness and quote status explicit.** Distinguish live, last-close, stale, unquoted, and placeholder. Do not carry entry price forward as a current quote.
  - **Accept:** stale/missing input yields `INSUFFICIENT_DATA`; no green PASS or fabricated 0% PnL.
- [ ] **G4. Fix outcome lifecycle and exit semantics.** Store `stop_initial` and `stop_at_exit`; distinguish trailing-stop, gap-through, time exit, manual close, missing-price, and unresolved. Preserve the old row and version each corrected replay.
  - **Accept:** each exit reason is supported by an auditable price/time path; no `SL_HIT` without a stop-level check or explicit trail evidence.
- [ ] **G5. Make promotion gates fail closed.** Missing/stale/unknown/thin cost evidence must produce `INSUFFICIENT`, never ALLOW. Return errors explicitly; remove broad catches that silently pass or suppress after-cost stamping failures.
  - **Accept:** fixtures for missing index, stale timestamp, low `n`, unknown class, and thrown exception cannot produce a promotable result.
- [ ] **G6. Separate recommendation status from live emission.** A money-ready verdict can hard-fail while live emission remains in shadow mode pending a reviewed migration. Do not silently disable all strategies as a side effect of a score change.
  - **Accept:** each gate declares its effect (`report_only`, `promotion_block`, or `emission_block`) and rollback.
- [ ] **G7. Audit source systems and class membership.** Enforce symbol allowlists, class mapping, valid entry/stop geometry, and parseable UTC timestamps at ingestion. Retain rejected rows in quarantine.
  - **Accept:** no proxy instrument is relabeled as the underlying class; rejected rows have reason codes and can be reprocessed.

## P1 - data quality and statistical process

- [ ] **G8. Create a hypothesis/trial registry.** Pre-register strategy, universe, signal, horizon, costs, benchmark, split dates, model/features, and a unique trial ID before evaluation.
  - **Accept:** every report links to its trial ID and input hashes; repeated tuning increments the trial count.
- [ ] **G9. Use purged, embargoed walk-forward evaluation.** Embargo at least the maximum holding period; fit normalizers and selectors on training data only.
  - **Accept:** tests detect shuffled dates, overlapping labels, and train/test feature leakage.
- [ ] **G10. Control multiple testing and concentration.** Report effective sample size, trial count, FDR/DSR/PBO with their assumptions, source and symbol concentration, and confidence intervals.
  - **Accept:** enforce FDR and single-source policy at the promotion/verdict layer only after shadow reports and tests validate behavior. Current source defaults both hard-enforcement switches OFF.
- [ ] **G11. Repair duplicate and lifecycle accounting.** Deduplicate on a documented economic key; quarantine suspected zombies/ghosts and relabels without deleting history.
  - **Accept:** every excluded row has a stable reason and before/after count; all denominators reconcile.
- [ ] **G12. Strengthen sample and calibration reporting.** Do not call a sample of 10 a stable winner. Publish Wilson intervals, calibration/Brier score, horizon, and sample counts by regime and symbol.
  - **Accept:** no `PROVEN` label without predeclared minimum sample and benchmark-relative OOS criteria.
- [ ] **G13. Keep passive benchmarks separate.** A mutual-fund/index allocation is a baseline sleeve, not an alpha signal or a live-pick class.
  - **Accept:** dashboard and reports distinguish beta/carry exposure from strategy alpha.

## P2 - operational consistency

- [ ] **G14. Add evidence-hash invalidation.** Generated verdicts cite input hashes and code version; consumers reject stale verdict snapshots.
- [ ] **G15. Add one-writer ownership for generated artifacts.** Map each JSON/dashboard output to one producer and document downstream consumers.
- [ ] **G16. Add row-level reproducer commands to reports.** A reviewer must be able to regenerate each material metric without production-side mutation.
- [ ] **G17. Document status vocabulary.** Define `NOT_BUILT`, `INSUFFICIENT_DATA`, `WATCH`, `BLOCKED`, and `MONEY_READY` in one shared contract; prohibit empty cohorts from passing.

