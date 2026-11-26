# Latest-run log audit

Every workflow's most recent run, log downloaded and scanned for errors, warnings and suspicious output. A green run is not a clean run.

- workflows examined: **386**
- logs audited: **73**
- no run on record: **313**

| Verdict | Count |
|---|---|
| ERRORS | 26 |
| WARNINGS | 20 |
| SUSPICIOUS | 6 |
| CLEAN | 21 |

## Workflows whose log contains errors

### `backfill-features.yml` — 38 error line(s), conclusion `success`
- 38× http 4xx
    - `backfill	Run backfill	2026-11-26T03:10:40.3083555Z   [WARN] All Binance mirrors failed for RENDERUSDT: HTTP Error 451:`
    - `backfill	Run backfill	2026-11-26T03:10:40.3084747Z   [WARN] All Binance mirrors failed for RENDERUSDT: HTTP Error 451:`

### `cross-aggregator.yml` — 20 error line(s), conclusion `success`
- 19× missing file
    - `aggregate	Run cross-system aggregator	2026-11-26T03:45:57.7402887Z   [WARN] Could not load /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/mercury2/data/active_picks.json: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca/fin`
    - `aggregate	Run cross-system aggregator	2026-11-26T03:45:57.7407431Z   [WARN] Could not load /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/battleground/data/active_picks.json: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca`
- 1× ERROR line
    - `aggregate	Commit and push if changed	2026-11-26T03:47:08.3262747Z [36;1m    echo "ERROR: all push attempts failed"[0m`

### `asterdex-paper-trading.yml` — 10 error line(s), conclusion `success`
- 10× ERROR line
    - `trade	Run strategy scanner	2026-11-26T03:19:46.4947610Z   [ERROR] Klines fetch failed for BTCUSDT: HTTP Error 451:`
    - `trade	Run strategy scanner	2026-11-26T03:19:46.4948057Z   [ERROR] Klines fetch failed for ETHUSDT: HTTP Error 451:`

### `etf-bond-scanner.yml` — 10 error line(s), conclusion `success`
- 10× http 4xx
    - `Bond Scanner	Run Bond Scanner	2026-11-26T03:40:24.6425182Z 2026***11***26 03:40:24,642 [alpha_engine.bond_data_fred] INFO: fred_json failed for DGS2: HTTP Error 400: Bad Request`
    - `Bond Scanner	Run Bond Scanner	2026-11-26T03:40:25.4210412Z 2026***11***26 03:40:25,420 [alpha_engine.bond_data_fred] INFO: fred_json failed for DGS10: HTTP Error 400: Bad Request`

### `alpha-engine-daily-picks.yml` — 8 error line(s), conclusion `success`
- 6× ERROR line
    - `generate-picks	Generate daily picks	2026-11-26T03:08:15.2234594Z 03:08:15 [ERROR] yfinance:`
    - `generate-picks	Generate daily picks	2026-11-26T03:08:15.2236376Z 03:08:15 [ERROR] yfinance: ['LLY']: OperationalError('database is locked')`
- 1× python traceback
    - `generate-picks	Generate daily picks	2026-11-26T03:08:21.7499439Z Traceback (most recent call last):`
- 1× missing file
    - `generate-picks	Validate proof-protocol metadata	2026-11-26T03:08:21.8866291Z ##[warning]Cannot read latest_picks.json: [Errno 2] No such file or directory: 'alpha_engine/output/latest_picks.json'`

### `audit-impact-tracker.yml` — 6 error line(s), conclusion `success`
- 5× missing file
    - `audit-impact	Run audit impact tracker	2026-11-26T03:27:43.5299245Z   [WARN] Could not load strategy_performance.json: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/data/strategy_performance.json'`
    - `audit-impact	Run audit impact tracker	2026-11-26T03:27:43.5301106Z   [WARN] Could not load active_picks.json: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/battleground/data/active_picks.json'`
- 1× ##[error] annotation
    - `audit-impact	Commit results	2026-11-26T03:32:57.1725742Z ##[error]The action 'Commit results' has timed out after 5 minutes.`

