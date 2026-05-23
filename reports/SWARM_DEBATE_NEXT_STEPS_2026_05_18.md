# Swarm Debate — Next Steps — 2026-05-18

3-agent / 3-round debate (edge-realist, pipeline-engineer, risk-strategist) on
what to do next given: no asset class money-ready, 9 edge-stability-harness
kills, ~5-8% odds of HF-grade edge, partial resolution pipeline
(CRYPTO 65% / EQUITY 45% / FOREX 22% / FUTURES 8.7% / ETF 33%), 3 untested
opt-in research sidecars (ET-1 H-026 / CO-1 H-027 / E-1 H-028).

## Outcome — all 3 agents RATIFIED a unified 9-step plan

Causal order. Steps 1-4 are safe-autonomous and land in parallel; steps 5-9
are operator-gated. Hard gate: the resolution-coverage panel must show **≥80%
per-class** resolution before step 8 re-derives any verdict.

| # | Step | Gate |
|---|------|------|
| 1 | Cover the orphan FUTURES source (8.7% resolution) | safe-auto* |
| 2 | Kill scanner fail-open (min_expected_picks floor + fail-closed) | safe-auto |
| 3 | Enforce the 2 monotone-conservative shadow gates (MDD_GATE_ENFORCE, ML_ENHANCED_CRYPTO_QUARANTINE) + tiered label NOT_READY/WATCH/CANDIDATE/READY with a <80%-coverage auto-cap-at-WATCH; demotion agent-doable, promotion operator-gated | safe-auto |
| 4 | Resolution-coverage dashboard panel (per-class resolved %, unresolved-by-reason) — the instrument for the ≥80% gate | safe-auto |
| 5 | Symbol-format DB backfill UPDATE (~2,086 rows) — write-time fix is prospective-only so backfill is mandatory | operator-gated |
| 6 | Re-resolve pass over backfilled + newly-sourced rows | operator-gated |
| 7 | Flip `active_picks_sync --apply` | operator-gated |
| 8 | Re-derive ALL verdicts: edge audit per class, re-litigate the 9 prior kills made under <50% resolution, recompute tiered label. ET-1/CO-1/E-1 stay FROZEN until here | operator-gated |
| 9 | Operator strategic-fork decision memo — authored only after step 8 | operator-gated |

## Step-1 viability correction (orchestrator pre-step-1 check — FAILED as framed)

All 3 R3 agents demanded the same pre-step-1 check: *verify the exact source
string `alpha_engine_unified` and that a JSON pick file backs it.* That check
was run and **failed**:

- `SYSTEM_SOURCES` in `audit_trail/universal_pick_resolver.py:86-234` maps a
  system name → a **JSON pick file** path.
- No Python file references `alpha_engine_unified`. No `*unified*` pick JSON
  exists in any `data/` dir (only backtest-results / trader-research /
  strategy-catalog files).
- The ~2,355 orphan FUTURES rows tagged `alpha_engine_unified` in
  `at_raw_picks` are written **MySQL-direct** (no JSON file), so they can
  never be added to `SYSTEM_SOURCES`.

**Conclusion:** step 1 as worded ("add to SYSTEM_SOURCES") is a near-miss — it
would "fix nothing" (exactly the risk-strategist's flagged failure mode). The
real coverage fix for the FUTURES orphans is the **MySQL-native
`active_picks_sync`** covering all sources — which is step 7 (operator-gated),
and is what `RESOLUTION_PIPELINE_FIX_PLAN_2026-05-18.md` Defect 2 already
recommends as primary. **Step 1 is therefore reclassified: it folds into step
7, not a standalone safe-auto action.** A live-DB query of the literal
`source_system` value on those rows is still required before step 5/7.

## R3 ratification + the 3 surfaced residual risks

All three: **RATIFY**. Residual risks the plan does NOT fully address:

1. **Survivorship bias is not undone by a coverage fix** (edge-realist). The 9
   prior kills already removed strategies; step 8 re-litigates on a ledger
   whose population was shaped under bad data. Clearing 80% coverage does not
   restore the missing counterfactual rows of killed strategies.
2. **No rollback path for steps 5-7** (pipeline-engineer). DB backfill UPDATE →
   re-resolve → sync `--apply` mutate production state in sequence with no
   snapshot/restore. If the re-resolve mislabels at scale there is only a
   forward fix. **Mitigation to add: a backup table + snapshot before step 5.**
3. **No fallback if coverage never reaches 80% for a class** (risk-strategist).
   The plan assumes backfill+re-resolve lifts every class past 80%. If FOREX
   (currently 22%) still lands below 80%, step-8 verdicts for it stall with no
   escalation path. **Mitigation to add: a per-class deep-dive trigger
   (CLAUDE.md deep-dive process) when a class stays <80% post-fix.**

## Non-negotiable splits (agent-doable vs operator-only)

- **Agent-doable:** steps 2-4; label *demotion*; staging + dry-run row-counts
  for steps 5-7.
- **Operator-only:** the DB backfill UPDATE, the re-resolve pass, the
  `active_picks_sync --apply` flip (irreversible live-ledger mutation); label
  *promotion* WATCH→CANDIDATE→READY; the strategic-fork decision itself.

## Recommended immediate action

Steps 2 and 4 are clean safe-autonomous wins. Step 3 is safe-autonomous but
redesigns the MONEY_READY label — it overlaps the operator's pending
"shadow-gate enforcement" decision, so it should be operator-confirmed before
shipping (enforcement only ever downgrades, but the label-schema change is a
product change). Step 1 is void as framed — see correction above.

*Method: 3 parallel general-purpose subagents × 3 rounds. No production code
edited by the debate itself. Sidecar E-1 (H-028) built same session, commit
685a4a1063d.*
