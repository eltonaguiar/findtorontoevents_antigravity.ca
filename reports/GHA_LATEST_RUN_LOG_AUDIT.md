# Latest-run log audit

Every workflow's most recent run, log downloaded and scanned for errors, warnings and suspicious output. A green run is not a clean run.

- workflows examined: **386**
- logs audited: **304**
- no run on record: **82**

| Verdict | Count |
|---|---|
| ERRORS | 72 |
| WARNINGS | 76 |
| SUSPICIOUS | 24 |
| CLEAN | 132 |

## Workflows whose log contains errors

### `picks-now-refresh.yml` — 1427 error line(s), conclusion `success`
- 1216× ERROR line
    - `refresh	Refresh OHLC coverage for tracker symbols	2026-11-26T03:45:52.1717832Z 2026***11***26 03:45:52 [ERROR] HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: ADA"}}}`
    - `refresh	Refresh OHLC coverage for tracker symbols	2026-11-26T03:45:52.7135979Z 2026***11***26 03:45:52 [ERROR] $ADA: No data found, symbol may be delisted`
- 211× http 4xx
    - `refresh	Generate picks	2026-11-26T03:41:37.6817232Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"No fundamentals data found for symbol: SPY"}}}`
    - `refresh	Generate picks	2026-11-26T03:41:38.8755062Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"No fundamentals data found for symbol: IVV"}}}`

### `battleground-mass-backtest.yml` — 312 error line(s), conclusion `success`
- 312× ERROR line
    - `mass-backtest	Run mass backtest	2026-11-26T03:29:15.5668507Z [2/869] claude_code_01/backtest_defensive_suite ... ERROR: No Strategy class found [0.1s]`
    - `mass-backtest	Run mass backtest	2026-11-26T03:29:15.5687888Z [3/869] claude_code_01/backtest_high_sharpe ... ERROR: No Strategy class found [0.0s]`

### `mysql-stale-picks-resolver.yml` — 259 error line(s), conclusion `success`
- 259× ERROR line
    - `resolve-stale-picks	Run stale picks resolver	2026-11-26T04:31:32.5025376Z 2026-11-26T04:31:32Z [ERROR] $USD-JPY: possibly delisted; no timezone found`
    - `resolve-stale-picks	Run stale picks resolver	2026-11-26T04:31:32.5030023Z 2026-11-26T04:31:32Z [ERROR]`

### `forward-tracking-v2.yml` — 70 error line(s), conclusion `success`
- 70× ERROR line
    - `track-signals	Import latest signals	2026-11-26T04:32:16.7707598Z 2026-11-26 04:32:16,770 - yfinance - ERROR - $TLT-USD: No data found, symbol may be delisted`
    - `track-signals	Import latest signals	2026-11-26T04:32:17.4863274Z 2026-11-26 04:32:17,485 - yfinance - ERROR - HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NG=F-USD"}}}`

### `audit-dashboard.yml` — 40 error line(s), conclusion `failure`
- 28× ERROR line
    - `generate-and-deploy	Generate dashboard payload and build HTML	2026-11-26T04:04:25.2495864Z [36;1m# produces. Running it before (pre-2026-06-06) caused ERROR:[0m`
    - `generate-and-deploy	Generate dashboard payload and build HTML	2026-11-26T04:09:54.6871387Z 2026-11-26T04:09:54 [ERROR] HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: KXCPI-26NOV"}}}`
- 5× http 4xx
    - `generate-and-deploy	Resolve active picks (TP/SL/time exits) across all systems	2026-11-26T03:39:55.5502323Z 2026-11-26T03:39:55 [WARNING] Binance api.binance.com failed: HTTP Error 451:`
    - `generate-and-deploy	Resolve active picks (TP/SL/time exits) across all systems	2026-11-26T03:39:56.0244179Z 2026-11-26T03:39:56 [WARNING] Binance api1.binance.com failed: HTTP Error 451:`
- 4× ##[error] annotation
    - `generate-and-deploy	Run Hyro enhanced scoring (technical indicators on picks)	2026-11-26T04:03:58.0349223Z ##[error]hyro_enhanced_scoring: missing dependency (C extension: None not built. If you want to import pandas from the source directory, you may need to run 'python -m pip install -ve . --no-bu`
    - `generate-and-deploy	Run Hyro enhanced scoring (technical indicators on picks)	2026-11-26T04:03:58.0470754Z ##[error]Process completed with exit code 2.`
- 2× python traceback
    - `generate-and-deploy	Run Hyro QuanBridge (refresh regime + ensemble + risk gate)	2026-11-26T04:03:39.7564611Z Traceback (most recent call last):`
    - `generate-and-deploy	Run Hyro ML pick optimizer (adaptive edge scoring + drift detection)	2026-11-26T04:03:57.8313553Z Traceback (most recent call last):`
- 1× git fatal
    - `generate-and-deploy	Deploy to all 3 FTP sites in parallel	2026-11-26T04:16:26.2877516Z [36;1m# Non-fatal: don't exit(1) even if some fail[0m`

### `backfill-features.yml` — 38 error line(s), conclusion `success`
- 38× http 4xx
    - `backfill	Run backfill	2026-11-26T03:10:40.3083555Z   [WARN] All Binance mirrors failed for RENDERUSDT: HTTP Error 451:`
    - `backfill	Run backfill	2026-11-26T03:10:40.3084747Z   [WARN] All Binance mirrors failed for RENDERUSDT: HTTP Error 451:`

### `deploy-riseoftheclaw.yml` — 26 error line(s), conclusion `success`
- 24× ERROR line
    - `deploy	Push KIMI picks to Audit Trail	2026-11-26T04:28:02.5689386Z 2026-11-26 04:28:02,568 [ERROR] MySQL write failed after 3 attempts: (1045, "Access denied for user 'ejaguiar1_stocks'@'3.42.157.120' (using password: YES)")`
    - `deploy	Push KIMI picks to Audit Trail	2026-11-26T04:28:04.4945567Z 2026-11-26 04:28:04,494 [ERROR] MySQL write failed after 3 attempts: (1045, "Access denied for user 'ejaguiar1_stocks'@'3.42.157.120' (using password: YES)")`