### `baby-strat-forward-paper.yml` — 4 error line(s), conclusion `success`
- 1× python traceback
    - `forward-monitor	Run incubator strategies (Chronos-Bolt, FundingRate, OI-Divergence, SMC-FVG)	2026-11-26T03:46:36.8029498Z Traceback (most recent call last):`
- 1× missing python module
    - `forward-monitor	Run incubator strategies (Chronos-Bolt, FundingRate, OI-Divergence, SMC-FVG)	2026-11-26T03:46:36.8040985Z ModuleNotFoundError: No module named 'api_helpers'`
- 1× ##[error] annotation
    - `forward-monitor	Run incubator strategies (Chronos-Bolt, FundingRate, OI-Divergence, SMC-FVG)	2026-11-26T03:46:36.8221260Z ##[error]Process completed with exit code 1.`
- 1× git fatal
    - `forward-monitor	Auto-commit changed forward artifacts	2026-11-26T03:46:39.6106385Z fatal: pathspec 'battleground/data/incubator_signals.json' did not match any files`

### `ai-model-portfolios-daily.yml` — 3 error line(s), conclusion `success`
- 2× python traceback
    - `portfolios-daily	Run daily portfolio engine	2026-11-26T03:09:23.3753521Z Traceback (most recent call last):`
    - `portfolios-daily	Run daily portfolio engine	2026-11-26T03:09:23.3768005Z Traceback (most recent call last):`
- 1× ##[error] annotation
    - `portfolios-daily	Run daily portfolio engine	2026-11-26T03:09:23.4641283Z ##[error]Process completed with exit code 1.`

### `backup-verify.yml` — 3 error line(s), conclusion `success`
- 3× ERROR line
    - `Backup Restore Verification	Run backup smoke queries	2026-11-26T03:08:51.6597931Z [36;1m        results["trading_picks_count"] = "ERROR"[0m`
    - `Backup Restore Verification	Run backup smoke queries	2026-11-26T03:08:51.6600111Z [36;1m    results["at_pick_outcomes_count"] = "ERROR"[0m`

### `claude-gainer-ml-live.yml` — 3 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `scan	Run live scanner	2026-11-26T03:30:16.6970952Z ##[error]No model .joblib files in claude_gainer_ml/models/ — scanner SKIPPED (scanner_ran=false, reason=no_models). Fail-open by design: job stays green but this run is a NO-OP. Status recorded in updates/data/antigravity_ml_performance.json.`
- 1× missing binary
    - `scan	Sync active picks + scorecard + history into dashboard JSON	2026-11-26T03:30:16.7344893Z /home/runner/work/_temp/12e87d11-b853-4983-b409-44fc1cd91d22.sh: line 2: scanner: command not found`
- 1× git fatal
    - `scan	Commit results	2026-11-26T03:30:16.7792075Z fatal: pathspec 'claude_gainer_ml/tracker/' did not match any files`

### `claude-gainer-tracker.yml` — 3 error line(s), conclusion `success`
- 2× ERROR line
    - `predict-and-track	Step 3: Self-improvement + ML feedback loop	2026-11-26T03:12:49.6435051Z [ERROR] No training data available at all`
    - `predict-and-track	Step 3: Self-improvement + ML feedback loop	2026-11-26T03:12:49.6435476Z [ERROR] Retraining failed`
- 1× ##[error] annotation
    - `predict-and-track	Step 2: Run live predictions (threshold=adaptive)	2026-11-26T03:12:48.3333802Z ##[error]No model .joblib files in claude_gainer_ml/models/ — scanner SKIPPED (scanner_ran=false, reason=no_models). Fail-open by design: job stays green but predictions are a NO-OP. Status recorded in u`

### `conviction-picks.yml` — 3 error line(s), conclusion `success`
- 3× http 4xx
    - `conviction-picks	Run Conviction Picks scanner	2026-11-26T02:54:26.4383988Z   [WARN] Binance klines failed (https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=60): HTTP Error 451:`
    - `conviction-picks	Run Conviction Picks scanner	2026-11-26T02:54:26.8442967Z   [WARN] Binance klines failed (https://api1.binance.com/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=60): HTTP Error 451:`

