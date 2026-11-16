# GitHub Actions health — eltonaguiar/findtorontoevents_antigravity.ca

> **Verified sweep.** 365 API calls, **0 fetch errors**, exit 0. This supersedes the earlier
> 232-entry "stale" figure from this folder's design doc, which was an artifact of the hourly
> API quota being exhausted mid-sweep (403s were being bucketed as "stale"). The real stale
> count is 20. The tool now distinguishes an unreadable history (`unknown`) from a workflow with
> no runs at all, and exits 3 rather than emit a report built on 403s.

- generated: `2026-11-16T03:48:38.083287+00:00`  ·  workflows scanned: **360**  ·  API calls: 365  ·  fetch errors: **0**

> All workflow histories fetched cleanly.

| Detector | Count |
|---|---|
| broken | **5** |
| never_passed | **3** |
| cancel_churn | **9** |
| queue_wait | **20** |
| long_run | **6** |
| stale | **20** |
| unknown | **0** |
| always-skipped jobs | **0** |

## BROKEN (failed, no later success) — 5

| name | conclusion | last_failed | age_hours |
|---|---|---|---|
| CI Tests | failure | 2026-11-16T03:10:52Z | 37.8 |
| DB Secret Scan | failure | 2026-06-05T06:57:28Z | 235971.2 |
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | failure | 2026-11-16T02:25:27Z | 83.2 |
| Mermaid Test Deploy | failure | 2026-11-14T18:23:49Z | 2004.8 |
| Regime Terminal  HMM Live Scanner | failure | 2026-11-16T03:42:14Z | 6.4 |

## NEVER PASSED in sampled history — 3

| name | runs | last |
|---|---|---|
| Branch Large File Duplicate Guard | 20 | 2026-11-16T02:47:18Z |
| DB Secret Scan | 2 | 2026-06-05T06:57:28Z |
| Mermaid Test Deploy | 5 | 2026-11-14T18:23:49Z |

## CANCEL CHURN (>50% cancelled) — 9

| name | cancelled | total | ratio |
|---|---|---|---|
| Academic Strategies Daily | 13 | 20 | 0.65 |
| Blacklist Reconciler (cross-check vs live systems) | 19 | 20 | 0.95 |
| Branch Large File Duplicate Guard | 20 | 20 | 1.0 |
| Edge stability refresh | 12 | 20 | 0.6 |
| Operator Review — Manual Candidates daily snapshot | 17 | 20 | 0.85 |
| rsi5070 Forward-Test Snapshot (Daily) | 19 | 20 | 0.95 |
| Sign-Coherence Gate | 16 | 20 | 0.8 |
| STOCKSUNIFY2 daily-stocks pull | 18 | 20 | 0.9 |
| Swarm Pick Review (resolve + weekly + patterns + tournament promotion) | 18 | 20 | 0.9 |

## QUEUE WAIT p90 > 60 min — 20

| name | p90_wait_min | max_wait_min |
|---|---|---|
| Algorithm Competition Refresh | 241 | 392 |
| ALPHA ENGINE - Live Autonomous Scanner | 115 | 117 |
| Autonomous Trading Bot - Runs Automatically Every 4 Hours | 186 | 186 |
| Backup Restore Verification | 234 | 461 |
| Daily Prices yfinance Refresh | 211 | 212 |
| DNA Strategy Pipeline | 195 | 197 |
| Edge stability refresh | 209 | 210 |
| Forward Test - Strategy Validation | 205 | 207 |
| HC Evaluator Parity Test | 210 | 250 |
| Live Trading Bot | 207 | 208 |
| Live Trading Bot - Canada Edition | 206 | 207 |
| Mirror: findtorontoevents.ca  torontoevent.net | 177 | 198 |
| H-002 PEAD Shadow Collector | 220 | 221 |
| Crypto Picks Dispatch | 184 | 209 |
| robust-edge-miner | 205 | 205 |
| Self-Optimizing Trading Bot - Auto-Validates & Tweaks | 184 | 211 |
| Stale Branch Cleanup | 353 | 359 |
| [torontoevent.net] Algorithm Competition Refresh | 238 | 387 |
| Verified pilot daily | 188 | 190 |
| Weekly score quartile spread | 226 | 250 |

## LONG RUN p90 > 60 min — 6

| name | p90_min | max_min |
|---|---|---|
| 2hour-challenge | 123 | 133 |
| ALPHA ENGINE - Live Autonomous Scanner | 68 | 75 |
| Unified Audit Dashboard | 125 | 145 |
| Discord Bot  Persistent | 354 | 644 |
| DNA Strategy Pipeline | 76 | 127 |
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | 79 | 80 |

## STALE (active, no runs in history) — 20

| name | path |
|---|---|
| Dynamic Runner Template | .github/workflows/_dynamic-runner-template.yml |
| Battleground Mass Backtest | .github/workflows/battleground-mass-backtest.yml |
| Clear Channel Command | .github/workflows/clear-channel-command.yml |
| Closed Picks Command | .github/workflows/closed-picks-command.yml |
| DB Credentials Test | .github/workflows/db-credentials-test.yml |
| Deploy fc/api/.env to GoDaddy (torontoevent.net) | .github/workflows/deploy-fc-api-env-godaddy.yml |
| Deploy FC API Hotfix (3 domains) | .github/workflows/deploy-fc-api-hotfix.yml |
| Deploy MOVIESHOWS3 Hotfix | .github/workflows/deploy-movieshows3-hotfix.yml |
| Deploy Strategy Bundle | .github/workflows/deploy_bundle.yml |
| Fast Stocks Competition  High Frequency Scanner | .github/workflows/fast-stocks-competition.yml |
| Fix Ghost Cards & Thumbnails  All Sites | .github/workflows/fix-ghost-cards.yml |
| gha-health-audit | .github/workflows/gha-health-audit.yml |
| MySQL Dedup Fix | .github/workflows/mysql_dedup_fix.yml |
| REAL 2-HOUR CHALLENGE - Live Market Data | .github/workflows/real_2hour_challenge.yml |
| Resolver Step 5-6 — at_raw_picks Backfill | .github/workflows/resolver-step5-6-backfill.yml |
| Resolver Step 7 — active_picks_sync APPLY | .github/workflows/resolver-step7-apply.yml |
| RL Agent (PPO) Train & Predict | .github/workflows/rl-agent-ppo.yml |
| Test Fast Variants | .github/workflows/test-fast.yml |
| Won PNL Contradiction Backfill | .github/workflows/won-pnl-contradiction-backfill.yml |
| WSL Runner Manager | .github/workflows/wsl-runner-manager.yml |

## UNKNOWN (history unreadable — NOT stale) — none


## ALWAYS-SKIPPED JOBS — none

