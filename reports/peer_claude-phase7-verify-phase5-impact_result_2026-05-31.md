# Phase-7 — Verify Phase-5 Impact (RESULT)

Date: 2026-05-31. Verifies that PR #182 (RETIRE cta_golden_cross_200 + prediction_market_consensus) propagated into published `/audit/data/`.

## TL;DR — Operator Actions Required

1. **TRIGGER REFRESH.** The live `pf_registry.json` (generated_utc 03:54:06Z) and `money_ready_verdict.json` (generated_at 03:54:05Z) were both produced BEFORE PR #182 merged (05:47:35Z). A `Unified Audit Dashboard` workflow_dispatch run is queued (id 26704679535, kicked 05:50Z) but stuck. **Action:** re-dispatch or cancel-and-rerun `Run Backtests & Deploy Dashboards` (workflow 281987111) once the runner clears the queue; that pipeline re-builds both JSONs from `quality_gates.py` which now has the RETIRE entries.
2. **Wiring is correct — no code follow-up needed.** PR #182 added the two strategies to `BLOCKED_SOURCE_SYSTEMS` in `audit_trail/quality_gates.py` (lines 2009, 2015). Both `tools/build_pf_registry.py` (lines 222–240) and `alpha_engine/money_ready_verdict.py` (line 258) import + apply that set. Once the next scheduled / dispatched run lands, the registry's `by_asset_class_strategy_policy_clean_net` view and the verdict's `classes.*` numbers will drop the two artifacts.
3. **PR #183 (at_strategy_stats schema diagnosis) was docs-only.** No code fix shipped. The strategy column still contains tier labels. Follow-up issue/PR still owed if anyone wants the table queryable by strategy.
4. **Expected post-refresh impact:** COMMODITY headline PF should drop further (clean view already excludes the cta_golden_cross_200 PF=44 inflation if it was source-tagged as that system; if it was tagged under a different source it persisted). CRYPTO PF change should be small — `prediction_market_consensus` was only 95 rows out of 4,451 CRYPTO closed.

## Verification Matrix

| Check | Source | Finding |
|---|---|---|
| PR #182 merged? | `gh pr view 182` | YES — mergedAt `2026-05-31T05:47:35Z` ("MERGED"). Files: `audit_trail/quality_gates.py` (+16). |
| PR #182 added suspects to retire set? | `grep` quality_gates.py | YES — `cta_golden_cross_200` at line 2009, `prediction_market_consensus` at line 2015, both inside `BLOCKED_SOURCE_SYSTEMS` with rationale comments referencing resolver-artifact analysis. |
| Wiring → pf_registry | `tools/build_pf_registry.py:222-240` | Imports `BLOCKED_SOURCE_SYSTEMS` and excludes matching strategies/source_systems before computing `_policy_clean_net`. |
| Wiring → money_ready_verdict | `alpha_engine/money_ready_verdict.py:258` | Reads `BLOCKED_SOURCE_SYSTEMS` from quality_gates and applies "Pass 1: global blocks". |
| Live `pf_registry.json` generated_utc | `curl` | `2026-05-31T03:54:06Z` — **PRE-MERGE** (1h53m before). |
| Live `money_ready_verdict.json` generated_at | `curl` | `2026-05-31T03:54:05Z` — **PRE-MERGE**. |
| Suspects in live `by_asset_class_strategy_policy_clean_net`? | `curl | jq` | Filter for `strategy in (cta_golden_cross_200, prediction_market_consensus)` returned `[]` (empty). However this view was produced PRE-MERGE — emptiness likely reflects no `strategy=` row tagging in source data, not the RETIRE effect. The registry rolls up at source/system, and the strategies-as-strings live under `top_strategy` of `by_asset_class_strategy_policy_clean_net` entries. Cannot use this snapshot as the post-merge confirmation. |
| Workflows refreshing data | `gh run list` | `Run Backtests & Deploy Dashboards` (281987111) last success `05:39:04Z` (PRE-MERGE). `Unified Audit Dashboard` (281988696) has a `workflow_dispatch` queued at `05:50:12Z` — POST-MERGE, but stuck in `queued` for 3m+. |
| PR #183 code change? | `gh pr view 183` | MERGED but docs-only — single file `reports/peer_claude-phase5-strategy-stats-schema-mismatch_plan_2026-05-31.md` (+143). No code fix. `at_strategy_stats.strategy` column still holds tier labels. |

## Class-level Before/After Comparison

