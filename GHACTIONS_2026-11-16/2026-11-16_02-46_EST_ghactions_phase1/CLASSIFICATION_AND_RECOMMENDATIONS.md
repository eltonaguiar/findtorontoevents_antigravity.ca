# GHA Phase 1 — Classification & Recommendations (2026-11-16 02:47Z)

## Scope / evidence
- Repo: `eltonaguiar/findtorontoevents_antigravity.ca` (main)
- Live snapshot: 360 workflows (API), 51 queued ghost runs, recent main-run sample (180), local `.github/workflows/*` inspected.
- Artifacts: `workflow_inventory.json`, `queued_runs.json`, `recent_main_runs_sample.json`, `INVENTORY_SUMMARY.md` (this folder).
- Prior mitigations on `origin/main`: `3eede133e01` added event guards to `.github/workflows/ml-gatekeeper-ab-bootstrap.yml.disabled` and `.github/workflows/mysql-q001-sync.yml.disabled` (no `/audit` pipeline impact).

## 1) Failed without subsequent success (latest-run)
| Item | Evidence | Status | Action |
|---|---|---|---|
| `.github/workflows/ml-gatekeeper-ab-bootstrap.yml` push run [43788940508](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43788940508) | push, main, `completed/failure`, **0 jobs**, no logs; workflow not active on main (`.disabled`, `on: {}` + guard) | Mitigated on main; orphan/0-job startup record | No rerun. Monitor for recurrence; if new 0-job pushes appear, inspect UI startup diagnostics / workflow registration. |
| `.github/workflows/mysql-q001-sync.yml` push run [43788941580](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43788941580) | same pattern; `.disabled` on main with `on: {}` + guard | Mitigated on main | Same as above. |

> Inventory script reported `fail 0` by API workflow-name matching; raw run sample shows the two path-named failures above — treat them as resolved-by-disable/guard unless they recur.

## 2) Queue blockers (ghost queue)
- **51 queued** runs (oldest `2026-08-07T09:09:20Z`, newest in sample `2026-11-11T20:43:24Z`), duplicates across scanner families.
- **CLI/API:** `gh run cancel` → `Cannot cancel a workflow run that is completed`; REST cancel → `409 Cannot cancel a workflow run that has not been queued yet`.
- **Conclusion:** ghost/inconsistent state; **not removable via CLI/API**.
- **Manual action:** Actions UI (logged-in) `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions?query=is%3Aqueued` attempt cancel/remove; if persistent, escalate to GitHub Support with run IDs (sample: 31164696055, 32203529158, 43097722505, 37655537671).

## 3) In-progress / cancelled / skipped signals
- In-progress runs at snapshot were recent scheduled jobs progressing normally; `Discord Bot  Persistent` (43745604081) in designed 5h50m step — **expected**, not a hang.
- `GHCOPILOT prospective paper monitor`: prior cancelled instance observed, later run completed success (isolated; workflow has `concurrency: ghcopilot-paper-monitor`, `cancel-in-progress: false`, 20m timeout). **Monitor only** unless cancels recur.

## 4) Stale / not-run-recently (active, >7d or absent in 180-run main sample): 235 workflows
### Evidence-based classification (subagent review of requested 35 + inventory heuristics)
| Class | Examples/evidence | Interpretation |
|---|---|---|
| **LIKELY_OK — manual/dispatch-only or reusable/draft** | `AI Leaderboard Refresh` (dispatch, superseded by freshness), `Battleground Mass Backtest*` (dispatch), `_dynamic-runner-template.yml` (`workflow_call`), `bt_backtest_trades...draft`, `Branch Large File Duplicate Guard` (push on non-main branches only) | Zero main-branch runs expected. |
| **LIKELY_OK — monthly/weekly cadence** | `Backup Restore Verification` (15th), `Beta Portfolio Refresh` (1st), weekly validators/refreshes | May be absent in finite sample. |
| **LIKELY_OK — scheduled but sample/runner/UI factors possible** | Daily/4h/6h cron workflows with valid YAML triggers (e.g. adaptive trust tuner, ETF emitter, trend catcher, daily picks, watchdogs, reporting) | YAML not broken; absence may reflect UI-disabled state, runner label/availability (`vars.ACTIONS_RUNNER_LABEL`), or sampling window. **Operator check recommended** in Actions UI per workflow. |
| **NEEDS_CHECK (prioritize)** | Any scheduled trading/data pipeline whose business output is stale downstream, or active workflows disabled in UI but enabled in API state confusion | Verify: last run in UI, cron due, secrets/runner, path filters. |
| **BROKEN_SIGNAL** | None confirmed from YAML alone in reviewed set | Reclassify only with run/UI evidence. |

## 5) Hygiene/risk signals (repo-wide, from inventory)
- **Active missing `timeout-minutes` (local YAML match): 83** — risk of long runner occupancy/default 360m hangs.
- **Active missing `concurrency` (local YAML match): 191** — risk of queue stacking/cancel-cascade on frequent schedules.
- **360 workflows total** — workflow explosion; consolidate/disable/templatize where safe (phased, with dry-run/observe).

## 6) Safest high-impact fixes (phased)
### Phase 1 (done): inventory & classification
- Generated machine-readable inventory + summary in this folder.

### Phase 2 (recommended, low-risk first)
1. **Dead/one-time:** keep disabled (`on: {}` / `.disabled`) like mysql-q001/ml-gatekeeper; do not delete blindly.
2. **High-frequency scheduled workflows lacking guards:** add per-workflow `concurrency` and explicit `timeout-minutes` (start with hourly/30m/15m scanners) — *per-file review required*; avoid mass PR without testing.
3. **Path filters:** add to push/PR workflows that run on all changes (only where safe).
4. **Stale branch cleanup:** dry-run first.

### Phase 3 (monitoring)
- Harden `actions-failure-guardian.yml` (or add audit workflow) to report: latest-failed-no-subsequent-success, queued age/count, long-running p90, perpetual skips, non-main duplicate runs. Emit committed JSON/MD report.
- Proposed draft: `PROPOSED_HARDENED_GUARDIAN.yml` (this folder) — **not enabled**.

### Phase 4 (structural)
- Consolidate similar scanners via reusable workflows/orchestrator; delete runs of removed workflows after disable+observe.

## 7) Audit/dashboard impact
- No audit-dashboard pipeline files changed in this phase. Prior pushed guards were on **disabled** workflows, outside `audit-dashboard.yml` dependencies; **no expected impact** to `https://findtorontoevents.ca/audit/`. Any future changes to audit/dashboard-triggering workflows must be validated against audit freshness and deploy outputs.

## 8) Revert notes (for this phase)
- This phase created report files only under `GHACTIONS_2026-11-16/2026-11-16_02-46_EST_ghactions_phase1/`. Revert by removing that folder (and do not push if undesired). No workflow behavior changed.
