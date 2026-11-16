# GitHub Actions remediation — design + measured findings

**Generated:** 2026-11-15 21:10 EST · **Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Evidence base:** 9,438 completed runs across 360 registered workflows (30/run history), plus job-level
sampling on 37 at-risk workflows, plus 357 local workflow files parsed for triggers/timeouts/concurrency.
**Tooling:** `tools/gha_health.py` (committed alongside this document).

---

## 1. Why the obvious approach fails on this repo

The repo produces roughly **1,000 runs/day**. Any report shaped like "here are the failures" is
immediately wrong: in one 24-hour window, **190 workflows failed and then succeeded**. On its own,
a failure count is not a health metric here — it is a measure of how busy the commit bots were.

The historical "97–98% failure" alarm was also a misreading: those runs carried `jobs_executed = 0`,
meaning they were **concurrency-slot replacements that never started**, not code failures.

So every detector below is defined in **sequence context** and each one maps to a specific cost:

| # | Detector | What it actually costs | Rule |
|---|---|---|---|
| 1 | **BROKEN** | Silent data loss in a pipeline nobody is watching | last completed run failed AND no success after it |
| 2 | **NEVER PASSED** | The workflow has never done its job — often a false green | no `success` in sampled history |
| 3 | **CANCEL CHURN** | Runner minutes burned for zero output | cancelled/total > 50% |
| 4 | **QUEUE WAIT** | Saturation: work is ready but starved of runners | p90 (started − queued) > 60 min |
| 5 | **LONG RUN** | One workflow monopolises a runner slot; schedule becomes a lie | p90 runtime > 60 min |
| 6 | **STALE** | Dead weight that still shows up in every triage | active, zero runs in history, checked against its own `on:` |
| 7 | **ALWAYS-SKIPPED JOB** | A job that exists but can never execute | skipped in every sampled run |

Detector 6 and 7 are the two that generate the most false positives in ad-hoc audits, which is why
both read the **workflow's own definition** before asserting anything.

---

## 2. What the measurement actually found

### 2.1 BROKEN NOW — 3

