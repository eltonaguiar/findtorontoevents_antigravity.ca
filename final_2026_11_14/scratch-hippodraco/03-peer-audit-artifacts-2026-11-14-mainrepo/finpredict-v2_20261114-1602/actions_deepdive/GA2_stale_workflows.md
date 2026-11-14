# GA2 — Stale / Never-Run / Duplicate Workflow Inventory

- **Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
- **Branch audited:** `main` (workflow files read from `origin/main` @ `be4f89608217`, 2026-11-14T17:43Z)
- **Snapshot time (UTC):** 2026-11-14T17:50Z
- **Data sources:** GitHub Actions REST API (`/actions/workflows`, `/actions/workflows/<id>/runs`) + `git show origin/main:.github/workflows/*.yml`
- **Raw evidence:** `actions_deepdive/raw_ga2/GA2_workflows.json`, `raw_ga2/runs/<id>_{all,main}.json`, `raw_ga2/GA2_runs_cache.json`, `raw_ga2/GA2_cron.json`, `raw_ga2/GA2_final.json`
- **Full matrix:** `actions_deepdive/GA2_workflow_matrix.csv` (365 rows)

## Verdict: **FAIL** (overall hygiene) — critical path **PASS**

Strict stale-workflow hygiene **FAILS**: 56/365 workflows (15.3%) are stale (never run or >7d), including 20 never-run workflows, 4 manually-disabled workflows that still carry `cron:` in their YAML, and 2 orphaned workflow registrations whose files were deleted from `main`.

The **critical audit/money path PASSES**: `audit-dashboard.yml` (hourly, last 2026-11-14T17:14Z), `audit-hourly-update.yml` (17:21Z success), `db-freshness-guardian.yml` (17:01Z success), `cross-db-audit.yml` (06:06Z success), and `pick-funnel-nightly.yml` (04:05Z success) are all fresh. No active recurring schedule is cadence-overdue.

## Summary counts

| Metric | Count |
|---|---|
| Workflows registered in Actions (API) | **365** |
| `active` | 361 |
| `disabled_manually` | 4 |
| `.github/workflows/*` registered paths | 362 |
| GitHub-generated `dynamic/*` workflows | 3 |
| YAML files in `origin/main:.github/workflows` | 360 |
| **Stale (never or >7d)** | **56** (52 active, 4 disabled) |
| — never run, all-time (`total_count == 0`) | 20 |
| — >7d to 30d | 12 |
| — >30d to 90d | 5 |
| — >90d to 180d | 19 |
| — >180d | 0 |
| Active within 7d | 309 |
| Stale with a `cron:` schedule in YAML | 14 |
| **True cadence-overdue recurring schedules (zombies)** | **0** |
| Fixed-date one-shot crons already elapsed | 2 |
| Disabled workflows still carrying `cron:` | 4 |
| Orphaned registrations (file deleted, still active) | 2 |
| Workflows touching audit/dashboard dependencies | 72 |
| — of those, stale | 9 |
| Stale with last conclusion = failure | 5 |

> **Age definition:** hours/days since the most recent run on **any branch** (`runs?per_page=1`, all-time). The CSV separately carries `last_run_main_utc` (main-only, per instruction) and `last_run_any_utc`. Buckets use all-branch activity so branch-only workflows (PR guards, security scans) are not mislabeled "never". Never-run uses all-time `total_count == 0`.
>
> **Cron detection:** parsed from `origin/main` YAML `schedule:` blocks only (comment lines and non-schedule `cron:` strings ignored). This matters: `walkforward-gate.yml` contains the word `cron` only in a comment and is **not** scheduled.
>
> **Independent cross-check:** the peer artifact `2026-11-14/finpredict-v2_20261114-1602/sub/A_actions_health.md` reports 365 workflows, 20 never-run, and 36 stale >7d (56 zero-run-in-7d). This inventory independently reproduces exactly those totals (20 + 36 = 56).

## Buckets (mutually exclusive)

