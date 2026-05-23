# ml_crypto_pred_v12 — Resurrection candidate (post-resolver-v2 verdict reverses kill)

**Date:** 2026-05-13
**Trigger:** Hidden-edge swarm B (cycle 2 report `reports/hidden_edge_scan_2026-05-13.md`) flagged ml_crypto_pred_v12 as silent 79.7d at PF 2.53. Cross-check exposed verdict contradiction.

## The contradiction

| Source | n | WR | PF | PnL_pct | Verdict |
|---|---|---|---|---|---|
| `audit_trail/quality_gates.py:1307` blacklist comment | 117 | 36.8% | **0.55** | -32% | KILL — blacklisted |
| `audit_dashboard/data/dashboard_data.json::systems[ml_crypto_pred_v12]` LIVE 2026-05-13 | 123 | 55.6% | **2.53** | +20.45% | **dead** (status flag — silent 79.7d) |

Last signal: 2026-02-22T13:38:39Z. **79.7 days silent.**

Same strategy, opposite verdicts. Live data shows it would clear Tier-2 (PF>1.5 AND WR>50). Blacklist holds the old PF 0.55 view.

## Hypothesis

Resolver-v2 (`outcome_resolver.py:115-126` `PNL_WIN_THRESHOLD_BY_CLASS` shipped 2026-04-28 per CLAUDE.md) re-resolved historical trades for non-CRYPTO classes at 5bp threshold (vs prior 1bp CRYPTO-only logic). For ml_crypto_pred_v12 specifically, that re-resolution flipped win/loss classifications and raised PF from 0.55 → 2.53.

The blacklist entry was added when the strategy ran at PF 0.55. **After resolver-v2 lifted the score, no one re-evaluated the blacklist.** The strategy was killed at the worst possible moment — right before the resolver fix would have exonerated it. Then no signals were emitted for 79.7 days, so the dashboard auto-flagged status=`dead`.

This is exactly the failure mode `feedback_mutate_before_kill.md` warns against (we killed before mutating) AND `feedback_diag_commits_can_break_prod.md` warns against (diagnostic fix changed downstream interpretation without back-cleaning).

## What this means for the broader system

The `audit_trail/quality_gates.py` blacklist may have **other strategies** in the same boat — killed when their PF was low under pre-v2 resolver math, but post-v2 they would meet Tier-2. Specifically the blacklist comments are frozen-in-time numbers.

**Recommended audit:** for each blacklisted strategy, cross-check current `systems[name]` PF/WR. Any strategy where live PF >= 1.5 AND WR >= 50 = blacklist-reversal candidate. Estimate: 6-12 strategies (anecdotal). If even 2-3 are true reversals, that's meaningful PF lift system-wide.

## Recommended actions (in order)

1. **DO NOT** unilaterally un-blacklist v12 here — peer manages `quality_gates.py` (commit `f7bd02da4c5` "exec-gate fix: copy_trader_bridge canonical BLACKLIST"). Coordinate first.

2. **Audit the full blacklist** in `quality_gates.py:BLACKLISTED_STRATEGIES` (~5 entries per peer's commit log). Cross-check each comment-cited PF against current `systems` block. Flag reversals.

3. **If v12 confirms as reversal:** restart its emission cron (find generator file in `alpha_engine/` — none found by direct grep, so emissions likely come from a parent ML generator tagging predictions with `ml_crypto_pred_v12` source-system label, OR the generator was deleted when blacklist was added). Validate generator exists before un-blacklisting.

4. **Add a daily check:** `tools/blacklist_reconciler.py` cron that compares every blacklisted strategy's blacklist-comment PF against live `systems` PF; flag any where live > 1.5 × blacklist threshold. Prevents this from happening to the NEXT blacklisted strategy.

## Acceptance bar for un-blacklisting

Per CLAUDE.md tier targets (T2 = PF>1.5 / WR>50 / MDD<20):
- v12 already meets PF (2.53), WR (55.6%) at n=123
- MDD unknown — live `systems` block doesn't expose `max_drawdown` for v12. Pull from `systems[ml_crypto_pred_v12].max_drawdown` OR re-compute from closed pick PnL series.
- If MDD <= 20% → APPROVE for un-blacklist + cron restart in shadow mode
- If MDD > 20% but < 30% → MUTATE per docs/MUTATION_THREE_AXIS_PROTOCOL.md before restart
- If MDD > 30% → keep blacklisted, document

## Effort + ETA

- Step 1 (this doc): DONE
- Step 2 (full blacklist audit): 1h
- Step 3 (validate generator exists): 30min
- Step 4 (`blacklist_reconciler.py` daily cron): 2h
- Total: ~3.5h to close the loop

## Memory candidate

"**Blacklist staleness — resolver-v2 silently exonerates blacklisted strategies.**" Same root pattern as `feedback_diag_commits_can_break_prod.md`: a downstream fix (resolver-v2) reclassified historical trades but the upstream policy (blacklist) wasn't re-validated. Generalizes the same issue: any time a metric definition changes, every threshold that depends on that metric is now stale and needs explicit re-validation. Suggested filename: `memory/feedback_metric_definition_change_invalidates_thresholds.md`.

Tie-in: this is the THIRD pattern this session of "disclosure ≠ enforcement" / "stale policy lingers" — joins:
1. `feedback_disclosure_is_not_enforcement.md` (PCG-5 motivation)
2. `feedback_gate_at_execution_not_generation.md` (existing)
3. (new) `feedback_metric_definition_change_invalidates_thresholds.md`

Three closely-related root causes, worth a shared umbrella memory entry.
