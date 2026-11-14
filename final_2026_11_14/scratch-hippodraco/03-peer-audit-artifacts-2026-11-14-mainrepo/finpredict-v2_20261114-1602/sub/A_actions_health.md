FAIL

# Subagent A — GitHub Actions health audit

Repo: `eltonaguiar/findtorontoevents_antigravity.ca`  |  Snapshot: **2026-11-14T16:05Z**  |  Auditor: Subagent A

> All counts below are derived from GitHub API output captured 16:03–16:08Z. Run statuses move; a handful of runs captured as `failure` were later auto-retried (attempts 2–8) and were `in_progress` again when logs were requested. That is called out where it applies.

## 1. Summary counts

| Metric | Value |
|---|---|
| Total workflows in repo | **365** (361 active, 4 `disabled_manually`) |
| Workflows that ran in last 24h | **269** |
| Workflows that ran in last 7d | **309** |
| Workflows that never ran (all-time) | **20** |
| Workflows stale >7d (last run older than 7d) | **36** |
| Zero-run in 7d (never + stale) | **56** |
| Runs in 24h (reconstructed) | **4,109** (3,747 success, 214 failure, 82 cancelled, 49 skipped, 17 running) |
| Runs in 7d (reconstructed) | **28,187** (26,112 success, 1,207 failure, 642 cancelled, 185 skipped, 41 in progress) |
| Failing workflows | **24** in 24h (214 failed runs) / **88** in 7d (1,207 failed runs) |
| Cancelled runs | **82** in 24h; **642** in 7d |
| Cancelled with zero jobs executed | **15** in 24h (all 82 checked); 7d not exhaustively checked |
| Timed-out runs (`timed_out`) | **0** in 24h and 7d |
| Last run failed | **25 workflows** |
| Last run cancelled | **11 workflows** |
| Last run in progress | **18 workflows** |

Definition note: "24h/7d" windows end at 2026-11-14T16:05Z (same clock as the run list capture). Per-workflow totals come from `total_count`; run-level breakdowns come from fully paginated run arrays (all 96 workflows with >100 runs in 7d were paginated to completion).

## 2. Failure clusters (last 24h, with 48h totals)

| Workflow | Fail 24h | Fail 48h | Latest failing run | Created (UTC) | Failing job / step | Root error |
|---|---:|---:|---|---|---|---|
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | 47 | 59 | [43609547717](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43609547717) | 2026-11-14T15:19:23Z | `alpha-engine` / Run Alpha Engine | `KeyError: 'LONG'` after data-source failures: Binance HTTP 451, CoinMetrics 400/403, `No module named xgboost`, `'high'`/`'close'` KeyErrors |
| ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | 46 | 60 | [43608586741](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43608586741) | 2026-11-14T15:08:51Z | `alpha-fast` / Run Alpha Engine FAST variant | same `KeyError: 'LONG'`; 508 error-ish lines in log |
| Sports endpoint smoke + Playwright | 24 | 48 | [43609430834](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43609430834) | 2026-11-14T15:18:06Z | _run retrying (no completed failed job now)_ | UNVERIFIED — run retrying (attempt 3 in progress at snapshot) |
| CI Tests | 15 | 31 | [43605861085](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43605861085) | 2026-11-14T14:37:47Z | _run retrying (no completed failed job now)_ | UNVERIFIED — run retrying (attempt 4, jobs test(3.11)/test(3.12) still running) |
| Market Beating System - Crypto & Forex Priority | 12 | 24 | [43603128044](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43603128044) | 2026-11-14T14:06:36Z | _run retrying (no completed failed job now)_ | UNVERIFIED — run retrying (attempt 5 in progress) |
| Signal Tracking & Validation - Beat the Market | 11 | 23 | [43602685216](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43602685216) | 2026-11-14T14:01:32Z | `track-and-validate` / Install dependencies | pandas 2.1.4 source build under Python 3.14: `_PyLong_AsByteArray` expected 6 args, have 5 |
| Forward Test - Strategy Validation | 6 | 12 | [43593382356](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43593382356) | 2026-11-14T12:09:06Z | `forward-test` / Install dependencies | same pandas/Python-3.14 build failure |
| Live Trading Bot | 6 | 12 | [43593223780](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43593223780) | 2026-11-14T12:07:07Z | `trade` / Install dependencies | same pandas/Python-3.14 build failure |
| Live Trading Bot - Canada Edition | 6 | 12 | [43593359756](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43593359756) | 2026-11-14T12:08:49Z | `trade` / Install dependencies | same pandas/Python-3.14 build failure |
| Live Trading Bot - Canada Edition (FREE Data) | 6 | 12 | [43593366467](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43593366467) | 2026-11-14T12:08:54Z | `trade` / Install dependencies | same pandas/Python-3.14 build failure |
| Autonomous Trading Bot - Runs Automatically Every 4 Hours | 5 | 11 | [43592761629](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43592761629) | 2026-11-14T12:01:27Z | `trade` / Install dependencies | same pandas/Python-3.14 build failure |
| DNA Strategy Pipeline | 5 | 11 | [43575056444](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43575056444) | 2026-11-14T08:16:53Z | `Generate Active Picks` / Generate Picks | `OSError: [Errno 24] Too many open files` in `alpha_engine/__init__.py` |
| Crypto Picks Dispatch | 5 | 11 | [43593034946](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43593034946) | 2026-11-14T12:04:50Z | `dispatch` / Install dependencies | same pandas/Python-3.14 build failure |
| Self-Optimizing Trading Bot - Auto-Validates & Tweaks | 5 | 11 | [43592941157](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43592941157) | 2026-11-14T12:03:38Z | `trade` / Install dependencies | same pandas/Python-3.14 build failure |
| Mirror: findtorontoevents.ca  torontoevent.net | 4 | 8 | [43593541152](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43593541152) | 2026-11-14T12:11:02Z | `mirror` / Download from findtorontoevents.ca (50webs FTP) | `The action 'Download from findtorontoevents.ca (50webs FTP)' has timed out after 30 minutes` |
| Daily Price Refresh | 2 | 4 | [43544373994](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43544373994) | 2026-11-14T02:05:57Z | `refresh-prices` / Refresh all stock tickers via fetch_prices.php | `fetch_prices.php returned HTTP 404` (expected 200) — daily_prices ingest broken |
| robust-edge-miner | 2 | 4 | [43596188828](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43596188828) | 2026-11-14T12:43:13Z | _run retrying (no completed failed job now)_ | UNVERIFIED — run retrying (attempt 8 at snapshot) |
| ALPHA ENGINE - Live Autonomous Scanner | 1 | 1 | [43603342689](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43603342689) | 2026-11-14T14:09:02Z | _run retrying (no completed failed job now)_ | UNVERIFIED — run retrying (attempt 3 in progress) |
| Daily Prices yfinance Refresh | 1 | 2 | [43521235051](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43521235051) | 2026-11-13T22:40:47Z | `refresh` / Run python3 tools/refresh_daily_prices_yf.py --days 30 | `ModuleNotFoundError: No module named 'tools'` |
| Deploy Rise of the Claw Dashboard | 1 | 1 | [43559740169](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43559740169) | 2026-11-14T05:04:38Z | `deploy` / Deploy to GitHub Pages | `No artifacts named "github-pages" were found for this workflow run` |
| LIVE SPIKE TRADING - Autonomous Crypto Monitor | 1 | 1 | [43546586116](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43546586116) | 2026-11-14T02:29:28Z | `spike-trading` / Commit results | `ERROR: All 8 push attempts failed` |
| H-002 PEAD Shadow Collector | 1 | 2 | [43520036730](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43520036730) | 2026-11-13T22:32:00Z | `collect-pead-shadow` / Commit shadow log | `ERROR: All 10 push attempts failed — next cycle will self-heal.` |
| [torontoevent.net] Run Backtests & Deploy Dashboards | 1 | 1 | [43502887476](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43502887476) | 2026-11-13T20:35:02Z | `backtest` / Verify *** deployments | `##[error]Process completed with exit code 28` (curl timeout in deploy verification) |
| Verified pilot daily | 1 | 2 | [43566181363](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43566181363) | 2026-11-14T06:24:27Z | `pilot` / Run verified pilots | exit code 1; no error line in job log (UNVERIFIED detail) |

### Dominant root causes

