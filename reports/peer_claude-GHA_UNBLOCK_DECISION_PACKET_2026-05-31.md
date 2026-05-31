# GHA Unblock — Operator Decision Packet (2026-05-31)

Autonomous loop hit floor at tick 12. 3 mutually-exclusive options compared with verbatim data.

## 1. Current GHA State (verbatim, 2026-05-31T08:30Z)

- **queued_total = 100** (cap of `--limit 100`; true count >=100)
- **in_progress_total = 39**

### Top queued workflows (group_by, sort_by(-count)):
```
[
  {"wf": "No stale DB passwords",            "count": 15, "oldest": "2026-05-31T07:50:21Z"},
  {"wf": "Secret Scan (M-043)",              "count": 15, "oldest": "2026-05-31T07:36:01Z"},
  {"wf": "Branch Large File Duplicate Guard","count": 12, "oldest": "2026-05-31T07:56:03Z"},
  {"wf": "Conflict Marker Check",            "count": 11, "oldest": "2026-05-31T07:56:15Z"},
  {"wf": "CI Tests",                         "count": 3,  "oldest": "2026-05-31T07:39:56Z"},
  {"wf": "Deploy Competition to Live Site",  "count": 3,  "oldest": "2026-05-31T07:40:01Z"}
]
```
PR-gating fan-out (`No stale DB passwords` + `Secret Scan` + `Branch Large File Duplicate Guard` + `Conflict Marker Check`) accounts for **53 of the queued** (`15+15+12+11`).

### Top in_progress workflows (group_by, with oldest age):
```
[
  {"wf": "Branch Large File Duplicate Guard","count": 24, "oldest_age_min": 143},
  {"wf": "DNA Genome Daily Pipeline",        "count": 1,  "oldest_age_min": 77},
  {"wf": "[torontoevent.net] Run Backtests", "count": 1,  "oldest_age_min": 69},
  {"wf": "Mirror: findtorontoevents.ca",     "count": 1,  "oldest_age_min": 65},
  {"wf": "ALPHA ENGINE FAST",                "count": 1,  "oldest_age_min": 60},
  {"wf": "ALPHA ENGINE - Live Autonomous Scanner","count":1,"oldest_age_min": 58},
  {"wf": "Polymarket Prediction Market Signals","count":1,"oldest_age_min": 57},
  {"wf": "Quick Guess ML Agent",             "count": 1,  "oldest_age_min": 57},
  {"wf": "Baby Strat Real Forward Monitor",  "count": 1,  "oldest_age_min": 56},
  {"wf": "Copy Trader Forward Test",         "count": 1,  "oldest_age_min": 55},
  {"wf": "Run Backtests & Deploy Dashboards","count": 1,  "oldest_age_min": 53}
]
```
**Smoking gun: 24 in_progress `Branch Large File Duplicate Guard` runs, oldest 143 min** — these are zombie/stuck, eating most runner slots.

## 2. Three Starved Targets (queue age)

| Target | run id | queued at | age (min) |
|---|---|---|---|
| Outcome Resolver — Validate Unresolved Picks | 26706652688 | 2026-05-31T07:34:48Z | **56** |
| Audit Hourly Update | 26706665803 | 2026-05-31T07:35:27Z | **55** |
| Consensus Outcome Tracker | 26707257562 | 2026-05-31T08:05:35Z | **25** |
| Run-Backtests 26706712727 | 26706712727 | 2026-05-31T07:37:51Z | **53 (in_progress, not starved)** |

Run-Backtests `26706712727` is currently `in_progress` per `gh run view`; it is not starved, it is running.

## 3. Three Options

### OPTION A — Big batch cancel of stuck Branch Large File Duplicate Guard + non-gating in_progress
- **What:** cancel all 24 in_progress `Branch Large File Duplicate Guard` (oldest 143 min, clearly stuck) plus the 12 queued of same workflow. Estimated runner-slot recovery: **24 slots immediate**.
- **Tradeoff:** loses guard coverage on those branches; PRs that depended on it will need re-run after fix.
- **Risk:** medium — if the guard is wedged it's already not protecting anything; cancelling is recovery, not loss.
- **Commands (operator):**
  ```bash
  # Cancel all in_progress Branch Large File Duplicate Guard runs
  gh run list --status in_progress --limit 50 --json workflowName,databaseId \
    | jq -r '.[] | select(.workflowName == "Branch Large File Duplicate Guard") | .databaseId' \
    | xargs -I{} gh run cancel {}

  # Cancel all queued Branch Large File Duplicate Guard runs
  gh run list --status queued --limit 100 --json workflowName,databaseId \
    | jq -r '.[] | select(.workflowName == "Branch Large File Duplicate Guard") | .databaseId' \
    | xargs -I{} gh run cancel {}
  ```

### OPTION B — Raise GitHub Actions plan cap
- **What:** upgrade billing plan (free tier 20 concurrent jobs per account on hosted runners → Team plan 60 → Enterprise higher).
- **Tradeoff:** cost ($4/user/mo Team minimum; concurrency limits documented at github.com/settings/billing).
- **Risk:** low.
- **Recovery:** immediate after upgrade.
- **Command:** manual — open `https://github.com/settings/billing/plans` and upgrade. Not scriptable via `gh`.

### OPTION C — Cron cadence reduction on hourly fan-out
- **What:** change highest-volume hourlies from `cron: '0 * * * *'` to `cron: '0 */2 * * *'` (every 2 hr). Targets identified by queued count + in_progress age:
  - `.github/workflows/audit-hourly-update.yml` (queued 1, but blocked)
  - `.github/workflows/outcome_resolver.yml`
  - `.github/workflows/consensus_outcome_tracker.yml` *(do NOT lengthen these — they ARE the starved targets we want to run faster)*
  - **Real target:** lengthen the hourlies that DON'T block money-ready: `branch-large-file-guard.yml`, `secret-scan.yml`, `no-stale-db-passwords.yml` (if these are hourly cron and not PR-triggered).
- **Tradeoff:** stale data on whatever is lengthened (2hr lag instead of 1hr).
- **Risk:** low.
- **Recovery:** takes effect at next cron tick (up to 1 hr).
- **YAML edit:**
  ```yaml
  on:
    schedule:
  -   - cron: '0 * * * *'
  +   - cron: '0 */2 * * *'
  ```

## 4. Recommendation

**OPTION A** — lowest-risk for the immediate next 6 hr.

Rationale:
- 24 in_progress `Branch Large File Duplicate Guard` runs at 143 min old are clearly **stuck zombies** (a healthy guard run is seconds–minutes, not hours).
- They are consuming ~60% of all in_progress slots (24 of 39).
- Cancelling them returns 24 runner slots immediately, which will drain the 3 starved targets within 1–2 cron ticks.
- Option B costs money for a problem that is a stuck-job leak, not a true capacity shortage.
- Option C creates stale data; doesn't address the leak.
- Once Option A unblocks the queue, file a follow-up to fix whatever made `Branch Large File Duplicate Guard` hang (likely a `git fetch` or large-file walk timing out without `timeout-minutes`).

Operator override: if you suspect those 24 runs are legitimately mid-scan, Option C on the gating fan-outs (`No stale DB passwords` + `Secret Scan` set to every 2 hr) is the next safest.