| Bucket | Count | Notes |
|---|---|---|
| Never run (all-time) | 20 | All `active`; 19 `workflow_dispatch`-triggered, 1 reusable template (`_dynamic-runner-template.yml`, no triggers) |
| >7d (7–30d) | 12 | 7 are monthly/quarterly jobs within cadence |
| >30d (30–90d) | 5 | `backup-verify` is the material one (audit dep, last failed) |
| >90d (90–180d) | 19 | Mix of one-off migrations, disabled money jobs, deploy leftovers |
| >180d | 0 | None |
| Active ≤7d | 309 | Healthy majority |

## Full stale table (56 rows)

Columns: name, path, last run (any branch), age, conclusion, cron? `[audit-dep]` = invokes an audit/dashboard dependency; `[DISABLED]` = `disabled_manually`.

| Name | Path | Last run (UTC) | Age | Conclusion | Cron? |
|---|---|---|---|---|---|
| Dynamic Runner Template | `_dynamic-runner-template.yml` | NEVER | n/a | no-run | N |
| Battleground Mass Backtest | `battleground-mass-backtest.yml` | NEVER | n/a | no-run | N |
| Clear Channel Command | `clear-channel-command.yml` | NEVER | n/a | no-run | N |
| Closed Picks Command | `closed-picks-command.yml` | NEVER | n/a | no-run | N |
| DB Credentials Test | `db-credentials-test.yml` | NEVER | n/a | no-run | N |
| Deploy fc/api/.env to GoDaddy (torontoevent.net) | `deploy-fc-api-env-godaddy.yml` | NEVER | n/a | no-run | N |
| Deploy FC API Hotfix (3 domains) | `deploy-fc-api-hotfix.yml` | NEVER | n/a | no-run | N |
| Deploy MOVIESHOWS3 Hotfix | `deploy-movieshows3-hotfix.yml` | NEVER | n/a | no-run | N |
| Deploy Strategy Bundle | `deploy_bundle.yml` | NEVER | n/a | no-run | N |
| Fast Stocks Competition  High Frequency Scanner | `fast-stocks-competition.yml` | NEVER | n/a | no-run | N |
| Fix Ghost Cards & Thumbnails  All Sites | `fix-ghost-cards.yml` | NEVER | n/a | no-run | N |
| Meme Coin Scanner  Fixed with Monitoring | `meme-scanner-fixed.yml` | NEVER | n/a | no-run | N |
| MySQL Dedup Fix | `mysql_dedup_fix.yml` | NEVER | n/a | no-run | N |
| REAL 2-HOUR CHALLENGE - Live Market Data | `real_2hour_challenge.yml` | NEVER | n/a | no-run | N |
| Resolver Step 5-6 — at_raw_picks Backfill | `resolver-step5-6-backfill.yml` | NEVER | n/a | no-run | N [audit-dep] |
| Resolver Step 7 — active_picks_sync APPLY | `resolver-step7-apply.yml` | NEVER | n/a | no-run | N |
| RL Agent (PPO) Train & Predict | `rl-agent-ppo.yml` | NEVER | n/a | no-run | N |
| Test Fast Variants | `test-fast.yml` | NEVER | n/a | no-run | N |
| Won PNL Contradiction Backfill | `won-pnl-contradiction-backfill.yml` | NEVER | n/a | no-run | N |
| WSL Runner Manager | `wsl-runner-manager.yml` | NEVER | n/a | no-run | N |
| Dependency Graph | `dynamic/dependabot/update-graph` | 2026-05-23 07:22:58 | 175.4d | success | N |
| DB Freshness Check (Legacy Manual) | `db-freshness-check.yml` | 2026-05-23 21:49:22 | 174.8d | failure | N [audit-dep] |
| MySQL Q-001 — Create picks table + sync from JSON | `mysql-q001-sync.yml` | 2026-05-24 11:32:03 | 174.3d | failure | Y |
| Pick Flow Snapshot (Fast) | `pick-flow-snapshot-fast.yml` | 2026-05-24 21:50:32 | 173.8d | success | N |
| Copilot cloud agent | `dynamic/copilot-swe-agent/copilot` | 2026-05-25 21:12:04 | 172.9d | success | N |
| ML Gatekeeper A/B Bootstrap | `ml-gatekeeper-ab-bootstrap.yml` | 2026-05-27 08:21:57 | 171.4d | failure | N |
| Deploy Alpha Engine Dashboard | `deploy-alpha-dashboard.yml` | 2026-05-27 12:08:23 | 171.2d | success | N |
| Deploy FriendTracker | `deploy-friendtracker.yml` | 2026-05-27 12:08:23 | 171.2d | success | N |
| Fix Battleground Deployment | `fix-battleground.yml` | 2026-05-27 12:08:23 | 171.2d | success | N |
| strategy_performance.json no-regression guard | `strategy-performance-no-regression.yml` | 2026-05-27 20:09:22 | 170.9d | success | N [audit-dep] |
| [torontoevent.net] Deploy Live Monitor APIs | `torontoevent-deploy-live-monitor.yml` | 2026-06-03 14:30:17 | 164.1d | success | N |
| Forex Agent | `forex-agent.yml` | 2026-06-03 18:29:34 | 164.0d | success | Y [DISABLED] |
| Forex Smart Picks Scanner | `forex-smart-picks.yml` | 2026-06-03 22:41:44 | 163.8d | success | Y [DISABLED] |
| AI Tournament Pipeline — Daily Picks + DB Ingest | `ai-tournament-pipeline.yml` | 2026-06-04 13:12:44 | 163.2d | success | Y [audit-dep] [DISABLED] |
| AI Leaderboard Refresh | `ai-leaderboard-refresh.yml` | 2026-06-05 02:38:12 | 162.6d | success | N [audit-dep] |
| DB Secret Scan | `db-secret-scan.yml` | 2026-06-05 07:16:48 | 162.4d | failure | N |
| Battleground Mass Backtest (Part 2 - Babies) | `battleground-mass-backtest-part2.yml` | 2026-06-06 07:32:55 | 161.4d | success | N |
| Real-Time Battle Test - Eliminate Losers, Optimize Winners | `battle_test.yml` | 2026-06-13 01:39:52 | 154.7d | success | Y [DISABLED] |
| POC Picks Checkpoint (2-week reminder) | `poc-picks-checkpoint.yml` | 2026-07-20 21:25:17 | 116.9d | success | Y |
| UEPS Value Resolver Quarterly | `value_resolver_quarterly.yml` | 2026-10-01 07:25:25 | 44.4d | success | Y [audit-dep] |
| Discord Token Selftest | `discord-token-selftest.yml` | 2026-10-04 04:52:51 | 41.5d | success | N |
| Fetch New Movies & TV Shows (Manual) | `fetch-movies.yml` | 2026-10-11 06:00:39 | 34.5d | success | N |
| Kimi Fetch Movies/TV (Manual) | `kimi-fetch-movies.yml` | 2026-10-11 06:30:29 | 34.5d | success | N |
| Backup Restore Verification | `backup-verify.yml` | 2026-10-15 09:11:26 | 30.4d | failure | Y [audit-dep] |
| Deploy FavCreators Frontend (/fc/) | `deploy-fc-frontend.yml` | 2026-10-18 01:47:05 | 27.7d | success | N |
| UEPS Smoke Tests | `ueps_smoke_tests.yml` | 2026-10-20 03:03:30 | 25.6d | success | N |
| Quant Auditor (fast PR check) | `quant-auditor-fast-pr.yml` | 2026-10-22 23:24:32 | 22.8d | success | N [audit-dep] |
| walkforward-gate | `walkforward-gate.yml` | 2026-10-22 23:24:32 | 22.8d | success | N |
| DB Password Leak Guard | `db-password-leak-guard.yml` | 2026-10-23 17:26:23 | 22.0d | success | N |
| masking-policy-lint | `masking-policy-lint.yml` | 2026-10-23 17:26:23 | 22.0d | success | N |
| ML Monthly Full Retrain | `ml-monthly-retrain.yml` | 2026-11-01 04:01:08 | 13.6d | success | Y |
| Beta Portfolio Refresh (monthly) | `beta-portfolio-refresh.yml` | 2026-11-01 06:29:57 | 13.5d | success | Y [audit-dep] |
| Monthly DNA Tournament | `monthly-tournament.yml` | 2026-11-01 06:13:31 | 13.5d | success | Y |
| Monthly Confidence Calibrator Refit (M-060) | `monthly-calibrator-refit.yml` | 2026-11-01 07:05:33 | 13.4d | success | Y |
| Secret Rotation Reminder | `secret-rotation-reminder.yml` | 2026-11-01 09:07:09 | 13.4d | success | Y |
| H-103 Forward Logger | `h103-forward-logger.yml` | 2026-11-01 14:01:39 | 13.2d | success | Y |

