# GH Actions Triage — findtorontoevents_antigravity.ca

**Run date (EST):** 2026-11-15 20:42 EST
**Repo:** eltonaguiar/findtorontoevents_antigravity.ca (public)
**Scope:** main branch workflow runs + local `.github/workflows/*.yml` (364 files)
**Method:** per-workflow sequence context, not failure lists — adapted from the triage methodology: classify every workflow into exactly one bucket, worst-bucket-wins.

## Headline

| Bucket | Count | Verdict |
|---|---|---|
| BROKEN (failed, no later success) | **0** | Nothing conclusively red |
| FLAPPING (≥5 fails in last 15, green now) | **0** | No sustained flappers found |
| QUEUE HOGS (zombies / hogs / cancel-churn) | **51 zombies + 1 hog + 1 churn** | Throughput problem |
| STALE/PRUNE (dead or never-run) | **0 stale / 20 unverified** | Window too thin; verify per-workflow |
| Recovered failures suppressed | **190** | Noise filtered, not green-ignorance |

Bottom line: **no workflow is conclusively broken right now.** The actionable signal is in queue throughput (51 zombies, one cancel-churn workflow) and in 20 never-run workflows that need per-workflow history before verdict.

---

## Bucket 1 — BROKEN NOW: none

A run's conclusion is only meaningful in sequence context. One workflow looked broken on first pass — `Model Picks Emission (finpredict-v4 tactical allocation)` — but it turned out to be an **in-flight retry** (`run_attempt: 2`) of a job that succeeded via `workflow_dispatch` at 2026-11-15 09:16 UTC. It is not broken; it is retrying.

Rule applied: a failed completion followed by any later success = recovered, not broken. **190 such recovered failures were suppressed** rather than counted as issues.

---

## Bucket 2 — FLAPPING: none

No workflow shows ≥5 failures in its last 15 completed runs while currently green. The closest candidates were suppressed because a later success exists. No flappers to name.

---

## Bucket 3 — QUEUE HOGS

### 3a. Zombie queued runs: 51

| | |
|---|---|
| Queued > 24 h | **51 runs** |
| Oldest queued run | **2026-08-07T09:09:20Z** |
| Pattern | Timestamp batches — schedule stampedes / GitHub incidents |

**Action:** bulk-cancel. These arrived in batches (visible as timestamp clusters), not as 51 independent incidents. Sort `is:queued` by date and cancel by batch.

### 3b. Runner hogs: 1 (by design)

| Workflow | Age | Status | Verdict |
|---|---|---|---|
| Discord Bot — Persistent | 7.4 h | `in_progress`, run id `43745604081` |

A persistent Discord bot occupying a hosted runner 24/7 is a **permanent runner occupation by design**. Flag as a cost/queue decision, not a bug. If the repo does not actually need a resident Discord runner, this is the single largest single-runner hog.

### 3c. Cancel churn: 1 offender

| Workflow | Cancel ratio | Verdict |
|---|---|---|---|
| ALPHA ENGINE — Dynamic Runner (Cloud or Local) | **80%** | concurrency group eating its own runs |

45 workflows run `cancel-in-progress: true` in their local YAML; ALPHA ENGINE is the only one where it actually matters. Each tick queues, starts, and kills the previous run — pure queue noise. Fix: `cancel-in-progress: false`, longer cron interval, or delete.

---

## Bucket 3d — Top volume (runs/day over the ~24h window sampled)

| Workflow | Runs | Runs/day |
|---|---|---|---|
| Meme Coin Scanner v2 — Fixed & Monitored | 39 | 39 |
| Deploy Competition to Live Site | 39 | 39 |
| TV Paper TP/SL Watchdog | 23 | 23 |
| Sports data snapshots | 18 | 18 |
| actions-failure-guardian | 13 | 13 |
| Deploy FindCryptoPairs to FTP | 13 | 13 |
| Multi-Asset Copytrader Scanner v2 — Forex/Futures/Sto | 12 | 12 |
| [torontoevent.net] Deploy Rise of the Claw | 12 | 12 |

