# GA4 — Job-Level & Scheduling / Concurrency Deep Dive

**Verdict: FAIL — job scheduling health.**

The scheduler is structurally saturated: 35% of the last 60 audit-dashboard runs were cancelled with **zero jobs executed**, and four key workflows now wait **1.5–3.7 hours** in the runner queue before their first job starts. The audit-dashboard cron interval (60 min) is shorter than the job's own p50 runtime (~97 min), so every hour it manufactures a run that cannot possibly start.

- Analysis timestamp: **2026-11-14 ~17:55Z**
- Repo: `eltonaguiar/findtorontoevents_antigravity.ca`, branch `main`
- Workflow files verified identical to `origin/main` (`be4f8960`) for every file cited below.
- Raw API evidence: `actions_deepdive/raw_ga4/` (`wf60_*.json`, `jobs_<run>.json`, `cron_map.txt`).
- No repo source was modified; this report is the only file written.

---

## 0. Executive summary

| Metric | Observed |
|---|---|
| Audit-dashboard runs sampled (last 60) | 37 success, 22 cancelled, 1 in progress |
| Audit cancels with **0 jobs executed** | **21 of 22 (95%)** — 21/60 = **35% of all runs** |
| Audit job p50 / p95 duration | **97.2 / 111.6 min** (linear-interpolated; nearest-rank p95 = 119.1, max 119.1) vs 60-min cron |
| Zero-job runs' queue wait | 39–67 min (median ~59) before discard |
| Scheduled workflows | 310 (strict cron parse); 166 have **no** `concurrency:` |
| Of those, scheduled workflows that push to main and have no concurrency | **91** |
| Cron entries firing at minute `:00` | **196** (114 of them push to main) |
| Queue p50: signal / market / mirror / PEAD | **91.4 / 118.5 / 174.0 / 221.2 min** |
| PEAD push-retry exhaustion | **60/60 recent runs failed** in `Commit shadow log` |
| Live Spike push-retry exhaustion | 1/60 (the failure burned 30.2 min in commit) |
| Mirror failures are push-related? | **No** — 60/60 fail in FTP download |

---

## 1. Representative runs — per-job data

All 15 requested runs (plus one healthy baseline) were pulled with
`gh api repos/.../actions/runs/<id>/jobs --paginate`. Every sampled job ran on
**GitHub-hosted `ubuntu-latest`** (runner names e.g. `GitHub Actions 1001041470`);
no self-hosted runner executed in this sample. The alpha-engine-live matrix's
"Set up Python (self-hosted Windows)" branch was `skipped` on every cloud run.

| # | Run | Workflow | Job(s) | Conclusion | Job duration | Queue wait | Steps | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | 43609078013 | Audit Dashboard | `generate-and-deploy` | success | **104.9 min** | 20.5 min | 54 | FTP deploy step 56.6 min |
| 2 | 43598734241 | Audit Dashboard | `generate-and-deploy` | success | **104.2 min** | 36.4 min | 54 | FTP deploy step 56.7 min |
| 3 | 43584306989 | Audit Dashboard | `generate-and-deploy` | success | 79.6 min | 54.8 min | 54 | |
| 4 | 43614551238 | Audit Dashboard | — | cancelled | 0 jobs | 59 min | 0 | zero-job discard |
| 5 | 43603788378 | Audit Dashboard | — | cancelled | 0 jobs | 60 min | 0 | zero-job discard |
| 6 | 43589060993 | Audit Dashboard | — | cancelled | 0 jobs | 64 min | 0 | zero-job discard |
| 7 | 43516057375 | Alpha Engine Daily Picks | `generate-picks` | success | 1.6 min | 0 min | 14 | healthy |
| 8 | 43603342689 | Alpha Engine Live | `alpha-engine` | cancelled | 4.0 min | 117.5 min | 62 | killed inside "Full cycle" |
| 9 | 43615290049 | CI Tests | `test (3.12)` / `test (3.11)` | failure / failure | 2.1 / 1.8 min | 70.9 min | 18 each | "Run all tests" step fails |
| 10 | 43598659309 | CI Tests | `test (3.12)` / `test (3.11)` | failure / failure | 1.9 / 1.5 min | 80.3 min | 18 each | same failing step |
| 11 | 43602685216 | Signal Tracking | `track-and-validate` | failure | 24.0 min | 92.3 min | 14 | checkout alone 20.0 min; install deps fails |
| 12 | 43603128044 | Market Beating | `market-beating` | failure | 19.0 min | 119.9 min | 14 | checkout 15.8 min; install deps fails |
| 13 | 43615875690 | Live Spike | `spike-trading` | success | 14.9 min | 0 min | 11 | commit 17 s |
| 14 | 43520036730 | H-002 PEAD | `collect-pead-shadow` | failure | 22.1 min | 217.8 min | 10 | `Commit shadow log` fails after 17.4 min |
| 15 | 43593541152 | Mirror | `mirror` | failure | 30.5 min | 174.8 min | 9 | FTP download hits 30-min step timeout |
| — | 43564583399 | DB Sync → Mirror | `Sync databases` | success | 2.4 min | 0 min | 13 | healthy baseline |