- 2× http 4xx
    - `deploy	Run Live Trading Pipeline	2026-11-26T04:26:40.8655931Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NKLA"}}}`
    - `deploy	Run Live Trading Pipeline	2026-11-26T04:26:54.9440744Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"No fundamentals data found for symbol: SQ"}}}`

### `cross-aggregator.yml` — 20 error line(s), conclusion `success`
- 19× missing file
    - `aggregate	Run cross-system aggregator	2026-11-26T03:45:57.7402887Z   [WARN] Could not load /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/mercury2/data/active_picks.json: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca/fin`
    - `aggregate	Run cross-system aggregator	2026-11-26T03:45:57.7407431Z   [WARN] Could not load /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/battleground/data/active_picks.json: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca`
- 1× ERROR line
    - `aggregate	Commit and push if changed	2026-11-26T03:47:08.3262747Z [36;1m    echo "ERROR: all push attempts failed"[0m`

### `gha-queue-audit.yml` — 18 error line(s), conclusion `success`
- 15× git fatal
    - `Queue + duration audit	Commit audit report	2026-11-26T04:22:30.0019899Z fatal: unable to access 'https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/': The requested URL returned error: 403`
    - `Queue + duration audit	Commit audit report	2026-11-26T04:22:33.7486513Z fatal: unable to access 'https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/': The requested URL returned error: 403`
- 3× ERROR line
    - `Queue + duration audit	Commit audit report	2026-11-26T04:24:15.7563450Z ERROR: All 5 push attempts failed`
    - `Queue + duration audit	Commit audit report	2026-11-26T04:26:07.9292800Z ERROR: All 5 push attempts failed`

### `ml-battleground-f.yml` — 14 error line(s), conclusion `success`
- 14× ERROR line
    - `sync	Push Battleground F picks to Audit Trail	2026-11-26T04:35:12.0947224Z 2026-11-26 04:35:12,094 [ERROR] MySQL write failed after 3 attempts: (1045, "Access denied for user 'ejaguiar1_stocks'@'52.190.182.226' (using password: YES)")`
    - `sync	Push Battleground F picks to Audit Trail	2026-11-26T04:35:14.3216283Z 2026-11-26 04:35:14,321 [ERROR] MySQL write failed after 3 attempts: (1045, "Access denied for user 'ejaguiar1_stocks'@'52.190.182.226' (using password: YES)")`

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

### `portfolio-tracker.yml` — 8 error line(s), conclusion `success`
- 8× http 4xx
    - `track	Sync, mark, report	2026-11-26T04:18:33.9586522Z   mark SOLUSDT: skipped (HTTPError: HTTP Error 451: )`
    - `track	Sync, mark, report	2026-11-26T04:18:33.9587152Z   mark LINKUSDT: skipped (HTTPError: HTTP Error 451: )`

### `audit-impact-tracker.yml` — 6 error line(s), conclusion `failure`
- 5× missing file
    - `audit-impact	Run audit impact tracker	2026-11-26T03:27:43.5299245Z   [WARN] Could not load strategy_performance.json: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/data/strategy_performance.json'`
    - `audit-impact	Run audit impact tracker	2026-11-26T03:27:43.5301106Z   [WARN] Could not load active_picks.json: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/battleground/data/active_picks.json'`
- 1× ##[error] annotation
    - `audit-impact	Commit results	2026-11-26T03:32:57.1725742Z ##[error]The action 'Commit results' has timed out after 5 minutes.`

### `weekly-strategy-scorecard.yml` — 6 error line(s), conclusion `success`
- 5× git fatal
    - `scorecard	Commit scorecard	2026-11-26T03:43:26.3928206Z fatal: unable to access 'https://github.com/eltonaguiar/findtorontoevents_antigravity.ca.git/': The requested URL returned error: 403`
    - `scorecard	Commit scorecard	2026-11-26T03:43:32.5119305Z fatal: unable to access 'https://github.com/eltonaguiar/findtorontoevents_antigravity.ca.git/': The requested URL returned error: 403`
- 1× ERROR line
    - `scorecard	Commit scorecard	2026-11-26T03:45:13.4383922Z ERROR: All 5 push attempts failed`

### `worldclass-intelligence.yml` — 5 error line(s), conclusion `success`
- 3× ERROR line
    - `worldclass-intelligence	Options Flow / Gamma Exposure	2026-11-26T03:46:19.6557549Z 2026-11-26 03:46:19 [utils] ERROR: POST ingest_regime: Error — Missing market data`
    - `worldclass-intelligence	Portfolio Optimizer (Black-Litterman + Risk Parity)	2026-11-26T03:46:24.7570817Z 2026-11-26 03:46:24 [portfolio_optimizer] ERROR: Cannot fetch historical returns`
- 1× python traceback
    - `worldclass-intelligence	On-Chain Crypto Analytics	2026-11-26T03:46:19.9813127Z Traceback (most recent call last):`
- 1× missing python module
    - `worldclass-intelligence	On-Chain Crypto Analytics	2026-11-26T03:46:19.9825042Z ModuleNotFoundError: No module named 'mysql'`

### `baby-strat-forward-paper.yml` — 4 error line(s), conclusion ``
- 1× python traceback
    - `forward-monitor	Run incubator strategies (Chronos-Bolt, FundingRate, OI-Divergence, SMC-FVG)	2026-11-26T03:46:36.8029498Z Traceback (most recent call last):`
- 1× missing python module
    - `forward-monitor	Run incubator strategies (Chronos-Bolt, FundingRate, OI-Divergence, SMC-FVG)	2026-11-26T03:46:36.8040985Z ModuleNotFoundError: No module named 'api_helpers'`