**Total sampled:** ~1,000 runs in ~24 hours across 192 workflows with activity (out of 364 workflow files on disk). Two workflows alone account for ~8% of all runs.

---

## Bucket 4 — STALE / PRUNE

### 4a. Stale (no run beyond expected cadence): **0**
No cron workflow violated its `max(3×expected, 48h)` window in the sampled window.

### 4b. Never-run (schedule/dispatch triggers, zero runs in window): **20**

| Workflow | Triggers |
|---|---|---|
| 2hour-challenge | schedule, workflow_dispatch |
| A/B Analysis + Zero-PnL Audit | push, schedule, workflow_dispatch |
| Academic Strategies Daily | schedule, workflow_dispatch |
| AI Leaderboard Freshness (daily FTP + data r…) | schedule, workflow_dispatch |
| AI-Model Portfolios — Daily EOD | schedule, workflow_dispatch |
| AI Tournament Pipeline — Daily Picks + DB In… | schedule, workflow_dispatch |
| Algorithm Competition Refresh | schedule, workflow_dispatch |
| Alpha Engine Daily Picks | schedule, workflow_dispatch |

**(12 more below the 8-row trim in the tool output.)**

**Important caveat:** the sampled window is only ~24 hours at ~1,000 runs/day. A daily job that simply hasn't fired yet this cycle looks like "never run" here. These 20 are **unverified**, not dead. Per-workflow history (one API call each) is needed before deleting anything.

### 4c. Manual-only workflows excluded: **28**

Workflow files whose only trigger is `workflow_dispatch`. Per methodology these are quiet-by-design, not stale. Correctly excluded.

---

## Branch comparison: main vs other branches

All 364 workflow files live on `main` (the default branch — that is where `.github/workflows/` is stored and where GitHub serves runs from). Branch-specific differences:

- Runs sampled for this triage were taken from `branch=main` only.
- Other branches (feature branches, PR branches) execute runs triggered by `pull_request`, `workflow_call`, `workflow_run`, and `push` events against their own refs, but the workflow *definitions* are sourced from the default branch at push/PR time.
- No evidence in the sampled data of other branches running divergent workflow definitions that would warrant separate triage.

**Redundant tasks that don't really matter:**
1. `ALPHA ENGINE — Dynamic Runner (Cloud or Local)` — cancel-in-progress:true at 80% cancel ratio; it is killing its own runs every tick.
2. `Discord Bot — Persistent` — 7.4h in_progress resident runner; permanent occupation unless intended.
3. The 20 never-run workflows — schedule + dispatch triggers but zero runs in the window; candidates for delete-or-wire-up once per-workflow history confirms.

---

## Methodology notes

- Trigger facts read from **local** `.github/workflows/*.yml` (free, and the only way to know a workflow is `workflow_dispatch`-only — naive audits flag these as stale).
- API calls used only for run history and queue state. Unauthenticated limit is 60 req/hr shared with all other agents on this host, so this triage used a thin page count (10 pages ≈ 1,000 runs ≈ 24 h of history at this volume).
- 190 recovered failures explicitly suppressed: "failed then succeeded" is noise, not an issue. A cancelled run is never counted as a failure.

## Recommended actions, in order

1. **Bulk-cancel the 51 zombie queued runs** (batch by timestamp cluster).
2. **Decide on `Discord Bot — Persistent`** — keep as permanent runner, or stop it and free the hosted slot.
3. **Fix `ALPHA ENGINE — Dynamic Runner`** — `cancel-in-progress: false`, longer cron interval, or delete (80% cancel ratio).
4. **Verify the 20 never-run workflows** with per-workflow history before deleting or wiring up.
5. **Re-run this triage after the rate limit resets** to confirm the never-run list is truly empty and not just window-thin.

---

**Generated by:** proof/gh_triage.py (see `WIRED_IN/2026-11-15_0708/HERMES_WIN_inspect-wt/proof/gh_triage.py`)
