# GitHub Actions Curated Job Log Review

Generated: 2026-05-21 03:47 UTC
Repository: eltonaguiar/findtorontoevents_antigravity.ca
Branch: main
Workflows reviewed: 12
Jobs with signals: 8

## Top Job Findings

| Rank | Workflow | Job | Conclusion | Error lines | Warning lines | Run | Job |
|---:|---|---|---|---:|---:|---|---|
| 1 | OBI Hourly Snapshot | snapshot | success | 12 | 0 | [run 26204175940](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26204175940) | [job 77100380917](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26204175940/job/77100380917) |
| 2 | Meme Coin Scanner v2  Fixed & Monitored | meme-scan | success | 5 | 4 | [run 26203023948](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26203023948) | [job 77096810439](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26203023948/job/77096810439) |
| 3 | Audit Drift Telemetry | drift | success | 4 | 6 | [run 26204019951](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26204019951) | [job 77099919869](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26204019951/job/77099919869) |
| 4 | CI Tests | test (3.12) | - | 4 | 5 | [run 26204019963](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26204019963) | [job 77099920038](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26204019963/job/77099920038) |
| 5 | CI Tests | test (3.11) | success | 2 | 8 | [run 26202470071](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26202470071) | [job 77095115201](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26202470071/job/77095115201) |
| 6 | CI Tests | test (3.12) | success | 2 | 8 | [run 26202470071](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26202470071) | [job 77095115218](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26202470071/job/77095115218) |
| 7 | Deploy Competition to Live Site | deploy | success | 2 | 0 | [run 26202444816](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26202444816) | [job 77095041272](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26202444816/job/77095041272) |
| 8 | No stale DB passwords | Grep for stale hardcoded DB passwords | success | 0 | 1 | [run 26204019950](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26204019950) | [job 77099919980](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26204019950/job/77099919980) |

## Error And Warning Excerpts

### OBI Hourly Snapshot :: snapshot :: run 26204175940

Errors:
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8445957Z [OBI] Failed to fetch BTCUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8447462Z [OBI] Failed to fetch ETHUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=ETHUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8448605Z [OBI] Failed to fetch BNBUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=BNBUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8449797Z [OBI] Failed to fetch SOLUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=SOLUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8450916Z [OBI] Failed to fetch XRPUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=XRPUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8451992Z [OBI] Failed to fetch TRXUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=TRXUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8453070Z [OBI] Failed to fetch ADAUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=ADAUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8454201Z [OBI] Failed to fetch AVAXUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=AVAXUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8455297Z [OBI] Failed to fetch TAOUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=TAOUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8456618Z [OBI] Failed to fetch LINKUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=LINKUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8458090Z [OBI] Failed to fetch NEARUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=NEARUSDT&limit=20
- snapshot Fetch OBI snapshots 2026-05-21T03:47:18.8459211Z [OBI] Failed to fetch RENDERUSDT depth: 451 Client Error: for url: https://api.binance.com/api/v3/depth?symbol=RENDERUSDT&limit=20

### Meme Coin Scanner v2  Fixed & Monitored :: meme-scan :: run 26203023948

