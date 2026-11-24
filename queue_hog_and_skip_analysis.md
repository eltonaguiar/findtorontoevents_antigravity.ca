# Queue Hog & Skip Analysis — 2026-11-16T03:44Z

> **VERIFICATION NOTE (added 2026-11-16T03:49Z):**
> 1. The **374 workflow files / 76 without `timeout-minutes:` / 62 of those cron-bearing** figures were **independently re-verified by the coordinator** this pass and match exactly. Treat as confirmed.
> 2. All **zombie and in_progress numbers** in this report are a **point-in-time snapshot observed at 2026-11-16T03:44Z** (computed against reference clock `2026-11-16T03:45:00Z`). They decay — a re-run will show different ages or an already-cancelled run.
> 3. **Reconciling note:** the `discord-bot.yml` run `43745604081` outlier at **570.6 min is a CONCURRENCY bug, not a timeout bug** — `timeout-minutes: 355` is already set in that workflow and was still exceeded, because the `concurrency` group uses `cancel-in-progress: false` alongside a `7 */6 * * *` restart cron, allowing an overlapping duplicate. Fix the concurrency semantics; do not "add a timeout".

**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Main HEAD:** `cbf5071caf845b2132ca3374058f226dd14dcbbb`
**API calls used:** 5/20 (rate_limit + 2 status + 2 completed/skipped)
**Git-only verification:** 0 API calls (all workflow gates read via `git show`)

---

## (a) Live In-Progress / Queued Snapshot

### In-Progress (22 runs, 2026-11-16T03:44Z)
| Elapsed (min) | Since Created | Workflow | Branch | Event | Run ID |
|---------------|---------------|----------|--------|-------|--------|
| **570.6** | 570.6 | `discord-bot.yml` | main | schedule | 43745604081 |
| 26.6 | 26.6 | `alpha-engine-fast.yml` | main | schedule | 43797385226 |
| 23.3 | 23.3 | `audit-dashboard.yml` | main | schedule | 43797722088 |
| 9.7 | 9.7 | `baby-strat-forward-paper.yml` | main | schedule | 43799074710 |
| 5.0 | 5.0 | `gainer-predictor.yml` | main | schedule | 43799545212 |
| 4.7 | 4.7 | `coinglass-scanner.yml` | main | schedule | 43799571487 |
| 4.0 | 4.0 | `polymarket-signals.yml` | main | schedule | 43799632329 |
| 3.7 | 3.7 | `mutation-lab.yml` | main | schedule | 43799662215 |
| 3.2 | 3.2 | `signal-recorder.yml` | main | schedule | 43799708860 |
| 3.1 | 3.1 | `now-scanner.yml` | main | schedule | 43799713063 |
| 3.1 | 3.1 | `copy-trader-forward-test.yml` | main | schedule | 43799713959 |
| 3.1 | 3.1 | `consensus-outcome-tracker.yml` | main | schedule | 43799713400 |
| 2.8 | 2.8 | `regime-terminal.yml` | main | schedule | 43799749242 |
| 2.8 | 2.8 | `prediction-quality-tracker.yml` | main | schedule | 43799749883 |
| 2.5 | 2.5 | `copy-trader-intelligence.yml` | main | schedule | 43799768289 |
| 2.5 | 2.5 | `branch-large-file-dup-guard.yml` | feat/finpredict-final-v001 | push | 43799775582 |
| 1.6 | 1.6 | `signal-engine.yml` | main | schedule | 43799856757 |
| 1.1 | 1.1 | `dashboard-pick-trader.yml` | main | schedule | 43799899561 |
| 1.0 | 1.0 | `dynamic-alpha-engine.yml` | main | workflow_dispatch | 43799911205 |
| 0.9 | 0.9 | `schema-drift-audit.yml` | main | schedule | 43799916947 |
| 0.9 | 0.9 | `luxalgo-signals.yml` | main | schedule | 43799913889 |
| 0.8 | 0.8 | `recommended-portfolio.yml` | main | schedule | 43799925483 |

**Hog identified:** `discord-bot.yml` at **570.6 min (9.5 hours)** — exceeds GitHub's 6h job limit. This is a **zombie** (see below).