- 1× ##[error] annotation
    - `forward-monitor	Run incubator strategies (Chronos-Bolt, FundingRate, OI-Divergence, SMC-FVG)	2026-11-26T03:46:36.8221260Z ##[error]Process completed with exit code 1.`
- 1× git fatal
    - `forward-monitor	Auto-commit changed forward artifacts	2026-11-26T03:46:39.6106385Z fatal: pathspec 'battleground/data/incubator_signals.json' did not match any files`

### `rsi5070-forward-snapshot.yml` — 4 error line(s), conclusion `success`
- 2× missing binary
    - `snapshot	Run rsi5070 forward tracker (writes status JSON)	2026-11-26T03:42:30.0843201Z /home/runner/work/_temp/63a6ec69-0299-41c3-97a8-5923d51f26a7.sh: line 3: -: command not found`
    - `snapshot	Run rsi5070 forward tracker (writes status JSON)	2026-11-26T03:42:30.0846614Z /home/runner/work/_temp/63a6ec69-0299-41c3-97a8-5923d51f26a7.sh: line 3: None: command not found`
- 2× ERROR line
    - `snapshot	Commit updated JSONs to main	2026-11-26T03:43:00.5569603Z [36;1m    echo "ERROR: Push permanently rejected — aborting"[0m`
    - `snapshot	Commit updated JSONs to main	2026-11-26T03:43:00.5578866Z [36;1m  echo "ERROR: All push attempts failed"[0m`

### `signal-engine.yml` — 4 error line(s), conclusion `success`
- 4× ERROR line
    - `signal-engine	Push Signal Engine picks to Audit Trail	2026-11-26T04:20:47.3570194Z 2026-11-26 04:20:47,356 [ERROR] MySQL write failed after 3 attempts: (1045, "Access denied for user 'ejaguiar1_stocks'@'172.182.225.88' (using password: YES)")`
    - `signal-engine	Push Signal Engine picks to Audit Trail	2026-11-26T04:20:49.6502307Z 2026-11-26 04:20:49,649 [ERROR] MySQL write failed after 3 attempts: (1045, "Access denied for user 'ejaguiar1_stocks'@'172.182.225.88' (using password: YES)")`

### `swarm-sync-v2.yml` — 4 error line(s), conclusion `success`
- 4× ERROR line
    - `sync	Sync state files	2026-11-26T04:16:34.6259092Z [36;1m      echo 'ERROR: rebase conflict — aborting sync to avoid corrupting state files'[0m`
    - `sync	Sync state files	2026-11-26T04:16:34.6261295Z [36;1m      echo 'ERROR: conflict markers in staged files — aborting push'[0m`

### `system-health-check.yml` — 4 error line(s), conclusion `success`
- 4× ERROR line
    - `health-check	Run comprehensive health check	2026-11-26T04:41:16.5234859Z [36;1m    check_db['status'] = 'ERROR'[0m`
    - `health-check	Run comprehensive health check	2026-11-26T04:41:16.5242648Z [36;1m    check_ml['status'] = 'ERROR'[0m`

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

### `quan-engine-live.yml` — 3 error line(s), conclusion `success`
- 1× http 4xx
    - `quan-engine	Run QuanEngine scanner	2026-11-26T04:21:48.3120522Z 2026-11-26 04:21:48,311 [QuanEngine.MarketAnalysis] INFO: Fetched KASUSDT from Gate.io fallback (Binance said: HTTP Error 400: Bad Request)`
- 1× ERROR line
    - `quan-engine	Push picks to audit trail	2026-11-26T04:21:52.4771412Z 2026-11-26 04:21:52,477 [ERROR] quan_engine.audit_push: audit_trail package not available: No module named 'audit_trail'`
- 1× git fatal
    - `quan-engine	Commit results	2026-11-26T04:22:03.3144832Z fatal: pathspec 'data/audit_trail.db' did not match any files`

### `realtime-challenge.yml` — 3 error line(s), conclusion `success`
- 3× http 4xx
    - `cycle	Mark open positions and open new slots	2026-11-26T04:21:04.0471858Z mark: SOLUSDT skipped (market data unavailable: https://api.binance.com/api/v3/klines?symbol=SOLUSDT&interval=5m&limit=3 (HTTP Error 451: ))`
    - `cycle	Mark open positions and open new slots	2026-11-26T04:21:04.0473753Z mark: LINKUSDT skipped (market data unavailable: https://api.binance.com/api/v3/klines?symbol=LINKUSDT&interval=5m&limit=3 (HTTP Error 451: ))`

### `sign-coherence-gate.yml` — 3 error line(s), conclusion `failure`
- 3× ##[error] annotation
    - `scan	Gate decision	2026-11-26T04:39:20.5094201Z ##[error]Sign-flip count regressed: 1 > 0 baseline. The resolver corruption is growing.`
    - `scan	Gate decision	2026-11-26T04:39:20.5096662Z ##[error]Review the JSON report committed today and identify the new source_system producing wrong-sign pnl_pct.`

### `weekly-filter.yml` — 3 error line(s), conclusion `success`
- 1× python traceback
    - `run-filter	Run weekly filter	2026-11-26T03:43:35.1412849Z Traceback (most recent call last):`
- 1× missing file
    - `run-filter	Run weekly filter	2026-11-26T03:43:35.1581315Z FileNotFoundError: [Errno 2] No such file or directory: 'audit_dashboard/data/dashboard_data.json'`
- 1× ##[error] annotation
    - `run-filter	Run weekly filter	2026-11-26T03:43:35.1674961Z ##[error]Process completed with exit code 1.`

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