1. **Python 3.14 vs pandas 2.1.4 (largest cluster, at least 9 workflows).** Workflows pin `python-version: '3.11'` with `actions/setup-python@v6` but also pass invalid input `update-environment: false`; the job then resolves the system interpreter (`/usr/include/python3.14`, pip from `/usr/lib/python3/dist-packages`), and `pandas==2.1.4` compiles from source and dies with `too few arguments to function ‘_PyLong_AsByteArray’; expected 6, have 5`.
2. **Alpha Engine fatal `KeyError: 'LONG'`** in 2 workflows (93 failed runs/24h combined), preceded by data-source failures: Binance HTTP 451 (geo), CoinMetrics 400/403 circuit breaker, `No module named 'xgboost'`, and per-strategy `KeyError: 'high'/'close'`.
3. **Git push contention**: Live Spike and H-002 PEAD exhaust 8 and 10 retry attempts (`All N push attempts failed`) — consistent with the known high-commit-frequency main branch.
4. **FTP/dashboard ops**: Mirror timed out at the 30-min step cap; `fetch_prices.php` returns HTTP 404; Pages deploy fails because no `github-pages` artifact was uploaded.
5. **Python import style**: `ModuleNotFoundError: No module named 'tools'` in `refresh_daily_prices_yf.py` (the documented relative-vs-direct-script gotcha in AGENTS.md).

## 3. Stale and never-run workflows

### Never run (20)

| Workflow | Path | State |
|---|---|---|
| Battleground Mass Backtest | `.github/workflows/battleground-mass-backtest.yml` | active |
| Clear Channel Command | `.github/workflows/clear-channel-command.yml` | active |
| Closed Picks Command | `.github/workflows/closed-picks-command.yml` | active |
| DB Credentials Test | `.github/workflows/db-credentials-test.yml` | active |
| Deploy FC API Hotfix (3 domains) | `.github/workflows/deploy-fc-api-hotfix.yml` | active |
| Deploy MOVIESHOWS3 Hotfix | `.github/workflows/deploy-movieshows3-hotfix.yml` | active |
| Deploy Strategy Bundle | `.github/workflows/deploy_bundle.yml` | active |
| Deploy fc/api/.env to GoDaddy (torontoevent.net) | `.github/workflows/deploy-fc-api-env-godaddy.yml` | active |
| Dynamic Runner Template | `.github/workflows/_dynamic-runner-template.yml` | active |
| Fast Stocks Competition  High Frequency Scanner | `.github/workflows/fast-stocks-competition.yml` | active |
| Fix Ghost Cards & Thumbnails  All Sites | `.github/workflows/fix-ghost-cards.yml` | active |
| Meme Coin Scanner  Fixed with Monitoring | `.github/workflows/meme-scanner-fixed.yml` | active |
| MySQL Dedup Fix | `.github/workflows/mysql_dedup_fix.yml` | active |
| REAL 2-HOUR CHALLENGE - Live Market Data | `.github/workflows/real_2hour_challenge.yml` | active |
| RL Agent (PPO) Train & Predict | `.github/workflows/rl-agent-ppo.yml` | active |
| Resolver Step 5-6 — at_raw_picks Backfill | `.github/workflows/resolver-step5-6-backfill.yml` | active |
| Resolver Step 7 — active_picks_sync APPLY | `.github/workflows/resolver-step7-apply.yml` | active |
| Test Fast Variants | `.github/workflows/test-fast.yml` | active |
| WSL Runner Manager | `.github/workflows/wsl-runner-manager.yml` | active |
| Won PNL Contradiction Backfill | `.github/workflows/won-pnl-contradiction-backfill.yml` | active |

### Stale >7d (36)

| Workflow | Last run (UTC) | Age | Last conclusion | 7d runs |
|---|---|---:|---|---:|
| Dependency Graph | 2026-05-23T07:22:58Z | 175.4d | success | 0 |
| DB Freshness Check (Legacy Manual) | 2026-05-23T18:28:36Z | 174.9d | failure | 0 |
| MySQL Q-001 — Create picks table + sync from JSON | 2026-05-24T08:48:30Z | 174.3d | failure | 0 |
| Pick Flow Snapshot (Fast) | 2026-05-24T21:50:32Z | 173.8d | success | 0 |
| Copilot cloud agent | 2026-05-25T21:12:04Z | 172.8d | success | 0 |
| ML Gatekeeper A/B Bootstrap | 2026-05-27T03:50:50Z | 171.5d | failure | 0 |
| Deploy Alpha Engine Dashboard | 2026-05-27T12:08:23Z | 171.2d | success | 0 |
| Deploy FriendTracker | 2026-05-27T12:08:23Z | 171.2d | success | 0 |
| Fix Battleground Deployment | 2026-05-27T12:08:23Z | 171.2d | success | 0 |
| strategy_performance.json no-regression guard | 2026-05-27T20:09:22Z | 170.8d | success | 0 |
| [torontoevent.net] Deploy Live Monitor APIs | 2026-06-03T14:30:17Z | 164.1d | success | 0 |
| Forex Agent | 2026-06-03T18:29:34Z | 163.9d | success | 0 |
| Forex Smart Picks Scanner | 2026-06-03T22:41:44Z | 163.7d | success | 0 |
| AI Tournament Pipeline — Daily Picks + DB Ingest | 2026-06-04T13:12:44Z | 163.1d | success | 0 |
| AI Leaderboard Refresh | 2026-06-05T02:38:12Z | 162.6d | success | 0 |
| DB Secret Scan | 2026-06-05T06:57:28Z | 162.4d | failure | 0 |
| Battleground Mass Backtest (Part 2 - Babies) | 2026-06-06T07:32:55Z | 161.4d | success | 0 |
| Real-Time Battle Test - Eliminate Losers, Optimize Winners | 2026-06-13T01:39:52Z | 154.6d | success | 0 |
| POC Picks Checkpoint (2-week reminder) | 2026-07-20T21:25:17Z | 116.8d | success | 0 |
| UEPS Value Resolver Quarterly | 2026-10-01T07:25:25Z | 44.4d | success | 0 |
| Discord Token Selftest | 2026-10-04T04:52:51Z | 41.5d | success | 0 |
| Fetch New Movies & TV Shows (Manual) | 2026-10-11T06:00:39Z | 34.4d | success | 0 |
| Kimi Fetch Movies/TV (Manual) | 2026-10-11T06:30:29Z | 34.4d | success | 0 |
| Backup Restore Verification | 2026-10-15T06:04:51Z | 30.4d | failure | 0 |
| Deploy FavCreators Frontend (/fc/) | 2026-10-18T01:47:05Z | 27.6d | success | 0 |
| UEPS Smoke Tests | 2026-10-20T03:03:30Z | 25.5d | success | 0 |
| Quant Auditor (fast PR check) | 2026-10-22T23:24:32Z | 22.7d | success | 0 |
| walkforward-gate | 2026-10-22T23:24:32Z | 22.7d | success | 0 |
| DB Password Leak Guard | 2026-10-23T17:26:23Z | 21.9d | success | 0 |
| masking-policy-lint | 2026-10-23T17:26:23Z | 21.9d | success | 0 |
| ML Monthly Full Retrain | 2026-11-01T04:01:08Z | 13.5d | success | 0 |
| Monthly DNA Tournament | 2026-11-01T06:13:31Z | 13.4d | success | 0 |
| Beta Portfolio Refresh (monthly) | 2026-11-01T06:29:57Z | 13.4d | success | 0 |
| Monthly Confidence Calibrator Refit (M-060) | 2026-11-01T07:05:33Z | 13.4d | success | 0 |
| Secret Rotation Reminder | 2026-11-01T09:07:09Z | 13.3d | success | 0 |
| H-103 Forward Logger | 2026-11-01T14:01:39Z | 13.1d | success | 0 |

Note: some stale entries are legitimately low-frequency schedules (monthly workflows last run 2026-11-01, e.g. ML Monthly Full Retrain, Monthly DNA Tournament) or intentionally disabled (`Forex Agent`, `Forex Smart Picks`, `AI Tournament Pipeline`, `Real-Time Battle Test`). The rest (last run May–October) appear abandoned.

## 4. Dashboard-pipeline health (`audit-dashboard.yml`, id 281988696)