### `academic-strategies-daily.yml` — 2 error line(s), conclusion `success`
- 2× http 4xx
    - `emit-academic-picks	Run priority_picks_emitter (writes priority_picks.json)	2026-11-26T03:12:06.8413036Z 2026-11-26 03:12:06,840 [yfinance] HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NKLA"}}}`
    - `emit-academic-picks	Run priority_picks_emitter (writes priority_picks.json)	2026-11-26T03:12:07.3999368Z 2026-11-26 03:12:07,399 [yfinance] HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: MULN"}}}`

### `backtest-and-deploy.yml` — 2 error line(s), conclusion `success`
- 2× http 4xx
    - `backtest	Run live market scanner	2026-11-26T03:11:47.7308637Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NKLA"}}}`
    - `backtest	Run live market scanner	2026-11-26T03:12:01.3574087Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"No fundamentals data found for symbol: SQ"}}}`

### `clear-channel-command.yml` — 2 error line(s), conclusion `failure`
- 1× ERROR line
    - `clear-channel	Clear Channel	2026-11-26T02:57:13.5448745Z ERROR:__main__:Bot lacks permission to delete messages in channel 1476311595977150779`
- 1× ##[error] annotation
    - `clear-channel	Clear Channel	2026-11-26T02:57:31.2984495Z ##[error]Process completed with exit code 1.`

### `ab_analysis.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `ab-analysis	Verify all Tier-2 winners DB vs dashboard PF/WR/n	2026-11-26T03:08:09.6641308Z ERROR: /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json missing`

### `alpha-engine-etf.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `emit-etf-picks	Commit ETF picks	2026-11-26T03:08:40.1598802Z [36;1m  echo "ERROR: All 10 push attempts failed — data generated, next cycle will self-heal."[0m`

### `alpha-equity-breakout.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `equity-breakout-scan	Commit new picks	2026-11-26T03:08:31.9414088Z [36;1m  echo "ERROR: All 10 push attempts failed — picks generated, next cycle self-heals."[0m`

### `alpha-weekly-validation.yml` — 1 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `weekly-validation	Commit updated reports	2026-11-26T03:22:28.4939801Z ##[error]The operation was canceled.`

### `audit-drift-telemetry.yml` — 1 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `drift	Pending SPA governance check	2026-11-26T03:08:02.5607909Z ##[error]Process completed with exit code 1.`

### `audit3-ledger.yml` — 1 error line(s), conclusion `success`
- 1× http 4xx
    - `ledger	Backfill price tables (bounded, best-effort)	2026-11-26T03:10:59.0356208Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: XPDUSD=F"}}}`

### `backfill.yml` — 1 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `backfill	Commit any updated tracking files	2026-11-26T03:38:48.3032817Z ##[error]The operation was canceled.`

### `coinglass-scanner.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `scan	Run Coinglass DNA Scanner	2026-11-26T03:38:00.3864489Z 2026-11-26 03:38:00,386 ERROR All sources failed for MATICUSDT`

### `db-freshness-guardian.yml` — 1 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `DB Freshness Check	Run DB freshness check	2026-11-26T03:37:20.3346425Z ##[error]Process completed with exit code 2.`

### `deploy-fc-api-env-godaddy.yml` — 1 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `deploy-env	Install lftp	2026-11-26T03:41:22.4946179Z ##[error]Process completed with exit code 1.`

### `feature-signals-hourly.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `emit	Emit feature signals	2026-11-26T03:37:57.7944841Z   [ERROR] All premiumIndex endpoints failed`

## Warnings only

