# GHA quality framework (Q1-Q10)

- workflows scanned: 375 (parse errors: 1)
- aggregate score: 94.4/100
- blocking violations: 103
- runtime signals merged: True

## Findings by rule

| Rule | Name | Severity | Count |
|---|---|---|---|
| Q1 | cron-stampede | P2 | 60 |
| Q2 | unpinned-action | P1 | 10 |
| Q3 | write-all-default | P1 | 28 |
| Q4 | self-push-without-skip-ci | P2 | 4 |
| Q5 | duplicate-producer | P0 | 21 |
| Q6 | orphan-artifact | P2 | 166 |
| Q7 | silent-failure | P0 | 40 |
| Q8 | missing-timeout | P1 | 4 |
| Q9 | secret-sprawl | P2 | 15 |
| Q10 | dead-schedule | P2 | 28 |

## Blocking findings

| Rule | Workflow | Detail |
|---|---|---|
| Q2 | FINDTORONTOEVENTS.CA Database Backups | third-party action not SHA-pinned: dawidd6/action-send-mail@v24 |
| Q2 | Deploy Strategy Bundle | third-party action not SHA-pinned: slackapi/slack-github-action@v1 |
| Q2 | DNA Genome Daily Pipeline | third-party action not SHA-pinned: SamKirkland/FTP-Deploy-Action@4.3.0 |
| Q2 | DNA Genome Daily Pipeline | third-party action not SHA-pinned: SamKirkland/FTP-Deploy-Action@4.3.0 |
| Q2 | KIMI Goldmine Data Collection | third-party action not SHA-pinned: shivammathur/setup-php@v2 |
| Q2 | Live Picks Tracker | third-party action not SHA-pinned: peaceiris/actions-gh-pages@v4 |
| Q2 | ML Feedback Loop | third-party action not SHA-pinned: peter-evans/repository-dispatch@v4 |
| Q2 | Secret Scan (M-043) | third-party action not SHA-pinned: gitleaks/gitleaks-action@v2 |
| Q2 | Sports Betting  Odds Refresh & Auto-Settle | third-party action not SHA-pinned: stefanzweifel/git-auto-commit-action@v7 |
| Q2 | Weekly Real-Money Filter | third-party action not SHA-pinned: stefanzweifel/git-auto-commit-action@v7 |
| Q3 | Backfill OHLCV Features | pushes to the repo but declares no `permissions:` |
| Q3 | Backfill Missing Audit Trail Sources | pushes to the repo but declares no `permissions:` |
| Q3 | Run Backtests & Deploy Dashboards | pushes to the repo but declares no `permissions:` |
| Q3 | Benchmark Comparison  Daily | pushes to the repo but declares no `permissions:` |
| Q3 | Breakout Arena  3 Approaches | pushes to the repo but declares no `permissions:` |
| Q3 | Claude Code Gainer ML Tracker | pushes to the repo but declares no `permissions:` |
| Q3 | Crypto Gainer ML Live Tracker | pushes to the repo but declares no `permissions:` |
| Q3 | Deploy Vetted Master-Picks | pushes to the repo but declares no `permissions:` |
| Q3 | Enhanced ML Crypto Train & Predict | pushes to the repo but declares no `permissions:` |
| Q3 | Forward Signal Scanner | pushes to the repo but declares no `permissions:` |
| Q3 | Funding-Rate Archive Collector | pushes to the repo but declares no `permissions:` |
| Q3 | Gainer Predictor Scanner | pushes to the repo but declares no `permissions:` |
| Q3 | Gate Config Emit | pushes to the repo but declares no `permissions:` |
| Q3 | Strategy Genome Evolution | pushes to the repo but declares no `permissions:` |
| Q3 | GHA scan job (reusable) | pushes to the repo but declares no `permissions:` |
| Q3 | H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) | pushes to the repo but declares no `permissions:` |
| Q3 | KIMI Goldmine Data Collection | pushes to the repo but declares no `permissions:` |
| Q3 | Meta-Strategy Permutation Engine | pushes to the repo but declares no `permissions:` |
| Q3 | ML Forward Test 1745 Models | pushes to the repo but declares no `permissions:` |
| Q3 | Optimize Score Thresholds | pushes to the repo but declares no `permissions:` |
| Q3 | Overnight Mutations | pushes to the repo but declares no `permissions:` |
| Q3 | RL Agent (PPO) Train & Predict | pushes to the repo but declares no `permissions:` |
| Q3 | Skyrocket Detector  Live Scanner | pushes to the repo but declares no `permissions:` |
| Q3 | SPY 20d Return Refresh | pushes to the repo but declares no `permissions:` |
| Q3 | swarm-janitor | pushes to the repo but declares no `permissions:` |
| Q3 | [torontoevent.net] Run Backtests & Deploy Dashboards | pushes to the repo but declares no `permissions:` |
| Q3 | TradingView Strategy Scanner | pushes to the repo but declares no `permissions:` |
| Q3 | Weekly Strategy Scorecard | pushes to the repo but declares no `permissions:` |
| Q5 | (repo) | 2 workflows write OPTIMIZATION_REPORT.md |
| Q5 | (repo) | 2 workflows write REAL_CHALLENGE_FINAL.md |
| Q5 | (repo) | 2 workflows write REAL_CHALLENGE_RESULTS.json |
| Q5 | (repo) | 2 workflows write STOCKS/competition/forward_picks.json |
| Q5 | (repo) | 2 workflows write STOCKSUNIFY/data/daily-stocks.json |
| Q5 | (repo) | 2 workflows write alpha_engine/data/active_picks.json |
| Q5 | (repo) | 2 workflows write audit_dashboard/data/ai_tournament_model_summary.json |
| Q5 | (repo) | 2 workflows write audit_dashboard/data/ai_tournament_picks_latest.json |
| Q5 | (repo) | 3 workflows write copy_trader_intel/data/polymarket_picks.json |
| Q5 | (repo) | 3 workflows write copy_trader_intel/data/polymarket_trader_profiles.json |
| Q5 | (repo) | 2 workflows write daily-stocks.json |
| Q5 | (repo) | 6 workflows write data/freshpicks_gate_state.json |
| Q5 | (repo) | 2 workflows write genome/active_picks.json |
| Q5 | (repo) | 2 workflows write ml_battleground/retrain_trigger.json |
| Q5 | (repo) | 3 workflows write signal_aggregator/data/master_picks_history.json |
| Q5 | (repo) | 3 workflows write signal_aggregator/data/master_picks_tracker.json |
| Q5 | (repo) | 2 workflows write signals_database.json |
| Q5 | (repo) | 2 workflows write tmp/audit/result.json |
| Q5 | (repo) | 4 workflows write trading_results.json |
| Q5 | (repo) | 2 workflows write tweak_history.json |
| Q5 | (repo) | 2 workflows write validation_results.json |
| Q7 | A/B Analysis + Zero-PnL Audit | gate-shaped step swallows failure: Verify all Tier-2 winners DB vs dashboard PF/WR/n |
| Q7 | A/B Analysis + Zero-PnL Audit | gate-shaped step swallows failure: Run CT=F friction-adjusted ROR MC + DSR gate |
| Q7 | AI Tournament Pipeline — Daily Picks + DB Ingest | gate-shaped step swallows failure: Check existing picks state |
| Q7 | ALPHA ENGINE - Live Autonomous Scanner | gate-shaped step swallows failure: Verify audit sources staleness |
| Q7 | Unified Audit Dashboard | gate-shaped step swallows failure: Run DB health check (PnL integrity, ghost rows, OPEN bloat → audit_dashboard/data/db_health.json) |
| Q7 | Unified Audit Dashboard | gate-shaped step swallows failure: Operator status check (validation/alerting snapshot — Grok next-step |
| Q7 | Unified Audit Dashboard | gate-shaped step swallows failure: ml_gatekeeper A/B sleeve decision (Phase D — reads OLD/NEW sleeves + closed_picks, runs z-test) |
| Q7 | Unified Audit Dashboard | gate-shaped step swallows failure: Run Hyro QuanBridge (refresh regime + ensemble + risk gate) |
| Q7 | Unified Audit Dashboard | gate-shaped step swallows failure: Run pick-flow funnel snapshot (DB → per-class raw/gated/forward-test counts) |
| Q7 | Audit Drift Telemetry | gate-shaped step swallows failure: Pending SPA governance check |
| Q7 | Audit Drift Telemetry | gate-shaped step swallows failure: Data source health check (C-008) |
| Q7 | Cross-System Signal Aggregator | gate-shaped step swallows failure: Forward-test top picks |
| Q7 | Daily Miracle DayTrades Scan | gate-shaped step swallows failure: Verify miracle dashboard |
| Q7 | Daily Picks Snapshot  Crypto, Forex & Stocks | gate-shaped step swallows failure: Verify crypto picks |
| Q7 | Daily Picks Snapshot  Crypto, Forex & Stocks | gate-shaped step swallows failure: Verify momentum picks |
| Q7 | Daily Picks Snapshot  Crypto, Forex & Stocks | gate-shaped step swallows failure: Verify recent wins |
| Q7 | Daily Stock Data Refresh | gate-shaped step swallows failure: Verify report page loads |
| Q7 | Daily Stock Data Refresh | gate-shaped step swallows failure: Verify cached report data |
| Q7 | DB Freshness Guardian | gate-shaped step swallows failure: Run DB freshness check |
| Q7 | DB Sync: findtorontoevents.ca  torontoevent.net | gate-shaped step swallows failure: Verify export script deployed |
| Q7 | Deals & Freebies  Verify & Refresh | gate-shaped step swallows failure: Verify deals API health |

## Lowest-scoring workflows

| Workflow | Score |
|---|---|
| Unified Audit Dashboard | 0 |
| Deals & Freebies  Verify & Refresh | 0 |
|  | 0 |
| Daily Picks Snapshot  Crypto, Forex & Stocks | 25 |
| Meta-Strategy Permutation Engine | 40 |
| Sports Betting  Odds Refresh & Auto-Settle | 45 |
| Cross-System Signal Aggregator | 48 |
| A/B Analysis + Zero-PnL Audit | 50 |
| Audit Drift Telemetry | 50 |
| Daily Stock Data Refresh | 50 |
| AI Tournament Pipeline — Daily Picks + DB Ingest | 57 |
| ALPHA ENGINE - Live Autonomous Scanner | 60 |
| Verified pilot daily | 70 |
| Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities | 72 |
| [torontoevent.net] Deploy Rise of the Claw | 72 |

## Advisory findings (P2)

- Q1 (repo): 36 workflows share cron minute :0
- Q1 (repo): 4 workflows share cron minute :1
- Q1 (repo): 6 workflows share cron minute :10
- Q1 (repo): 6 workflows share cron minute :11
- Q1 (repo): 5 workflows share cron minute :12
- Q1 (repo): 6 workflows share cron minute :13
- Q1 (repo): 12 workflows share cron minute :14
- Q1 (repo): 10 workflows share cron minute :15
- Q1 (repo): 3 workflows share cron minute :16
- Q1 (repo): 2 workflows share cron minute :17
- Q1 (repo): 4 workflows share cron minute :18
- Q1 (repo): 6 workflows share cron minute :19
- Q1 (repo): 4 workflows share cron minute :2
- Q1 (repo): 8 workflows share cron minute :20
- Q1 (repo): 6 workflows share cron minute :22
- Q1 (repo): 6 workflows share cron minute :23
- Q1 (repo): 7 workflows share cron minute :24
- Q1 (repo): 7 workflows share cron minute :25
- Q1 (repo): 6 workflows share cron minute :26
- Q1 (repo): 4 workflows share cron minute :27
- Q1 (repo): 3 workflows share cron minute :28
- Q1 (repo): 7 workflows share cron minute :29
- Q1 (repo): 4 workflows share cron minute :3
- Q1 (repo): 5 workflows share cron minute :30
- Q1 (repo): 4 workflows share cron minute :31
- Q1 (repo): 7 workflows share cron minute :32
- Q1 (repo): 9 workflows share cron minute :33
- Q1 (repo): 6 workflows share cron minute :34
- Q1 (repo): 2 workflows share cron minute :34,4
- Q1 (repo): 13 workflows share cron minute :35
- Q1 (repo): 2 workflows share cron minute :36
- Q1 (repo): 4 workflows share cron minute :37
- Q1 (repo): 4 workflows share cron minute :38
- Q1 (repo): 4 workflows share cron minute :39
- Q1 (repo): 2 workflows share cron minute :4
- Q1 (repo): 7 workflows share cron minute :40
- Q1 (repo): 3 workflows share cron minute :40,10
- Q1 (repo): 15 workflows share cron minute :41
- Q1 (repo): 6 workflows share cron minute :42
- Q1 (repo): 9 workflows share cron minute :43