## Never-run list (20, all-time zero runs)

| Name | Path | State | Cron? |
|---|---|---|---|
| Dynamic Runner Template | `_dynamic-runner-template.yml` | active | N |
| Battleground Mass Backtest | `battleground-mass-backtest.yml` | active | N |
| Clear Channel Command | `clear-channel-command.yml` | active | N |
| Closed Picks Command | `closed-picks-command.yml` | active | N |
| DB Credentials Test | `db-credentials-test.yml` | active | N |
| Deploy fc/api/.env to GoDaddy (torontoevent.net) | `deploy-fc-api-env-godaddy.yml` | active | N |
| Deploy FC API Hotfix (3 domains) | `deploy-fc-api-hotfix.yml` | active | N |
| Deploy MOVIESHOWS3 Hotfix | `deploy-movieshows3-hotfix.yml` | active | N |
| Deploy Strategy Bundle | `deploy_bundle.yml` | active | N |
| Fast Stocks Competition  High Frequency Scanner | `fast-stocks-competition.yml` | active | N |
| Fix Ghost Cards & Thumbnails  All Sites | `fix-ghost-cards.yml` | active | N |
| Meme Coin Scanner  Fixed with Monitoring | `meme-scanner-fixed.yml` | active | N |
| MySQL Dedup Fix | `mysql_dedup_fix.yml` | active | N |
| REAL 2-HOUR CHALLENGE - Live Market Data | `real_2hour_challenge.yml` | active | N |
| Resolver Step 5-6 — at_raw_picks Backfill | `resolver-step5-6-backfill.yml` | active | N |
| Resolver Step 7 — active_picks_sync APPLY | `resolver-step7-apply.yml` | active | N |
| RL Agent (PPO) Train & Predict | `rl-agent-ppo.yml` | active | N |
| Test Fast Variants | `test-fast.yml` | active | N |
| Won PNL Contradiction Backfill | `won-pnl-contradiction-backfill.yml` | active | N |
| WSL Runner Manager | `wsl-runner-manager.yml` | active | N |

