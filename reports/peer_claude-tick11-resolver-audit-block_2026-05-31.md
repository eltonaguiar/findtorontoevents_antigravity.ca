# Tick 11 — Resolver + Audit Hourly Block Diagnosis (2026-05-31 ~08:25Z)

## TL;DR

**Not a concurrency-group lock. Runner-capacity backlog.** The two stuck
hourlies (`Outcome Resolver`, `Audit Hourly Update`) and the original
`Run Backtests & Deploy Dashboards` (`26706712727`) are queued on
GitHub-hosted runner capacity, which is currently saturated at the
account cap (**30 in-progress + 30 queued, 1:1 ratio**).

`next_action = wait-for-natural` is preferred. No stuck in-progress run
holds either concurrency group, so cancelling will not help unless we
want to free a slot for a higher-priority job.

## Evidence

### 1. Queued hourlies (oldest blocking newer)
| Workflow | Run ID | Created | Age @ 08:25Z |
|---|---|---|---|
| Outcome Resolver (oldest) | `26706652688` | 07:34:48Z | ~50 min |
| Audit Hourly Update (oldest) | `26706665803` | 07:35:27Z | ~50 min |
| Outcome Resolver (newer, pending) | `26707555405` | 08:20:34Z | ~5 min |
| Audit Hourly Update (newer, pending) | `26707555853` | 08:20:35Z | ~5 min |
| Run Backtests & Deploy Dashboards | `26706712727` | 07:37:51Z | ~47 min |

The 08:20 "pending" runs cannot start until the 07:34/07:35 runs of the
same workflow finish, because both workflows declare
`cancel-in-progress: false`. That part IS a concurrency-group queue, but
the *root cause* of why the 07:34/07:35 runs haven't started yet is
runner capacity, not the group.

### 2. Concurrency-group inspection (negative result)
```
.github/workflows/outcome-resolver.yml:
  concurrency:
    group: outcome-resolver
    cancel-in-progress: false

.github/workflows/audit-hourly-update.yml:
  concurrency:
    group: auto-commit-main-audit-hourly-update
    cancel-in-progress: false

.github/workflows/backtest-and-deploy.yml:
  concurrency:
    group: auto-commit-main-${{ github.workflow }}
    cancel-in-progress: false
```
`gh api .../runs?status=in_progress` shows **zero** in-progress runs
matching workflow names "Outcome Resolver", "Audit Hourly Update", or
"Run Backtests & Deploy Dashboards". So no older sibling is holding the
group key — the queued runs are first in their own concurrency lane.

### 3. Runner-pool saturation (the real blocker)
- In-progress: **30**
- Queued: **30**
- All three target workflows declare `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`. With no self-hosted runner registered, they fall back to ubuntu-latest and compete with everyone else.
- Major in-progress consumers right now: ~12 `Branch Large File Duplicate Guard` runs (one per docs-push in the last 45 min), 2 ALPHA ENGINE scanners, QUAN ENGINE scanner, Multi-Asset Copytrader v2, ML Model Auto-Training, several "Deploy Competition" + Mirror jobs, and `Baby Strat Real Forward Monitor`.

### 4. Trigger validity
Both workflows have `workflow_dispatch`:
```
on:
  schedule:
    - cron: '15 */1 * * *'        # outcome-resolver
    - cron: "20 * * * *"          # audit-hourly-update
  workflow_dispatch:
```
So the retrigger was **valid** (not a silent no-op). The dispatched run
just got placed at the back of the runner queue along with everything
else.

### 5. Backtests `26706712727`
```
{"status":"queued","conclusion":"","createdAt":"2026-05-31T07:37:51Z","startedAt":"2026-05-31T07:37:51Z",
 "workflowName":"Run Backtests & Deploy Dashboards"}
```
~47 min queued. Same runner-capacity cause. Not a stuck in-progress run.

## Why this doesn't match the "concurrency lock" hypothesis

The hypothesis was: a stuck >2h in-progress run holds the same group key
and pins the queued one. Refuted by item 2 (no matching in-progress)
plus the symptom matching runner saturation (1:1 in-progress:queued
ratio, lots of short-lived docs-CI jobs eating slots).

## Recommended action

**`wait-for-natural`** for the next ~10-20 min, watching the
`Branch Large File Duplicate Guard` and ALPHA/QUAN scanners drain. Once
in-progress drops below 20, the 07:34/07:35 hourlies will pick up
automatically.

Optional accelerants (only if user wants the resolver to land faster):
1. Cancel the 8 oldest in-progress `Branch Large File Duplicate Guard`
   runs — they're triggered by docs-only branches and don't gate any
   production path. Frees ~8 slots, lets the 07:34 resolver start
   within seconds.
2. Do **not** cancel the queued 07:34 resolver / 07:35 hourly to
   retrigger — that loses queue position and re-queues at the back.
3. Long-term: register a self-hosted runner and set
   `vars.ACTIONS_RUNNER_LABEL` to it, so the resolver + hourly +
   backtests can bypass the 30-slot free-tier cap.

## Verdict line

`BLOCKER:concurrency_lock=false:stuck_in_progress_to_cancel=none:retrigger_validity=dispatchable:next_action=wait-for-natural`
