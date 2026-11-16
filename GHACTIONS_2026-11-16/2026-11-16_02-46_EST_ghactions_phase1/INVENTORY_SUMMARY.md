# GHA Phase 1 Inventory (2026-11-16 02:48Z)

- Workflows (API): 360 (active=353, disabled=7)
- Recent main runs sample: 180
- Queued now: 51
- Failed latest without subsequent success (sampled): 0
- Active stale/no-recent-run (>7d or absent): 235
- Active missing timeout-minutes (local YAML): 83
- Active missing concurrency (local YAML): 191

## Failed latest without subsequent success
- none

## Queued (oldest first, up to 20)
- 2026-08-07T09:09:20Z | 31164696055 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | queued
- 2026-08-19T01:03:08Z | 32203529158 | robust-edge-miner | queued
- 2026-08-19T03:06:50Z | 32210976213 | Claude Gainer ML  Live Scanner | queued
- 2026-08-19T04:11:14Z | 32214823886 | MOMENTUM SCALP SCANNER - Dynamic Universe Expansion | queued
- 2026-08-19T04:15:45Z | 32215115317 | Claude's Test - Portfolio Manager | queued
- 2026-08-19T05:09:52Z | 32218394723 | [torontoevent.net] Deploy Rise of the Claw | queued
- 2026-08-19T05:54:41Z | 32221226100 | Prediction Quality Tracker | queued
- 2026-09-13T08:43:36Z | 34748398994 | MOMENTUM TRACKER - Real-Time Gainer Scanner | queued
- 2026-09-13T08:45:05Z | 34748433814 | Claude Gainer Short-Term Predictor | queued
- 2026-09-13T08:57:18Z | 34748717095 | Deploy FindCryptoPairs to FTP | queued
- 2026-09-13T08:58:48Z | 34748752206 | Claude Gainer ML  Live Scanner | queued
- 2026-09-13T09:02:13Z | 34748837532 | ML Battleground System F (Claws of Doom) | queued
- 2026-09-13T09:04:37Z | 34748893146 | Picks-Now Live PnL (hourly) | queued
- 2026-09-13T09:14:07Z | 34749162544 | Meme Coin Scanner v2  Fixed & Monitored | queued
- 2026-09-13T09:20:21Z | 34749339939 | Regime Terminal  HMM Live Scanner | queued
- 2026-09-15T09:25:02Z | 34952444632 | Quick Guess ML Agent | queued
- 2026-10-07T15:07:40Z | 37642368073 | Analyst Tracker  Top 20 Crypto Analysts | queued
- 2026-10-07T15:08:01Z | 37642372833 | DARWIN ENGINE - DNA Evolution Pipeline | queued
- 2026-10-07T15:08:44Z | 37642380252 | Mutation Lab  Strategy Evolution Pipeline | queued
- 2026-10-07T15:08:47Z | 37642380619 | Deploy Rise of the Claw Dashboard | queued

## Active missing timeout-minutes (up to 30)
- 2hour-challenge | triggers=['workflow_dispatch:'] | .github/workflows/2hour_challenge.yml
- actions-failure-guardian | triggers=['workflow_dispatch:'] | .github/workflows/actions-failure-guardian.yml
- AI-Model Portfolios — Daily EOD | triggers=['schedule:'] | .github/workflows/ai-model-portfolios-daily.yml
- Autonomous Trading Bot - Runs Automatically Every 4 Hours | triggers=['# Run automatically every 4 hours (no user action needed!)'] | .github/workflows/autonomous_trading.yml
- Backfill Missing Audit Trail Sources | triggers=['schedule:'] | .github/workflows/backfill.yml
- Run Backtests & Deploy Dashboards | triggers=['schedule:'] | .github/workflows/backtest-and-deploy.yml
- Backup Restore Verification | triggers=['schedule:'] | .github/workflows/backup-verify.yml
- Beta Portfolio Refresh (monthly) | triggers=['schedule:'] | .github/workflows/beta-portfolio-refresh.yml
- CFTC COT Refresh | triggers=['schedule:'] | .github/workflows/cftc-cot-refresh.yml
- Check Streamer Live Status | triggers=['schedule:'] | .github/workflows/check-streamer-status.yml
- Claude Code Gainer ML Tracker | triggers=['schedule:'] | .github/workflows/claude-gainer-tracker.yml
- Contested Pick Checker (Claude vs Antigravity) | triggers=['schedule:'] | .github/workflows/contested-pick-checker.yml
- Cross-DB Strategy Consistency Audit | triggers=['schedule:'] | .github/workflows/cross-db-audit.yml
- Daily Prices yfinance Refresh | triggers=['schedule:'] | .github/workflows/daily-prices-yf-refresh.yml
- Daily Runs | triggers=['schedule:'] | .github/workflows/daily_runs.yml
- Data Pipeline Reliability Test | triggers=['schedule:'] | .github/workflows/data-pipeline-test.yml
- DB Freshness Guardian | triggers=['schedule:'] | .github/workflows/db-freshness-guardian.yml
- Deploy Competition to Live Site | triggers=['push:'] | .github/workflows/deploy-competition-to-site.yml
- Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) | triggers=['workflow_dispatch:'] | .github/workflows/deploy-movieshows-all.yml
- Deploy MOVIESHOWS3 Hotfix | triggers=['workflow_dispatch:'] | .github/workflows/deploy-movieshows3-hotfix.yml
- Deploy Strategy Bundle | triggers=['workflow_dispatch:'] | .github/workflows/deploy_bundle.yml
- Discord Token Selftest | triggers=['workflow_dispatch:'] | .github/workflows/discord-token-selftest.yml
- ANTIGRAVITY ML  Hourly Discord Status + Picks (DISABLED) | triggers=['schedule:'] | .github/workflows/discord_status.yml
- DNA Mutation Cycle | triggers=['schedule:'] | .github/workflows/dna-mutation-cycle.yml
- ETF & Bond Scanner | triggers=['schedule:'] | .github/workflows/etf-bond-scanner.yml
- Feed Health Check | triggers=['schedule:'] | .github/workflows/feed-health.yml
- Fix Battleground Deployment | triggers=['workflow_dispatch:'] | .github/workflows/fix-battleground.yml
- Forward Signal Scanner | triggers=['schedule:'] | .github/workflows/forward-signal-scanner.yml
- Forward Trade Tracking v2 | triggers=['schedule:'] | .github/workflows/forward-tracking-v2.yml
- Forward Test - Strategy Validation | triggers=['schedule:'] | .github/workflows/forward_test.yml
- ... +53 more