### Where audit-dashboard time goes (run 43609078013)

| Step | Duration |
|---|---|
| Resolve active picks (step 7) | 19.1 min |
| Generate dashboard payload + HTML (step 37) | 11.3 min |
| DB health check (step 11) | 9.3 min |
| **Deploy to all 3 FTP sites (step 50)** | **56.6 min** |
| Everything else (~49 steps) | ~8.6 min |
| **Total job** | **104.9 min** |

The FTP deploy step alone consumes 54% of the job. That is why the documented
"30–35 min" runtime in the cron comment (`.github/workflows/audit-dashboard.yml:5`)
is now wrong by ~3x.

**Second generator invocation:** `python -m audit_trail.dashboard_generator`
at `.github/workflows/audit-dashboard.yml:997` is **inside** the
`if grep -rq '<<<<<<' audit_dashboard/index.html` branch of the push/merge retry
loop (lines ~993–1001). It runs only when a merge leaves conflict markers in
`index.html` — not on every merge-retry. Normal runs never invoke the generator
a second time.

---

## 2. Job-duration table (p50 / p95)

Durations are **job** time, not queue time. Audit uses per-run `jobs` data
(n=15 sampled executed jobs); the others use `run_started_at → updated_at`, which
matches the sampled job's `started_at` within seconds.

| Workflow | n | p50 | p95 | max | Comment |
|---|---|---|---|---|---|
| **Audit Dashboard** (`generate-and-deploy`) | 15 | **97.2 min** | **111.6 min** (nearest-rank 119.1) | 119.1 min | 60-min cron cannot fit |
| Alpha Engine Live (`alpha-engine`) | 29 | 50.0 min | 77.4 min | 80.4 min | 90-min job timeout |
| Alpha Engine Daily Picks (`generate-picks`) | 60 | 1.4 min | 2.0 min | 2.3 min | healthy |
| CI Tests (run; 2 matrix jobs in parallel) | 60 | 2.1 min | 2.4 min | 4.0 min | 100% failure at test step |
| Signal Tracking (`track-and-validate`) | 59 | 21.8 min | 26.2 min | 26.8 min | 100% failure at install deps |
| Market Beating (`market-beating`) | 59 | 23.4 min | 27.5 min | 53.8 min | 100% failure at install deps |
| Mirror (`mirror`) | 60 | 30.4 min | 30.7 min | 31.1 min | pinned at 30-min download timeout |
| H-002 PEAD (`collect-pead-shadow`) | 60 | 22.9 min | 25.7 min | 27.5 min | 100% failure at commit/push |
| Live Spike (`spike-trading`) | 60 | 15.0 min | 15.3 min | 44.8 min | one commit-retry exhaustion |
| DB Sync → Mirror | 58 | 2.5 min | 2.7 min | 4.8 min | healthy |

Longest individual jobs observed:

| Run | Job | Duration | Outcome |
|---|---|---|---|
| 43539482330 | audit `generate-and-deploy` | **119.1 min** | `cancelled` at finalization; all 54 steps report `success` |
| 43525630490 | audit `generate-and-deploy` | 108.5 min | success |
| 43565933484 | audit `generate-and-deploy` | 105.5 min | success |
| 43609078013 | audit `generate-and-deploy` | 104.9 min | success |
| 43598734241 | audit `generate-and-deploy` | 104.2 min | success |
| 43391608981 | alpha-engine | 74.0 min | success |
| 43423663795 | alpha-engine | 73.8 min | success |

