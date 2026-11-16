# cron_verification.md
**Base commit:** `eb23252219786dc09362a5a500aef2f9bc6f794f` (origin/main)
**STAMP:** 2026-11-15_21-00-33_EST_ghactions
**Generated:** local git only — `git show origin/main:<path>`

## Retraction
Earlier claim of a `deploy-competition.yml` running every ~2 min is **retracted**. No such file exists on `main`. The two lookalikes (`torontoevent-*.yml`) are `push:` + `paths:` + `workflow_run:` chained, **not cron**. No 2-minute cron present anywhere.

## Cron Inventory (reproducible commands)
```bash
mkdir -p /tmp/triage_wf
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
git ls-tree -r --name-only origin/main -- .github/workflows \
  | grep -E '\.ya?ml$' | grep -v '\.disabled$' > /tmp/triage_wf/list.txt
# 358 workflow files
: > /tmp/triage_wf/crons.tsv
while read p; do
  git show origin/main:"$p" 2>/dev/null \
    | grep -oE "cron:\s*['\"][^'\"]+['\"]" \
    | sed -E "s/cron:\s*['\"]//; s/['\"]$//" \
    | while read -r e; do
        printf '%s\t%s\n' "$p" "$(echo "$e" | tr -s ' ')" >> /tmp/triage_wf/crons.tsv
      done
done < /tmp/triage_wf/list.txt
```
**Result:** 358 workflow files, **362 cron lines**, 310 files with ≥1 cron, 48 with none.

## Top Cron Tiers (tie resolved)
| cron | count | example workflows |
|------|-------|-------------------|
| `0 */2 * * *` | **15** | backfill.yml, check-streamer-status.yml, daily-feed-summary.yml, fc-crypto-pro.yml, forward-signal-scanner.yml, kimi-feb172026-live.yml, kimi-goldmine-collector.yml, market_beating.yml, meme-scanner.yml, pick-monitor-30min.yml, proven-strategies-scanner.yml, signal_tracking.yml, spike-scanner.yml, system-health-check.yml, update-creator-news.yml |
| `0 */6 * * *` | **13** | audit-impact-tracker.yml, buy-now-analysis.yml, crypto-winner-scan.yml, data-pipeline-test.yml, forward-test-new-strategies.yml, fred-macro-refresh.yml, gha-summary-report.yml, hoffman-tracker.yml, mirror-site.yml, ml-feedback-loop.yml, ml-health-monitor.yml, ml-model-autotraining.yml, refresh-top-movies.yml |
| `0 */4 * * *` | **13** | autonomous_trading.yml, discord-heartbeat.yml, kimi-feb172026-live.yml, live_trading.yml, live_trading_canada.yml, master-automation-scheduler.yml, momentum-scanner.yml, parquet-ingest.yml, picks_dispatch.yml, self_optimizing_trading.yml, strategy-health-monitor.yml, tv-strategy-scanner.yml, what-worked-insights.yml |
| `*/30 * * * *` | 12 | actions-failure-guardian.yml, claudes-test-portfolios.yml, consensus-outcome-tracker.yml, gainer-predictor.yml, momentum-catcher.yml, multi-asset-scanner.yml, quan-engine-live.yml, regime-terminal.yml, signal-engine.yml, swarm-sync-v2.yml, torontoevent-deploy-riseoftheclaw.yml, torontoevent-spike-scanner.yml |
| `0 * * * *` | 12 | analyst-tracker.yml, battle_test.yml, contested-pick-checker.yml, crypto-ml-tracker.yml, darwin-evolution.yml, db-freshness-guardian.yml, discord_status.yml, forward-tracking-v2.yml, master-automation-scheduler.yml, meme-scanner-v2.yml, qa-market-validation.yml, send-accountability-reminders.yml |

**Minute-0 concentration:** 190 lines (52.5 %) start at minute `0`. This is the primary queue-hog driver.

## Multi-Cron Files (36 total) — `github.event.schedule` dispatch warning
**Deleting a cron entry in these files removes a dispatch mode.** Highest-risk files explicitly test `github.event.schedule`:

| #crons | file | crons | schedule dispatch? |
|--------|------|-------|--------------------|
| 4 | traditional-test-portfolios.yml | 30 13/19/1/7 * * 1-5 | no (stagger only) |
| 4 | non-crypto-ab-test.yml | same four | no |
| 4 | master-automation-scheduler.yml | 0 * / 0 */4 / 0 3 * * * / 0 0 * * 0 | **YES** — lines 33/186/220/340: `github.event.schedule == '0 * * * *' || inputs.job_type == 'hourly'` etc. Named-mode dispatcher. |
| 3 | torontoevent-goldmine-tracker.yml | 0 7 / 0 18 / 0 0 | no |
| 3 | torontoevent-backtest-and-deploy.yml | 0 6 / */15 14-21 1-5 / 0 */4 0,6 | **YES** — line 53 |
| 3 | torontoevent-backtest-and-deploy-ROOCODE.yml | same three | **YES** |
| 3 | meme-scanner-v2.yml | */10 / 0 */3 / 0 * | **YES** — lines 45/67/79/135/176 |
| 3 | kimi-feb172026-live.yml | 0 */2 / 0 */4 / 0 0 | **YES** — line 55-57 |
| 3 | goldmine-tracker.yml | 0 7 / 0 18 / 0 0 | no |
| 3 | futures-agent.yml | 0 14 1-5 / 0 22 1-5 / 0 22 0 | no |
| 3 | crypto-winner-scan.yml | */15 / 0 */6 / 0 3 0 | no |
| 3 | claude-gainer-tracker.yml | 15 */4 / 15 13 / 0 6 0 | no |
| 3 | backtest-and-deploy.yml | 0 6 / 0 14,16,18,20 1-5 / 0 */4 0,6 | **YES** — line 62 |
| 2 | worldclass-pipeline.yml | 45 20 1-5 / 0 15 0 | **YES** — line 223 |
| 2 | worldclass-intelligence.yml | 30 11 1-5 / 0 14 0 | **YES** — lines 152/219 |
| 2 | track-quick-picks.yml | 0 23 1-5 / 0 12 0 | no |
| 2 | smart-money-tracker.yml | 0 11 1-5 / 0 14 0 | **YES** — lines 16/91/123 |
| 2 | signal-engine.yml | */30 / 0 2 | no |
| 2 | sec-edgar-fetch.yml | 0 13 1-5 / 0 6 0 | **YES** — line 83 |
| 2 | scrape-events.yml | 0 4 / 0 3 | no |
| 2 | regime-detector.yml | 30 20 1-5 / 0 14 0 | **YES** — line 73 |
| 2 | poc-picks-checkpoint.yml | 0 21 18 7 * / 0 21 20 7 * (date-pinned) | no |
| 2 | meta-strategy.yml | 20 * / 0 5,11,17,23 | **YES** — line 62: `CRON="${{ github.event.schedule }}"` |
| 2 | meme-scanner.yml | 0 */2 / 0 */3 | **YES** — line 45 |
| 2 | live-monitor-refresh.yml | 42 * / 0 2 0 | **YES** — line 154 |
| 2 | kimi-goldmine-collector.yml | 0 13,15,17,19 1-5 / 0 */2 | no |
| 2 | etf-bond-scanner.yml | 35 13 1-5 / 0 14 1-5 | no |
| 2 | equities-agent.yml | 0 13 1-5 / 0 21 1-5 | no |
| 2 | enhanced-ml-crypto.yml | 0 2 / 19 */2 | inputs.mode gated (line 59) |
| 2 | deals-refresh.yml | 0 14 1 / 0 14 1 * * | no |
| 2 | daily-stock-refresh.yml | 30 22 1-5 / 0 14 1-5 | no |
| 2 | daily-picks-snapshot.yml | 0 22 1-5 / 0 5 1 | no |
| 2 | commodities-agent.yml | 0 10 1-5 / 0 20 1-5 | no |
| 2 | automated-reporting.yml | 0 8 * / 0 9 1 | **YES** — line 58 |
| 2 | analyst-tracker.yml | 15 */4 / 0 * | **YES** — lines 22-25 |
| 2 | alpha-engine-daily-picks.yml | 0 22 1-5 / 0 5 0 | no |

**Recommendation:** Any cron-de-duplication pass must preserve the `github.event.schedule` branches above or the named modes will silently disappear.
