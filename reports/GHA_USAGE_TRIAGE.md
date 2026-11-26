# GitHub Actions Usage Triage

Cost-weighted join of the GitHub Actions usage export (minutes + run counts) against the repo workflow inventory, the per-workflow run matrix, and the latest-run log audit.

## Headline

| Metric | Value |
|--------|------:|
| Workflow files in repo | 382 |
| Workflows present in usage export | 380 |
| Billed minutes | 560,627 |
| Billed runs | 104,981 |
| **Workflows needing investigation** | **160** |
| — with errors in latest log | 86 |
| — suspicious log | 60 |
| — never ran (no billed runs) | 5 |
| — audit had no log to read | 8 |
| — billed under a deleted file name | 1 |
| — billed under a renamed file name | 3 |

## Buckets

| Bucket | Workflows | Minutes | Runs |
|--------|----------:|--------:|-----:|
| ERRORS | 86 | 200,354 | 24,116 |
| SUSPICIOUS | 60 | 74,449 | 16,723 |
| NEVER_RAN | 5 | 0 | 0 |
| AUDIT_INCOMPLETE | 8 | 110,317 | 3,601 |
| DELETED | 1 | 5 | 5 |
| RENAMED | 3 | 2,787 | 774 |
| DISABLED | 1 | 1,613 | 364 |
| WARN_ONLY | 49 | 75,883 | 11,197 |
| UNAUDITED | 10 | 3,442 | 2,567 |
| CLEAN | 166 | 89,905 | 45,027 |
| MANAGED | 2 | 1,872 | 607 |

## Top 25 by priority

| # | Workflow | Bucket | Minutes | Runs | Latest | Errors |
|--:|----------|--------|--------:|-----:|--------|-------:|
| 1 | `audit-dashboard.yml` | ERRORS | 28,689 | 334 | success | 38 |
| 2 | `dynamic-alpha-engine.yml` | ERRORS | 25,870 | 641 | success | 47 |
| 3 | `gainer-predictor.yml` | ERRORS | 17,059 | 1,206 | success | 205 |
| 4 | `alpha-engine-live.yml` | ERRORS | 16,050 | 394 | cancelled | 27 |
| 5 | `cross-aggregator.yml` | ERRORS | 15,009 | 1,204 | success | 19 |
| 6 | `self_optimizing_trading.yml` | ERRORS | 11,839 | 614 | — | 1 |
| 7 | `baby-strat-forward-paper.yml` | ERRORS | 11,452 | 606 | success | 4 |
| 8 | `discord-bot.yml` | AUDIT_INCOMPLETE | 35,340 | 101 | cancelled | 0 |
| 9 | `alpha-engine-fast.yml` | AUDIT_INCOMPLETE | 34,331 | 1,186 | cancelled | 0 |
| 10 | `mirror-site.yml` | ERRORS | 8,329 | 325 | — | 1 |
| 11 | `torontoevent-deploy-riseoftheclaw.yml` | ERRORS | 6,901 | 1,343 | — | 2 |
| 12 | `deploy-riseoftheclaw.yml` | ERRORS | 6,575 | 1,216 | success | 25 |
| 13 | `strategy-funnel-hourly.yml` | ERRORS | 5,788 | 606 | — | 1 |
| 14 | `copy-trader-intelligence.yml` | AUDIT_INCOMPLETE | 30,651 | 1,200 | success | 0 |
| 15 | `dna_strategy_pipeline.yml` | SUSPICIOUS | 15,380 | 489 | cancelled | 0 |
| 16 | `live_spike_trading.yml` | ERRORS | 4,949 | 308 | success | 1 |
| 17 | `signal-engine.yml` | ERRORS | 4,518 | 1,234 | — | 4 |
| 18 | `multi-asset-scanner.yml` | ERRORS | 3,371 | 1,208 | — | 1 |
| 19 | `quan-engine-live.yml` | ERRORS | 3,266 | 1,208 | — | 3 |
| 20 | `social-prediction-tracker.yml` | ERRORS | 2,436 | 304 | — | 1 |
| 21 | `realtime-challenge.yml` | ERRORS | 2,174 | 414 | — | 3 |
| 22 | `deploy-vetted-picks.yml` | ERRORS | 1,875 | 151 | success | 1 |
| 23 | `forward-tracking-v2.yml` | ERRORS | 1,739 | 604 | success | 70 |
| 24 | `claude-gainer-ml-live.yml` | ERRORS | 1,612 | 1,210 | success | 3 |
| 25 | `2hour_challenge.yml` | ERRORS | 1,563 | 21 | cancelled | 1 |

## Most expensive workflows