The 119.1-min run is a **timeout edge**: `timeout-minutes: 115` is only ~3.4 min
above the p95. GitHub recorded `cancelled` even though "Complete job" had already
returned success (03:16:33) and the job ended at 03:16:35. Whether the kill came
from the 115-min cap or the next cron entering the concurrency group at 03:16:32
is **UNVERIFIED** (needs the job log/annotation). Either way, 115 min is too tight.

---

## 3. Zero-job cancels (queue discard)

Last 60 audit runs: **22 cancelled, 21 with `total_count = 0`** jobs.
All were pending in the `dashboard-publish` group and were discarded because a
newer run in the same group arrived (GitHub cancels the previously *pending* run
even when `cancel-in-progress: false`). None ever allocated a runner.

| run_id | created (UTC) | cancelled (UTC) | queued |
|---|---|---|---|
| 43614551238 | 2026-11-14T16:14:52Z | 2026-11-14T17:14:16Z | 59 min |
| 43603788378 | 2026-11-14T14:14:03Z | 2026-11-14T15:14:14Z | 60 min |
| 43589060993 | 2026-11-14T11:14:16Z | 2026-11-14T12:18:42Z | 64 min |
| 43570175588 | 2026-11-14T07:14:45Z | 2026-11-14T08:16:54Z | 62 min |
| 43560599415 | 2026-11-14T05:14:54Z | 2026-11-14T06:21:26Z | 67 min |
| 43545655088 | 2026-11-14T02:19:31Z | 2026-11-14T03:16:33Z | 57 min |
| 43535071245 | 2026-11-14T00:34:14Z | 2026-11-14T01:15:33Z | 41 min |
| 43517634445 | 2026-11-13T22:14:29Z | 2026-11-13T23:14:37Z | 60 min |
| 43500038928 | 2026-11-13T20:16:34Z | 2026-11-13T21:14:13Z | 58 min |
| 43470794969 | 2026-11-13T17:14:20Z | 2026-11-13T18:16:53Z | 63 min |
| 43424478810 | 2026-11-13T12:21:36Z | 2026-11-13T13:15:12Z | 54 min |
| 43400124132 | 2026-11-13T09:17:52Z | 2026-11-13T10:15:43Z | 58 min |
| 43378405428 | 2026-11-13T06:23:49Z | 2026-11-13T07:03:22Z | 40 min |
| 43357965100 | 2026-11-13T03:17:29Z | 2026-11-13T04:17:44Z | 60 min |
| 43338348439 | 2026-11-13T00:36:06Z | 2026-11-13T01:14:57Z | 39 min |
| 43308237800 | 2026-11-12T21:14:13Z | 2026-11-12T22:14:26Z | 60 min |
| 43288103590 | 2026-11-12T19:14:24Z | 2026-11-12T20:15:31Z | 61 min |
| 43257166868 | 2026-11-12T16:18:11Z | 2026-11-12T17:14:43Z | 57 min |
| 43225553812 | 2026-11-12T13:15:24Z | 2026-11-12T14:16:30Z | 61 min |
| 43198794910 | 2026-11-12T10:15:49Z | 2026-11-12T11:15:18Z | 59 min |
| 43182039867 | 2026-11-12T08:19:49Z | 2026-11-12T09:17:21Z | 58 min |

The one other cancelled run, 43539482330, **did** execute (119.1 min) and is
discussed in §2.

**Mechanism proof (serialization works):** run 43619994221 was created 17:14:14
and did **not** start until 17:19:39 — 3 seconds after 43609078013 finished at
17:19:36. So `cancel-in-progress: false` is doing its job; the loss is the
pending-run supersede, not a concurrent overlap.

---

## 4. Stuck / queued jobs (>30 min) and in-progress checks

`created_at → job.started_at` (or `run_started_at` for one-job workflows):