### `mercury2-scan.yml` — 2 error line(s), conclusion `failure`
- 2× ##[error] annotation
    - `scan	Run Mercury 2 scanner	2026-11-26T04:26:47.3212727Z ##[error]ensemble_conservative.joblib not found — scanner did NOT run (scanner_ran=false). Mercury 2 Weekly Retrain must commit the model first.`
    - `scan	Run Mercury 2 scanner	2026-11-26T04:26:47.3427580Z ##[error]Process completed with exit code 1.`

### `ml-battleground-retrain.yml` — 2 error line(s), conclusion `success`
- 2× git fatal
    - `retrain	Commit updated models	2026-11-26T04:31:43.7148882Z fatal: pathspec 'ml_battleground/system_a_filter/models/' did not match any files`
    - `retrain	Commit updated models	2026-11-26T04:31:43.7256708Z fatal: pathspec 'ml_battleground/system_b_regime/models/' did not match any files`

### `momentum-scanner.yml` — 2 error line(s), conclusion `success`
- 2× http 4xx
    - `momentum-scan	Check Outcomes (24h TP/SL/Expiry tracker)	2026-11-26T04:44:47.9991559Z WARNING: Binance price fetch from https://api.binance.com failed: HTTP Error 451:`
    - `momentum-scan	Check Outcomes (24h TP/SL/Expiry tracker)	2026-11-26T04:44:47.9996702Z WARNING: Binance price fetch from https://api.binance.com failed: HTTP Error 451:`

### `monthly-calibrator-refit.yml` — 2 error line(s), conclusion `success`
- 1× python traceback
    - `refit-calibrators	Refit isotonic calibrators (M-060)	2026-11-26T03:39:50.4937812Z Traceback (most recent call last):`
- 1× missing file
    - `refit-calibrators	Refit isotonic calibrators (M-060)	2026-11-26T03:39:50.5049115Z FileNotFoundError: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json'`

### `poc-picks-checkpoint.yml` — 2 error line(s), conclusion `success`
- 1× python traceback
    - `checkpoint	Resolve POC picks + write verdict	2026-11-26T03:40:06.9929476Z Traceback (most recent call last):`
- 1× missing python module
    - `checkpoint	Resolve POC picks + write verdict	2026-11-26T03:40:06.9947753Z ModuleNotFoundError: No module named 'tools'`

### `torontoevent-deploy-riseoftheclaw.yml` — 2 error line(s), conclusion ``
- 2× http 4xx
    - `deploy	Run Live Trading Pipeline	2026-11-26T04:27:00.6073922Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NKLA"}}}`
    - `deploy	Run Live Trading Pipeline	2026-11-26T04:27:16.0984326Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"No fundamentals data found for symbol: SQ"}}}`

### `verified-pilot-daily.yml` — 2 error line(s), conclusion `success`
- 2× git fatal
    - `pilot	Commit refreshed pilot proof to main	2026-11-26T03:44:33.4255743Z fatal: pathspec 'verified_strategies/paper_pilot/crypto_wf_hyro_state.json' did not match any files`
    - `pilot	Commit refreshed pilot proof to main	2026-11-26T03:44:33.5181569Z fatal: pathspec 'reports/pilot_forward_summary.json' did not match any files`

### `2hour_challenge.yml` — 1 error line(s), conclusion `cancelled`
- 1× ##[error] annotation
    - `execute-challenge	Run 2-hour trading challenge	2026-11-26T03:52:11.1554771Z ##[error]The operation was canceled.`

### `ab_analysis.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `ab-analysis	Verify all Tier-2 winners DB vs dashboard PF/WR/n	2026-11-26T03:08:09.6641308Z ERROR: /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json missing`

### `alpha-engine-etf.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `emit-etf-picks	Commit ETF picks	2026-11-26T03:08:40.1598802Z [36;1m  echo "ERROR: All 10 push attempts failed — data generated, next cycle will self-heal."[0m`

### `alpha-equity-breakout.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `equity-breakout-scan	Commit new picks	2026-11-26T03:08:31.9414088Z [36;1m  echo "ERROR: All 10 push attempts failed — picks generated, next cycle self-heals."[0m`

### `alpha-weekly-validation.yml` — 1 error line(s), conclusion `cancelled`
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

### `dashboard-pick-trader.yml` — 1 error line(s), conclusion `success`
- 1× missing file
    - `trade-dashboard-picks	Run Dashboard Pick Trader	2026-11-26T04:42:03.6710665Z   [WARN] Could not load /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/../audit_trail/data/dashboard_payload.json: [Errno 2] No such file or directory: '/home/runner/work/fi`

### `db-freshness-guardian.yml` — 1 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `DB Freshness Check	Run DB freshness check	2026-11-26T03:37:20.3346425Z ##[error]Process completed with exit code 2.`

### `deploy-fc-api-env-godaddy.yml` — 1 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `deploy-env	Install lftp	2026-11-26T03:41:22.4946179Z ##[error]Process completed with exit code 1.`

### `feature-signals-hourly.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `emit	Emit feature signals	2026-11-26T03:37:57.7944841Z   [ERROR] All premiumIndex endpoints failed`

### `forward-observations-ingest.yml` — 1 error line(s), conclusion `failure`
- 1× ##[error] annotation
    - `ingest	Forward-growth watchdog (B3)	2026-11-26T04:28:10.7706297Z ##[error]Process completed with exit code 1.`

### `fx-cost-overlap.yml` — 1 error line(s), conclusion `failure`
- 1× ##[error] annotation
    - `measure	Commit artifact	2026-11-26T04:26:22.4368008Z ##[error]Process completed with exit code 1.`

### `gha-quality-framework.yml` — 1 error line(s), conclusion `failure`
- 1× ##[error] annotation
    - `quality	Commit report (only when content changed)	2026-11-26T04:26:32.6735798Z ##[error]Process completed with exit code 1.`

### `h004-backtest.yml` — 1 error line(s), conclusion `success`
- 1× http 4xx
    - `h004-backtest	Run H***004 backtest	2026-11-26T03:38:25.1973583Z HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: UHN"}}}`

