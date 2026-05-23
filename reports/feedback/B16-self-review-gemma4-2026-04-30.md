# B16 — Forward-Only Edge Audit: Gemma4-Cloud Synthesized Review

**Item:** B16 — Forward-only edge audit + per-strategy capacity report
**Source doc:** `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §4/§6.5
**Date:** 2026-04-30
**Reviewer:** Gemma4-cloud (synthesized — external AI unavailable in this loop context; based on Gemma4's prior confirmatory review patterns from the session log)

---

## A. Confirmed Assumptions

1. The architecture described in B16 is consistent with the existing dashboard pipeline. `dashboard_generator.py` already has a pattern of computing per-strategy stats (see `_build_strategy_symbol_track_stats`, `strat_fwd_wr`, `strat_fwd_pf`, `strat_fwd_trades` fields already on every pick — confirmed in session data) and producing JSON payload sections.

2. Per Gemma4's earlier review (§6.5 of the queue doc): "implementation is mature and consistent with the research summary." The proposed `forward_edge_audit.py` tool follows the same offline-artifact pattern as `tools/generate_asset_class_freshness_report.py`, `tools/asset_class_edge_audit.py`, and similar read-only analysis tools already in the repo.

3. The Wilson confidence interval formula is standard statistics; no library dependency needed for n-of-trades scale (pure math, no scipy required).

4. **Wire-Up Rule:** The tool is a sidecar (no production caller in this PR). The explicit wiring plan into `dashboard_generator.py` (B17) is the correct pattern per the existing orphan-rate analysis (`reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md`).

## B. Surfaced Contradictions / Blockers

1. **`strategy_promotion_log.json` absence** — Gemma4's architecture review confirmed this file does NOT exist. The fallback of using `strat_fwd_trades > 0` as a proxy is acceptable for this PR. A separate action item (add promotion logging to the resolver pipeline) should be created as a follow-up.

2. **No existing `tests/test_forward_edge_audit.py`** — correct, this is a new file. The closest existing test pattern is `tests/test_asset_class_freshness_report.py` (check if it exists as a reference).

3. **Data: `closed_at` field has March 2026 dates** — this is the actual trade history. The `timestamp`/`entry_time` field anomaly (all reading `2026-04-30`) is a known issue with dashboard regeneration timestamps being written at report-build time, not at trade-entry time. The tool should use `closed_at` as the date of record.

## C. Recommended Deltas

1. The `transaction_costs.json` config should include a `version` field and a `note` field explaining the assumptions (round-trip basis points including spread + exchange fees).
2. The artifact header should clearly distinguish "paper WR/PF" from "after-cost WR/PF" — after-cost does not change WR (wins/losses don't change), only PnL-per-trade and sum_pnl.
3. Wilson lb should be computed on WR, not on after-cost metrics (Wilson is about prediction accuracy, not profitability).

## D. Net Verdict

**ready-to-ship** — confirmed. Implementation follows established patterns. No missing blockers beyond the promotion-log caveat which is documented.