- `autonomous_trading.yml` — 12 warning(s): 12× WARNING line
- `ci.yml` — 8 warning(s): 6× deprecation, 2× ##[warning] annotation
- `audit3-evidence.yml` — 6 warning(s): 2× deprecation, 3× WARNING line, 1× ##[warning] annotation
- `claudes-test-portfolios.yml` — 6 warning(s): 5× workflow warning, 1× WARNING line
- `asset-class-freshness-watchdog.yml` — 5 warning(s): 5× workflow warning
- `ai-tournament-price-tracker.yml` — 4 warning(s): 1× workflow warning, 3× WARNING line
- `breakout-arena.yml` — 4 warning(s): 4× deprecated
- `crypto-intraday-sim.yml` — 4 warning(s): 2× deprecation, 2× ##[warning] annotation
- `algorithm-competition-refresh.yml` — 3 warning(s): 2× ##[warning] annotation, 1× workflow warning
- `audit3-health.yml` — 3 warning(s): 2× deprecation, 1× ##[warning] annotation
- `bestiejob-page-qa.yml` — 3 warning(s): 2× deprecation, 1× ##[warning] annotation
- `bond-agent.yml` — 2 warning(s): 1× workflow warning, 1× ##[warning] annotation
- `audit-hourly-update.yml` — 1 warning(s): 1× WARNING line
- `auto-shutdown-monitor.yml` — 1 warning(s): 1× workflow warning
- `automated-reporting.yml` — 1 warning(s): 1× ##[warning] annotation
- `blacklist-reconciler.yml` — 1 warning(s): 1× ##[warning] annotation
- `buy-now-analysis.yml` — 1 warning(s): 1× ##[warning] annotation
- `dxy-state-update.yml` — 1 warning(s): 1× workflow warning
- `edge-stability-daily.yml` — 1 warning(s): 1× workflow warning
- `edge-stability-refresh.yml` — 1 warning(s): 1× workflow warning

## Suspicious output only

- `actions-failure-guardian.yml` — 7: 7× skipped work
- `ai-leaderboard-freshness.yml` — 3: 3× skipped work
- `deploy-findcryptopairs-ftp.yml` — 2: 2× skipped work
- `alpha-verify-predictions.yml` — 1: 1× skipped work
- `crypto-ml-tracker.yml` — 1: 1× skipped work
- `discord-token-selftest.yml` — 1: 1× skipped work

## Not auditable