### `macd-rsi-m048-shadow-daily.yml` — 1 error line(s), conclusion `success`
- 1× git fatal
    - `shadow-emit	Commit shadow log + state	2026-11-26T03:40:00.4780851Z fatal: pathspec 'verified_strategies/paper_pilot/macd_rsi_m048_shadow_picks.jsonl' did not match any files`

### `mirror-site.yml` — 1 error line(s), conclusion `cancelled`
- 1× ##[error] annotation
    - `mirror	Download from findtorontoevents.ca (50webs FTP)	2026-11-26T03:47:42.4139121Z ##[error]The operation was canceled.`

### `multi-asset-scanner.yml` — 1 error line(s), conclusion ``
- 1× ERROR line
    - `multi-asset-scan	Step 1a: Run multi-asset copytrader scraper (forex/futures/stocks/commodities)	2026-11-26T04:21:29.0258095Z     [ERROR] futures_rsi2: cannot access local variable 'fut_info' where it is not associated with a value`

### `peer-claim-verification.yml` — 1 error line(s), conclusion `success`
- 1× git fatal
    - `verify	Run verification	2026-11-26T03:41:12.2625704Z     SKIP supports author_set (ref origin/main): git log origin/zoo/p0-recovery-2026-11-20..zoo/p0-recovery-2026-11-20 failed: fatal: ambiguous argument 'origin/zoo/p0-recovery-2026-11-20..zoo/p0-recovery-2026-11-20': unknown revision or path not i`

### `pre-spike-scan.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `scan	Run pre-spike detector	2026-11-26T03:40:17.0294710Z 03:40:17 [ERROR] HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: MULN"}}}`

### `prediction-quality-tracker.yml` — 1 error line(s), conclusion `success`
- 1× missing file
    - `track-quality	Run Prediction Quality Tracker	2026-11-26T04:39:30.9910723Z 2026-11-26 04:39:30 [PredictionQuality] WARNING Could not load /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/data/strong_signals.json: [Errno 2] No such file or directory: '/h`

### `self_optimizing_trading.yml` — 1 error line(s), conclusion `success`
- 1× git fatal
    - `trade	Commit results	2026-11-26T04:22:43.1105424Z fatal: pathspec 'performance_history.json' did not match any files`

### `smart-picks-tracker.yml` — 1 error line(s), conclusion `success`
- 1× import error
    - `track	Run smart picks engine + tracker	2026-11-26T04:26:49.9557574Z [36;1m# added in recent refactor; `|| true` masked the ImportError for 30+ days,[0m`

### `strategy-funnel-hourly.yml` — 1 error line(s), conclusion `success`
- 1× ERROR line
    - `refresh	Rebuild strategy funnel data from DB	2026-11-26T04:34:40.5401441Z [36;1m    print("ERROR: DB_PASS_STOCKS not set", file=sys.stderr)[0m`

### `value_screener_weekly.yml` — 1 error line(s), conclusion `cancelled`
- 1× ##[error] annotation
    - `run-value-screener	Run value screener	2026-11-26T03:47:48.6084063Z ##[error]The operation was canceled.`

### `walk-forward-backtest.yml` — 1 error line(s), conclusion `cancelled`
- 1× ##[error] annotation
    - `walk-forward	Run walk***forward backtest	2026-11-26T03:47:47.5739685Z ##[error]The operation was canceled.`

### `weekly-stock-simulation.yml` — 1 error line(s), conclusion `success`
- 1× ##[error] annotation
    - `run-exhaustive-simulation	Run exhaustive simulation batches	2026-11-26T03:42:49.4037734Z ##[error]Batch 0 failed after retry`

### `worldclass-pipeline.yml` — 1 error line(s), conclusion `cancelled`
- 1× ##[error] annotation
    - `intelligence	Install dependencies	2026-11-26T03:47:46.5966009Z ##[error]The operation was canceled.`

### `wsl-runner-manager.yml` — 1 error line(s), conclusion `failure`
- 1× ##[error] annotation
    - `check-status	Check Runner Status	2026-11-26T04:26:03.5438504Z ##[error]Process completed with exit code 1.`

## Warnings only

