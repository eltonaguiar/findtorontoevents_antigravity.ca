# GHA Best Practices — Research Findings and Engagement

**Date:** 2026-11-16
**Sources:** GitHub Actions official docs (docs.github.com/en/actions) — Reuse workflows, Control concurrency, Limits, Actions overview.

## 1. Concurrency

**Official recommendation:**
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
- Group name is **case-insensitive**; `prod` == `Prod`.
- Group must be **unique across workflows** or it cancels other workflows' runs. Always include `github.workflow`.
- `cancel-in-progress` accepts an **expression** — e.g. skip cancellation on release branches:
  `cancel-in-progress: ${{ !contains(github.ref, 'release/') }}`
- **New option `queue`:** `single` (default, 1 pending) or `max` (up to 100 pending per group). `queue: max` cannot combine with `cancel-in-progress: true`.
- FIFO by time each run started waiting, not by dispatch time.

**Repo status:** Applied to 9 high-frequency cron workflows + 3 push-only workflows. ~191 workflows still lack a group. **Priority: add groups to all hourly/30-min cron workflows next** (they are the queue-stackers).

## 2. Timeouts

- GitHub-hosted job hard cap: **6 hours** (default 360 min).
- Recommended: 15–30 min most jobs, ≤60 min heavy. A stuck job occupies a runner for 6h otherwise.
- **Repo status:** 7 high-frequency scheduled workflows now have `timeout-minutes`. ~88 workflows still lack it. `academic-strategies-daily.yml` uses 25 min and is being killed by it — raise to 45–60 min.

## 3. Reusable workflows

- `on: workflow_call` + `jobs.<id>.uses: $/.github/workflows/{file}` (same-repo, running-commit reference).
- Max **10 levels** of nesting; no loops.
- `secrets: inherit` passes all secrets; otherwise pass by name.
- `cache-mode: read|write|write-only|none` controls cache access propagation.
- **500 KB workflow-file cap** — move shared logic into reusable workflows or composite actions.
- **Repo status:** Many scanner workflows share checkout → setup-python → pip → run → commit steps. A reusable `gha-scan-job.yml` (checkout+setup+push) would cut duplication and file size. **Not yet built** — document as a follow-up; do not mass-refactor without a canary.

## 4. Stale branch cleanup

- Already covered: `.github/workflows/stale-branch-cleanup.yml` — weekly Mon 06:31 UTC, `dry_run` default **true**, 45-day threshold, skips protected/reserved names and branches with open PRs, handles unrelated histories (gh-pages). **No change needed.**

## 5. Queue & skip monitoring (Phase 3) — IMPLEMENTED

New `tools/gha_queue_audit.py` + `.github/workflows/gha-queue-audit.yml`:
- Runs every 4 hours (`17 */4 * * *`), staggered from the failure guardian.
- Surfaces: queued/pending >30 min, in_progress >90 min, per-workflow p50/p90 duration, latest-failed-no-subsequent-success.
- Commits `reports/gha_queue_audit.json` with `[skip ci]`.

## 6. Limits to watch (per GitHub docs)

| Limit | Threshold | Note |
|-------|-----------|------|
| Job execution | 6 h | hard cap |
| Workflow run | 35 days | includes waiting/approval |
| Workflow file | 500 KB | must move logic out |
| Trigger events | 1500 / 10s / repo | storm-commit risk |
| Workflow runs queued | 500 / 10s | |
| Concurrency queue | 100 / group | with `queue: max` |
| Re-runs | 50 / run | |
| GITHUB_TOKEN | 1000 req/h/repo | guardian uses it |
| Free concurrent jobs | 20 | Pro 40, Team 60 |
| Cache storage | 10 GB / repo | |

**Repo risk:** ~4000 runs/day against a 20-job (Free) or 40-job (Pro) cap. Queue depth monitoring (above) is the mitigation.

## 7. Remaining action items

1. Add concurrency groups to remaining ~191 workflows — prioritize cron frequency.
2. Add `timeout-minutes` to remaining ~88 workflows.
3. Raise `academic-strategies-daily.yml` timeout 25 → 45 min (currently being killed).
4. Consider reusable `gha-scan-job.yml` after a canary workflow proves it.
5. Phantom queued runs (51) still need GitHub Support / classic PAT.
6. QA Market Validation 5 secrets still need GitHub UI.