- `2hour_challenge.yml` — ALWAYS_RED: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `_dynamic-runner-template.yml` — SCHEDULE_ONLY: no run on record
- `adaptive-trust-tuner.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `ai-tournament-pipeline.yml` — DISABLED: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `alpha-engine-fast.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `alpha-engine-live.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `anti-overfit-gate.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `audit-dashboard.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `battle_test.yml` — DISABLED: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `battleground-mass-backtest.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `branch-large-file-dup-guard.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `ci-tests.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `closed-picks-command.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `commodities-agent.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `consensus-outcome-tracker.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `continuous-improvement-monitor.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `copilot` — SCHEDULE_ONLY: no run on record
- `copy-trader-forward-test.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `copy-trader-intelligence.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `correlation-monitor.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `cross-db-audit.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `crypto-ohlcv-refresh.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `crypto-smart-picks.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `crypto-test-portfolios.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `crypto-winner-scan.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `daily-feed-summary.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `daily-miracle-scan.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `daily-picks-snapshot.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `daily-prices-yf-refresh.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `daily-scrutiny-engine.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `daily-stock-refresh.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `daily-top-picks-filter.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `daily_runs.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `darwin-evolution.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `dashboard-pick-trader.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `data-pipeline-test.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `db-backup-email.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `db-password-leak-guard.yml` — SCHEDULE_ONLY: no run on record
- `db-secret-scan.yml` — DISABLED: no run on record
- `db-sync-bidirectional.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `db-sync-to-mirror.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deals-refresh.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-alpha-dashboard.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-battleground-ftp.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-competition-to-site.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-fc-api-hotfix.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-fc-frontend.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-friendtracker.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-fte-events-json.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-fte-index.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-movieshows-all.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-movieshows3-hotfix.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-riseoftheclaw.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `deploy-vetted-picks.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `discord-bot.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `discord-heartbeat.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `discord_status.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `dna-mutation-cycle.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `dna_strategy_pipeline.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `dynamic-alpha-engine.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `dynamic-universe.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `ema-retracement-scan.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `enhanced-ml-crypto.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `equities-agent.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `etf-agent.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `fc-crypto-pro.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `feature-stability-check.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `feed-health.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `fetch-movies-v3.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `fetch-movies.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `fix-battleground.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `fix-ghost-cards.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `forex-agent.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `forex-smart-picks.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `forward-benchmark-ledger.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `forward-observations-ingest.yml` — RED_REGRESSION: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `forward-signal-scanner.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `forward-test-new-strategies.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `forward-tracking-v2.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `forward_test.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `fred-macro-refresh.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `funding-rate-collector.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `futures-agent.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `fx-cost-overlap.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `gainer-predictor.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `gate-config-emit.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `genome-daily-pipeline.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `genome-evolution.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `gha-failure-digest.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `gha-health-audit.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `gha-quality-framework.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `gha-queue-audit.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `gha-scan-job.yml` — SCHEDULE_ONLY: no run on record
- `gha-stale-workflows-audit.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `gha-summary-report.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `ghcopilot-paper-monitor.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `goldmine-tracker.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `growth-stock-screener-daily.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `h004-backtest.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `h103-forward-logger.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `hc-parity.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `hierarchical-bayes.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `hindsight-learner.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `hoffman-tracker.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `honest-kill-switch.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `hourly-master-picks.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `hub-sync.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `hyro-bridge-regen.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `hyro-daily.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `incidents-enhancements-nightly.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `incubator-pipeline.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `incubator-strategies.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `index-creator-content.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `insider-trades-refresh.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `kalshi-snapshot.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `kimi-feb172026-live.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `kimi-fetch-movies.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `kimi-goldmine-collector.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `live-monitor-refresh.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `live_spike_trading.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `live_tracker.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `live_trading.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `live_trading_canada.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `low-score-tracker.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `luxalgo-signals.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `macd-rsi-m048-shadow-daily.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `market_beating.yml` — GREEN_RECENT: log unavailable: failed to get run: HTTP 403: API rate limit exceeded for user ID 38769710. If you reach out to GitHub Support for help, 
- `masking-policy-lint.yml` — SCHEDULE_ONLY: no run on record
- `master-automation-scheduler.yml` — NEVER_RUN: no run on record
- `master-picks-health.yml` — NEVER_RUN: no run on record
- `mega-mutation-tracker.yml` — NEVER_RUN: no run on record
- `meme-scanner-v2.yml` — NEVER_RUN: no run on record
- `meme-scanner.yml` — NEVER_RUN: no run on record
- `mercury2-retrain.yml` — NEVER_RUN: no run on record
- `mercury2-scan.yml` — NEVER_RUN: no run on record
- `mermaid-test-deploy.yml` — DISABLED: no run on record
- `meta-strategy.yml` — NEVER_RUN: no run on record
- `mirror-site.yml` — NEVER_RUN: no run on record
- `missed-opportunity-scan.yml` — NEVER_RUN: no run on record
- `ml-battleground-f.yml` — NEVER_RUN: no run on record
- `ml-battleground-retrain.yml` — NEVER_RUN: no run on record
- `ml-feedback-loop.yml` — NEVER_RUN: no run on record
- `ml-feedback-retrain.yml` — NEVER_RUN: no run on record
- `ml-forward-test.yml` — NEVER_RUN: no run on record
- `ml-gatekeeper-train-ab.yml` — NEVER_RUN: no run on record
- `ml-health-monitor.yml` — NEVER_RUN: no run on record
- `ml-model-autotraining.yml` — NEVER_RUN: no run on record
- `ml-monthly-retrain.yml` — NEVER_RUN: no run on record
- `ml-staleness-watchdog.yml` — NEVER_RUN: no run on record
- `ml-strategy-reviver.yml` — NEVER_RUN: no run on record
- `model-picks-emission.yml` — NEVER_RUN: no run on record
- `momentum-catcher.yml` — NEVER_RUN: no run on record
- `momentum-scanner.yml` — NEVER_RUN: no run on record
- `momentum-tracker.yml` — NEVER_RUN: no run on record
- `money-ready-registry-gate.yml` — NEVER_RUN: no run on record
- `money-ready-snapshot.yml` — NEVER_RUN: no run on record
- `monthly-calibrator-refit.yml` — NEVER_RUN: no run on record
- `monthly-tournament.yml` — NEVER_RUN: no run on record
- `multi-asset-scanner.yml` — NEVER_RUN: no run on record
- `mutation-analysis-report.yml` — NEVER_RUN: no run on record
- `mutation-lab.yml` — NEVER_RUN: no run on record
- `mutation-lifecycle-runner.yml` — NEVER_RUN: no run on record
- `mysql-stale-picks-resolver.yml` — NEVER_RUN: no run on record
- `mysql-trading-sync.yml` — NEVER_RUN: no run on record
- `mysql_dedup_fix.yml` — NEVER_RUN: no run on record
- `news-video-healthcheck.yml` — NEVER_RUN: no run on record
- `no-stale-db-passwords.yml` — NEVER_RUN: no run on record
- `non-crypto-ab-test.yml` — NEVER_RUN: no run on record
- `now-scanner.yml` — NEVER_RUN: no run on record
- `obi-snapshot.yml` — NEVER_RUN: no run on record
- `operator-review-today.yml` — NEVER_RUN: no run on record
- `optimize-score-thresholds.yml` — NEVER_RUN: no run on record
- `outcome-resolver.yml` — NEVER_RUN: no run on record
- `overnight-mutations.yml` — NEVER_RUN: no run on record
- `pages-build-deployment` — SCHEDULE_ONLY: no run on record
- `paper-pilot-daily.yml` — NEVER_RUN: no run on record
- `parquet-ingest.yml` — NEVER_RUN: no run on record
- `pead-shadow-collector.yml` — NEVER_RUN: no run on record
- `peer-claim-verification.yml` — NEVER_RUN: no run on record
- `penny-skyrocket-runner.yml` — NEVER_RUN: no run on record
- `penny-stock-picks.yml` — NEVER_RUN: no run on record
- `php52-gate.yml` — NEVER_RUN: no run on record
- `pick-data-quality-gate.yml` — NEVER_RUN: no run on record
- `pick-funnel-nightly.yml` — NEVER_RUN: no run on record
- `pick-monitor-30min.yml` — NEVER_RUN: no run on record
- `picks-now-live-pnl.yml` — NEVER_RUN: no run on record
- `picks-now-refresh.yml` — NEVER_RUN: no run on record
- `picks_dispatch.yml` — NEVER_RUN: no run on record
- `pine-generator.yml` — NEVER_RUN: no run on record
- `poc-picks-checkpoint.yml` — NEVER_RUN: no run on record
- `pod-emission-audit.yml` — NEVER_RUN: no run on record
- `pod-h201-forward-clock.yml` — NEVER_RUN: no run on record
- `polymarket-signals.yml` — NEVER_RUN: no run on record
- `populate-alpha-macro-daily.yml` — NEVER_RUN: no run on record
- `portfolio-tracker.yml` — NEVER_RUN: no run on record
- `portfolio-trackers.yml` — NEVER_RUN: no run on record
- `pre-spike-scan.yml` — NEVER_RUN: no run on record
- `prediction-market-agents.yml` — NEVER_RUN: no run on record
- `prediction-quality-tracker.yml` — NEVER_RUN: no run on record
- `proven-strategies-scanner.yml` — NEVER_RUN: no run on record
- `provenance-verify.yml` — NEVER_RUN: no run on record
- `prune-strategy-performance.yml` — NEVER_RUN: no run on record
- `qa-market-validation.yml` — NEVER_RUN: no run on record
- `quan-engine-live.yml` — NEVER_RUN: no run on record
- `quant-auditor-deep-nightly.yml` — NEVER_RUN: no run on record
- `quant-auditor-fast-pr.yml` — SCHEDULE_ONLY: no run on record
- `quick-guess-ml.yml` — NEVER_RUN: no run on record
- `rapid-validation-CLAUDECODE_Feb152026.yml` — NEVER_RUN: no run on record
- `real_2hour_challenge.yml` — NEVER_RUN: no run on record
- `realtime-challenge.yml` — NEVER_RUN: no run on record
- `recommended-portfolio.yml` — NEVER_RUN: no run on record
- `refresh-creator-updates.yml` — NEVER_RUN: no run on record
- `refresh-top-movies.yml` — NEVER_RUN: no run on record
- `regime-detector.yml` — NEVER_RUN: no run on record
- `regime-terminal.yml` — NEVER_RUN: no run on record
- `research-orchestrator.yml` — NEVER_RUN: no run on record
- `resolver-step5-6-backfill.yml` — NEVER_RUN: no run on record
- `resolver-step7-apply.yml` — NEVER_RUN: no run on record
- `riseoftheclaw-weekly-backtest.yml` — NEVER_RUN: no run on record
- `rl-agent-ppo.yml` — NEVER_RUN: no run on record
- `robust-edge-miner.yml` — NEVER_RUN: no run on record
- `rsi5070-forward-snapshot.yml` — NEVER_RUN: no run on record
- `schema-drift-audit.yml` — NEVER_RUN: no run on record
- `schema-drift-watchdog.yml` — NEVER_RUN: no run on record
- `scrape-events.yml` — NEVER_RUN: no run on record
- `sec-edgar-fetch.yml` — NEVER_RUN: no run on record
- `secret-rotation-reminder.yml` — NEVER_RUN: no run on record
- `secret-scan.yml` — NEVER_RUN: no run on record
- `self_optimizing_trading.yml` — NEVER_RUN: no run on record
- `send-accountability-reminders.yml` — NEVER_RUN: no run on record
- `sidecar-status-update.yml` — NEVER_RUN: no run on record
- `sign-coherence-gate.yml` — NEVER_RUN: no run on record
- `signal-engine.yml` — NEVER_RUN: no run on record
- `signal-integrator.yml` — NEVER_RUN: no run on record
- `signal-quality-monitor.yml` — NEVER_RUN: no run on record
- `signal-recorder.yml` — NEVER_RUN: no run on record
- `signal_tracking.yml` — NEVER_RUN: no run on record
- `simulation-picks-resolver.yml` — NEVER_RUN: no run on record
- `skyrocket-detector.yml` — NEVER_RUN: no run on record
- `sleeve-daily.yml` — NEVER_RUN: no run on record
- `smart-money-tracker.yml` — NEVER_RUN: no run on record
- `smart-picks-tracker.yml` — NEVER_RUN: no run on record
- `social-prediction-tracker.yml` — NEVER_RUN: no run on record
- `social_investigation.yml` — NEVER_RUN: no run on record
- `specialized-scanners.yml` — NEVER_RUN: no run on record
- `spike-scanner.yml` — NEVER_RUN: no run on record
- `sports-betting-refresh.yml` — DISABLED: no run on record
- `sports-data-snapshots.yml` — DISABLED: no run on record
- `sports-forensics-weekly.yml` — DISABLED: no run on record
- `sports-prediction-market-sync.yml` — DISABLED: no run on record
- `sports-smoke-and-e2e.yml` — DISABLED: no run on record
- `spy-data-refresh.yml` — NEVER_RUN: no run on record
- `stale-branch-cleanup.yml` — NEVER_RUN: no run on record
- `statistical_validation.yml` — NEVER_RUN: no run on record
- `stock-picks-writer.yml` — NEVER_RUN: no run on record
- `stocks-daily-stocksunify.yml` — NEVER_RUN: no run on record
- `stocks-daily.yml` — NEVER_RUN: no run on record
- `stocksunify2-pull.yml` — NEVER_RUN: no run on record
- `strategy-forward-tester.yml` — NEVER_RUN: no run on record
- `strategy-funnel-hourly.yml` — NEVER_RUN: no run on record
- `strategy-health-monitor.yml` — NEVER_RUN: no run on record
- `strategy-health-report.yml` — NEVER_RUN: no run on record
- `strategy-perf-by-class-rebuild.yml` — NEVER_RUN: no run on record
- `strategy-performance-no-regression.yml` — SCHEDULE_ONLY: no run on record
- `strategy-tribunal.yml` — NEVER_RUN: no run on record
- `sustained-gainer-scan.yml` — NEVER_RUN: no run on record
- `swarm-janitor.yml` — NEVER_RUN: no run on record
- `swarm-pick-review.yml` — NEVER_RUN: no run on record
- `swarm-sync-v2.yml` — NEVER_RUN: no run on record
- `swing_screener_daily.yml` — NEVER_RUN: no run on record
- `system-health-check.yml` — NEVER_RUN: no run on record
- `taste-profile-scan.yml` — NEVER_RUN: no run on record
- `test-fast.yml` — NEVER_RUN: no run on record
- `test-portfolios.yml` — NEVER_RUN: no run on record
- `top-gainers-scan.yml` — NEVER_RUN: no run on record
- `torontoevent-algorithm-refresh.yml` — NEVER_RUN: no run on record
- `torontoevent-backtest-and-deploy.yml` — NEVER_RUN: no run on record
- `torontoevent-deploy-competition.yml` — NEVER_RUN: no run on record
- `torontoevent-deploy-live-monitor.yml` — NEVER_RUN: no run on record
- `torontoevent-deploy-riseoftheclaw.yml` — NEVER_RUN: no run on record
- `torontoevent-goldmine-tracker.yml` — NEVER_RUN: no run on record
- `torontoevent-rapid-validation.yml` — NEVER_RUN: no run on record
- `torontoevent-spike-scanner.yml` — NEVER_RUN: no run on record
- `track-quick-picks.yml` — NEVER_RUN: no run on record
- `traditional-test-portfolios.yml` — NEVER_RUN: no run on record
- `tribunal-runtime-gate.yml` — NEVER_RUN: no run on record
- `tv-paper-tpsl-watchdog.yml` — NEVER_RUN: no run on record
- `tv-strategy-scanner.yml` — NEVER_RUN: no run on record
- `ueps-pick-runner.yml` — NEVER_RUN: no run on record
- `ueps_smoke_tests.yml` — NEVER_RUN: no run on record
- `universe-expander.yml` — NEVER_RUN: no run on record
- `update-creator-news.yml` — NEVER_RUN: no run on record
- `update-graph` — SCHEDULE_ONLY: no run on record
- `validate-hf-asset-class.yml` — NEVER_RUN: no run on record
- `validation-gates.yml` — NEVER_RUN: no run on record
- `value_resolver_quarterly.yml` — NEVER_RUN: no run on record
- `value_screener_weekly.yml` — NEVER_RUN: no run on record
- `verification-tests.yml` — NEVER_RUN: no run on record
- `verified-pilot-daily.yml` — NEVER_RUN: no run on record
- `volatile-alt-scanner.yml` — NEVER_RUN: no run on record
- `walk-forward-backtest.yml` — NEVER_RUN: no run on record
- `walkforward-gate.yml` — NEVER_RUN: no run on record
- `weekly-filter.yml` — NEVER_RUN: no run on record
- `weekly-scorecard.yml` — NEVER_RUN: no run on record
- `weekly-stock-simulation.yml` — NEVER_RUN: no run on record
- `weekly-strategy-scorecard.yml` — NEVER_RUN: no run on record
- `weekly_score_quartile_spread.yml` — NEVER_RUN: no run on record
- `what-worked-insights.yml` — NEVER_RUN: no run on record
- `winner-pattern-scanner.yml` — NEVER_RUN: no run on record
- `won-pnl-contradiction-backfill.yml` — NEVER_RUN: no run on record
- `worldclass-intelligence.yml` — NEVER_RUN: no run on record
- `worldclass-pipeline.yml` — NEVER_RUN: no run on record
- `wsl-runner-manager.yml` — NEVER_RUN: no run on record