| Workflow | n | queue p50 | queue p95 | max | runs queued >30 min |
|---|---|---|---|---|---|
| Signal Tracking | 60 | **91.4 min** | 92.8 min | 93.3 min | **60 / 60** |
| Market Beating | 60 | **118.5 min** | 129.9 min | 130.9 min | 59 / 60 |
| Mirror | 60 | **174.0 min** | 201.3 min | 204.4 min | 59 / 60 |
| H-002 PEAD | 60 | **221.2 min** | 239.5 min | **637.6 min** | **60 / 60** |
| CI Tests | 60 | 74.6 min | 95.4 min | 104.4 min | 59 / 60 |
| Alpha Engine Live | 60 | 69.6 min | 119.5 min | 128.0 min | 32 / 60 |
| Audit Dashboard (executed) | 15 | 23.6 min | 54.8 min | 58.0 min | 7 / 15 |
| Live Spike | 60 | 0.0 min | 0.0 min | 64.4 min | 1 / 60 |
| DB Sync → Mirror | 60 | 0.0 min | 7.8 min | 7.8 min | 0 / 60 |
| Alpha Daily Picks | 60 | 0.0 min | 0.0 min | 0.0 min | 0 / 60 |

Representative >30-min queue waits:

| Run | Workflow | Created | Job start | Queue |
|---|---|---|---|---|
| 43520036730 | PEAD | 22:32:00 | 02:09:51 | **217.8 min** |
| 43593541152 | Mirror | 12:11:02 | 15:05:50 | **174.8 min** |
| 43603128044 | Market | 14:06:36 | 16:06:32 | **119.9 min** |
| 43603342689 | Alpha Live | 14:09:02 | 16:06:32 | **117.5 min** |
| 43602685216 | Signal | 14:01:32 | 15:33:49 | **92.3 min** |
| 43615290049 | CI | 16:22:50 | 17:33:45 | **70.9 min** |

The PEAD 637.6-min outlier (run 33132269711, 2026-08-28) shows the queue can
stall for >10 hours.

**In-progress jobs at 17:55Z vs 2x median** — none stuck:

| Run | Job start | Elapsed | 2x median | Verdict |
|---|---|---|---|---|
| 43619994221 (audit) | 17:19:39 | 28.5 min | 194.4 min | OK (inside DB health check) |
| 43614126400 (alpha) | 17:33:46 | 14.4 min | 100.0 min | OK |
| 43613316905 (signal) | 17:33:56 | 14.2 min | 43.6 min | OK (still in checkout) |
| 43613854784 (market) | 17:33:47 | completed | 46.8 min | OK |

No `in_progress` job exceeded 2x its workflow median at the analysis timestamp.

---

## 5. Cron overlap map

Strict parse of `.github/workflows/*.yml`: **310 scheduled workflows**, 362 cron
entries (including multi-cron workflows).

### Minute-of-hour clusters (all cron entries)

| Minute | Entries | Of which push to main | Notes |
|---|---|---|---|
| **`:00`** | **196** | **114** | worst cluster; most `0 * * * *`, `0 */2 * * *`, `0 */4 * * *`, `0 22 * * 1-5` |
| `:30` | 35 | 20 | includes PEAD, ml-forward-test, non-crypto-ab-test |
| `:15` | 26 | 17 | `15 * * * *` hourly pushers |
| `:*/30` | 13 | 10 | `*/30 * * * *` |
| `:10` | 3 | 2 | **audit-dashboard**, breakout-arena |
| `:29` | 1 | 1 | live-spike-trading |

### High-risk simultaneous windows

| UTC window | Workflows | Contention |
|---|---|---|
| **Every `:00`** | 114 scheduled push-to-main workflows (battle_test, crypto-ml-tracker, darwin-evolution, signal_tracking, market_beating, master-automation-scheduler, forward-signal-scanner, backfill, …) | Runner pool + `git push` race on `main` |
| **Every `:15`** | 17 push-to-main workflows (baby-strat-forward, signal-integrator, signal-quality-monitor, outcome-resolver, ema-retracement-scan, …) | runner + push |
| **Every `:30`** | 20 push-to-main workflows (PEAD, ml-forward-test, non-crypto-ab-test ×4 slots, traditional-test-portfolios ×4 slots, …) | runner + push |
| **Every `:10`** | audit-dashboard (~97-min job) + breakout-arena | audit starts while :00 cluster is still draining |
| **07:00 daily** | `operator-review-today` + `rsi5070-forward-snapshot` both fire, **both in `dashboard-publish`**; audit at 07:10 | 3-way concurrency contention |
| **22:30 weekdays** | PEAD + alpha-equity-breakout (`30 22`) + daily-price-refresh (`0 22`) + daily-stock-refresh (`30 22`) | push + FTP contention |