> `fast-stocks-competition.yml` has `workflow_dispatch` only despite its "High Frequency Scanner" name — it is not a scheduled zombie, but it is dead configuration. `_dynamic-runner-template.yml` is a reusable template and is expected to have zero runs.

## Zombie schedules / cadence analysis

**True recurring zombies: 0.** Every active `cron` workflow has run within its expected cadence (intraday ≤1.5d, daily ≤2.5d, weekly ≤8d, monthly ≤40d, quarterly ≤100d, annual/specific-month ≤380d).

Two **fixed-date one-shot crons** are effectively dead schedule entries and should be removed/disabled:
- `mysql-q001-sync.yml` — `0 8 24 5 *` (annual May 24 migration). Last/only run 2026-05-24, **fails**. It will silently re-fire each May.
- `poc-picks-checkpoint.yml` — fixed dates `2026-07-18` and `2026-07-20` ("2-week reminder"). Already fired; will not run again until 2027. Dead config.

The 14 stale-cron workflows and their cadence verdict:

| Name | Path | State | Cadence | Cron | Last run | Age (d) | Verdict |
|---|---|---|---|---|---|---|---|
| MySQL Q-001 — Create picks table + sync from JSON | `mysql-q001-sync.yml` | active | annual/specific-month | 0 8 24 5 * | 2026-05-24 11:32:03 | 174.3 | **one-shot elapsed (dead)** |
| Forex Agent | `forex-agent.yml` | disabled_manually | weekly | 0 0,8,13,17 * * 1-5 | 2026-06-03 18:29:34 | 164.0 | within cadence |
| Forex Smart Picks Scanner | `forex-smart-picks.yml` | disabled_manually | weekly | 0 2,6,10,14,18,22 * * 1-5 | 2026-06-03 22:41:44 | 163.8 | within cadence |
| AI Tournament Pipeline — Daily Picks + DB Ingest | `ai-tournament-pipeline.yml` | disabled_manually | daily | 0 12 * * * | 2026-06-04 13:12:44 | 163.2 | within cadence |
| Real-Time Battle Test - Eliminate Losers, Optimize Winners | `battle_test.yml` | disabled_manually | intraday | 0 * * * * | 2026-06-13 01:39:52 | 154.7 | within cadence |
| POC Picks Checkpoint (2-week reminder) | `poc-picks-checkpoint.yml` | active | annual/specific-month | 0 21 18 7 *; 0 21 20 7 * | 2026-07-20 21:25:17 | 116.9 | **one-shot elapsed (dead)** |
| UEPS Value Resolver Quarterly | `value_resolver_quarterly.yml` | active | quarterly~ | 0 7 1 */3 * | 2026-10-01 07:25:25 | 44.4 | within cadence |
| Backup Restore Verification | `backup-verify.yml` | active | monthly | 0 6 15 * * | 2026-10-15 09:11:26 | 30.4 | within cadence |
| ML Monthly Full Retrain | `ml-monthly-retrain.yml` | active | monthly | 0 4 1 * * | 2026-11-01 04:01:08 | 13.6 | within cadence |
| Beta Portfolio Refresh (monthly) | `beta-portfolio-refresh.yml` | active | monthly | 20 6 1 * * | 2026-11-01 06:29:57 | 13.5 | within cadence |
| Monthly DNA Tournament | `monthly-tournament.yml` | active | monthly | 0 6 1 * * | 2026-11-01 06:13:31 | 13.5 | within cadence |
| Monthly Confidence Calibrator Refit (M-060) | `monthly-calibrator-refit.yml` | active | monthly | 0 7 1 * * | 2026-11-01 07:05:33 | 13.4 | within cadence |
| Secret Rotation Reminder | `secret-rotation-reminder.yml` | active | monthly | 0 9 1 * * | 2026-11-01 09:07:09 | 13.4 | within cadence |
| H-103 Forward Logger | `h103-forward-logger.yml` | active | monthly | 0 14 1 * * | 2026-11-01 14:01:39 | 13.2 | within cadence |