| # | Workflow | Minutes | Runs | Bucket | Top job |
|--:|----------|--------:|-----:|--------|---------|
| 1 | `discord-bot.yml` | 35,340 | 101 | AUDIT_INCOMPLETE | `run-bot` (35,340) |
| 2 | `alpha-engine-fast.yml` | 34,331 | 1,186 | AUDIT_INCOMPLETE | `alpha-fast` (34,331) |
| 3 | `copy-trader-intelligence.yml` | 30,651 | 1,200 | AUDIT_INCOMPLETE | `copy-trader-scan` (30,651) |
| 4 | `audit-dashboard.yml` | 28,689 | 334 | ERRORS | `generate-and-deploy` (28,756) |
| 5 | `dynamic-alpha-engine.yml` | 25,870 | 641 | ERRORS | `alpha-engine` (25,870) |
| 6 | `gainer-predictor.yml` | 17,059 | 1,206 | ERRORS | `scan` (17,059) |
| 7 | `alpha-engine-live.yml` | 16,050 | 394 | ERRORS | `alpha-engine` (16,050) |
| 8 | `market_beating.yml` | 15,910 | 865 | WARN_ONLY | `market-beating` (15,515) |
| 9 | `dna_strategy_pipeline.yml` | 15,380 | 489 | SUSPICIOUS | `Generate Active Picks` (14,357) |
| 10 | `cross-aggregator.yml` | 15,009 | 1,204 | ERRORS | `aggregate` (15,011) |
| 11 | `signal_tracking.yml` | 13,661 | 751 | WARN_ONLY | `track-and-validate` (13,663) |
| 12 | `self_optimizing_trading.yml` | 11,839 | 614 | ERRORS | `trade` (11,839) |
| 13 | `autonomous_trading.yml` | 11,612 | 614 | WARN_ONLY | `trade` (11,615) |
| 14 | `baby-strat-forward-paper.yml` | 11,452 | 606 | ERRORS | `forward-monitor` (11,452) |
| 15 | `ci-tests.yml` | 10,879 | 1,389 | SUSPICIOUS | `test (3.12)` (5,646) |
| 16 | `polymarket-signals.yml` | 8,525 | 1,209 | SUSPICIOUS | `polymarket-scan` (8,534) |
| 17 | `mirror-site.yml` | 8,329 | 325 | ERRORS | `mirror` (8,329) |
| 18 | `torontoevent-deploy-riseoftheclaw.yml` | 6,901 | 1,343 | ERRORS | `deploy` (6,901) |
| 19 | `outcome-resolver.yml` | 6,844 | 616 | SUSPICIOUS | `resolve-outcomes` (6,844) |
| 20 | `signal-integrator.yml` | 6,710 | 607 | CLEAN | `integrate` (6,710) |
| 21 | `deploy-riseoftheclaw.yml` | 6,575 | 1,216 | ERRORS | `deploy` (6,575) |
| 22 | `branch-large-file-dup-guard.yml` | 6,560 | 131 | AUDIT_INCOMPLETE | `detect-duplicate-large-blobs` (6,560) |
| 23 | `strategy-funnel-hourly.yml` | 5,788 | 606 | ERRORS | `refresh` (5,790) |
| 24 | `darwin-evolution.yml` | 5,786 | 605 | WARN_ONLY | `evolve` (5,786) |
| 25 | `genome-daily-pipeline.yml` | 5,503 | 211 | CLEAN | `strategy-permutation` (3,413) |

## Billed under a name the repo no longer has

| Billed workflow | Minutes | Runs | Classification | Successor |
|-----------------|--------:|-----:|----------------|-----------|
| `live_trading_canada_free.yml` | 2,606 | 593 | RENAMED | `live_trading_canada.yml` |
| `pages-build-deployment` | 1,870 | 606 | MANAGED | `GitHub-generated workflow` |
| `torontoevent-backtest-and-deploy-ROOCODE.yml` | 1,613 | 364 | DISABLED | `torontoevent-backtest-and-deploy-ROOCODE.yml.disabled` |
| `daily-price-refresh.yml` | 166 | 166 | RENAMED | `daily-prices-yf-refresh.yml` |
| `cross-db-consistency.yml` | 15 | 15 | RENAMED | `cross-db-audit.yml` |
| `mermaid-test-deploy.yml` | 5 | 5 | DELETED | — |
| `update-graph` | 2 | 1 | MANAGED | `GitHub-generated workflow` |

## Cost concentration

- Top 10 workflows = 234,289 min (41.8% of billed minutes)
- Top 25 workflows = 361,253 min (64.4% of billed minutes)
- Top 50 workflows = 445,791 min (79.5% of billed minutes)


> Minutes are the provider's billed total for the export window, not a per-run wall clock. A workflow with 0 minutes and 0 runs never executed in that window; it is still `active` in the repo and will execute the moment its trigger fires. See `reports/GHA_VALIDATION_LEDGER.md` for the per-workflow verdict ledger and `reports/GHA_PER_WORKFLOW_RUN_TODOS.md` for actions.