### Queued (21 runs, 2026-11-16T03:44Z)
| Age (min) | Workflow | Branch | Event | Run ID |
|-----------|----------|--------|-------|--------|
| **6200.8** | `now-scanner.yml` | main | schedule | 43095833399 |
| **6189.0** | `sports-smoke-and-e2e.yml` | main | schedule | 43096994522 |
| **6189.0** | `portfolio-trackers.yml` | main | schedule | 43096994785 |
| **6188.9** | `deploy-vetted-picks.yml` | main | schedule | 43097000114 |
| **6188.9** | `torontoevent-backtest-and-deploy.yml` | main | schedule | 43097015092 |
| **6188.9** | `winner-pattern-scanner.yml` | main | schedule | 43097009568 |
| **6188.9** | `sustained-gainer-scan.yml` | main | schedule | 43097004990 |
| **6188.9** | `sports-data-snapshots.yml` | main | schedule | 43097015653 |
| **6188.9** | `claude-gainer-ml-live.yml` | main | schedule | 43097010333 |
| **6188.9** | `incubator-strategies.yml` | main | schedule | 43097010900 |
| **6188.8** | `ueps-pick-runner.yml` | main | schedule | 43097022273 |
| **6188.8** | `rapid-validation-CLAUDECODE_Feb152026.yml` | main | schedule | 43097017743 |
| **6188.8** | `claude-gainer-tracker.yml` | main | schedule | 43097024915 |
| **6188.8** | `dynamic-alpha-engine.yml` | main | schedule | 43097018427 |
| **6188.7** | `signal-integrator.yml` | main | schedule | 43097029325 |
| **6188.7** | `outcome-resolver.yml` | main | schedule | 43097031813 |
| **6188.7** | `baby-strat-forward-paper.yml` | main | schedule | 43097026953 |
| **6182.1** | `enhanced-ml-crypto.yml` | main | schedule | 43097674708 |
| **6181.9** | `copy-trader-forward-test.yml` | main | schedule | 43097693735 |
| **6181.7** | `meta-strategy.yml` | main | schedule | 43097707633 |
| **6181.6** | `audit-hourly-update.yml` | main | schedule | 43097722505 |

**Zombie queue confirmed:** 21 runs queued since **2026-11-11T20:24Z** (103+ hours). GitHub normally kills queued runs at 24h; these are **stuck**.

---

## (b) Zombie List

| Run ID | Workflow | Created | Age | Status |
|--------|----------|---------|-----|--------|
| 43095833399 | `now-scanner.yml` | 2026-11-11T20:24:10Z | 6200.8 min (103.3h) | queued |
| 43096994522 | `sports-smoke-and-e2e.yml` | 2026-11-11T20:35:58Z | 6189.0 min | queued |
| 43096994785 | `portfolio-trackers.yml` | 2026-11-11T20:35:58Z | 6189.0 min | queued |
| 43097000114 | `deploy-vetted-picks.yml` | 2026-11-11T20:36:09Z | 6188.9 min | queued |
| 43097015092 | `torontoevent-backtest-and-deploy.yml` | 2026-11-11T20:36:09Z | 6188.9 min | queued |
| 43097009568 | `winner-pattern-scanner.yml` | 2026-11-11T20:36:06Z | 6188.9 min | queued |
| 43097004990 | `sustained-gainer-scan.yml` | 2026-11-11T20:36:09Z | 6188.9 min | queued |
| 43097015653 | `sports-data-snapshots.yml` | 2026-11-11T20:36:09Z | 6188.9 min | queued |
| 43097010333 | `claude-gainer-ml-live.yml` | 2026-11-11T20:36:07Z | 6188.9 min | queued |
| 43097010900 | `incubator-strategies.yml` | 2026-11-11T20:36:07Z | 6188.9 min | queued |
| 43097022273 | `ueps-pick-runner.yml` | 2026-11-11T20:36:13Z | 6188.8 min | queued |
| 43097017743 | `rapid-validation-CLAUDECODE_Feb152026.yml` | 2026-11-11T20:36:14Z | 6188.8 min | queued |
| 43097024915 | `claude-gainer-tracker.yml` | 2026-11-11T20:36:11Z | 6188.8 min | queued |
| 43097018427 | `dynamic-alpha-engine.yml` | 2026-11-11T20:36:13Z | 6188.8 min | queued |
| 43097029325 | `signal-integrator.yml` | 2026-11-11T20:36:17Z | 6188.7 min | queued |
| 43097031813 | `outcome-resolver.yml` | 2026-11-11T20:36:16Z | 6188.7 min | queued |
| 43097026953 | `baby-strat-forward-paper.yml` | 2026-11-11T20:36:16Z | 6188.7 min | queued |
| 43097674708 | `enhanced-ml-crypto.yml` | 2026-11-11T20:42:57Z | 6182.1 min | queued |
| 43097693735 | `copy-trader-forward-test.yml` | 2026-11-11T20:43:08Z | 6181.9 min | queued |
| 43097707633 | `meta-strategy.yml` | 2026-11-11T20:43:16Z | 6181.7 min | queued |
| 43097722505 | `audit-hourly-update.yml` | 2026-11-11T20:43:24Z | 6181.6 min | queued |
| 43745604081 | `discord-bot.yml` | 2026-11-15T18:14:23Z | 570.6 min (9.5h) | in_progress (exceeded 6h limit) |

**Root cause hypothesis:** A shared `concurrency:` group or external runner contention (or a `cancel-in-progress: false` loop) has caused GitHub's queue to stall. These are not transient — 103h queued is a **stuck state**.