> The >7d rows that look stale are **monthly** jobs that legitimately ran on 2026-11-01 (13.x days ago) — e.g. `ml-monthly-retrain`, `beta-portfolio-refresh`, `monthly-tournament`, `monthly-calibrator-refit`, `secret-rotation-reminder`, `h103-forward-logger`. `value_resolver_quarterly` is quarterly (last 2026-10-01). `backup-verify` is monthly (ran 2026-10-15) but **failed** — see P0.

## `db-freshness-check.yml` verification

**Verified manual-only.** In `origin/main` the file is named `DB Freshness Check (Legacy Manual)` and its only trigger is:

```yaml
on:
  workflow_dispatch:
```

There is **no `schedule:`/`cron:`**. This confirms the 2026-05-23 hardening claim. It is superseded by `db-freshness-guardian.yml`, which is active with `cron: '0 * * * *'` and last ran successfully 2026-11-14T17:01Z. `db-freshness-check` has only 2 all-time runs, both failures, last 2026-05-23T21:49Z.

## Duplicate / legacy / variant inventory

No file is literally named `*-legacy`; the legacy marker is in the display name. Candidates below are **recommendations for owner confirmation**, not proof of identical behavior.

| Family | Files | Evidence / status | Recommendation |
|---|---|---|---|
| DB freshness | `db-freshness-check.yml` (legacy manual, 2 runs, failure) vs `db-freshness-guardian.yml` (hourly, 3,837 runs, fresh) | Same job; guardian is canonical | **Delete-file** legacy (recommend) |
| Secret scan | `db-secret-scan.yml` (orphaned registration, >90d failure) vs `secret-scan.yml` (active) | Legacy superseded + file removed from main | **Disable/cleanup** orphan |
| Edge stability | `edge-stability-daily.yml` and `edge-stability-refresh.yml` | **Identical duplicate name** ("edge stability refresh"), both active | **Consolidate** |
| Movie fetch | `fetch-movies.yml` (>30d, 141 runs) vs `kimi-fetch-movies.yml` (>30d, 141 runs) vs `fetch-movies-v3.yml` (active) | Manual variants + v3 | Keep v3; **delete/retire** manual pair |
| Meme scanner | `meme-scanner.yml` vs `meme-scanner-v2.yml` (active) vs `meme-scanner-fixed.yml` (**never**) | Three generations | Keep v2; **delete** fixed |
| 2-hour challenge | `2hour_challenge.yml` (active) vs `real_2hour_challenge.yml` (**never**) | Unused "real" fork | **Delete-file** real_ |
| Battleground backtest | `battleground-mass-backtest.yml` (**never**) vs `battleground-mass-backtest-part2.yml` (>90d) | Abandoned pair | **Delete** both |
| Tournament | `ai-tournament-pipeline.yml` (disabled, cron) vs `monthly-tournament.yml` (active) vs `ai-tournament-price-tracker.yml` (active) | Overlapping tournament jobs | **Delete/disable** old pipeline |
| Battleground fix/retrain | `fix-battleground.yml` (>90d) vs `ml-battleground-f.yml` / `ml-battleground-retrain.yml` (active) | Deploy/retrain variants | **Consolidate** |
| Forward test | `forward_test.yml`, `ml-forward-test.yml`, `forward-test-new-strategies.yml`, `forward-tracking-v2.yml` (all active) | Overlapping forward validation | Review/consolidate |
| Live trading | `live_trading.yml`, `live_trading_canada.yml`, `live_trading_canada_free.yml`, `live_spike_trading.yml` (all active) | Regional/free variants on money path | Keep but document ownership |
| Deploy variants | `deploy-fc-api-hotfix.yml` + `deploy-movieshows3-hotfix.yml` (both **never**) | Dead hotfix stubs | **Delete-file** |
| Deploy mirrors | `backtest-and-deploy.yml`, `torontoevent-backtest-and-deploy.yml`, `torontoevent-backtest-and-deploy-ROOCODE.yml`, `deploy-riseoftheclaw.yml` vs `torontoevent-deploy-riseoftheclaw.yml`, `goldmine-tracker.yml` vs `torontoevent-goldmine-tracker.yml`, `spike-scanner.yml` vs `torontoevent-spike-scanner.yml` | Site-mirror pairs | Verify one canonical per target |