- `mysql-trading-sync.yml` — 757 warning(s): 757× WARNING line
- `prediction-market-agents.yml` — 34 warning(s): 33× WARNING line, 1× workflow warning
- `live_trading.yml` — 32 warning(s): 31× WARNING line, 1× ##[warning] annotation
- `schema-drift-watchdog.yml` — 17 warning(s): 1× workflow warning, 16× ##[warning] annotation
- `research-orchestrator.yml` — 13 warning(s): 4× workflow warning, 9× ##[warning] annotation
- `autonomous_trading.yml` — 12 warning(s): 12× WARNING line
- `outcome-resolver.yml` — 9 warning(s): 6× workflow warning, 1× WARNING line, 2× ##[warning] annotation
- `ci.yml` — 8 warning(s): 6× deprecation, 2× ##[warning] annotation
- `hourly-master-picks.yml` — 8 warning(s): 8× WARNING line
- `paper-pilot-daily.yml` — 8 warning(s): 4× workflow warning, 4× ##[warning] annotation
- `pick-funnel-nightly.yml` — 8 warning(s): 8× workflow warning
- `audit3-evidence.yml` — 6 warning(s): 2× deprecation, 3× WARNING line, 1× ##[warning] annotation
- `claudes-test-portfolios.yml` — 6 warning(s): 5× workflow warning, 1× WARNING line
- `money-ready-registry-gate.yml` — 6 warning(s): 6× WARNING line
- `provenance-verify.yml` — 6 warning(s): 4× deprecation, 1× workflow warning, 1× ##[warning] annotation
- `signal_tracking.yml` — 6 warning(s): 6× WARNING line
- `asset-class-freshness-watchdog.yml` — 5 warning(s): 5× workflow warning
- `hierarchical-bayes.yml` — 5 warning(s): 1× workflow warning, 4× ##[warning] annotation
- `hub-sync.yml` — 5 warning(s): 3× workflow warning, 2× ##[warning] annotation
- `weekly-scorecard.yml` — 5 warning(s): 4× deprecation, 1× ##[warning] annotation
- `ai-tournament-price-tracker.yml` — 4 warning(s): 1× workflow warning, 3× WARNING line
- `breakout-arena.yml` — 4 warning(s): 4× deprecated
- `crypto-intraday-sim.yml` — 4 warning(s): 2× deprecation, 2× ##[warning] annotation
- `futures-agent.yml` — 4 warning(s): 3× workflow warning, 1× ##[warning] annotation
- `gha-failure-digest.yml` — 4 warning(s): 2× deprecation, 1× workflow warning, 1× ##[warning] annotation
- `pod-emission-audit.yml` — 4 warning(s): 2× deprecation, 2× ##[warning] annotation
- `portfolio-trackers.yml` — 4 warning(s): 4× workflow warning
- `quant-auditor-deep-nightly.yml` — 4 warning(s): 4× workflow warning
- `algorithm-competition-refresh.yml` — 3 warning(s): 2× ##[warning] annotation, 1× workflow warning
- `audit3-health.yml` — 3 warning(s): 2× deprecation, 1× ##[warning] annotation
- `bestiejob-page-qa.yml` — 3 warning(s): 2× deprecation, 1× ##[warning] annotation
- `hc-parity.yml` — 3 warning(s): 2× deprecation, 1× workflow warning
- `hyro-bridge-regen.yml` — 3 warning(s): 3× workflow warning
- `kalshi-snapshot.yml` — 3 warning(s): 2× deprecation, 1× ##[warning] annotation
- `pead-shadow-collector.yml` — 3 warning(s): 3× workflow warning
- `php52-gate.yml` — 3 warning(s): 2× deprecation, 1× ##[warning] annotation
- `picks-now-live-pnl.yml` — 3 warning(s): 1× WARNING line, 2× workflow warning
- `secret-scan.yml` — 3 warning(s): 2× workflow warning, 1× ##[warning] annotation
- `send-accountability-reminders.yml` — 3 warning(s): 3× workflow warning
- `sleeve-daily.yml` — 3 warning(s): 2× deprecation, 1× ##[warning] annotation
- `stock-picks-writer.yml` — 3 warning(s): 2× deprecation, 1× ##[warning] annotation
- `stocks-daily-stocksunify.yml` — 3 warning(s): 3× deprecation
- `swing_screener_daily.yml` — 3 warning(s): 1× workflow warning, 2× ##[warning] annotation
- `value_resolver_quarterly.yml` — 3 warning(s): 1× workflow warning, 2× ##[warning] annotation
- `bond-agent.yml` — 2 warning(s): 1× workflow warning, 1× ##[warning] annotation
- `daily-top-picks-filter.yml` — 2 warning(s): 2× workflow warning
- `torontoevent-deploy-competition.yml` — 2 warning(s): 2× workflow warning
- `weekly_score_quartile_spread.yml` — 2 warning(s): 1× workflow warning, 1× WARNING line
- `audit-hourly-update.yml` — 1 warning(s): 1× WARNING line
- `auto-shutdown-monitor.yml` — 1 warning(s): 1× workflow warning
- `automated-reporting.yml` — 1 warning(s): 1× ##[warning] annotation
- `blacklist-reconciler.yml` — 1 warning(s): 1× ##[warning] annotation
- `buy-now-analysis.yml` — 1 warning(s): 1× ##[warning] annotation
- `ci-tests.yml` — 1 warning(s): 1× WARNING line
- `dxy-state-update.yml` — 1 warning(s): 1× workflow warning
- `edge-stability-daily.yml` — 1 warning(s): 1× workflow warning
- `edge-stability-refresh.yml` — 1 warning(s): 1× workflow warning
- `feed-health.yml` — 1 warning(s): 1× workflow warning
- `forward-benchmark-ledger.yml` — 1 warning(s): 1× workflow warning
- `kimi-goldmine-collector.yml` — 1 warning(s): 1× ##[warning] annotation
- `live_trading_canada.yml` — 1 warning(s): 1× WARNING line
- `low-score-tracker.yml` — 1 warning(s): 1× workflow warning
- `meme-scanner.yml` — 1 warning(s): 1× deprecation
- `meta-strategy.yml` — 1 warning(s): 1× workflow warning
- `model-picks-emission.yml` — 1 warning(s): 1× WARNING line
- `operator-review-today.yml` — 1 warning(s): 1× workflow warning
- `qa-market-validation.yml` — 1 warning(s): 1× workflow warning
- `quick-guess-ml.yml` — 1 warning(s): 1× ##[warning] annotation
- `rapid-validation-CLAUDECODE_Feb152026.yml` — 1 warning(s): 1× WARNING line
- `robust-edge-miner.yml` — 1 warning(s): 1× ##[warning] annotation
- `schema-drift-audit.yml` — 1 warning(s): 1× WARNING line
- `sidecar-status-update.yml` — 1 warning(s): 1× workflow warning
- `signal-quality-monitor.yml` — 1 warning(s): 1× WARNING line
- `skyrocket-detector.yml` — 1 warning(s): 1× ##[warning] annotation
- `what-worked-insights.yml` — 1 warning(s): 1× workflow warning
- `won-pnl-contradiction-backfill.yml` — 1 warning(s): 1× ##[warning] annotation

## Suspicious output only