`audit-dashboard.yml:5` is the only job in this set whose p50 runtime (~97 min)
exceeds its own cron interval (60 min). Live Spike deliberately sits at `:29` (`live_spike_trading.yml:5`) and shows
a 0-min queue — evidence that off-`:00` scheduling works.

---

## 6. Concurrency findings

1. **159 of 361 workflow files define `concurrency:`**; **166 of 310 scheduled
   workflows do not**, and **91 of those unguarded workflows push to `main`**.
   That is the main source of push-lock contention.
2. `cancel-in-progress` distribution among workflows that define concurrency:
   **114 `false`, 33 `true`**, ~10 expressions. Most pushers therefore queue
   instead of collapsing.
3. **`dashboard-publish` is shared by 3 workflows**:
   - `audit-dashboard.yml:41`
   - `operator-review-today.yml:39` (daily 07:00)
   - `rsi5070-forward-snapshot.yml:59` (daily 07:00)

   With `cancel-in-progress: false`, the two 07:00 dailies can push the 07:10
   audit run into a pending slot that the 08:10 audit run then supersedes —
   another zero-job discard. The comment at `operator-review-today.yml:28`
   ("after audit-dashboard 06:10 hourly runs ~35min") is stale: audit now runs
   ~97 min.
4. **`auto-commit-main-${{ github.workflow }}` is not a shared group.** Used by
   6 workflows (`backtest-and-deploy`, `battleground-mass-backtest`,
   `buy-now-analysis`, `darwin-evolution`, `meta-strategy`, `skyrocket-detector`),
   but `github.workflow` resolves to each workflow's own name, so each gets a
   distinct group. It does **not** serialize commits against the others despite
   the name. Same for `${{ github.workflow }}-${{ github.ref }}` (6 files) and
   `${{ github.workflow }}-${{ github.sha }}` (CI).
5. **Duplicate triggers (`schedule` + `push` + `workflow_dispatch`) are common.**
   26 scheduled workflows also run on `push`; `signal_tracking.yml` and
   `market_beating.yml` have all three. A push-triggered run enters the same
   queue as the cron run and is not de-duplicated.
6. **Audit-dashboard timeout is undersized relative to reality.**
   `timeout-minutes: 115` (`audit-dashboard.yml:55`) vs p95 111.6 (nearest-rank p95
   119.1) and observed max 119.1. One run was `cancelled` at 119.1 min after all steps had reported
   success.
7. **`signal_tracking` and `market_beating` have no `concurrency:` and no
   `timeout-minutes:`.** A stuck run can occupy a runner for the default 360 min.
   Their `fetch-depth: 0` checkout takes 15–20 min on this ~19 GB repo
   (`signal_tracking.yml:29`, `market_beating.yml:29`), unlike audit's
   `filter: blob:none` checkout (1–2 min).
8. **One group has no `cancel-in-progress`:** `won-pnl-contradiction-backfill.yml`.
   It defaults to `false`; harmless but should be explicit.

---

## 7. Push contention

| Workflow | Recent runs | Failures | Failing step | Interpretation |
|---|---|---|---|---|
| **H-002 PEAD** | 60 | **60 (100%)** | `Commit shadow log` (step 7) | **10-attempt push-retry exhaustion**. Sampled runs burned 17.4 / 17.7 / 17.3 min in the step. Loop: `pead-shadow-collector.yml:82-101` (10 iterations, up to 120 s backoff). |
| **Live Spike** | 60 | **1 (1.7%)** | `Commit results` (step 8) | `safe_push.sh` **8-attempt exhaustion** (30.2 min spent, run 43546586116). Healthy runs commit in ~17 s. |
| **Mirror** | 60 | **60 (100%)** | `Download from findtorontoevents.ca` (step 3) | **Not push contention** — FTP download hits the 30-min step timeout (`mirror-site.yml:39`). No commit step exists. |
| Signal Tracking | 59 | 59 | `Install dependencies` | Not push; dependency install fails after 15–20 min checkout. |
| Market Beating | 59 | 59 | `Install dependencies` | Not push; same. |
| CI Tests | 60 | 60 | `Run all tests` | Not push; genuine test failures. |

