# Peer Report: Poll Stuck Workflow — Run-Backtests 26706712727

**Date:** 2026-05-31T08:07Z
**Agent:** peer-claude (poll-stuck-workflow)
**Mode:** READ-ONLY

## Finding

Workflow run **26706712727** (Run-Backtests) is **STILL QUEUED** ~30 minutes after creation. No progress beyond `queued`.

| Field | Value |
|---|---|
| status | `queued` |
| conclusion | `""` (none) |
| startedAt | 2026-05-31T07:37:51Z |
| updatedAt | 2026-05-31T07:49:36Z |
| poll time | 2026-05-31T08:07:07Z |
| elapsed queued | ~29 minutes |
| job (`backtest`) status | `queued` (since 07:46:35Z) |
| steps | `[]` (runner never picked it up) |

Expected ETA was 20 minutes. Run has now exceeded ETA by ~10 minutes without leaving the queue.

## Live db_health.json (production)

```json
{
  "gen": null,
  "any_red": false,
  "passed": 5,
  "failed": 0
}
```

`gen` is `null` — the published JSON does not carry a generation timestamp at the top level. `any_red=false` and `passed=5/failed=0` are consistent with peer's PR #210 fix holding on whatever snapshot is currently live. Since the workflow has not started, **no fresh publish is possible from this run**.

## Diagnosis

This is **not a workflow failure** — it is a **runner starvation / queue-depth issue**. The job never transitioned to `in_progress`, so no steps ran and no logs exist to extract. Common causes (cannot confirm without admin):

1. Hosted-runner minutes quota throttled for the org.
2. Self-hosted runner offline (if this workflow is pinned to one).
3. Concurrency group blocking on a prior in-flight run.
4. GitHub Actions incident (queues elevated org-wide).

## Recommendation

- **Do NOT auto-retry / cancel.** Operator approval required per task rules.
- Operator action items (manual):
  - Check `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26706712727` for a queue-position banner.
  - Check `gh api /repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runners` for runner availability.
  - Check `https://www.githubstatus.com/` for Actions incidents.
- If queue does not drain within another 30 min, cancel + requeue is a valid operator-approved next step.

## Result Line

`POLL:state=queued:fresh_db_health=false:any_red=false`
