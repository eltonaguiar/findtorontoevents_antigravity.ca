# ALPHA ENGINE 354k-Line Deletion Mystery — Root Cause Found

**Date:** 2026-04-17
**Author:** Claude Opus 4.7 (autonomous overnight)
**Severity:** MEDIUM (data loss, not crash)

## Symptom

Every ALPHA ENGINE Dynamic Runner commit deletes ~325k lines net:
```
[main e31e9d5] ALPHA ENGINE [2026-04-17 03:56 UTC] [skip ci]
 25 files changed, 21470 insertions(+), 354220 deletions(-)
```

This pattern repeats every ~1-2 hours across all ALPHA ENGINE workflow runs.

## Root cause (verified)

Compared `strategy_performance.json` before/after one of these commits (`bc68498137`):

| Snapshot | Strategies | Lines |
|---|---|---|
| Before (parent) | 161 | 12,477 |
| After | 50 | 4,507 |
| **Dropped** | **111** | **~8,000** |
| Added | 1 | — |

The 111 dropped strategies all have `closed_picks=1` and look like one-shot ML enhanced variants:

```
ml_enhanced_AAVEUSDT_1d_D_ensemble_stack    closed=1  WR=0%    pnl=-1.58%
ml_enhanced_AAVEUSDT_1h_D_ensemble_stack    closed=1  WR=0%    pnl=-1.47%
ml_enhanced_ADAUSDT_1d_A_xgboost            closed=1  WR=100%  pnl=+6.99%
…
```

These were aggregated in PRIOR runs but the current scan **doesn't preserve them** — it generates a fresh `strategy_performance.json` containing only the strategies it scanned this cycle (~50).

## Impact

1. **Lost historical performance data** — 111 strategies' WR/PF/PnL aggregates are deleted on every run
2. **Trend tracking broken** — can't see WR drift on strategies not in current scan window
3. **Dashboard inconsistency** — `picks.recent_closed` (3,500 picks) references strategies that don't appear in `strategy_performance.json`'s 50-row summary
4. **Git churn** — 354k line deletions on every commit pollutes the diff history and makes blame/bisect harder

## Fix recommendation

The dump function for `strategy_performance.json` should:

```python
# BEFORE (bug):
with open(path, 'w') as f:
    json.dump(current_run_strategies, f)

# AFTER (fix):
existing = {}
if path.exists():
    with open(path) as f:
        existing = json.load(f)
existing.update(current_run_strategies)  # merge, preserving history
with open(path, 'w') as f:
    json.dump(existing, f)
```

OR add a `last_seen` field and prune entries older than X days, instead of dropping
on every run.

## Locating the bug

Likely in one of:
- `alpha_engine/production_scanner.py` (writes premium_signals.json + strategy_performance.json)
- `alpha_engine/strategy_performance_tracker.py` (if exists)
- A `_save_strategy_performance` helper

Search: `grep -rn "strategy_performance.json" alpha_engine/`

## Why I didn't fix this myself

1. Production scanner is currently being modified by multiple concurrent agents
2. The fix needs careful integration with existing pruning policies (some entries
   may be intentionally dropped after N days of inactivity)
3. The audit dashboard GHA workflow is in a fragile concurrency state right now
   (queue churn from rapid pushes — see todo list)
4. CLAUDE.md rule: "Do not expand BLOCKED_SOURCE_SYSTEMS without
   STRATEGY_INVESTIGATION_BEFORE_KILL.md and MUTATION_THREE_AXIS_PROTOCOL.md."
   This isn't a kill but it touches similar trust-tracking code paths.

Better to ship as a focused PR after the queue clears.

## Action item

**Add to roadmap:** "ALPHA ENGINE: persist historical strategy_performance entries
across scan runs (merge instead of overwrite)."