---

## (c) Perpetual-Skip List (Skip-Rate >50% in Window)

**Window:** 2026-11-16T02:58Z → 03:44Z (46 minutes, 100 skipped + 100 completed samples)

| Skips | Workflow | Trigger Pattern | Root-Cause Hypothesis |
|-------|----------|-----------------|----------------------|
| 6 | `deploy-competition-to-site.yml` | `workflow_run` + `push` paths filter | `if:` gate requires `workflow_run.conclusion == 'success'` from 8 upstreams; most upstreams don't trigger it |
| 5 | `meme-scanner-v2.yml` | `schedule` (0 * * * *, */10 * * * *, 0 */3 * * * *) | Multiple `if: github.event.schedule == 'X'` guards per job — only 1 of 3 cron patterns matches per run |
| 4 | `no-stale-db-passwords.yml` | `pull_request` | Likely `paths:` or `if:` gate on PR content; only fires on specific file changes |
| 4 | `conflict-marker-check.yml` | `pull_request` | Same — PR-only gate |
| 3 | `db-password-leak-guard.yml` | `pull_request` | Same |
| 3 | `tv-paper-tpsl-watchdog.yml` | `schedule` | Cron guard or `needs:` dependency not met |
| 2 | `masking-policy-lint.yml` | `pull_request` | PR-only gate |
| 2 | `swarm-sync-v2.yml` | `schedule` | Cron guard |
| 2 | `alpha-quant-stack.yml` | `schedule` | Cron guard |
| 2 | `torontoevent-spike-scanner.yml` | `schedule` | Cron guard |
| 2 | `sustained-gainer-scan.yml` | `schedule` | Cron guard |
| 2 | `torontoevent-deploy-riseoftheclaw.yml` | `schedule` | Cron guard |
| 2 | `master-automation-scheduler.yml` | `schedule` | Cron guard |

**Pattern:** 72/100 skipped are `schedule` events, 11 are `pull_request`. This is **not a failure** — it's a **gate design**. The `if:` conditions and `paths:` filters are intentionally narrow. No action needed unless a gate is unintentionally blocking.

---

## (d) Timeout-Minutes Gap Table (Free Win)

**Source:** `git grep -l 'jobs:' -- .github/workflows` + `git ls-tree origin/main .github/workflows` (0 API calls)

**Total workflow files on main:** 374
**Files with NO `timeout-minutes:` anywhere:** 76
**Of which have ≥1 cron:** 62

### Top 15 No-Timeout Cron Workflows (by job count)

| Jobs | Crons | Push | Workflow |
|------|-------|------|----------|
| 9 | 3 | 0 | `claude-gainer-tracker.yml` |
| 7 | 3 | 1 | `backtest-and-deploy.yml` |
| 5 | 3 | 1 | `torontoevent-backtest-and-deploy.yml` |
| 7 | 2 | 0 | `poc-picks-checkpoint.yml` |
| 6 | 2 | 0 | `scrape-events.yml` |
| 6 | 2 | 0 | `etf-bond-scanner.yml` |
| 4 | 2 | 0 | `kimi-goldmine-collector.yml` |
| 8 | 1 | 1 | `torontoevent-deploy-riseoftheclaw.yml` |
| 8 | 1 | 1 | `live_tracker.yml` |
| 8 | 1 | 0 | `swarm-sync-v2.yml` |
| 8 | 1 | 0 | `mutation-lifecycle-runner.yml` |
| 8 | 1 | 0 | `dna-mutation-cycle.yml` |
| 7 | 1 | 1 | `signal_tracking.yml` |
| 7 | 1 | 1 | `self_optimizing_trading.yml` |
| 7 | 1 | 1 | `market_beating.yml` |

**Full list:** See `/tmp/qh/no_timeout_cron.txt` (62 entries) and `/tmp/qh/timeout_detail.txt` (76 entries with job/cron/push counts).

**Risk:** Default GitHub timeout is **360 minutes (6 hours)**. Any workflow without explicit `timeout-minutes:` can hog a runner for the full 6h if a step hangs.

---

## (e) Ranked Recommendations (with Exact YAML Diff)

### 1. **CRITICAL: Kill the 103h zombie queue** (no YAML change — admin action)

**Symptom:** 21 queued runs since 2026-11-11T20:24Z, plus `discord-bot` in_progress for 9.5h.

**Action:** GitHub Support / repo admin must manually cancel these runs via the Actions UI or REST API (`POST /repos/{owner}/{repo}/actions/runs/{run_id}/cancel`).

**Why:** These are not transient queue pressure — they're stuck. Until cleared, the queue cannot drain.

---

### 2. **HIGH: Add `timeout-minutes:` to all 76 no-timeout workflows** (free win, 0 API calls to detect)