## Active missing concurrency (up to 30)
- 2hour-challenge | triggers=['workflow_dispatch:'] | .github/workflows/2hour_challenge.yml
- Dynamic Runner Template | triggers=['workflow_call:'] | .github/workflows/_dynamic-runner-template.yml
- ALPHA ENGINE - Adaptive Trust Tuner | triggers=['schedule:'] | .github/workflows/adaptive-trust-tuner.yml
- AI Leaderboard Freshness (daily FTP + data rebuild) | triggers=['schedule:'] | .github/workflows/ai-leaderboard-freshness.yml
- AI Leaderboard Refresh | triggers=['# Superseded by ai-leaderboard-freshness.yml (daily FTP + MA + truth panel).'] | .github/workflows/ai-leaderboard-refresh.yml
- AI Tournament Price Tracker | triggers=['schedule:'] | .github/workflows/ai-tournament-price-tracker.yml
- Algorithm Competition Refresh | triggers=['schedule:'] | .github/workflows/algorithm-competition-refresh.yml
- Alpha Engine  Daily Picks | triggers=['schedule:'] | .github/workflows/alpha-engine-daily-picks.yml
- Alpha Engine - Weekly Validation Suite | triggers=['schedule:'] | .github/workflows/alpha-weekly-validation.yml
- Analyst Tracker  Top 20 Crypto Analysts | triggers=['schedule:'] | .github/workflows/analyst-tracker.yml
- AsterDEX Paper Trading | triggers=['schedule:'] | .github/workflows/asterdex-paper-trading.yml
- Audit Drift Telemetry | triggers=['push:'] | .github/workflows/audit-drift-telemetry.yml
- Audit Frontend Manifest | triggers=['push:'] | .github/workflows/audit-frontend-manifest.yml
- Audit Impact Tracker | triggers=['schedule:'] | .github/workflows/audit-impact-tracker.yml
- Auto-Retire — Daily Bleeder Check | triggers=['schedule:'] | .github/workflows/auto-retire-daily.yml
- Auto-Shutdown Source Monitor | triggers=['schedule:'] | .github/workflows/auto-shutdown-monitor.yml
- Automated Reporting | triggers=['schedule:'] | .github/workflows/automated-reporting.yml
- Autonomous Trading Bot - Runs Automatically Every 4 Hours | triggers=['# Run automatically every 4 hours (no user action needed!)'] | .github/workflows/autonomous_trading.yml
- Backfill OHLCV Features | triggers=['schedule:'] | .github/workflows/backfill-features.yml
- Backfill Missing Audit Trail Sources | triggers=['schedule:'] | .github/workflows/backfill.yml
- Backup Restore Verification | triggers=['schedule:'] | .github/workflows/backup-verify.yml
- Battleground Mass Backtest (Part 2 - Babies) | triggers=['workflow_dispatch:'] | .github/workflows/battleground-mass-backtest-part2.yml
- Benchmark Comparison  Daily | triggers=['schedule:'] | .github/workflows/benchmark-comparison.yml
- Breakout Arena  3 Approaches | triggers=['schedule:'] | .github/workflows/breakout-arena.yml
- bt_backtest_trades cross-DB sync (DRAFT) | triggers=['workflow_dispatch:'] | .github/workflows/bt-backtest-trades-sync.yml
- CFTC COT Refresh | triggers=['schedule:'] | .github/workflows/cftc-cot-refresh.yml
- Check Streamer Live Status | triggers=['schedule:'] | .github/workflows/check-streamer-status.yml
- Claude Gainer ML  Live Scanner | triggers=['schedule:'] | .github/workflows/claude-gainer-ml-live.yml
- Claude Code Gainer ML Tracker | triggers=['schedule:'] | .github/workflows/claude-gainer-tracker.yml
- Clear Channel Command | triggers=['workflow_dispatch:'] | .github/workflows/clear-channel-command.yml
- ... +161 more