| Metric | 24h | 7d |
|---|---:|---:|
| Runs | 24 | 168 |
| Success | 13 | 106 |
| Cancelled | 10 | 61 |
| In progress at snapshot | 1 | 1 |
| Success rate | 54.2% | 63.1% |

- Cron is `10 * * * *`; concurrency group `dashboard-publish`, `cancel-in-progress: false`, job `timeout-minutes: 115`.
- **Runtime has grown far past the documented 30–35 min.** Five sampled successful jobs ran **79.6, 81.9, 84.5, 86.7 and 104.2 minutes** (job `started_at`→`completed_at`; median 84.5 min for n=5). Run created→updated median was 121.0 min including queueing.
- With an hourly schedule and ~80–105 min jobs, GitHub keeps only the newest pending run per concurrency group and cancels older queued ones: **9 of the 24h cancellations were zero-job, queued audit-dashboard runs** (43470794969, 43500038928, 43517634445, 43535071245, 43545655088, 43560599415, 43570175588, 43589060993, 43603788378). 61/168 (36%) of 7d runs cancelled.
- Effect: the dashboard refreshes roughly every ~1.5–2h, not hourly — consistent with the peer finding that live payloads were ~1.4–1.6h old at 15:45Z.
- `push:` trigger remains absent as documented (2026-05-19 removal rationale intact in the workflow comments).

### Related pipeline workflows (last run snapshot)

| Workflow | Last run (UTC) | Age | Last conclusion | 24h runs | 24h fail |
|---|---|---:|---|---:|---:|

## 5. In-progress / retry-loop risk

- At capture, 17 runs were `in_progress`; most were fresh (<10 min). Two exceeded 3.5h: `Discord Bot  Persistent` (43593989922, started 12:16Z) and `DNA Strategy Pipeline` (43594177096, attempt 5).
- Several 48h failure records were re-running with high attempt counts at log time (`run_attempt` 3–8), indicating automated rerun/failure-guardian flapping: Sports smoke (a3), CI Tests (a4), Market Beating (a5), ALPHA Live (a3), robust-edge-miner (a8), DNA Strategy (a5), Daily Price Refresh (a8), Daily Prices yfinance (a8), H-002 PEAD (a8), Verified pilot daily (a8).

## 6. Warnings / deprecations