"Before" = Phase-2 raw-DB audit (2026-05-31 morning, pre-RETIRE, includes the two suspects).
"Now (pre-refresh)" = live `money_ready_verdict.json` 03:54Z snapshot.
"After (expected)" = post next pipeline refresh once PR #182 quality_gates is read.

### CRYPTO

| metric | Phase-2 baseline (raw, all strategies) | Now (live JSON, pre-PR#182 refresh) | After (expected, post-refresh) |
|---|---|---|---|
| n_resolved | 4,451 | 330 (policy-clean) | ~241 (minus 89 prediction_market_consensus rows) |
| WR | 41.43% | 37.58% | slightly lower (PMC was 84% WR; removing it drops headline WR) |
| PF | 0.863 (raw) | 0.887 | slightly lower (PMC PF 24.5 inflated the clean view; removing it brings the rest closer to the raw 0.86) |
| verdict | FAIL | NOT_READY | NOT_READY (no axis change) |

**Interpretation:** RETIRE will improve TRUTHFULNESS (kill resolver artifacts) but NOT improve the headline. The class still fails T2 on every axis. This matches what we'd expect — removing inflated wins makes the dashboard more honest, not better-looking.

### COMMODITY

| metric | Phase-2 baseline (raw, all strategies) | Now (live JSON, pre-PR#182 refresh) | After (expected, post-refresh) |
|---|---|---|---|
| n_resolved | 712 | 10 (policy-clean — heavily filtered) | ~9 (one cta_golden_cross_200 row in clean cohort, if any) |
| WR | 38.90% | 40.0% | similar |
| PF | 0.700 (raw) | 1.7241 | likely drops below 1.0 (cta_golden_cross_200 was the PF=44 artifact; if even 1 row survived the policy-clean filter into this cohort, its removal materially moves PF on n=10) |
| verdict | FAIL | INSUFFICIENT_DATA (n=10) | INSUFFICIENT_DATA (n stays <100) |

**Interpretation:** The clean COMMODITY cohort is tiny (n=10). The pre-refresh PF 1.72 looks like an artifact too — likely residual look-ahead survivor. The post-refresh number will be more trustworthy but the verdict stays INSUFFICIENT_DATA either way.

## Remaining Gaps

| # | Gap | Owner action |
|---|---|---|
| G1 | Dashboard JSON files are stale (pre-PR#182). Live dashboard still shows pre-RETIRE numbers. | Operator: re-dispatch `Run Backtests & Deploy Dashboards`. Or wait for next scheduled cron (every ~4h, last 05:39Z → next ~09:39Z). |
| G2 | Queued `Unified Audit Dashboard` workflow_dispatch (id 26704679535) is stuck. | Operator: check runner availability; if needed `gh run cancel 26704679535 && gh workflow run "Unified Audit Dashboard"`. |
| G3 | PR #183 diagnosed `at_strategy_stats.strategy` schema mismatch but no code fix shipped. Per-strategy queries via that table are still broken. | Future PR: rename column OR populate it correctly from the picks source. Out of scope for Phase-7. |
| G4 | `pf_registry.by_asset_class_strategy_policy_clean_net` returns empty when filtered by suspect strategies in the live JSON. Cannot use the live registry as the audit-trail for "did we remove them"; need to inspect raw DB or wait for refresh + recompare. | Add a strategy-level "retired_in_quality_gates" flag to the registry output (small enhancement to `tools/build_pf_registry.py`) so the audit history is preserved. |
| G5 | Class-aggregate verdicts (NOT_READY / INSUFFICIENT_DATA) won't change after refresh. The Phase-5 RETIRE is honesty-only, not edge-finding. | Operator: this is expected and correct. Don't expect dashboard improvement; expect dashboard becoming more truthful. The path to better numbers is Phase-2/3 strategy-level work (mutation, slippage tightening, new edge), not killing artifacts. |

## Recommendation

Single operator action: trigger one fresh `Run Backtests & Deploy Dashboards` run after the merged batch (PR #182 + sibling Phase-5/6 PRs) settles. Then re-pull the two JSONs and confirm:

- `pf_registry.generated_utc > 2026-05-31T05:47:35Z`
- `pf_registry.by_asset_class_strategy_policy_clean_net | map(.top_strategy)` contains neither `cta_golden_cross_200` nor `prediction_market_consensus`.
- `money_ready_verdict.classes.COMMODITY.pf` is lower than the current 1.7241 (expected drop reflects removal of the PF=44 artifact's contribution).

No code change owed by Phase-7 itself. This is a verification-only doc.
