# GitHub Actions verification methodology — how we know the fleet is healthy

**Date:** 2026-11-16 · **Scope:** `eltonaguiar/findtorontoevents_antigravity.ca` (360 workflows, ~900 runs/day)

The question this answers: *"is everything working, and are duplicate or useless jobs stealing our
runs?"* — repeatably, without a human reading the Actions tab. Four layers, each with a different
cadence and a different failure mode it catches.

## Layer 1 — standing health report (automated, every 4h)

`.github/workflows/gha-health-audit.yml` (cron `37 */4 * * *`, `concurrency` serialized,
`cancel-in-progress: false`) runs `tools/gha_health_audit.py`, which implements rules **R1–R12** and
commits `GHACTIONS_LIVE/gha_health.json` + `GHACTIONS_LIVE/gha_health_summary.md`.

| Rule | Catches |
|---|---|
| R1 | latest run failed **and nothing succeeded after it** (the only real "broken" signal) |
| R2 | latest failed, next run not yet due → auto-watch the next 2 |
| R3 | flapping: ≥5 fails in last 15 with a green latest |
| R4 | phantom queue: `queued` >24h with 0 materialized jobs (uncancellable) |
| R5 | runner hogs: `in_progress` >2h or >2× p90 |
| R6 | cancel churn: ≥50% cancelled in last 15 at own tick spacing |
| R7 | mass-cancel clusters (cross-workflow, same timestamp) |
| R8 | perpetual skip: always-false `if:`, or >80% skipped on a live trigger |
| R9 | stale by cadence (30d daily / 60d weekly / 90d monthly; dispatch-only exempt) |
| R10 | non-main duplicate: branch-only workflow with a matching `push` trigger |
| R11 | fan-in amplification (`workflow_run` consumers per upstream) |
| R12 | output with no consumer (writes a file nothing reads) |

**Reading it:** `GHACTIONS_LIVE/gha_health_summary.md` is the dashboard. `counts` in the JSON gives
the one-line verdict (`broken_now`, `flapping`, `queue_hogs`, `stale_skipped_prune`,
`no_consumer_outputs`, `fan_in_chains`, `plain_green`). Green means: R1 empty or explained, R4 batch
not growing, R6/R7 zero.

Last verified run: `#43806327755` (04:48Z, success).

## Layer 2 — queue depth and guardrail census (on demand)

```bash
python3 tools/gha_queue_audit.py --pages 25
```
Answers "what is sitting in the queue", "what has been running for hours", "what is skipped every
time", "which workflow has no concurrency/timeout". Emits `reports/gha_queue_audit.{json,md}`.
Run it before and after any concurrency/timeout change.

## Layer 3 — non-main branch duplicates (weekly or after branch churn)

```bash
python3 tools/gha_nonmain_audit.py --pages 12 --compare
```
Emits `reports/gha_nonmain_audit.{json,md}`. The measured baseline on 2026-11-16:
1,200 runs scanned → **68 non-main**, across **213 branches**, **0 duplicate run groups, 0 duplicate
runs, 0 hazards**.

**Why the answer is structurally "no waste" — and where it can still bite:**

- `schedule` fires **only from the default branch**, so the ~370 branch copies of scheduled
  workflows cost **zero** runner minutes. Branch workflow trees are fork-lag, not a second fleet.
- `workflow_dispatch` also only exists on the default branch — branch dispatch jobs are unreachable
  by design, not broken.
- The **one** real per-push waste class is a branch-only workflow with a `push` trigger that matches
  its own branch, because GitHub runs the **pushed ref's** YAML. Live example: the guard workflow
  `branch-large-file-dup-guard.yml` is `push: branches-ignore: [main]`, so a branch carrying a stale
  copy (no timeout, `cancel-in-progress: true`) re-runs the pathological variant. Measured cost:
  7 runs / 198 runner-minutes, all cancelled, never green.
- Remedy is **never** to edit someone else's branch: land the fix on `main` and let the owner
  merge-back. Deleting branches is a separate, owner-approved hygiene task.

## Layer 4 — ad-hoc deep report (when something looks wrong)

```bash
python3 tools/gha_queue_and_failure_report.py     # needs reports/gha_run_matrix_*.json
```
Per-workflow runner-minutes, failure/cancel/skip ratios, post-fix verification of a specific run
(startup failures show 0 jobs and no log), and the cross-check table against other agents' reports.

## Decision rules (what counts as a real problem)

| Observation | Real problem? |
|---|---|
| `cancelled` on a scanner with `cancel-in-progress: true` | No — by design (pending-slot eviction) |
| `cancelled` with `cancel-in-progress: false` | **Yes** — external kill or push-wave stack-kill; investigate |
| `timed_out`/`cancelled` at exactly N minutes | Job `timeout-minutes` hit (GitHub reports timeouts as `cancelled`) |
| 0 jobs, no log, filename as workflow name | Startup failure — check the file exists at that commit |
| `queued` >24h, cancel → 409 | Phantom run — GitHub Support / admin-scoped token only |
| Branch-only scheduled workflow with no runs | Expected — schedules are default-branch only |
| Workflow disabled in the UI, still queued | Disabling does not drain the queue |
| `skipped` on `workflow_run` deploy | Path/conclusion gate — by design unless >80% |

## What "healthy" looks like (2026-11-16 baseline)

- R1: 0 unexplained (the 6 rows were ALPHA pre-#829, two orphan 0-job runs, and one stale-age artifact).
- R4: 21 phantom runs, stable since 2026-11-11, not growing.
- R6/R7: 0.
- Failures in an 8h window: 13, all accounted for (ALPHA ×4 → fixed by `safe_push.sh` #829; CI Tests
  → cron-assertion drift, fixed; Regime Terminal → step timeout, fixed; Feed Health → one short blip;
  two 0-job orphans → files renamed `.disabled`).
- Non-main: 0 duplicate groups, 0 hazards.
