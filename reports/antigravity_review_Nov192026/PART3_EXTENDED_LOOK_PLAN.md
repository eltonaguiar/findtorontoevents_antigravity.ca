# Extended Look — Part 3/4 Plan

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 04:00 EST
**Predecessors:** Part 1 (per-class deep dives + GHA framework), Part 2 (forward clock, reconciliation, measurement fixes, GHA QA findings, pod promotion).

---

## Why Part 3/4

Part 2 established the *structural* problems (orphan H-119, dashboard divergence, measurement blockers, QA hazards). Part 3/4 goes **one level deeper into the cell/strategy layer** to answer: *which strategies are actually closest to edge, why is nothing forward-testable, is the data fresh, and what are the concrete patches to unblock promotion and QA.*

---

## Part 3/4 deliverables

| # | Deliverable | Source data | Target |
|---|---|---|---|
| P3-1 | **Strategy-cell ranking** — all 67 tested cells ranked by net expectancy/DSR; identify closest-to-positive cells per class | `audit3_ledger.json` `cells` | `PART3_STRATEGY_RANKING.md` |
| P3-2 | **Backtest-vs-forward decay** — analysis of why `fwd_trades=0` across the entire backtest/forward table; what blocks the decay clock | `dashboard_data.json` `backtest_vs_forward`, `hf_decay_watchlist`, `fwd_vs_bt_divergence` | `PART3_BT_FWD_DECAY.md` |
| P3-3 | **Data freshness & DB health audit** — age/drift of all audit sidecars | `db_freshness.json`, `db_health.json`, sidecar timestamps | `PART3_DATA_FRESHNESS.md` |
| P3-4 | **Promotion-path fix blueprint** — concrete patch to adopt H-119 into a pod + wire tribunal to emission blocks | Part 2 findings | `PART3_PROMOTION_BLUEPRINT.md` |
| P3-5 | **GHA QA remediation patches** — exact YAML edits for the 7 flagged workflows | `gha_qa_audit_2026-11-22.md` | `PART3_GHA_REMEDIATION.md` |

---

## Execution order

1. **P3-1** — rank all 67 tested cells; produce per-class "closest to positive" table; note which cells only fail the multiplicity/DSR gate vs the edge gate.
2. **P3-2** — confirm the 0-forward blocker across the whole backtest/forward table; explain why decay can't be measured; identify root cause.
3. **P3-3** — audit freshness of every audit sidecar (`dashboard_data.json` vs ledger vs recency panels vs DB health).
4. **P3-4** — write the H-119 adoption patch (create `POD-H119-FORWARD-ALPHA`), plus the tribunal→emission wiring patch.
5. **P3-5** — write exact YAML remediation for the 7 flagged workflows (add `workflow_dispatch`, `concurrency`, narrow globs).

## Success criteria

- All 5 Part 3 docs pushed to `antigravity_review_Nov192026` `main`.
- COMS updated with Part 3 findings.
- Every number traces to a cited data file.

---
*Not investment advice. Evidence-first.*