## Orphaned registrations / file-tree integrity

- **2 orphaned registrations** (Actions lists them `active`, but the file is absent from `origin/main:.github/workflows`):
  - `.github/workflows/db-secret-scan.yml` — 2 runs, last 2026-06-05 **failure**
  - `.github/workflows/mermaid-test-deploy.yml` — 2 runs, last 2026-11-13 **failure** (main-branch count 0)
- **0 unregistered YAML files** (every `.yml` on `main` is registered).
- `dynamic/copilot-swe-agent/copilot`, `dynamic/dependabot/update-graph`, `dynamic/pages/pages-build-deployment` are GitHub-managed and out of scope for deletion.

## Prioritized actions

### P0 — Critical path / correctness (fix, keep)
- `backup-verify.yml` — monthly audit dependency; last run **failed** (2026-10-15). **Fix the restore verification** or document known-failing status. Keep schedule.

### P1 — Money-path stale / dead schedules (disable schedule or delete-file)
- `mysql-q001-sync.yml` — one-off migration cron, failed, annual re-fire. **Delete-file** (recommend).
- `poc-picks-checkpoint.yml` — elapsed fixed-date reminder. **Delete-file** (recommend).
- `ai-tournament-pipeline.yml` — disabled but cron remains. **Delete-file** (superseded by `monthly-tournament.yml`).
- `forex-agent.yml`, `forex-smart-picks.yml`, `battle_test.yml` — disabled but cron remains. **Delete-file** or strip `schedule:` to prevent accidental re-enable.
- `ml-gatekeeper-ab-bootstrap.yml` — one-off, failed, >90d. **Delete-file**.
- `resolver-step5-6-backfill.yml`, `resolver-step7-apply.yml`, `won-pnl-contradiction-backfill.yml` — never-run one-off backfills. **Delete-file** (or keep as documented manual if still needed).
- `db-freshness-check.yml` — legacy manual. **Delete-file** (guardian covers it).