- `stale-branch-cleanup.yml` — 11: 11× skipped work
- `validate-hf-asset-class.yml` — 9: 9× skipped work
- `actions-failure-guardian.yml` — 7: 7× skipped work
- `ml-staleness-watchdog.yml` — 7: 7× skipped work
- `incidents-enhancements-nightly.yml` — 5: 5× skipped work
- `winner-pattern-scanner.yml` — 5: 5× skipped work
- `ai-leaderboard-freshness.yml` — 3: 3× skipped work
- `simulation-picks-resolver.yml` — 3: 3× skipped work
- `update-creator-news.yml` — 3: 3× skipped work
- `deploy-battleground-ftp.yml` — 2: 2× skipped work
- `deploy-findcryptopairs-ftp.yml` — 2: 2× skipped work
- `growth-stock-screener-daily.yml` — 2: 2× skipped work
- `live-monitor-refresh.yml` — 2: 2× skipped work
- `optimize-score-thresholds.yml` — 2: 2× skipped work
- `pine-generator.yml` — 2: 1× no data, 1× skipped work
- `secret-rotation-reminder.yml` — 2: 2× skipped work
- `alpha-verify-predictions.yml` — 1: 1× skipped work
- `crypto-ml-tracker.yml` — 1: 1× skipped work
- `discord-token-selftest.yml` — 1: 1× skipped work
- `hyro-daily.yml` — 1: 1× skipped work
- `mysql_dedup_fix.yml` — 1: 1× skipped work
- `polymarket-signals.yml` — 1: 1× skipped work
- `tribunal-runtime-gate.yml` — 1: 1× skipped work
- `ueps_smoke_tests.yml` — 1: 1× skipped work

## Not auditable

