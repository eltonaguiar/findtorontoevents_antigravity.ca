# wf_audit_signals — pipeline starvation investigation

**Date:** 2026-05-03
**Salvaged from:** PR #681 (closed — see PR comment for rationale)
**Scope:** single-finding investigation note. The wider `strategy-decay-diagnostic-and-fixes.md` doc from #681 is NOT carried over (the KILL/REDUCE recommendations were based on contaminated data per the resolver flat-close bug — see `feedback_noncrypto_resolver_live_close_bug`).

## Finding

`wf_audit_signals` strategy has emitted **zero picks for 152 hours** (last emission ≈ 2026-04-26T08:40Z, observed 2026-05-02).

| Metric | Value |
|---|---|
| Last pick timestamp | ≈ 2026-04-26T08:40Z |
| Quiet period | ~152 hours (~6.3 days) |
| Severity | MEDIUM — investigate, do not auto-kill |

## Six possible root causes (rank by likelihood)

1. **Cron / scheduler stopped firing** — most likely. Check `.github/workflows/` and any local schedulers for `walkforward_validator` invocations.
2. **All candidates failing validation gate** — strategy is running but every candidate fails the new tighter gates (post-2026-04-20 trust-tier correction). Check validator log for "rejected" lines.
3. **Demoted via decay-tracker** — silent demotion to BLOCKED list. Check `BLOCKED_SOURCE_SYSTEMS` and `BLOCKED_STRATEGY_SYMBOL_PAIRS`.
4. **Data pipeline gap** — upstream walkforward results not generating. Check `backtest_results/walk_forward_results.json` mtime.
5. **Moved to incubator** — explicitly demoted. Check `incubator/` for the strategy ID.
6. **Validator script broken** — silent exception swallowed by bare `except`. Check pipeline logs.

## Reproducible health-check commands

```bash
python -m audit_trail.walkforward_validator --check-health
grep -i "walkforward\|wf_audit" audit_trail/dashboard_generator.log | tail -40
ls -la backtest_results/walk_forward_results.json
git log --since="6 days ago" -- audit_trail/walkforward_validator.py
```

## Decision rule (do NOT auto-kill)

- If quiet period < 7 days AND root cause identified as #1/#3/#5 (transient): document and monitor.
- If quiet period > 7 days AND no candidate-failure logs: rebuild from `walkforward_optimizer.py` per CLAUDE.md mutate-before-kill rule.
- Do NOT add to `BLOCKED_SOURCE_SYSTEMS` until `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` walkthrough completes.

## Wire-up

None — investigation note only. No code touched.

## Why this is the only piece salvaged from #681

PR #681 bundled this finding with a "decay guard" module and 11-strategy KILL/REDUCE list. The guard module had:
- wrong-data-file bug (`closed_picks.json` returned 0 hits for 7/12 named strategies)
- falsy-zero bugs at `:128`, `:157`, `:170`
- misclassified profitable strategies (e.g., MomentumEMA WR 62.8% +$44 PnL → "reduce 25%")
- no production caller in `smart_picks_engine.py` (Wire-Up Rule violation)

This single finding, separated from the broken guard, is real and worth documenting. PR #681 closed; investigation tracked here.