### P2 — Audit-dependency but non-hourly (keep, review)
- `strategy-performance-no-regression.yml` — >90d, PR-only guard. Keep if PR checks still desired; otherwise delete.
- `ai-leaderboard-refresh.yml` — >90d, superseded by `ai-leaderboard-freshness.yml`. Review, then delete.
- `quant-auditor-fast-pr.yml` — >7d, PR-only (main count 0, 261 runs elsewhere). Keep.
- `beta-portfolio-refresh.yml`, `value_resolver_quarterly.yml` — within cadence; no action.

### P3 — Never-run / deploy / research noise (delete-file or keep-as-manual)
- Never-run deploy/hotfix stubs: `deploy-fc-api-env-godaddy.yml`, `deploy-fc-api-hotfix.yml`, `deploy-movieshows3-hotfix.yml`, `deploy_bundle.yml`, `fix-ghost-cards.yml`, `mysql_dedup_fix.yml`, `real_2hour_challenge.yml`, `test-fast.yml`, `wsl-runner-manager.yml`, `rl-agent-ppo.yml`, `meme-scanner-fixed.yml`, `clear-channel-command.yml`, `closed-picks-command.yml`, `db-credentials-test.yml`, `battleground-mass-backtest.yml` — **delete-file** unless an owner confirms active manual use. Keep `_dynamic-runner-template.yml` (template).
- >90d deploy/misc leftovers: `deploy-alpha-dashboard.yml`, `deploy-friendtracker.yml`, `fix-battleground.yml`, `torontoevent-deploy-live-monitor.yml`, `battleground-mass-backtest-part2.yml`, `ml-gatekeeper-ab-bootstrap.yml`, `pick-flow-snapshot-fast.yml` — **delete-file** or keep-as-manual.

### Bucket-level policy

| Bucket | Recommended policy |
|---|---|
| Active ≤7d | **Keep** — no action |
| Never-run | **Delete-file** unless documented manual; templates exempt |
| >7d within cadence | **Keep** — monthly/quarterly by design |
| >7d overdue | **Fix** (none found) |
| >30d | **Review** — `backup-verify` fix; others likely dead |
| >90d | **Delete-file** unless a money/audit owner claims it |
| >180d | **Delete-file** (none present) |
| Disabled + cron | **Delete-file** or remove `schedule:` |
| Orphaned registration | **Disable** then let Actions prune |

## Observation outside stale scope — recent mass failure (UNVERIFIED cause)

At **2026-11-14T17:33:40–17:33:49Z** at least 20 active workflows completed with `conclusion=failure` (e.g. `ci-tests`, `live_trading`, `live_trading_canada`, `live_trading_canada_free`, `picks_dispatch`, `forward_test`, `sports-smoke-and-e2e`, `missed-opportunity-scan`). Several were scheduled runs created ~16:03–16:22Z and only **started** ~17:33Z (~70–90 min queued), suggesting a runner-backlog/shared-dependency event. **Root cause UNVERIFIED** and outside this inventory's scope; recommend a separate failure-triage pass. This does not change the staleness verdict.

## UNVERIFIED markers

- **UNVERIFIED:** root cause of the 2026-11-14T17:33Z mass-failure wave.
- **UNVERIFIED:** whether any never-run manual workflow is still intentionally used by an operator (API cannot show intent).
- **UNVERIFIED:** `audit-dashboard.yml` last run has no terminal `conclusion` in the snapshot (run appears in-progress/queued at 17:14Z); freshness inferred from `started_at`, not success.
- **UNVERIFIED:** duplicate-family pairings are token/name-based candidates; behavioral equivalence not diffed line-by-line.
- **UNVERIFIED:** `dynamic/*` workflows are GitHub-managed; excluded from delete recommendations.

## Data files

- `actions_deepdive/GA2_workflow_matrix.csv` — full 365-row matrix
- `actions_deepdive/raw_ga2/GA2_workflows.json` — registered workflows (id, name, path, state)
- `actions_deepdive/raw_ga2/GA2_runs_cache.json` — cached `runs?branch=main` + all-branch responses
- `actions_deepdive/raw_ga2/GA2_cron.json` — parsed `schedule:`/`cron:` per path
- `actions_deepdive/raw_ga2/GA2_final.json` — enriched rows used to build this report