- GitHub annotations: **3** `##[warning]` lines, all `Node.js 20 is deprecated ... forced to run on Node.js 24` (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/download-artifact@v5`).
- No `::warning::` annotations were emitted; the 2 literal occurrences are echoed script text inside H-002 PEAD.
- Runtime `WARN` lines in the 19 sampled non-empty logs: **722**, dominated by Alpha Engine (`Kill switch: WARNING -- Dead features: 30/32 (94%) -- health_score=0.06`, Binance HTTP 451 fallbacks, anomaly alerts) and mirror retry notices.
- `DeprecationWarning`: 75 occurrences in sampled logs, chiefly Node `punycode` (`[DEP0040]`) in retry loops and Python `datetime.utcnow()` in `genome/generate_picks.py:447`.
- These counts are for sampled failure logs only; a repo-wide warning census would require downloading all 1,207 failed-run logs. See UNVERIFIED.

## 7. Evidence commands

```bash
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows --paginate \
  --jq '.workflows[] | {id,name,path,state}'          # 365 rows -> raw/A_workflows.json
gh run list --repo eltonaguiar/findtorontoevents_antigravity.ca --limit 500 \
  --json databaseId,name,workflowName,event,status,conclusion,createdAt,updatedAt,headBranch,number,url
gh api repos/.../actions/workflows/<id>/runs?per_page=10
gh api repos/.../actions/workflows/<id>/runs?per_page=100&created=%3E%3D2026-11-13T16:05:00Z   # 24h
gh api repos/.../actions/workflows/<id>/runs?per_page=100&created=%3E%3D2026-11-07T16:05:00Z   # 7d
# paginated to completion for 96 workflows with >100 runs/7d (raw/wf7d_full/*.jsonl)
gh api repos/.../actions/runs/<id>/jobs?per_page=100
gh run view <id> --repo ... --log-failed        # 19 sampled logs in raw/logs/
gh api repos/.../actions/jobs/<job_id>/logs     # fallback when --log-failed refused an in-progress run
```

Exact reconstructed totals (summed across all 365 workflows): 24h = **4,109** runs; 7d = **28,187** runs. Repo-level `actions/runs?created=>=...` returns `total_count=2500` for both windows (API cap), so repo-level `total_count` was **not** used for any window aggregate.

## 8. UNVERIFIED

- Root errors for runs that were mid-retry when logs were requested: Sports endpoint smoke + Playwright (43609430834), CI Tests (43605861085), Market Beating (43603128044), robust-edge-miner (43596188828), ALPHA ENGINE - Live Autonomous Scanner (43603342689).
- 7d count of zero-job cancelled runs (only the 82 runs in 24h were job-checked; 15 had zero jobs).
- Repo-wide warning/deprecation census (only 19 failed logs sampled).
- Whether the `update-environment: false` failure is specific to a self-hosted runner label (`vars.ACTIONS_RUNNER_LABEL`) or applies to cloud `ubuntu-latest`; logs show Python 3.14 and `/usr/include/python3.14`, but the runner label per job was not captured.

## Appendix — per-workflow last-run matrix (365 rows)

Also written as CSV: `sub/A_workflow_matrix.csv`. Legend: r24/r7 = total runs; s/f/c = success/failure/cancelled.

| Workflow | Last run UTC | Age | Last state | Last event | r24 | s24 | f24 | c24 | r7 | s7 | f7 | c7 |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Deploy Competition to Live Site | 2026-11-14T15:58:08Z | 0.0d | success | workflow_run | 159 | 149 | 0 | 0 | 1000 | 908 | 22 | 0 |
| Meme Coin Scanner v2  Fixed & Monitored | 2026-11-14T15:52:27Z | 0.0d | success | schedule | 172 | 172 | 0 | 0 | 1000 | 995 | 2 | 3 |
| TV Paper TP/SL Watchdog | 2026-11-14T16:00:39Z | 0.0d | success | schedule | 95 | 95 | 0 | 0 | 662 | 661 | 1 | 0 |
| Sports data snapshots | 2026-11-14T15:48:21Z | 0.0d | success | schedule | 94 | 94 | 0 | 0 | 649 | 635 | 13 | 0 |
| Deploy FindCryptoPairs to FTP | 2026-11-14T15:50:54Z | 0.0d | success | workflow_run | 52 | 52 | 0 | 0 | 363 | 353 | 1 | 0 |
| Crypto Signal Engine | 2026-11-14T16:00:52Z | 0.0d | success | schedule | 49 | 49 | 0 | 0 | 343 | 343 | 0 | 0 |
| [torontoevent.net] Deploy Rise of the Claw | 2026-11-14T15:32:39Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 337 | 336 | 0 | 0 |
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | 2026-11-14T15:48:59Z | 0.0d | in_progress | schedule | 48 | 0 | 47 | 0 | 336 | 146 | 113 | 75 |
| ALPHA ENGINE Gainer Capture (15min) | 2026-11-14T15:42:21Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 336 | 0 | 0 |
| Claude Gainer ML  Live Scanner | 2026-11-14T15:48:24Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 330 | 1 | 4 |
| Cross-System Signal Aggregator | 2026-11-14T15:41:22Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 326 | 1 | 9 |
| Gainer Predictor Scanner | 2026-11-14T16:01:06Z | 0.0d | in_progress | schedule | 48 | 45 | 0 | 2 | 336 | 333 | 0 | 2 |
| Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities | 2026-11-14T15:32:53Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 330 | 1 | 4 |
| Polymarket Prediction Market Signals (Multi-Asset) | 2026-11-14T15:44:21Z | 0.0d | success | schedule | 48 | 47 | 0 | 1 | 336 | 335 | 0 | 1 |
| Rapid Fire - NOW Scanner | 2026-11-14T15:47:48Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 326 | 0 | 9 |
| Sustained Gainer Confluence Scanner | 2026-11-14T15:48:08Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 334 | 1 | 0 |
| Swarm State Sync | 2026-11-14T16:01:05Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 336 | 0 | 0 |
| Winner Pattern Precursor Scanner | 2026-11-14T15:48:17Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 329 | 1 | 5 |
| [torontoevent.net] Spike Scanner | 2026-11-14T16:00:39Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 336 | 336 | 0 | 0 |
| Claude's Test - Portfolio Manager | 2026-11-14T15:34:01Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 335 | 330 | 0 | 5 |
| Consensus Outcome Tracker | 2026-11-14T15:33:37Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 335 | 334 | 1 | 0 |
| Copy Trader Intelligence  Scrape + Analyze + Track | 2026-11-14T15:53:38Z | 0.0d | in_progress | schedule | 48 | 47 | 0 | 0 | 335 | 333 | 1 | 0 |
| Deploy Rise of the Claw Dashboard | 2026-11-14T15:32:19Z | 0.0d | success | schedule | 48 | 47 | 1 | 0 | 335 | 318 | 15 | 1 |
| QUAN ENGINE - Live Autonomous Scanner | 2026-11-14T15:33:51Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 335 | 334 | 1 | 0 |
| Regime Terminal  HMM Live Scanner | 2026-11-14T16:02:45Z | 0.0d | in_progress | schedule | 48 | 47 | 0 | 1 | 335 | 326 | 0 | 9 |
| actions-failure-guardian | 2026-11-14T15:33:00Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 335 | 333 | 2 | 0 |
| ALPHA ENGINE - Quant Stack (KAMA + ATR + Regime) | 2026-11-14T15:35:48Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 334 | 333 | 1 | 0 |
| Claude Gainer Short-Term Predictor | 2026-11-14T15:40:32Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 334 | 333 | 1 | 0 |
| ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | 2026-11-14T15:35:02Z | 0.0d | in_progress | schedule | 48 | 0 | 46 | 1 | 333 | 206 | 118 | 8 |
| MOMENTUM CATCHER - Real-time Pump Detector | 2026-11-14T15:35:21Z | 0.0d | success | schedule | 48 | 48 | 0 | 0 | 330 | 329 | 1 | 0 |
| Conflict Marker Check | 2026-11-14T16:01:24Z | 0.0d | success | push | 54 | 53 | 0 | 1 | 285 | 283 | 0 | 2 |
| No stale DB passwords | 2026-11-14T16:01:24Z | 0.0d | success | push | 54 | 53 | 0 | 1 | 285 | 283 | 0 | 2 |
| Master Automation Scheduler | 2026-11-14T15:04:57Z | 0.0d | success | schedule | 31 | 31 | 0 | 0 | 218 | 217 | 1 | 0 |
| Analyst Tracker  Top 20 Crypto Analysts | 2026-11-14T15:03:21Z | 0.0d | success | schedule | 29 | 29 | 0 | 0 | 210 | 210 | 0 | 0 |
| Deploy Battleground to FTP | 2026-11-14T15:17:12Z | 0.0d | success | schedule | 28 | 28 | 0 | 0 | 196 | 195 | 1 | 0 |
| Meta-Strategy Permutation Engine | 2026-11-14T15:21:27Z | 0.0d | success | schedule | 28 | 28 | 0 | 0 | 196 | 187 | 0 | 8 |
| [torontoevent.net] Run Backtests & Deploy Dashboards | 2026-11-14T12:08:04Z | 0.2d | success | schedule | 29 | 28 | 1 | 0 | 177 | 174 | 2 | 0 |
| [torontoevent.net] Run Backtests & Deploy Dashboards (ROOCODE) | 2026-11-14T16:00:37Z | 0.0d | success | schedule | 29 | 29 | 0 | 0 | 177 | 176 | 1 | 0 |
| [torontoevent.net] Deploy Competition to Live Site | 2026-11-14T15:22:11Z | 0.0d | success | workflow_run | 24 | 24 | 0 | 0 | 175 | 164 | 2 | 0 |
| Live Trading Monitor  Auto Refresh | 2026-11-14T15:45:57Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 169 | 169 | 0 | 0 |
| ANTIGRAVITY ML  Hourly Discord Status + Picks (DISABLED) | 2026-11-14T15:08:22Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| AsterDEX Paper Trading | 2026-11-14T15:11:12Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 166 | 2 | 0 |
| Audit Hourly Update | 2026-11-14T15:21:24Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 166 | 1 | 0 |
| Baby Strat Real Forward Monitor | 2026-11-14T15:19:41Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 0 | 0 |
| Breakout Arena  3 Approaches | 2026-11-14T15:12:39Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Coinglass DNA Scanner | 2026-11-14T15:10:14Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 166 | 1 | 1 |
| Contested Pick Checker (Claude vs Antigravity) | 2026-11-14T15:05:37Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Conviction Picks Ultra-Selective Discord Alert | 2026-11-14T15:57:03Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Copy Trader Forward Test | 2026-11-14T15:21:05Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 0 | 0 |
| Crypto Gainer ML Live Tracker | 2026-11-14T15:09:27Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| DARWIN ENGINE - DNA Evolution Pipeline | 2026-11-14T15:03:33Z | 0.0d | success | schedule | 24 | 23 | 0 | 1 | 168 | 158 | 0 | 9 |
| DB Freshness Guardian | 2026-11-14T16:01:12Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Dashboard Pick Trader | 2026-11-14T15:47:09Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 0 | 1 |
| EMA Retracement Mean Reversion Scanner | 2026-11-14T15:15:25Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Feed Health Check | 2026-11-14T15:28:19Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Forward Trade Tracking v2 | 2026-11-14T16:01:31Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| GHCOPILOT prospective paper monitor | 2026-11-14T15:40:29Z | 0.0d | success | schedule | 24 | 23 | 0 | 1 | 168 | 167 | 0 | 1 |
| Hindsight Learner  Hourly Winner Analysis | 2026-11-14T15:10:23Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 166 | 1 | 1 |
| Hourly Master Picks to Discord | 2026-11-14T15:10:24Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Hub Data Sync | 2026-11-14T15:24:41Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Live Picks Tracker | 2026-11-14T15:26:20Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Low-Score Winner Tracker | 2026-11-14T15:10:42Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| LuxAlgo Signal Generator | 2026-11-14T15:28:31Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 166 | 0 | 2 |
| ML Battleground System F (Claws of Doom) | 2026-11-14T15:49:17Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 0 | 1 |
| MOMENTUM TRACKER - Real-Time Gainer Scanner | 2026-11-14T15:38:23Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Mega Mutation Live Tracker | 2026-11-14T15:46:28Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Mercury 2  Signal Scanner | 2026-11-14T15:38:17Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Missed Opportunity Analyzer Hourly Self-Improvement | 2026-11-14T15:22:23Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 158 | 10 | 0 |
| MySQL Trading Picks Sync | 2026-11-14T15:34:42Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| OBI Hourly Snapshot | 2026-11-14T15:35:19Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Outcome Resolver  Validate Unresolved Picks | 2026-11-14T15:19:09Z | 0.0d | cancelled | schedule | 24 | 1 | 0 | 23 | 168 | 5 | 1 | 161 |
| Picks-Now Live PnL (hourly) | 2026-11-14T15:50:49Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Portfolio Trackers (Real Money + Theory) | 2026-11-14T15:18:04Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 166 | 1 | 0 |
| Prediction Quality Tracker | 2026-11-14T15:47:41Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Quick Guess ML Agent | 2026-11-14T15:12:23Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Recommended Portfolio Generator | 2026-11-14T15:30:39Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Send Accountability Reminders | 2026-11-14T16:04:33Z | 0.0d | in_progress | schedule | 25 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Signal Integrator - Isolated Source Aggregator | 2026-11-14T15:19:23Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 0 | 0 |
| Signal Quality Monitor | 2026-11-14T15:17:22Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Signal Recorder | 2026-11-14T15:51:12Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Skyrocket Detector  Live Scanner | 2026-11-14T15:35:45Z | 0.0d | success | schedule | 24 | 23 | 0 | 1 | 168 | 162 | 0 | 6 |
| Smart Picks Tracker | 2026-11-14T15:56:44Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 168 | 0 | 0 |
| Sports endpoint smoke + Playwright | 2026-11-14T15:18:06Z | 0.0d | failure | schedule | 24 | 0 | 24 | 0 | 168 | 0 | 167 | 0 |
| Strategy Funnel Hourly Refresh | 2026-11-14T15:46:30Z | 0.0d | success | schedule | 24 | 9 | 0 | 15 | 168 | 37 | 0 | 131 |
| Test Portfolios  Hourly Strategy Validation | 2026-11-14T15:24:27Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| Unified Audit Dashboard | 2026-11-14T15:14:13Z | 0.0d | in_progress | schedule | 24 | 13 | 0 | 10 | 168 | 106 | 0 | 61 |
| VOLATILE ALT SCANNER Hyperliquid High-Vol Alts | 2026-11-14T15:10:06Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| [torontoevent.net] Rapid Validation Engine | 2026-11-14T15:22:04Z | 0.0d | success | schedule | 24 | 24 | 0 | 0 | 168 | 167 | 1 | 0 |
| pages-build-deployment | 2026-11-14T15:27:26Z | 0.0d | success | dynamic | 24 | 24 | 0 | 0 | 167 | 167 | 0 | 0 |
| Pine Script Generator | 2026-11-14T15:33:54Z | 0.0d | skipped | workflow_run | 39 | 0 | 0 | 0 | 151 | 54 | 0 | 0 |
| Meme Coin Scanner Auto Scan & Resolve | 2026-11-14T15:00:36Z | 0.0d | success | schedule | 20 | 20 | 0 | 0 | 140 | 139 | 1 | 0 |
| Audit Drift Telemetry | 2026-11-14T14:37:47Z | 0.1d | success | push | 20 | 20 | 0 | 0 | 139 | 138 | 1 | 0 |
| KIMI_FEB172026 - Live Trading System | 2026-11-14T16:02:14Z | 0.0d | in_progress | schedule | 19 | 18 | 0 | 0 | 133 | 133 | 0 | 0 |
| CI Tests | 2026-11-14T14:37:47Z | 0.1d | failure | push | 15 | 0 | 15 | 0 | 108 | 0 | 108 | 0 |
| Money-Ready Registry Gate | 2026-11-14T14:37:47Z | 0.1d | success | push | 15 | 15 | 0 | 0 | 108 | 108 | 0 | 0 |
| KIMI Goldmine Data Collection | 2026-11-14T14:04:59Z | 0.1d | success | schedule | 14 | 14 | 0 | 0 | 104 | 104 | 0 | 0 |
| Enhanced ML Crypto Train & Predict | 2026-11-14T14:20:43Z | 0.1d | success | schedule | 13 | 13 | 0 | 0 | 91 | 90 | 0 | 0 |
| ALPHA  Verify Predictions | 2026-11-14T14:29:34Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 84 | 0 | 0 |
| ALPHA ENGINE - Incubator Strategies | 2026-11-14T14:18:44Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 83 | 0 | 0 |
| ALPHA ENGINE - Live Autonomous Scanner | 2026-11-14T14:09:02Z | 0.1d | failure | schedule | 12 | 0 | 1 | 11 | 84 | 54 | 1 | 29 |
| Backfill Missing Audit Trail Sources | 2026-11-14T14:07:25Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 84 | 0 | 0 |
| CRYPTO SMART PICKS - Portfolio A/B/C/D Scanner | 2026-11-14T14:48:56Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 84 | 0 | 0 |
| Check Streamer Live Status | 2026-11-14T16:03:06Z | 0.0d | in_progress | schedule | 12 | 11 | 0 | 0 | 84 | 83 | 0 | 0 |
| Continuous Improvement Monitor | 2026-11-14T14:39:56Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 84 | 0 | 0 |
| Copy Trader Portfolio Tracker | 2026-11-14T14:43:01Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 83 | 0 | 1 |
| Daily Feed Summary | 2026-11-14T14:05:19Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 84 | 0 | 0 |
| Dynamic Universe Scanner | 2026-11-14T14:39:59Z | 0.1d | success | schedule | 12 | 11 | 0 | 1 | 84 | 83 | 0 | 1 |
| FC-CRYPTO PRO Top Actionable Picks | 2026-11-14T14:09:25Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 83 | 1 | 0 |
| Forward Signal Scanner | 2026-11-14T14:07:41Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 83 | 1 | 0 |
| LIVE SPIKE TRADING - Autonomous Crypto Monitor | 2026-11-14T14:29:31Z | 0.1d | success | schedule | 12 | 11 | 1 | 0 | 84 | 83 | 1 | 0 |
| ML Strategy Reviver Bridge & Standalone | 2026-11-14T14:26:22Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 82 | 1 | 1 |
| Market Beating System - Crypto & Forex Priority | 2026-11-14T14:06:36Z | 0.1d | failure | schedule | 12 | 0 | 12 | 0 | 84 | 0 | 83 | 0 |
| Pick Monitor & Price Validator (30min) | 2026-11-14T16:01:11Z | 0.0d | success | schedule | 12 | 12 | 0 | 0 | 84 | 84 | 0 | 0 |
| Prediction Market Agents | 2026-11-14T14:16:56Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 84 | 0 | 0 |
| Proven Strategies Scanner | 2026-11-14T16:02:56Z | 0.0d | in_progress | schedule | 12 | 11 | 0 | 0 | 84 | 83 | 0 | 0 |
| Signal Tracking & Validation - Beat the Market | 2026-11-14T16:01:33Z | 0.0d | in_progress | schedule | 12 | 0 | 11 | 0 | 84 | 0 | 83 | 0 |
| Social Media Prediction Tracker | 2026-11-14T14:30:54Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 84 | 0 | 0 |
| Spike Scanner | 2026-11-14T14:09:25Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 83 | 1 | 0 |
| Strategy Forward Tester | 2026-11-14T14:17:15Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 82 | 2 | 0 |
| System Health Check | 2026-11-14T14:09:46Z | 0.1d | success | schedule | 12 | 12 | 0 | 0 | 84 | 83 | 1 | 0 |
| Update Creator News | 2026-11-14T16:01:16Z | 0.0d | in_progress | schedule | 12 | 11 | 0 | 0 | 84 | 83 | 0 | 0 |
| Top Gainers Spike Scanner | 2026-11-13T19:30:37Z | 0.9d | success | schedule | 7 | 7 | 0 | 0 | 70 | 70 | 0 | 0 |
| DNA Genome Daily Pipeline | 2026-11-14T15:01:02Z | 0.0d | success | schedule | 8 | 8 | 0 | 0 | 56 | 56 | 0 | 0 |
| Mutation Lab  Strategy Evolution Pipeline | 2026-11-14T15:03:51Z | 0.0d | success | schedule | 8 | 8 | 0 | 0 | 56 | 55 | 1 | 0 |
| Claude Code Gainer ML Tracker | 2026-11-14T13:17:32Z | 0.1d | success | schedule | 7 | 7 | 0 | 0 | 50 | 49 | 0 | 0 |
| ALPHA ENGINE - Trend Catcher (4H Adaptive) | 2026-11-14T12:16:27Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| ALPHA ENGINE - Universe Expander | 2026-11-14T12:55:51Z | 0.1d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Autonomous Trading Bot - Runs Automatically Every 4 Hours | 2026-11-14T16:01:06Z | 0.0d | in_progress | schedule | 6 | 0 | 5 | 0 | 42 | 0 | 41 | 0 |
| Crypto Picks Dispatch | 2026-11-14T16:03:05Z | 0.0d | in_progress | schedule | 6 | 0 | 5 | 0 | 42 | 0 | 41 | 0 |
| Crypto Test Portfolios | 2026-11-14T12:18:46Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| DNA Strategy Pipeline | 2026-11-14T12:18:41Z | 0.2d | in_progress | schedule | 6 | 0 | 5 | 0 | 42 | 0 | 41 | 0 |
| Daily Top-Picks Filter | 2026-11-14T12:26:32Z | 0.1d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Deploy Vetted Master-Picks | 2026-11-14T12:21:06Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 41 | 0 | 0 |
| Discord Channel Heartbeat | 2026-11-14T12:08:17Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Forward Test - Strategy Validation | 2026-11-14T12:09:06Z | 0.2d | failure | schedule | 6 | 0 | 6 | 0 | 42 | 0 | 42 | 0 |
| Live Trading Bot | 2026-11-14T12:07:07Z | 0.2d | failure | schedule | 6 | 0 | 6 | 0 | 42 | 0 | 42 | 0 |
| Live Trading Bot - Canada Edition | 2026-11-14T12:08:49Z | 0.2d | failure | schedule | 6 | 0 | 6 | 0 | 42 | 0 | 42 | 0 |
| Live Trading Bot - Canada Edition (FREE Data) | 2026-11-14T12:08:54Z | 0.2d | failure | schedule | 6 | 0 | 6 | 0 | 42 | 0 | 42 | 0 |
| ML Forward Test 1745 Models | 2026-11-14T12:31:08Z | 0.1d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| MOMENTUM SCALP SCANNER - Dynamic Universe Expansion | 2026-11-14T16:00:41Z | 0.0d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Master-Picks Health Score | 2026-11-14T12:30:28Z | 0.1d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Parquet Data Ingestion | 2026-11-14T12:09:35Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Rapid Validation Engine | 2026-11-14T12:21:50Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 41 | 0 | 0 |
| Self-Optimizing Trading Bot - Auto-Validates & Tweaks | 2026-11-14T16:02:48Z | 0.0d | in_progress | schedule | 6 | 0 | 5 | 0 | 42 | 0 | 41 | 0 |
| Sidecar Status Markdown Update | 2026-11-14T12:16:30Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Specialized Scanners - Rocket, Short Engine, TSMOM | 2026-11-14T13:07:30Z | 0.1d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Strategy Health Monitor | 2026-11-14T16:04:39Z | 0.0d | in_progress | schedule | 7 | 6 | 0 | 0 | 42 | 41 | 0 | 0 |
| TradingView Strategy Scanner | 2026-11-14T16:02:55Z | 0.0d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| UEPS Pick Runner | 2026-11-14T12:22:15Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 41 | 0 | 0 |
| What Worked Active Picks Insights | 2026-11-14T12:13:03Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| crypto-ohlcv refresh | 2026-11-14T12:25:13Z | 0.2d | success | schedule | 6 | 6 | 0 | 0 | 42 | 42 | 0 | 0 |
| Run Backtests & Deploy Dashboards | 2026-11-14T12:13:22Z | 0.2d | success | schedule | 7 | 7 | 0 | 0 | 39 | 39 | 0 | 0 |
| Sports Betting  Odds Refresh & Auto-Settle | 2026-11-14T15:04:45Z | 0.0d | success | schedule | 5 | 5 | 0 | 0 | 35 | 35 | 0 | 0 |
| Crypto Winner Scanner  Auto Scan | 2026-11-14T12:05:04Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 29 | 29 | 0 | 0 |
| ALPHA ENGINE - ETF Emitter | 2026-11-14T12:16:43Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| Audit Impact Tracker | 2026-11-14T12:07:02Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| Buy Now Analysis & Tracking | 2026-11-14T12:06:36Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| Cross-Asset Correlation Monitor | 2026-11-14T12:18:50Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 27 | 1 | 0 |
| Data Pipeline Reliability Test | 2026-11-14T12:06:12Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) | 2026-11-14T12:03:51Z | 0.2d | success | workflow_dispatch | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| Discord Bot  Persistent | 2026-11-14T12:16:26Z | 0.2d | in_progress | schedule | 4 | 3 | 0 | 0 | 28 | 25 | 1 | 1 |
| FRED Macro Refresh | 2026-11-14T12:05:00Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| Forward-Test New Strategies Tracker | 2026-11-14T12:09:32Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 27 | 1 | 0 |
| Hoffman IRB Strategy Tracker | 2026-11-14T12:01:14Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| ML Feedback Loop | 2026-11-14T12:10:05Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| ML Model Auto-Training | 2026-11-14T12:14:59Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 27 | 1 | 0 |
| ML System Health Monitor | 2026-11-14T12:01:09Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| Mirror: findtorontoevents.ca  torontoevent.net | 2026-11-14T12:11:02Z | 0.2d | failure | schedule | 4 | 0 | 4 | 0 | 28 | 0 | 28 | 0 |
| Refresh Top Movies Data | 2026-11-14T12:03:01Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| gha-summary-report | 2026-11-14T12:12:45Z | 0.2d | success | schedule | 4 | 4 | 0 | 0 | 28 | 28 | 0 | 0 |
| Branch Large File Duplicate Guard | 2026-11-14T08:11:41Z | 0.3d | cancelled | push | 4 | 0 | 0 | 4 | 21 | 0 | 0 | 21 |
| Feature Signals — Non-LLM Emitters | 2026-11-14T08:28:52Z | 0.3d | success | schedule | 3 | 3 | 0 | 0 | 21 | 21 | 0 | 0 |
| Goldmine Tracker - Archive & Maintain | 2026-11-14T07:04:23Z | 0.4d | success | schedule | 3 | 3 | 0 | 0 | 21 | 20 | 1 | 0 |
| Picks NOW Refresh | 2026-11-14T12:03:40Z | 0.2d | success | schedule | 3 | 3 | 0 | 0 | 21 | 19 | 0 | 2 |
| [torontoevent.net] Goldmine Tracker - Archive & Maintain | 2026-11-14T07:05:45Z | 0.4d | success | schedule | 3 | 3 | 0 | 0 | 21 | 20 | 1 | 0 |
| Non-Crypto A/B Portfolio Tracker | 2026-11-13T19:32:53Z | 0.9d | success | schedule | 1 | 1 | 0 | 0 | 20 | 20 | 0 | 0 |
| Traditional Test Portfolios (5-8) | 2026-11-13T19:31:30Z | 0.9d | success | schedule | 1 | 1 | 0 | 0 | 20 | 20 | 0 | 0 |
| Pre-Spike Early Warning | 2026-11-13T14:10:59Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 |
| ALPHA ENGINE - Adaptive Trust Tuner | 2026-11-14T12:20:21Z | 0.2d | success | schedule | 2 | 2 | 0 | 0 | 14 | 14 | 0 | 0 |
| Deploy findtorontoevents.ca core site | 2026-11-14T04:12:31Z | 0.5d | success | workflow_run | 2 | 2 | 0 | 0 | 14 | 13 | 0 | 1 |
| Deploy findtorontoevents.ca next/events.json | 2026-11-14T04:12:31Z | 0.5d | success | workflow_run | 2 | 2 | 0 | 0 | 14 | 14 | 0 | 0 |
| Honest Kill Switch | 2026-11-14T12:09:38Z | 0.2d | success | schedule | 2 | 2 | 0 | 0 | 14 | 14 | 0 | 0 |
| ML Feedback Retrain  Learn from Closed Trades | 2026-11-14T12:26:25Z | 0.1d | success | schedule | 2 | 2 | 0 | 0 | 14 | 14 | 0 | 0 |
| Scrape events | 2026-11-14T04:06:50Z | 0.5d | success | schedule | 2 | 2 | 0 | 0 | 14 | 14 | 0 | 0 |
| Sports Prediction Market Sync | 2026-11-14T14:07:41Z | 0.1d | success | schedule | 2 | 2 | 0 | 0 | 14 | 14 | 0 | 0 |
| robust-edge-miner | 2026-11-14T12:43:13Z | 0.1d | failure | schedule | 2 | 0 | 2 | 0 | 14 | 0 | 14 | 0 |
| Futures Agent | 2026-11-13T22:03:33Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 11 | 11 | 0 | 0 |
| Commodities Agent | 2026-11-13T20:01:18Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 10 | 10 | 0 | 0 |
| Daily Price Refresh | 2026-11-14T02:05:57Z | 0.6d | failure | schedule | 2 | 0 | 2 | 0 | 10 | 0 | 10 | 0 |
| Daily Stock Data Refresh | 2026-11-13T22:34:31Z | 0.7d | success | schedule | 1 | 1 | 0 | 0 | 10 | 10 | 0 | 0 |
| ETF & Bond Scanner | 2026-11-13T14:05:51Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 10 | 10 | 0 | 0 |
| Equities & Stocks Agent | 2026-11-13T21:03:11Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 10 | 10 | 0 | 0 |
| Automated Reporting | 2026-11-14T08:09:23Z | 0.3d | success | schedule | 1 | 1 | 0 | 0 | 8 | 8 | 0 | 0 |
| A/B Analysis + Zero-PnL Audit | 2026-11-14T05:34:36Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| AI Leaderboard Freshness (daily FTP + data rebuild) | 2026-11-14T04:32:31Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| AI Tournament Price Tracker | 2026-11-13T23:03:48Z | 0.7d | success | schedule | 1 | 1 | 0 | 0 | 7 | 6 | 0 | 1 |
| Academic Strategies Daily | 2026-11-14T13:00:49Z | 0.1d | cancelled | schedule | 1 | 0 | 0 | 1 | 7 | 1 | 0 | 6 |
| Asset Class Freshness Watchdog | 2026-11-14T13:35:03Z | 0.1d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Audit Frontend Manifest | 2026-11-14T07:41:38Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Auto-Retire — Daily Bleeder Check | 2026-11-14T09:34:21Z | 0.3d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Auto-Shutdown Source Monitor | 2026-11-14T08:04:38Z | 0.3d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Backfill OHLCV Features | 2026-11-14T04:09:10Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Benchmark Comparison  Daily | 2026-11-14T07:08:51Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Blacklist Reconciler (cross-check vs live systems) | 2026-11-14T04:03:02Z | 0.5d | cancelled | schedule | 1 | 0 | 0 | 1 | 7 | 0 | 0 | 7 |
| Cross-DB Consistency Guardian (M-005) | 2026-11-14T02:03:31Z | 0.6d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Cross-DB Strategy Consistency Audit | 2026-11-14T06:06:15Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| DB Sync: Bi-directional User Data | 2026-11-14T08:12:32Z | 0.3d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| DB Sync: findtorontoevents.ca  torontoevent.net | 2026-11-14T06:05:06Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| DNA Mutation Cycle | 2026-11-14T05:03:36Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Daily Per-Class Scrutiny Engine | 2026-11-14T07:34:22Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Daily Runs | 2026-11-14T00:05:09Z | 0.7d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Decile Separation Test | 2026-11-14T06:11:20Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Edge stability refresh | 2026-11-14T01:38:40Z | 0.6d | success | schedule | 1 | 1 | 0 | 0 | 7 | 3 | 4 | 0 |
| Edge stability refresh | 2026-11-14T00:43:03Z | 0.6d | success | schedule | 1 | 1 | 0 | 0 | 7 | 2 | 0 | 5 |
| FINDTORONTOEVENTS.CA Database Backups | 2026-11-14T04:01:28Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Funding-Rate Archive Collector | 2026-11-14T00:44:15Z | 0.6d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| GHA stale workflows audit | 2026-11-14T05:34:40Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Gate Config Emit | 2026-11-14T05:07:15Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Hierarchical Bayesian Edge Update | 2026-11-14T02:34:26Z | 0.6d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Hyro Quan Bridge Regen | 2026-11-14T05:42:58Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Hyro daily (filter + backtest) | 2026-11-14T13:37:50Z | 0.1d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Incidents + Enhancements — Nightly Page Render | 2026-11-14T04:33:06Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Incubator Pipeline  Strategy Graduation | 2026-11-14T06:17:33Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Index All Creator Content | 2026-11-14T03:06:30Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| ML Battleground Daily Retrain | 2026-11-14T04:09:40Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| ML Gatekeeper Train A/B (Phase D) | 2026-11-13T19:16:31Z | 0.9d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| ML Model Staleness Watchdog | 2026-11-14T13:05:56Z | 0.1d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Money-Ready Verdict Snapshot | 2026-11-14T06:22:49Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Mutation Lifecycle Runner | 2026-11-14T05:34:57Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| MySQL Stale OPEN Picks Resolver | 2026-11-14T04:09:48Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Operator Review — Manual Candidates daily snapshot | 2026-11-14T07:11:02Z | 0.4d | cancelled | schedule | 1 | 0 | 0 | 1 | 7 | 0 | 0 | 7 |
| Optimize Score Thresholds | 2026-11-14T03:33:00Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Pick Data Quality Gate | 2026-11-14T13:19:07Z | 0.1d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Pick Funnel — nightly | 2026-11-14T04:05:36Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Populate alpha_macro Daily | 2026-11-13T21:10:21Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Prune strategy_performance.json (30d) | 2026-11-14T03:08:08Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Quant Auditor (deep nightly) | 2026-11-14T06:25:04Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Refresh Creator Updates | 2026-11-14T02:09:54Z | 0.6d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Refresh Movies Databases (50webs + GoDaddy) | 2026-11-14T07:00:41Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| SPY 20d Return Refresh | 2026-11-14T06:17:28Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| STOCKSUNIFY2 daily-stocks pull | 2026-11-14T13:10:49Z | 0.1d | cancelled | schedule | 1 | 0 | 0 | 1 | 7 | 0 | 0 | 7 |
| Schema Drift Audit | 2026-11-14T03:05:08Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Schema Drift Watchdog | 2026-11-14T09:15:35Z | 0.3d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Secret Scan (M-043) | 2026-11-14T04:09:09Z | 0.5d | cancelled | schedule | 1 | 0 | 0 | 1 | 7 | 0 | 0 | 7 |
| Sign-Coherence Gate | 2026-11-14T04:11:24Z | 0.5d | cancelled | schedule | 1 | 0 | 0 | 1 | 7 | 0 | 0 | 7 |
| Social Media Algo Trader Investigation | 2026-11-14T12:00:52Z | 0.2d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Statistical Rigor Validation - Thousands of Signals | 2026-11-14T00:10:14Z | 0.7d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Strategy Health Report | 2026-11-14T08:03:16Z | 0.3d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Strategy Perf By Class Rebuild | 2026-11-14T13:44:10Z | 0.1d | success | schedule | 1 | 1 | 0 | 0 | 7 | 6 | 0 | 1 |
| Swarm Pick Review (resolve + weekly + patterns + tournament promotion) | 2026-11-14T03:08:47Z | 0.5d | cancelled | schedule | 1 | 0 | 0 | 1 | 7 | 0 | 0 | 7 |
| Validate HF by asset class | 2026-11-14T06:38:15Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Verified pilot daily | 2026-11-14T06:24:27Z | 0.4d | failure | schedule | 1 | 0 | 1 | 0 | 7 | 0 | 7 | 0 |
| macd_rsi_m048 Shadow Generator | 2026-11-13T23:40:03Z | 0.7d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| paper-pilot-daily | 2026-11-14T13:31:14Z | 0.1d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| rsi5070 Forward-Test Snapshot (Daily) | 2026-11-14T07:03:08Z | 0.4d | cancelled | schedule | 1 | 0 | 0 | 1 | 7 | 0 | 0 | 7 |
| swarm-janitor | 2026-11-14T04:07:22Z | 0.5d | success | schedule | 1 | 1 | 0 | 0 | 7 | 7 | 0 | 0 |
| Alpha Engine  Daily Picks | 2026-11-13T22:03:29Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 |
| Daily Picks Snapshot  Crypto, Forex & Stocks | 2026-11-13T22:05:28Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 |
| Daily Regime Detection + Position Sizing | 2026-11-13T20:34:05Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 |
| SEC EDGAR  Insider Trades & 13F Holdings | 2026-11-13T13:07:17Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 6 | 6 | 0 | 0 |
| Track Quick Pick Portfolios | 2026-11-13T23:08:00Z | 0.7d | success | schedule | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 |
| World-Class Algorithm Pipeline | 2026-11-13T20:45:27Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 |
| World-Class Intelligence  Daily Pipeline | 2026-11-13T11:30:29Z | 1.2d | success | schedule | 0 | 0 | 0 | 0 | 6 | 6 | 0 | 0 |
| 🧠 Smart Money Intelligence | 2026-11-13T11:07:35Z | 1.2d | success | schedule | 0 | 0 | 0 | 0 | 6 | 6 | 0 | 0 |
| 2hour-challenge | 2026-11-13T12:13:46Z | 1.2d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| AI-Model Portfolios — Daily EOD | 2026-11-13T22:01:32Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 5 | 5 | 0 | 0 |
| ALPHA ENGINE - Equity 52wk High Breakout Scanner | 2026-11-13T22:32:28Z | 0.7d | success | schedule | 1 | 1 | 0 | 0 | 5 | 5 | 0 | 0 |
| Bond Agent | 2026-11-13T14:33:36Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| DXY State Update | 2026-11-13T13:35:30Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| Daily Miracle DayTrades Scan | 2026-11-13T23:01:04Z | 0.7d | success | schedule | 1 | 1 | 0 | 0 | 5 | 5 | 0 | 0 |
| Daily Prices yfinance Refresh | 2026-11-13T22:40:47Z | 0.7d | failure | schedule | 1 | 0 | 1 | 0 | 5 | 0 | 5 | 0 |
| Daily Stock Picks Generator (STOCKSUNIFY) | 2026-11-13T21:38:56Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 5 | 5 | 0 | 0 |
| ETF Agent | 2026-11-13T14:36:13Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| Edge decay monitor | 2026-11-13T07:24:16Z | 1.4d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| Growth Stock Screener Daily | 2026-11-13T14:12:02Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| H-002 PEAD Shadow Collector | 2026-11-13T22:32:00Z | 0.7d | failure | schedule | 1 | 0 | 1 | 0 | 5 | 0 | 5 | 0 |
| Penny Skyrocket Detector | 2026-11-13T14:48:38Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| Penny Stock Daily Picks | 2026-11-13T12:02:49Z | 1.2d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| STOCKSUNIFY Daily Stock Picks | 2026-11-13T21:40:49Z | 0.8d | success | schedule | 1 | 1 | 0 | 0 | 5 | 5 | 0 | 0 |
| UEPS Swing Screener Daily | 2026-11-13T14:06:39Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| Mermaid Test Deploy | 2026-11-13T00:07:30Z | 1.7d | failure | push | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 |
| 📺 News Video Health Check | 2026-11-12T15:11:12Z | 2.0d | success | schedule | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 |
| AI Hedge Fund Simulation — Weekly Pick Resolution | 2026-11-07T23:01:09Z | 6.7d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Algorithm Competition Refresh | 2026-11-08T10:03:12Z | 6.2d | failure | schedule | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| Alpha Engine - Weekly Validation Suite | 2026-11-09T06:13:52Z | 5.4d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| CFTC COT Refresh | 2026-11-14T12:08:14Z | 0.2d | success | schedule | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| Deals & Freebies  Verify & Refresh | 2026-11-09T14:08:33Z | 5.1d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Feature Stability Check (Weekly) | 2026-11-09T06:05:03Z | 5.4d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) | 2026-11-09T06:18:24Z | 5.4d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| HC Evaluator Parity Test | 2026-11-09T15:09:53Z | 5.0d | failure | schedule | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| Insider Trades Refresh | 2026-11-09T11:02:48Z | 5.2d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Mercury 2  Weekly Retrain | 2026-11-08T02:16:14Z | 6.6d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Mutation analysis report | 2026-11-09T06:42:16Z | 5.4d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Overnight Mutations | 2026-11-14T02:07:53Z | 0.6d | success | schedule | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| Research Orchestrator (weekly) | 2026-11-14T06:10:25Z | 0.4d | success | schedule | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| Sports Forensics Weekly | 2026-11-09T06:45:58Z | 5.4d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Stale Branch Cleanup | 2026-11-09T06:39:00Z | 5.4d | failure | schedule | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| Strategy Genome Evolution | 2026-11-08T06:08:19Z | 6.4d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Strategy Kill Tribunal | 2026-11-13T14:10:30Z | 1.1d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Taste Profile Scanner | 2026-11-08T03:10:32Z | 6.5d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| UEPS Value Screener Weekly | 2026-11-09T06:15:52Z | 5.4d | cancelled | schedule | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| Walk-Forward Backtest (Weekly) | 2026-11-08T08:13:08Z | 6.3d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Weekly Exhaustive Stock Simulation | 2026-11-08T06:14:18Z | 6.4d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Weekly Real-Money Filter | 2026-11-09T06:09:52Z | 5.4d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Weekly Strategy Scorecard | 2026-11-08T00:27:51Z | 6.6d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| Weekly score quartile spread | 2026-11-09T14:18:23Z | 5.1d | failure | schedule | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| [RiseOfTheClaw] Weekly Backtest + Elimination | 2026-11-08T03:06:55Z | 6.5d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| [torontoevent.net] Algorithm Competition Refresh | 2026-11-08T10:07:08Z | 6.2d | failure | schedule | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| bt_backtest_trades cross-DB sync (DRAFT) | 2026-11-08T04:08:25Z | 6.5d | success | schedule | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| AI Leaderboard Refresh | 2026-06-05T02:38:12Z | 162.6d | success | workflow_dispatch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| AI Tournament Pipeline — Daily Picks + DB Ingest | 2026-06-04T13:12:44Z | 163.1d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Backup Restore Verification | 2026-10-15T06:04:51Z | 30.4d | failure | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Battleground Mass Backtest | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Battleground Mass Backtest (Part 2 - Babies) | 2026-06-06T07:32:55Z | 161.4d | success | workflow_dispatch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Beta Portfolio Refresh (monthly) | 2026-11-01T06:29:57Z | 13.4d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Clear Channel Command | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Closed Picks Command | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Copilot cloud agent | 2026-05-25T21:12:04Z | 172.8d | success | dynamic | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| DB Credentials Test | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| DB Freshness Check (Legacy Manual) | 2026-05-23T18:28:36Z | 174.9d | failure | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| DB Password Leak Guard | 2026-10-23T17:26:23Z | 21.9d | success | pull_request | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| DB Secret Scan | 2026-06-05T06:57:28Z | 162.4d | failure | pull_request | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Dependency Graph | 2026-05-23T07:22:58Z | 175.4d | success | dynamic | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Deploy Alpha Engine Dashboard | 2026-05-27T12:08:23Z | 171.2d | success | push | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Deploy FC API Hotfix (3 domains) | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Deploy FavCreators Frontend (/fc/) | 2026-10-18T01:47:05Z | 27.6d | success | push | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Deploy FriendTracker | 2026-05-27T12:08:23Z | 171.2d | success | push | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Deploy MOVIESHOWS3 Hotfix | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Deploy Strategy Bundle | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Deploy fc/api/.env to GoDaddy (torontoevent.net) | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Discord Token Selftest | 2026-10-04T04:52:51Z | 41.5d | success | workflow_dispatch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Dynamic Runner Template | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Fast Stocks Competition  High Frequency Scanner | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Fetch New Movies & TV Shows (Manual) | 2026-10-11T06:00:39Z | 34.4d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Fix Battleground Deployment | 2026-05-27T12:08:23Z | 171.2d | success | push | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Fix Ghost Cards & Thumbnails  All Sites | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Forex Agent | 2026-06-03T18:29:34Z | 163.9d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Forex Smart Picks Scanner | 2026-06-03T22:41:44Z | 163.7d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H-103 Forward Logger | 2026-11-01T14:01:39Z | 13.1d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Kimi Fetch Movies/TV (Manual) | 2026-10-11T06:30:29Z | 34.4d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ML Gatekeeper A/B Bootstrap | 2026-05-27T03:50:50Z | 171.5d | failure | workflow_dispatch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ML Monthly Full Retrain | 2026-11-01T04:01:08Z | 13.5d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Meme Coin Scanner  Fixed with Monitoring | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Monthly Confidence Calibrator Refit (M-060) | 2026-11-01T07:05:33Z | 13.4d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Monthly DNA Tournament | 2026-11-01T06:13:31Z | 13.4d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MySQL Dedup Fix | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MySQL Q-001 — Create picks table + sync from JSON | 2026-05-24T08:48:30Z | 174.3d | failure | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| POC Picks Checkpoint (2-week reminder) | 2026-07-20T21:25:17Z | 116.8d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Pick Flow Snapshot (Fast) | 2026-05-24T21:50:32Z | 173.8d | success | workflow_dispatch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Quant Auditor (fast PR check) | 2026-10-22T23:24:32Z | 22.7d | success | pull_request | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| REAL 2-HOUR CHALLENGE - Live Market Data | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| RL Agent (PPO) Train & Predict | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Real-Time Battle Test - Eliminate Losers, Optimize Winners | 2026-06-13T01:39:52Z | 154.6d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Resolver Step 5-6 — at_raw_picks Backfill | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Resolver Step 7 — active_picks_sync APPLY | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Secret Rotation Reminder | 2026-11-01T09:07:09Z | 13.3d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Test Fast Variants | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| UEPS Smoke Tests | 2026-10-20T03:03:30Z | 25.5d | success | pull_request | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| UEPS Value Resolver Quarterly | 2026-10-01T07:25:25Z | 44.4d | success | schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| WSL Runner Manager | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Won PNL Contradiction Backfill | — | — | never | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| [torontoevent.net] Deploy Live Monitor APIs | 2026-06-03T14:30:17Z | 164.1d | success | push | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| masking-policy-lint | 2026-10-23T17:26:23Z | 21.9d | success | pull_request | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| strategy_performance.json no-regression guard | 2026-05-27T20:09:22Z | 170.8d | success | pull_request | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| walkforward-gate | 2026-10-22T23:24:32Z | 22.7d | success | pull_request | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