Errors:
- meme-scan Health Check 2026-05-21T03:09:38.3490753Z ❌ Data freshness issue: Database connection failed
- meme-scan Health Check 2026-05-21T03:09:38.3491469Z [2026-05-21 03:09 UTC] [CRITICAL] Scanner data freshness critical: Database connection failed
- meme-scan Print stats 2026-05-21T03:09:38.3722215Z print(f\"Error: {d.get('error','unknown')}\")
- meme-scan Print stats 2026-05-21T03:09:38.3722958Z print(f\"Parse error: {e}\")
- meme-scan Print stats 2026-05-21T03:09:38.5925670Z Error: Database connection failed
Warnings:
- meme-scan Health Check 2026-05-21T03:09:38.0187623Z /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/scripts/meme_scanner_monitor.py:167: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
- meme-scan Health Check 2026-05-21T03:09:38.0190589Z /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/scripts/meme_scanner_monitor.py:171: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
- meme-scan Health Check 2026-05-21T03:09:38.3069636Z /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/scripts/meme_scanner_monitor.py:124: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
- meme-scan Health Check 2026-05-21T03:09:38.3494310Z [2026-05-21 03:09 UTC] [WARNING] Low signal volume: only 0 signals in 7 days

### Audit Drift Telemetry :: drift :: run 26204019951

Errors:
- drift Validate backtest integrity 2026-05-21T03:42:50.7893020Z 2026-05-21T03:42:50Z WARN integrity check failed for 31/50 rows; looking for fallback snapshot
- drift Pending SPA governance check 2026-05-21T03:42:52.9746105Z ##[error]Process completed with exit code 1.
- drift Data source health check (C-008) 2026-05-21T03:42:53.4291600Z [data-source-health] binance_primary: FAIL HTTP Error 451:
- drift Data source health check (C-008) 2026-05-21T03:42:53.4436788Z ##[error]Process completed with exit code 1.
Warnings:
- drift Setup Node 2026-05-21T03:42:45.4383997Z [command]/usr/bin/tar xz --strip 1 --warning=no-unknown-keyword --overwrite -C /home/runner/work/_temp/732e52ce-886e-4cdf-b1b4-343fdf9ca058 -f /home/runner/work/_temp/69e8ea80-2962-424b-b8ba-aa9a164bb065
- drift Pending SPA governance check 2026-05-21T03:42:52.9667265Z ## Alerts (early warning — may need intervention before n=20)
- drift Data source health check (C-008) 2026-05-21T03:42:52.9795349Z print(f'WARNING: {len(failures)} data source(s) unreachable: {failures}')
- drift Data source health check (C-008) 2026-05-21T03:42:53.4293035Z WARNING: 1 data source(s) unreachable: ['binance_primary']
- drift Upload telemetry artifacts 2026-05-21T03:42:53.4483825Z if-no-files-found: warn
- drift Complete job 2026-05-21T03:42:54.5874271Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/setup-node@v4, actions/upload-artifact@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the FO...

### CI Tests :: test (3.12) :: run 26204019963

Errors:
- test (3.12) Run all tests 2026-05-21T03:45:16.2221944Z tests/test_emitter_whitelist.py::test_hardcoded_toxic_pairs FAILED [ 33%]
- test (3.12) Run all tests 2026-05-21T03:46:42.8074505Z tests/test_money_ready_verdict.py::TestMoneyReadyVerdict::test_money_ready_high_edge FAILED [ 57%]
- test (3.12) Run all tests 2026-05-21T03:46:42.9849664Z tests/test_money_ready_verdict.py::TestMoneyReadyVerdict::test_m070_diversified_symbols_allow_money_ready FAILED [ 57%]
- test (3.12) Run all tests 2026-05-21T03:47:42.0504076Z ##[error]The operation was canceled.
Warnings:
- test (3.12) Upload test results 2026-05-21T03:47:42.0569709Z if-no-files-found: warn
- test (3.12) Upload test results 2026-05-21T03:47:42.3140522Z ##[warning]No files were found with the provided path: test-results.xml. No artifacts will be uploaded.
- test (3.12) Upload coverage report 2026-05-21T03:47:42.3268750Z if-no-files-found: warn
- test (3.12) Upload coverage report 2026-05-21T03:47:42.5709011Z ##[warning]No files were found with the provided path: coverage.xml. No artifacts will be uploaded.
- test (3.12) Complete job 2026-05-21T03:47:43.2416703Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/cache@v4, actions/upload-artifact@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the F...

### CI Tests :: test (3.11) :: run 26202470071

Errors:
- test (3.11) Post Checkout 2026-05-21T02:58:00.2270035Z fatal: No url found for submodule path 'openclaude' in .gitmodules
- test (3.11) Post Checkout 2026-05-21T02:58:00.2309694Z ##[warning]The process '/usr/bin/git' failed with exit code 128
Warnings:
- test (3.11) Run all tests 2026-05-21T02:56:08.9674312Z /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/coverage/report_core.py:107: CoverageWarning: Couldn't parse Python file '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/backtest_quant_algorithms.py' (couldnt-parse); see https://coverage.readthedocs.io/en/7.14.0/messages.html#warning-couldnt-parse
- test (3.11) Run all tests 2026-05-21T02:56:11.5609664Z /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/coverage/report_core.py:107: CoverageWarning: Couldn't parse Python file '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/copytrader_integration.py' (couldnt-parse); see https://coverage.readthedocs.io/en/7.14.0/messages.html#warning-couldnt-parse
- test (3.11) Run all tests 2026-05-21T02:56:14.3815116Z /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/coverage/report_core.py:107: CoverageWarning: Couldn't parse Python file '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/equity_rsi_divergence_mr_old.py' (couldnt-parse); see https://coverage.readthedocs.io/en/7.14.0/messages.html#warning-couldnt-parse
- test (3.11) Run all tests 2026-05-21T02:56:17.8153178Z /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/coverage/report_core.py:107: CoverageWarning: Couldn't parse Python file '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/high_conviction_enhancements.py' (couldnt-parse); see https://coverage.readthedocs.io/en/7.14.0/messages.html#warning-couldnt-parse
- test (3.11) Run all tests 2026-05-21T02:57:50.3486830Z warnings.warn(
- test (3.11) Run all tests 2026-05-21T02:57:50.3490255Z warnings.warn(
- test (3.11) Run all tests 2026-05-21T02:57:50.3494723Z warnings.warn(
- test (3.11) Upload test results 2026-05-21T02:57:55.3972473Z if-no-files-found: warn

### CI Tests :: test (3.12) :: run 26202470071

Errors:
- test (3.12) Post Checkout 2026-05-21T03:00:56.5776507Z fatal: No url found for submodule path 'openclaude' in .gitmodules
- test (3.12) Post Checkout 2026-05-21T03:00:56.5821667Z ##[warning]The process '/usr/bin/git' failed with exit code 128
Warnings:
- test (3.12) Run all tests 2026-05-21T02:59:09.9732480Z /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/coverage/report_core.py:107: CoverageWarning: Couldn't parse Python file '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/backtest_quant_algorithms.py' (couldnt-parse); see https://coverage.readthedocs.io/en/7.14.0/messages.html#warning-couldnt-parse
- test (3.12) Run all tests 2026-05-21T02:59:12.2632272Z /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/coverage/report_core.py:107: CoverageWarning: Couldn't parse Python file '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/copytrader_integration.py' (couldnt-parse); see https://coverage.readthedocs.io/en/7.14.0/messages.html#warning-couldnt-parse
- test (3.12) Run all tests 2026-05-21T02:59:14.9669806Z /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/coverage/report_core.py:107: CoverageWarning: Couldn't parse Python file '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/equity_rsi_divergence_mr_old.py' (couldnt-parse); see https://coverage.readthedocs.io/en/7.14.0/messages.html#warning-couldnt-parse
- test (3.12) Run all tests 2026-05-21T02:59:18.6773787Z /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/coverage/report_core.py:107: CoverageWarning: Couldn't parse Python file '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/high_conviction_enhancements.py' (couldnt-parse); see https://coverage.readthedocs.io/en/7.14.0/messages.html#warning-couldnt-parse
- test (3.12) Run all tests 2026-05-21T03:00:47.5791675Z warnings.warn(
- test (3.12) Run all tests 2026-05-21T03:00:47.5796166Z warnings.warn(
- test (3.12) Run all tests 2026-05-21T03:00:47.5801127Z warnings.warn(
- test (3.12) Upload test results 2026-05-21T03:00:51.7473037Z if-no-files-found: warn

### Deploy Competition to Live Site :: deploy :: run 26202444816

Errors:
- deploy Post Checkout 2026-05-21T02:50:34.7441357Z fatal: No url found for submodule path 'openclaude' in .gitmodules
- deploy Post Checkout 2026-05-21T02:50:34.7491979Z ##[warning]The process '/usr/bin/git' failed with exit code 128

### No stale DB passwords :: Grep for stale hardcoded DB passwords :: run 26204019950

Warnings:
- Grep for stale hardcoded DB passwords Complete job 2026-05-21T03:43:06.6117564Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/checkout@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the ...