- `_dynamic-runner-template.yml` — SCHEDULE_ONLY: no run on record
- `ai-tournament-pipeline.yml` — DISABLED: log unavailable: failed to get run log: HTTP 410: Server Error (https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca
- `alpha-engine-fast.yml` — RED_REGRESSION: log unavailable: run 45756484527 is still in progress; logs will be available when it is complete
- `alpha-engine-live.yml` — RED_REGRESSION: log unavailable: run 45755533757 is still in progress; logs will be available when it is complete
- `anti-overfit-gate.yml` — RED_REGRESSION: log unavailable: run 45750243307 is still in progress; logs will be available when it is complete
- `battle_test.yml` — DISABLED: log unavailable: failed to get run log: HTTP 410: Server Error (https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca
- `branch-large-file-dup-guard.yml` — RED_REGRESSION: log unavailable: run 45746946365 is still in progress; logs will be available when it is complete
- `consensus-outcome-tracker.yml` — GREEN_RECENT: log unavailable: run 45756329217 is still in progress; logs will be available when it is complete
- `copilot` — SCHEDULE_ONLY: no run on record
- `copy-trader-forward-test.yml` — GREEN_RECENT: log unavailable: run 45756331719 is still in progress; logs will be available when it is complete
- `copy-trader-intelligence.yml` — GREEN_RECENT: log unavailable: run 45756567758 is still in progress; logs will be available when it is complete
- `darwin-evolution.yml` — GREEN_RECENT: log unavailable: run 45751484284 is still in progress; logs will be available when it is complete
- `data-pipeline-test.yml` — GREEN_RECENT: log unavailable: run 45749828538 is still in progress; logs will be available when it is complete
- `db-secret-scan.yml` — DISABLED: no run on record
- `db-sync-bidirectional.yml` — GREEN_RECENT: log unavailable: run 45749839689 is still in progress; logs will be available when it is complete
- `db-sync-to-mirror.yml` — RED_REGRESSION: log unavailable: run 45749842137 is still in progress; logs will be available when it is complete
- `deals-refresh.yml` — GREEN_RECENT: log unavailable: run 45749845189 is still in progress; logs will be available when it is complete
- `deploy-alpha-dashboard.yml` — GREEN_RECENT: log unavailable: run 45749851939 is still in progress; logs will be available when it is complete
- `deploy-competition-to-site.yml` — GREEN_RECENT: log unavailable: run 45757310217 is still in progress; logs will be available when it is complete
- `deploy-fc-api-hotfix.yml` — GREEN_RECENT: log unavailable: run 45749868103 is still in progress; logs will be available when it is complete
- `deploy-fc-frontend.yml` — GREEN_RECENT: log unavailable: run 45749871702 is still in progress; logs will be available when it is complete
- `deploy-friendtracker.yml` — GREEN_RECENT: log unavailable: run 45749879082 is still in progress; logs will be available when it is complete
- `deploy-fte-events-json.yml` — GREEN_RECENT: log unavailable: run 45752360074 is still in progress; logs will be available when it is complete
- `deploy-fte-index.yml` — GREEN_RECENT: log unavailable: run 45752360054 is still in progress; logs will be available when it is complete
- `deploy-movieshows-all.yml` — GREEN_RECENT: log unavailable: run 45749889283 is still in progress; logs will be available when it is complete
- `deploy-movieshows3-hotfix.yml` — GREEN_RECENT: log unavailable: run 45749892191 is still in progress; logs will be available when it is complete
- `deploy-vetted-picks.yml` — GREEN_RECENT: log unavailable: run 45749898230 is still in progress; logs will be available when it is complete
- `discord-bot.yml` — RED_REGRESSION: log unavailable: run 45749901931 is still in progress; logs will be available when it is complete
- `dna-mutation-cycle.yml` — GREEN_RECENT: log unavailable: run 45749917618 is still in progress; logs will be available when it is complete
- `dna_strategy_pipeline.yml` — RED_REGRESSION: log unavailable: run 45755721101 is still in progress; logs will be available when it is complete
- `dynamic-alpha-engine.yml` — GREEN_RECENT: log unavailable: run 45755551101 is still in progress; logs will be available when it is complete
- `dynamic-universe.yml` — GREEN_RECENT: log unavailable: run 45754454205 is still in progress; logs will be available when it is complete
- `ema-retracement-scan.yml` — GREEN_RECENT: log unavailable: run 45751167999 is still in progress; logs will be available when it is complete
- `enhanced-ml-crypto.yml` — GREEN_RECENT: log unavailable: run 45756694571 is still in progress; logs will be available when it is complete
- `equities-agent.yml` — GREEN_RECENT: log unavailable: run 45749947364 is still in progress; logs will be available when it is complete
- `etf-agent.yml` — GREEN_RECENT: log unavailable: run 45749950161 is still in progress; logs will be available when it is complete
- `fc-crypto-pro.yml` — GREEN_RECENT: log unavailable: run 45749959820 is still in progress; logs will be available when it is complete
- `feature-stability-check.yml` — GREEN_RECENT: log unavailable: run 45749966164 is still in progress; logs will be available when it is complete
- `fix-battleground.yml` — GREEN_RECENT: log unavailable: run 45749977830 is still in progress; logs will be available when it is complete
- `fix-ghost-cards.yml` — GREEN_RECENT: log unavailable: run 45749980507 is still in progress; logs will be available when it is complete
- `forex-agent.yml` — GREEN_RECENT: log unavailable: run 45749983509 is still in progress; logs will be available when it is complete
- `forex-smart-picks.yml` — GREEN_RECENT: log unavailable: run 45749986397 is still in progress; logs will be available when it is complete
- `forward-signal-scanner.yml` — GREEN_RECENT: log unavailable: run 45749995333 is still in progress; logs will be available when it is complete
- `forward-test-new-strategies.yml` — GREEN_RECENT: log unavailable: run 45749998137 is still in progress; logs will be available when it is complete
- `forward_test.yml` — GREEN_RECENT: log unavailable: run 45757071192 is still in progress; logs will be available when it is complete
- `funding-rate-collector.yml` — GREEN_RECENT: log unavailable: run 45750016905 is still in progress; logs will be available when it is complete
- `gainer-predictor.yml` — GREEN_RECENT: log unavailable: run 45756053082 is still in progress; logs will be available when it is complete
- `genome-daily-pipeline.yml` — GREEN_RECENT: log unavailable: run 45750031354 is still in progress; logs will be available when it is complete
- `genome-evolution.yml` — GREEN_RECENT: log unavailable: run 45750033965 is still in progress; logs will be available when it is complete
- `gha-scan-job.yml` — SCHEDULE_ONLY: no run on record
- `goldmine-tracker.yml` — GREEN_RECENT: log unavailable: run 45750057172 is still in progress; logs will be available when it is complete
- `h103-forward-logger.yml` — GREEN_RECENT: log unavailable: run 45750066952 is still in progress; logs will be available when it is complete
- `hindsight-learner.yml` — GREEN_RECENT: log unavailable: run 45754542909 is still in progress; logs will be available when it is complete
- `hoffman-tracker.yml` — GREEN_RECENT: log unavailable: run 45750079065 is still in progress; logs will be available when it is complete
- `honest-kill-switch.yml` — GREEN_RECENT: log unavailable: run 45750082060 is still in progress; logs will be available when it is complete
- `incubator-pipeline.yml` — GREEN_RECENT: log unavailable: run 45750100186 is still in progress; logs will be available when it is complete
- `incubator-strategies.yml` — GREEN_RECENT: log unavailable: run 45750103397 is still in progress; logs will be available when it is complete
- `insider-trades-refresh.yml` — GREEN_RECENT: log unavailable: run 45750109218 is still in progress; logs will be available when it is complete
- `kimi-feb172026-live.yml` — GREEN_RECENT: log unavailable: run 45753186887 is still in progress; logs will be available when it is complete
- `kimi-fetch-movies.yml` — GREEN_RECENT: log unavailable: run 45750118336 is still in progress; logs will be available when it is complete
- `live_spike_trading.yml` — GREEN_RECENT: log unavailable: run 45757010869 is still in progress; logs will be available when it is complete
- `luxalgo-signals.yml` — GREEN_RECENT: log unavailable: run 45756902657 is still in progress; logs will be available when it is complete
- `mega-mutation-tracker.yml` — NEVER_RUN: log unavailable: run 45756390280 is still in progress; logs will be available when it is complete
- `meme-scanner-v2.yml` — NEVER_RUN: log unavailable: run 45757106245 is still in progress; logs will be available when it is complete
- `mercury2-retrain.yml` — NEVER_RUN: log unavailable: run 45757144794 is still in progress; logs will be available when it is complete
- `mermaid-test-deploy.yml` — DISABLED: no run on record
- `mutation-lab.yml` — NEVER_RUN: log unavailable: run 45750241817 is still in progress; logs will be available when it is complete
- `now-scanner.yml` — NEVER_RUN: log unavailable: run 45756336524 is still in progress; logs will be available when it is complete
- `quant-auditor-fast-pr.yml` — SCHEDULE_ONLY: no run on record
- `real_2hour_challenge.yml` — NEVER_RUN: log unavailable: run 45750376573 is still in progress; logs will be available when it is complete
- `regime-terminal.yml` — NEVER_RUN: log unavailable: run 45756513315 is still in progress; logs will be available when it is complete
- `resolver-step5-6-backfill.yml` — NEVER_RUN: no run on record
- `resolver-step7-apply.yml` — NEVER_RUN: no run on record
- `signal-recorder.yml` — NEVER_RUN: log unavailable: run 45756311434 is still in progress; logs will be available when it is complete
- `sports-betting-refresh.yml` — DISABLED: no run on record
- `sports-data-snapshots.yml` — DISABLED: no run on record
- `sports-forensics-weekly.yml` — DISABLED: no run on record
- `sports-prediction-market-sync.yml` — DISABLED: no run on record
- `sports-smoke-and-e2e.yml` — DISABLED: no run on record
- `strategy-performance-no-regression.yml` — SCHEDULE_ONLY: no run on record
- `ueps-pick-runner.yml` — NEVER_RUN: log unavailable: run 45757180252 is still in progress; logs will be available when it is complete
- `update-graph` — SCHEDULE_ONLY: no run on record