PEAD's near-100% commit failure is a chronic push-lock/merge problem, not a
one-off: every sampled run ends in the 10-attempt loop and exits 1. Its cron
(`30 22`) queues ~3.7 h and then competes with the nightly `:22–:30` push cluster.

---

## 8. Exact proposed edits

Each row is a minimal, reversible change. Line numbers are current `origin/main`.

| # | File:line | Change | Expected effect | Rollback |
|---|---|---|---|---|
| 1 | `.github/workflows/audit-dashboard.yml:5` | `cron: '10 * * * *'` → `cron: '10 */2 * * *'` | Removes the structural overlap: job p50 97 min < 120-min interval. Eliminates the ~21 zero-job discards per 60 runs (≈35% of runs). Freshness becomes ≤2 h instead of ≤1 h. | Restore `'10 * * * *'` (discards resume). |
| 2 | `.github/workflows/audit-dashboard.yml:55` | `timeout-minutes: 115` → `130` | Covers the interpolated p95 (111.6), the nearest-rank p95, and the observed 119.1-min finalization edge; prevents a near-complete run from being marked cancelled. | Restore `115`. |
| 3 | `.github/workflows/operator-review-today.yml:39` and `.github/workflows/rsi5070-forward-snapshot.yml:59` | `group: dashboard-publish` → `group: dashboard-publish-daily` | Removes 3-way contention at 07:00/07:10. The two dailies still serialize with each other (shared group) to protect the shared JSONs; audit-dashboard's hourly slot is isolated. | Restore `dashboard-publish` in both. |
| 4 | `.github/workflows/signal_tracking.yml:9-14` and `.github/workflows/market_beating.yml:9-14` | Delete the `push:` trigger block (keep `schedule` + `workflow_dispatch`) | Stops every push to `main` from spawning a duplicate run in an already 91-min queue. Both currently fail 100% before doing any work. | Restore the `push:` blocks. |
| 5 | `.github/workflows/signal_tracking.yml` after line 19 (`permissions:`) and `.github/workflows/market_beating.yml` after line 19 | Add `concurrency: { group: <workflow>, cancel-in-progress: true }` and `timeout-minutes: 30` on the job | Collapses stacked runs; caps a hung run at 30 min instead of the 360-min default. | Remove the blocks. |
| 6 | `.github/workflows/signal_tracking.yml:29` and `.github/workflows/market_beating.yml:29` | `fetch-depth: 0` → add `filter: blob:none` | Cuts checkout from 15–20 min to ~1–2 min (audit-dashboard proves this on the same repo), removing ~15 min of avoidable runtime per run. | Remove `filter:` line. |
| 7 | `.github/workflows/pead-shadow-collector.yml:11` | `cron: '30 22 * * 1-5'` → `cron: '30 6 * * 1-5'` | Runs after the 06:00 DB-sync window instead of the 22:30 nightly push cluster; should cut the 221-min queue p50 and most of the push-lock contention. | Restore `'30 22 * * 1-5'`. |
| 8 | `.github/workflows/pead-shadow-collector.yml:85` | `git pull --rebase --no-recurse-submodules -X theirs origin main` → `git pull --no-rebase --no-recurse-submodules -X ours --no-edit origin main` | Avoids replaying the commit across a constantly moving `main`; matches the audit-dashboard merge strategy that succeeds. Reduces the 10-attempt loop to cheap retries. | Restore the rebase line. |
| 9 | `.github/workflows/mirror-site.yml:8` | `cron: '0 */6 * * *'` → `cron: '20 */6 * * *'` | Moves mirror out of the 114-job `:00` push cluster; expected to reduce the 174-min queue p50. Does **not** fix the FTP download failure. | Restore `'0 */6 * * *'`. |
| 10 | `.github/workflows/ci-tests.yml:41-42` | `group: ${{ github.workflow }}-${{ github.sha }}` / `cancel-in-progress: false` → `group: ${{ github.workflow }}-${{ github.ref }}` / `cancel-in-progress: true` | Collapses superseded push runs (queue p50 74.6 min). **Conditional:** may cancel required checks for older SHAs; confirm branch-protection expectations first. | Restore the SHA-scoped group and `false`. |
| 11 | `.github/workflows/db-freshness-guardian.yml:12`, `battle_test.yml:6`, `crypto-ml-tracker.yml:6`, `darwin-evolution.yml:5` (and the other `:00` pushers) | Stagger `0 * * * *` to `5/12/18/24 * * * *` (or another per-workflow offset) | Spreads the 114 workflow/hour `:00` spike across the hour, reducing queue latency and push collisions without changing cadence. | Restore original minutes. |
| 12 | `.github/workflows/won-pnl-contradiction-backfill.yml` concurrency block | Add explicit `cancel-in-progress: false` | Removes ambiguity; documents intent. | Delete the line. |