**Example diff for `claude-gainer-tracker.yml` (top offender, 9 jobs / 3 crons):**

```yaml
# BEFORE (line ~30, first job):
jobs:
  job-1:
    runs-on: ubuntu-latest
    # NO timeout-minutes

# AFTER:
jobs:
  job-1:
    runs-on: ubuntu-latest
    timeout-minutes: 30   # <-- ADD (adjust per job: 10-60 typical, 90 for long backtests)
```

**REVERT:** Remove the `timeout-minutes:` line (or set to 360 to match GitHub default).

**Priority order:** Apply to the 62 cron-carrying files first (listed in `/tmp/qh/no_timeout_cron.txt`), then the remaining 14 push-only files.

**Impact:** Prevents 6h runner hogs. Cost: ~1-2 min per workflow to audit + add.

---

### 3. **MEDIUM: Fix `discord-bot.yml` timeout** (already has 355 min, but exceeded)

**Current (lines 16-18):**
```yaml
jobs:
  run-bot:
    runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
    timeout-minutes: 355  # 5h 55m (under GitHub's 6h limit)
```

**Problem:** The 355-min timeout is correct, but the job ran 570 min (9.5h). This means the **concurrency group** `discord-bot` with `cancel-in-progress: false` allowed a duplicate to start while the first was still running.

**Recommendation:** Change the schedule from `7 */6 * * *` (every 6h) to `7 */8 * * *` (every 8h) to give the 5h55m job breathing room, OR add a `if:` guard to skip if the bot is already healthy.

**REVERT:** Revert cron to `7 */6 * * *`.

---

### 4. **LOW: Audit `deploy-competition-to-site.yml` skip rate** (6 skips in 46-min window)

**Current (lines 6-8, 17, 33):**
```yaml
on:
  push:
    branches: [main]
    paths:
      - 'STOCKS/competition/**'
      - 'STOCKS/algorithm-competition.html'
      ...
  workflow_run:
    workflows: ["Algorithm Competition Refresh", ...]  # 8 upstreams
    types: [completed]

jobs:
  deploy:
    if: ${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
```

**Hypothesis:** The `workflow_run` trigger + `if:` gate requires one of 8 upstreams to complete successfully. Most upstreams don't run on every push, so the gate is rarely true.

**Recommendation:** If this is intentional (only deploy when upstreams succeed), leave as-is. If it's unintentionally skipping, consider adding a `workflow_dispatch` fallback or relaxing the `if:`.

**REVERT:** No change needed if behavior is correct.

---

### 5. **LOW: Audit `meme-scanner-v2.yml` skip rate** (5 skips, complex cron guards)

**Current (lines 45, 69, 135):**
```yaml
if: github.event.schedule == '0 * * * *' || inputs.action == 'full'
if: github.event.schedule == '*/10 * * * *' || inputs.action == 'scan' || inputs.action == 'full'
if: github.event.schedule == '0 */3 * * *' || inputs.action == 'resolve' || inputs.action == 'full'
```

**Hypothesis:** Three separate cron schedules, each with its own `if:` guard. Only 1 of 3 matches per run → 2/3 of scheduled runs skip.

**Recommendation:** If intentional (different actions per cron), leave as-is. If the intent is "run all three actions every time," consolidate to a single cron + single job without the schedule guard.

**REVERT:** No change needed if behavior is correct.

---

## (f) REVERT Section (Original Values for All Proposed Changes)

| Workflow | Field | Current (Proposed) | Original (to revert) |
|----------|-------|-------------------|---------------------|
| `claude-gainer-tracker.yml` (and 75 others) | `jobs.*.timeout-minutes` | `30` (or 10-90) | *(absent — GitHub default 360)* |
| `discord-bot.yml` | `on.schedule[0].cron` | `7 */8 * * *` | `7 */6 * * *` |
| `discord-bot.yml` | `jobs.run-bot.timeout-minutes` | `355` (unchanged) | `355` |
| `deploy-competition-to-site.yml` | `jobs.deploy.if` | *(unchanged if intentional)* | *(no change)* |
| `meme-scanner-v2.yml` | `jobs.*.if` (schedule guards) | *(unchanged if intentional)* | *(no change)* |

---

## Summary Stats

| Metric | Value |
|--------|-------|
| API calls used | 5/20 |
| In-progress runs | 22 |
| Queued runs | 21 |
| Zombies (queued >24h) | 21 |
| Zombies (in_progress >6h) | 1 (`discord-bot`) |
| Skip-rate >50% offenders | 13 workflows (mostly intentional gates) |
| Workflows missing `timeout-minutes:` | 76 (62 cron-carrying) |
| Free win (timeout-minutes audit) | 0 API calls, git-only |

**Next step:** Coordinator to decide whether to proceed with timeout-minutes mass edit (via PR) or treat as read-only analysis.