| Workflow | Last completed | Age | Reading |
|---|---|---|---|
| `DB Secret Scan` | 2026-06-05 failure | 176 d | Dead. Never passed. Prune or fix in one line. |
| `ALPHA ENGINE - Dynamic Runner` | 2026-11-16 01:49 failure | 78 min | Live but never green in 30 runs; also 17/30 cancelled. Cron fix already merged (PR #814); this is a separate runtime defect. |
| `Mermaid Test Deploy` | 2026-11-14 failure | — | Branch-only workflow, absent from `main` and from every branch. Already pruned. |

### 2.2 CANCEL CHURN — 10 workflows, one of them total

| Workflow | Cancelled / sampled |
|---|---|
| **Branch Large File Duplicate Guard** | **30 / 30 (100%)** |
| Blacklist Reconciler (cross-check vs live systems) | 29 / 30 |
| rsi5070 Forward-Test Snapshot (Daily) | 29 / 30 |
| STOCKSUNIFY2 daily-stocks pull | 28 / 30 |
| Operator Review — Manual Candidates daily snapshot | 27 / 30 |
| Swarm Pick Review | 27 / 30 |
| Sign-Coherence Gate | 22 / 30 |
| Academic Strategies Daily | 20 / 30 |
| ALPHA ENGINE - Dynamic Runner | 17 / 30 |
| Edge stability refresh | 17 / 30 |

The guard is the worst case and it is **not** a concurrency bug: its job carries
`timeout-minutes: 15` while its own header comment says the scan takes **2–3 hours** across 213
branches. Every run dies at exactly 15:00. It had already been "fixed" once (2026-11-15,
`cancel-in-progress: false`) and still completed **zero** runs — which is why fixes must be
verified against the *next* run, not against the diff.

**Applied:** timeout 15 → 180 and the `push` trigger replaced with a weekly `schedule` + `dispatch`
(in a PR, revertible). See `FIX_branch_guard.md` in this folder.

### 2.3 QUEUE WAIT — 22 workflows starving behind the queue

| Workflow | p90 wait |
|---|---|
| Stale Branch Cleanup | **377 min** |
| Weekly score quartile spread | 291 min |
| HC Evaluator Parity Test | 270 min |
| Algorithm Competition Refresh | 241 min |
| [torontoevent.net] Algorithm Competition Refresh | 239 min |
| Backup Restore Verification | 234 min |
| Daily Prices yfinance Refresh | 229 min |
| H-002 PEAD Shadow Collector | 226 min |
| Verified pilot daily | 213 min |
| Edge stability refresh | 209 min |

A p90 wait of 6 hours means the schedule's promise is fiction: a job that must run daily is
executing in a queue slot it waited half a day for. This is the clearest evidence of **queue
saturation**, and it is not fixed by touching these eleven workflows — it is fixed by reducing
the runner-occupancy of the two workflows in §2.4.

### 2.4 LONG RUN — 6 workflows holding runner slots

| Workflow | p90 | max |
|---|---|---|
| Discord Bot — Persistent | **353 min** | 644 min |
| Unified Audit Dashboard | 125 min | 145 min |
| 2hour-challenge | 123 min | 133 min |
| ALPHA ENGINE - Dynamic Runner | 80 min | 87 min |
| DNA Strategy Pipeline | 74 min | 127 min |
| ALPHA ENGINE - Live Autonomous Scanner | 62 min | 75 min |

`Discord Bot — Persistent` alone occupies a hosted runner for ~6 hours per run and stacks duplicate
pending runs (it has no concurrency group). That is a **standing reservation of a runner**, not a
bug — it needs an owner decision, not an agent edit.

### 2.5 SKIPPED JOBS — one, and it is intentional

Workflow-level skip-dominated: **0**. Job-level, exactly one job is skipped in every sampled run:

```
ALPHA ENGINE - Dynamic Runner → job "wsl-direct"
   if: github.event.inputs.use_wsl_direct == 'true'
```

The `use_wsl_direct` input exists (line 39) and defaults off, so this job is a **manual escape
hatch**, not dead code. It does reserve a `windows-latest` runner (2× minutes) when triggered.
Verdict: intentional — do **not** delete. An earlier reading of "perpetually skipped = broken"
would have deleted a working manual path.

### 2.6 STALE — small, and mostly explainable

19 active workflows show no runs in API history. Reading their `on:` blocks separates them:
`_dynamic-runner-template.yml` is a reusable `workflow_call` template (never runs alone — correct),
several are `workflow_dispatch`-only commands (correct), and the remainder need per-workflow history
before deletion. Seven workflows are `disabled_manually` and **all seven are sports or
ai-tournament** — matching the owner's standing decision to disable sports betting. They are not
stale and must not be re-enabled.

---

## 3. Best practices that apply here (from GitHub's own docs)

These are the rules that decided the fixes above, each traced to its source.

**Concurrency**
- A concurrency group allows **at most one running** job/run at a time; a new arrival makes the
  existing **pending** one pending-then-cancelled. `cancel-in-progress: true` also kills the
  **running** one.
  → This is why the cron inversions (§PR #814) lost 43%/62% of their fires even with
  `cancel-in-progress: false`: the replacement target is the *pending* run.
- `queue: single` (default) holds **one** pending; `queue: max` holds **up to 100**.
  → `queue: max` is the correct tool when runtime slightly exceeds interval and you want **zero
  lost fires**. It is **not** appropriate for a 105-minute job on an hourly cron: the backlog then
  grows ~45 min/hour until 100 pending. Widening the interval is correct there; `queue: max` is
  correct for a job that merely needs headroom.
- `queue: max` + `cancel-in-progress: true` is a **validation error**.
- Group names are **case-insensitive** (`prod` == `Prod`). Pending order is FIFO by wait start.
- Up to **100 runs per concurrency group** with `queue: max`; beyond that, runs are rejected.

**Timeouts**
- Job `timeout-minutes` default is **360**; a runaway job can hold a hosted runner for 6 hours
  (hard cap 6h; self-hosted 5 days).
  → The guard's `timeout-minutes: 15` was the inverse error: far *under* the real runtime, so it
  was guaranteed to be killed. A timeout must be set **above** measured p99, not below it.

**Limits worth knowing before adding workflows**
- 500 KB per workflow file; 256 matrix jobs/run; 50 re-runs; 35-day run lifetime.
- 1,500 trigger events / 10 s / repo, and 500 queued runs / 10 s — reachable in a repo that commits
  every minute.
- `paths` filters are the cheapest queue reduction available for push-triggered workflows.

**Lifecycle**
- Disable (`state: disabled_manually`) rather than delete — reversible, and the workflow disappears
  from the Actions list only when its runs are purged too.
- A scheduled workflow fires from the **default branch only**; a fix sitting on a branch changes
  nothing. This is why every change here was PR'd *and merged*.

---

## 4. The approach: measure → classify → fix one thing → verify the next run

```
        ┌──────────────┐
        │ tools/       │  authenticated sweep, 7 detectors,
        │ gha_health.py│  refuses to report if >5% of histories were unreadable
        └──────┬───────┘
               │ JSON + Markdown
        ┌──────▼───────┐
        │ classify     │  each workflow in exactly one bucket; worst wins;
        │ (sequence)   │  recoveries suppressed so "green" ≠ "ignored"
        └──────┬───────┘
               │ ranked by cost: runner-minutes and data-staleness
        ┌──────▼───────┐
        │ fix ONE      │  branch → PR → YAML+cron parse check → merge
        │ thing        │  (a scheduled workflow only reads main)
        └──────┬───────┘
               │
        ┌──────▼───────┐
        │ verify the   │  read the cron back out of main, then confirm the NEXT
        │ next run     │  run's conclusion — a diff is not a fix
        └──────────────┘
```

**Non-negotiables that keep fixes from breaking things**

1. **Sequence context or nothing.** Never assert a workflow is dead from one run.
2. **Read `on:` before calling anything stale** — dispatch-only and reusable templates are correct.
3. **A cancelled run is not a failure**, and `jobs_executed = 0` means it never started.
4. **One change per PR, with the revert command in the body** and the pre-fix file committed.
5. **Never re-enable a `disabled_manually` workflow** without asking — disable is a decision.
6. **Verify by reading the value back out of the default branch**, then watch the next run.
7. **A timeout must exceed measured p99**; a timeout below runtime is a guaranteed kill.
8. **If the data is incomplete, say so.** A sweep that hit the rate limit and called 232 workflows
   "stale" is worse than no report (this actually happened during development; the tool now exits
   non-zero rather than emit it).

---

## 5. Ranked remediation plan

| # | Action | Expected effect | Risk | Status |
|---|---|---|---|---|
| 1 | `audit-dashboard` + `dynamic-alpha-engine` cron widening | recovers 43%/62% of lost fires | Low | **merged** (PR #814) |
| 2 | Branch Large File Guard: timeout 15→180, push→weekly | ends ~7.5 wasted runner-hours per 30 runs, gives the guard its first ever completed run | Low (revertible) | **PR open** |
| 3 | Owner decision: keep `Discord Bot — Persistent` reservation or stop it | frees the largest single runner occupancy (~6 h/run) | — | needs owner |
| 4 | Raise `timeout-minutes` on the remaining no-timeout workflows (77 files lack it anywhere) | bounds runaway jobs that could hold a runner for 6 h | Low | open |
| 5 | Investigate the 9 other cancel-churn workflows (Blacklist Reconciler, rsi5070, STOCKSUNIFY2, …) | each is burning runs for zero output | Low | open |
| 6 | Purge `DB Secret Scan` (dead 176 d, never passed) | removes a permanent red from every triage | Low | open |
| 7 | Re-run the sweep hourly via `tools/gha_health.py` and diff the buckets | turns this from an audit into a monitor | Low | open |

Items 3 and 5 need either an owner decision or a per-workflow read; nothing in this document was
applied to those without evidence.

---

## 6. Reproduction

```bash
export GHA_TOKEN=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill | grep '^password=' | cut -d= -f2-)
python tools/gha_health.py --repo eltonaguiar/findtorontoevents_antigravity.ca \
       --per-workflow 30 --job-sample 2 --out gha_health.json --md gha_health.md
```

The run needs ≈ (workflows × 1.15) API calls; at 359 workflows that is ~415 against a 5,000/hour
ceiling. The tool checks `/rate_limit` first, counts unreadable histories separately, and **exits 3
rather than emit a report built on 403s**.