**Priority order:** #1 and #2 are the single highest-value pair (they remove 35%
of audit runs and the timeout edge). #3 removes the 07:00 three-way collision.
#7/#8 are needed to make PEAD stop failing 100% of the time. #11 is a broad,
low-risk load-shedding change.

**Root-cause alternative to #1:** fix the 56-min FTP deploy step
(`audit-dashboard.yml:1040`). The step uploads every JSON serially with a 300-s
socket timeout; uploading only changed files (or parallelising per site) would
bring the job to ~50 min and allow the hourly cron to be kept. This is a larger
change and should be validated separately.

---

## 9. UNVERIFIED / limits

| Item | Status |
|---|---|
| Cause of the 119.1-min `cancelled` audit run 43539482330 (timeout vs. concurrency-group supersede) | **UNVERIFIED** — all 54 steps report `success`; needs the job log/annotation. |
| Whether `cancel-in-progress: false` was in effect for every historical audit run | **UNVERIFIED** for older runs; the current `origin/main` file and the 17:14→17:19 serialization prove it for 2026-11-14. |
| Distinct workflows vs. cron entries at `:00` | **196 counts cron entries**; multi-cron workflows count once per expression. The distinct-workflow count is lower and not separately enumerated. |
| PEAD failures all being push-retry exhaustion | **UNVERIFIED** for all 60; 3 of 3 sampled runs failed in `Commit shadow log` after 17–18 min, matching the 10-attempt loop. |
| GitHub's pending-run supersede as the sole cause of all 21 zero-job cancels | Strongly supported by timing (each cancel lands at the next run's creation) and 0 jobs; **UNVERIFIED** by per-run event log. |
| Runner-pool capacity as the cause of multi-hour queues | Inferred from queue waits with no failure; the actual hosted-runner concurrency limit is **UNVERIFIED**. |
| Live Spike 30.2-min commit failure as exactly 8 `safe_push` attempts | Consistent with `safe_push.sh` MAX_RETRIES=8 and 60-s caps; step log **UNVERIFIED**. |

---

## 10. Top 5 findings

1. **Audit-dashboard is self-cancelling by design mismatch.** p50 runtime is
   97.2 min (p95 111.6, nearest-rank 119.1) against a 60-min cron. In the last 60 runs, **21 of 22
   cancels executed zero jobs** (35% of all runs), each discarded after 39–67 min
   pending. The cron at `audit-dashboard.yml:5` and its "30–35 min" comment are
   stale; the 56.6-min FTP deploy step is the runtime driver.
2. **Runner queue saturation is severe and measurable.** p50 queue waits:
   Signal 91.4 min, Market 118.5, Mirror 174.0, PEAD 221.2 (max 637.6); CI 74.6,
   Alpha Live 69.6. 60/60 signal runs and 59/60 market/mirror/CI runs waited
   >30 min. Only off-`:00` workflows (Live Spike, DB Sync, Alpha Daily) had ~0 queue.
3. **`dashboard-publish` is a 3-workflow group.** Audit-dashboard shares it with
   `operator-review-today` and `rsi5070-forward-snapshot`, both firing at 07:00,
   so the 07:10 audit run competes with two dailies before the 08:10 run
   supersedes it. The dailies should move to their own group.
4. **PEAD's commit step fails on 60/60 recent runs from push-retry exhaustion**
   (10 attempts, ~17–18 min each), and Live Spike lost one run to `safe_push`
   exhaustion (8 attempts, 30.2 min). Mirror's 60/60 failures are FTP-download
   timeouts, not push contention.
5. **Concurrency hygiene is uneven.** 166/310 scheduled workflows have no
   `concurrency:` (91 of them push to main); `auto-commit-main-${{ github.workflow }}`
   is not actually shared; `signal_tracking`/`market_beating` have no concurrency
   and no job timeout; and 114 push-to-main workflows all fire at minute `:00`.
