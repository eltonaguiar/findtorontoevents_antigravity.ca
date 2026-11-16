# GitHub Actions: Safe-Fix Approach, Best Practices & Queue-Hog Playbook
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca` · **Date:** 2026-11-16 · **Author:** ghactions-v2 session

This doc designs a **safe** way to fix this repo's ~370-workflow Actions fleet without breaking
`findtorontoevents.ca/audit` or the trading pipelines, and gives **detection rules** for the exact
failure patterns you called out (failed-without-later-success, latest-failed-needs-monitoring,
non-main duplicates/stale, long-idle, queue hogs, perpetual skips, long runners).

---

## 1. Ground truth (measured, not assumed)

Static scan of **355** workflow files on `origin/main` (PyYAML parse, 0 parse errors):

| Signal | Count | Meaning |
|---|---|---|
| Workflows with **no job-level `timeout-minutes`** | **79** (~59 scheduled) | inherit **360-min** default → a hang occupies a runner for 6h (top queue-hog risk) |
| High-freq crons (`<=30 min`) | 3 | — |
| High-freq crons **without `concurrency`** | **2** (the torontoevent backtest pair) | can stack → **FIXED (PR #815 disabled the ROOCODE dup)** |
| `push:` triggers **without** `branches`/`paths` filter | **0** | good — no whole-fleet-on-push hazard (note: untracked local `lint.yml` was correctly kept out) |
| Jobs with `if: false` (always-skip) | **0** | good |
| Workflows with a `continue-on-error` step | 68 | *masks* failures — often intentional for optional data steps; audit case-by-case, do not bulk-change |
| Crons firing at minute **`:00`** | **41** | thundering herd on the runner pool |

Runtime check (last 500 runs, live API): 467 success / 17 in-progress / 7 failure / 5 cancelled /
4 pending. The failures were: my own transient `on: {}` spurious errors (fixed by peer rename to
`.disabled`, stopped 01:54Z) + ALPHA Dynamic Runner step-timeout (fixed). **No stale
"failed-without-later-success" workflow remains on main.**

## 2. GitHub Actions best-practice foundation (cited)
- **`timeout-minutes` defaults to 360 min** per job — set it explicitly on every job
  ([workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)).
- **`concurrency` + `cancel-in-progress`** prevents superseded runs stacking. Use
  `cancel-in-progress: false` for deploy/data jobs (never kill a half-written push); `true` only
  for supersedable checks.
- **Path/branch filters** (`paths`, `paths-ignore`, `branches`) stop irrelevant triggers.
- **Schedules fire only from the default branch** → branch-only workflow copies cost **zero**
  runtime (don't chase them).
- **`workflow_dispatch` only works from the default branch.**
- **Concurrency limits**: standard runners are limited account-wide (free ~20 concurrent jobs);
  heavy overlapping hourly crons starve each other. Stagger cron minutes (see §5).
- **Disable**, don't delete: rename `*.yml → *.yml.disabled` (reversible, matches repo pattern);
  delete only proven true-duplicates.
- **Reusable workflows** (`workflow_call`) collapse near-identical scanners into one definition.

## 3. Classification model — sequence context, not failure lists
Assign every workflow exactly one bucket. The distinguishing question is always **"what happened
*after* the failure?"**, not "did it fail?".

| Bucket | Rule | Action |
|---|---|---|
| **BROKEN** | latest *completed* run failed/timed-out/startup_failure **AND no success after it** | fix or disable. Severity ∝ cadence (hourly-broken-3h = 3 missed cycles). |
| **RECOVERED** | any success *after* the last failure | **not** an issue; count only. |
| **FLAPPING** | ≥5 fails in last 15 runs but currently green | watch; name failing **step**, split infra-flake vs real bug. |
| **NEEDS-MONITOR** | latest run failed, next run not yet due | watch the next scheduled/push run; don't "fix" a one-off. |
| **QUEUE HOG** | (a) `queued` run >1h with 0 materialized jobs = phantom/uncancellable; (b) `in_progress` >2h runner hog; (c) ≥50% cancelled/15 = cancel-loop; (d) no `timeout-minutes` on a long job | serialize / add timeout / escalate phantom batches to Support |
| **STALE** | trigger-aware: `workflow_dispatch`-only quiet = **by design**; daily silent 30d+, weekly 60d+, monthly 90d+ = dead trigger | prune or re-wire |
| **SKIPPED** | jobs permanently `skipped` inside green runs (dead `if:`), or `if: false` | delete the dead job / trigger |

## 4. Non-main branch rule
Workflow definitions on feature branches only matter if **`push`-triggered** (they run the pushed
ref's YAML). Schedule-only branch copies cost zero. So branch cleanup is about **stale-branch
noise + accidental push triggers**, not run cost. (Dedicated branch audit: see Subagent B results,
§8.)

## 5. Queue / runner-pool hygiene
1. **Stagger cron minutes.** 41 workflows fire at `:00`. Move each to a deterministic offset
   (e.g. `crc32(workflow_name) % 60` or hand-assign) to flatten the herd. The repo already does
   this for many (":19", ":52", ":47") — finish the job.
2. **Serialise same-family scanners** with a shared `concurrency.group` + `cancel-in-progress: false`.
3. **Bound every job** with `timeout-minutes` (see §6 backlog).
4. **Kill duplicate double-deploys** (this session: the torontoevent backtest pair → PR #815).

## 6. Backlog — 79 workflows with NO timeout (prioritised, safe rollout)
Do **not** mass-edit. Roll out in **canary waves**, one PR per wave, watching each wave's next run:
- **Wave 1 (lowest risk):** `*dispatch/push`-only workflows (short, manual): `deploy-movieshows*`,
  `deploy_bundle`, `fix-battleground`, `discord-token-selftest`, `masking-policy-lint`,
  `no-stale-db-passwords`, `pine-generator`, `test-fast`, `walkforward-gate`, `wsl-runner-manager`,
  `pick-flow-snapshot-fast`. Set `timeout-minutes: 30`.
- **Wave 2:** short scheduled snapshots: `hub-sync`, `signal-recorder`, `signal-integrator`,
  `send-accountability-reminders`, `qa-market-validation`, `daily-prices-yf-refresh`,
  `spy-data-refresh`, `live_tracker`, `refresh-*`, `cross-db-audit`, `ml-health-monitor`.
  Set `timeout-minutes: 30`.
- **Wave 3 (careful — may be long):** `backtest-and-deploy`, `genome-daily-pipeline`,
  `self_optimizing_trading`, `parquet-ingest`, `backfill`, `statistical_validation`,
  `walkforward-gate`. Set `timeout-minutes: 60` and verify p90 duration first from run history.
- **Never** set a timeout below a job's observed p95 or you create false reds.

> Why waves: a too-low timeout turns slow-but-fine jobs red (the exact failure mode we just fixed
> on ALPHA). Canary → observe → widen.

## 7. Fixing principles (do-no-harm)
1. **Disable → observe → archive/delete.** Never mass-delete.
2. **Build workflow edits against main's blob**, not a stale local file:
   `git show origin/main:.github/workflows/X.yml > /tmp/X.yml`, edit, `git diff origin/main -- X.yml`
   must show only the intended hunk. (This repo's local clones are shallow + advance every ~60s.)
3. **Never `git add .github/workflows/` wholesale** — resurrects deleted files / reverts live fixes.
4. **`on: {}` is INVALID** (causes "No event triggers defined in on" red on every push). Use
   **rename to `.yml.disabled`** — the correct GitHub convention. *(Lesson from this session: my
   PR #812 used `on: {}`, which a peer had to convert to `.disabled` in `3d1aa94ba5e`.)*
5. Prefer explicit error handling over `continue-on-error`/`|| true` that hides real bugs.
6. **Document + revert** every change: what broke, exact diff, downstream verdict, revert command,
   and the pre-change SHA.

## 8. Monitoring (make it continuous, not manual)
Extend `actions-failure-guardian.yml` (already 30-min) to emit a committed JSON/Markdown report with:
- **BROKEN**: latest conclusion ∈ {failure,timed_out,startup_failure} **and** no later success.
- **NEEDS-MONITOR**: latest failed, next due within cadence window.
- **QUEUE HOGS**: `queued`>60min w/ no jobs; `in_progress`>120min; cancel-ratio≥50%/15.
- **NO-TIMEOUT**: jobs lacking `timeout-minutes`.
- **SKIPPED**: jobs skipped in the last N green runs.
- **Cron histogram** to catch new `:00` pile-ups.

Rules are cheap (REST or browser). When the API is rate-limited, use the logged-in-browser
pipeline (`/tmp/kilo/gha_browser/scrape.py`) — but a bot PAT (as used this session) covers it.

## 9. What changed this session (already on main)
| PR | Change | Reversible via |
|---|---|---|
| #811 | finpredict emitter download hardening + ALPHA job timeout 60→90 | `git checkout origin/main -- …` |
| #812 | (superseded) disabled Q-001 + gatekeeper via `on:{}` → corrected by peer `3d1aa94ba5e` to `.disabled` | rename back |
| #813 | ALPHA **"Commit results" step** timeout 5→15m (real cause of red failures) | set back to 5 |
| #815 | disabled **duplicate ROOCODE** torontoevent backtest/deploy (true dup, FTP race) | rename back |

## 10. Reusable agent prompt
A hardened, ready-to-use job-analysis prompt already lives at
`GHACTIONS_2026-11-16/2026-11-15_21-45_EST_ghactions/AGENT_PROMPT_job_analysis.md`. Use it verbatim
for the next pass; this doc adds (a) the `on:{}`-is-invalid rule, (b) the timeout-wave rollout, and
(c) the measured backlog above.
