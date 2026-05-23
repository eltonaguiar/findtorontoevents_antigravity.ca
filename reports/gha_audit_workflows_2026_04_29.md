# GitHub Actions Audit-Related Workflow Audit

**Date:** 2026-04-29
**Scope:** 295 workflow files in `.github/workflows/`, prioritizing those that feed `findtorontoevents.ca/audit`
**Mode:** Read-only. Workflow files and logs were not modified.
**Sample:** Last 1000 runs (gh API), plus targeted log fetches on top failure/cancellation patterns.

## Headline numbers

| Metric | Value |
| --- | --- |
| Workflow files in repo | 295 |
| Last 1000 runs: success | 957 (95.7%) |
| Last 1000 runs: failure | 1 (0.1%) |
| Last 1000 runs: cancelled | 14 (1.4%) |
| Last 1000 runs: skipped | 10 (1.0%) |
| Last 1000 runs: empty/null conclusion | 18 (1.8%) — in-progress + recent cancel-superseded |
| Last 500 *failure-only* lookback (older runs reachable via `--status failure`) | 500 reachable failures, 207 of them on `CI Tests` alone |
| Workflows missing `concurrency:` block | 180 / 295 (~61%) |
| Workflows touching `safe_push.sh` | 178 / 295 (~60%) |
| Workflows that explicitly `git push origin (main|HEAD)` directly (bypassing safe_push) | 6 (alpha-engine-bond, alpha-engine-etf, alpha-quant-stack, audit-dashboard, dynamic-alpha-engine, fix-battleground) |

> NB: the spread between "1 failure in last 1000 runs" and "207 CI Tests failures reachable via `--status failure`" is real — most CI Test failures sit further back than the 1000-run cron-firehose window because cron-driven runs dominate volume.

## Inventory — audit-relevant workflows (cron + last cron-success duration)

| Workflow | Cron | Last successful run | Avg duration | Concurrency? | Notes |
| --- | --- | --- | --- | --- | --- |
| `audit-dashboard.yml` (Unified Audit Dashboard) | `10 * * * *` | 2026-04-29 12:43Z | **~42 min** | yes (split push/cron) | budget exceeds 25-min target |
| `audit-drift-telemetry.yml` | `10 * * * *` | 2026-04-29 15:50Z | 2.6 min | n/a | healthy, but **collides with audit-dashboard at :10** |
| `audit-impact-tracker.yml` | `0 */6 * * *` | clean | <5 min | n/a | low volume |
| `actions-failure-guardian.yml` | `0 */4 * * *` | clean | ~3 min | yes | working as designed |
| `dynamic-alpha-engine.yml` (Dynamic Runner) | `18,48 * * * *` | runs ~2200s (37 min) | **~37 min** | yes (no cancel) | 49 failures in last-500-failure window |
| `enhanced-ml-crypto.yml` | `0 2 * * *` + `19 */2 * * *` | clean | varies | yes (no cancel) | recent cancels = supersession |
| `feed-health.yml` | (last failure 2026-04-17) | clean | <5 min | n/a | stable |
| `crypto-smart-picks.yml` | `47 */2 * * *` | clean | <10 min | n/a | stable |
| `crypto-test-portfolios.yml` | `15 */4 * * *` | clean | varies | n/a | reduced from `*/30`; per file comment was "doesn't feed audit, 9/12 runs failed" |
| `dynamic-universe.yml` | `37 */2 * * *` | clean | <10 min | n/a | stable |
| `hindsight-learner.yml` | `7 * * * *` | last failure 2026-04-28 14:59Z = **cancelled** at 16 min (timeout cap is 20 min; concurrency `cancel-in-progress: false`) | varies | yes | timeout vs cancel race |
| `incubator-strategies.yml` | `15 */2 * * *` | clean | n/a | n/a | last failure 2026-04-06 |
| `ml-feedback-retrain.yml` | n/a | 3+ wk dormant | — | — | last 3 failures 2026-03-27, then nothing |
| `mercury2-scan.yml` | (varies) | last failure 2026-04-28 14:22Z | varies | n/a | one-off cancel |
| `rl-agent-ppo.yml` | n/a | last fail 2026-03-27 | — | — | dormant |
| `live_spike_trading.yml` | n/a | recent | varies | n/a | not in top failures |
| `conviction-picks.yml` | `56 * * * *` | clean | <5 min | n/a | stable |
| `copytrader-tracker.yml` | `42 */2 * * *` | clean | <5 min | n/a | last fail 2026-03-27 |
| `universe-expander.yml` | (varies) | clean | <10 min | n/a | stable |
| `torontoevent-deploy-live-monitor.yml` | (varies) | clean | n/a | n/a | not in top-failure cohort |
| `ci-tests.yml` (CI Tests) | push to `main` only | currently red on `main` | 4 min until error | n/a | **207 failures reachable** |

## Failures (top 3)

### 1. CI Tests — 207 failures reachable (most volume by far)

**Latest:** run `25091434474` (2026-04-29 04:47Z), Python 3.11 + 3.12 matrix.

**Failure mode** (collection-time SyntaxError, every test errors at setup):
```
tests/test_quan_engine_concurrency_cap.py:41: in integrator
E       (hash(f'{symbol}{direction}{normalized.get('created_at', '')}') % 10**10)
E                                                   ^^^^^^^^^^
E   SyntaxError: f-string: f-string: unmatched '('
```
The single-quoted dict key `'created_at'` is nested inside an outer single-quoted f-string. Python ≤ 3.11 cannot lex this; under 3.12 it is permitted by PEP 701 but the file is being executed under 3.11 in the matrix where collection blows up before any test runs. Every dependent fixture aborts with the same SyntaxError, so pytest exits with code 1 and the whole CI Tests job is red on `main` HEAD.

**Fix recommendation:** Replace the inner literal with a double-quoted key OR a temp variable: `normalized.get("created_at", "")`. One-line change. Until merged, every push to main shows red CI, which trains everyone to ignore the indicator (alarm-fatigue).

### 2. Unified Audit Dashboard — 37 reachable failures

**Latest:** run `25081087246` (2026-04-28 22:32Z). Job ran 13 min 33 s and was cancelled. All steps after `Checkout` show `conclusion=null`. Five failures clustered on 2026-04-28 (15:03Z, 19:47Z, 20:40Z, 21:34Z, 22:32Z).

**Failure mode:** push-event runs being cancelled by `cancel-in-progress: ${{ github.event_name == 'push' }}` while the next push lands. The cron group (`dashboard-publish-cron`) does *not* cancel, but data-touching peer commits inside the [skip ci]-protected paths still queue push runs and supersede each other within the ~42-min execution window. The `[skip ci]` guard on line 95 catches data-file commits, but workflow/template edits trigger a push run that races with the still-running cron run on the same `generate-and-deploy` job semantics (different concurrency groups but same git push contention).

**Fix recommendation:** The 42-min average duration is the deeper problem. Profile the `Generate dashboard payload and build HTML` and `Resolve active picks` steps (currently capped at 20 min with `continue-on-error`) — these are likely the two slowest. Splitting the resolver into its own scheduled workflow that publishes a JSON artifact would shave ~20 min off the dashboard build. The 115-min timeout is far too generous and disguises drift; trim to 60 min so blow-ups surface as failures rather than silently expensive runs.

### 3. ALPHA ENGINE - Dynamic Runner — 49 reachable failures

**Latest:** run `25076721843` (2026-04-28 20:44Z). Job ran 37 minutes; production scanner completed in 2213.5s (37 min). Errors observed in log were marked `non-fatal` and continued, e.g.:
- `Binance Futures ping failed — BINANCE_FUTURES_DISABLED=True for this session`
- `All funding rate sources failed for BTCUSDT/ETHUSDT/SOLUSDT/BNBUSDT/XRPUSDT`
- `All Binance endpoints failed for /api/v3/klines?symbol=币安人生USDT…: 'ascii' codec can't encode characters in position 26-29`
- `[KPI] Monitoring skipped (non-fatal): 'str' object has no attribute 'get'`
- `[CALIBRATION] / [SPC] / [PATTERN] Diagnostics failed (non-fatal): '<' not supported between instances of 'NoneType' and 'NoneType'`
- `[RISK] Pre-generation check failed (non-fatal): 'total_closed'`

**Failure mode:** The job *finishes* the scanner but the run conclusion ends up `failure`, suggesting either the post-scanner push step or the audit sync (`MySQL credentials not found in env -- skipping MySQL sync`) is being treated as the failure point. Concurrency group is `dynamic-alpha-engine-push` with `cancel-in-progress: false`, so cancels are not the cause here.

**Fix recommendation:** Three layered concerns:
1. The non-ASCII symbol `币安人生USDT` is being passed unencoded to the Binance URL builder (`'ascii' codec can't encode`). Add `urllib.parse.quote(symbol, safe='')` or filter non-ASCII tickers at the universe layer.
2. The `(KPI / CALIBRATION / SPC / PATTERN / RISK)` blocks each say "non-fatal" but are silently degrading the run quality on every cycle — these should fire one-line Discord notifications rather than disappear into stdout.
3. Promote at least one of these branches to `continue-on-error: false` and `if: always()` artifact upload so the underlying `'NoneType' < NoneType'` regression actually pages someone.

## Slow / silent runs

| Workflow | Symptom | Likely cause |
| --- | --- | --- |
| Unified Audit Dashboard | 42-min avg duration vs 25-min budget | resolver step (`universal_pick_resolver`) capped at 20 min `continue-on-error: true`; dashboard generator re-run after rebase consumes 11+ min; FTP step single-threaded across 3 sites |
| ALPHA ENGINE FAST | 28-32 min, runs every 30 min | scanner runtime touching cron interval — back-to-back queueing risk |
| Copy Trader Intelligence | 29 min, runs every 45/15 min | scrape + analyze + track all in one job; long network section |
| Dynamic Runner | 37 min, runs every 30 min (`18,48 * * * *`) | runtime > interval; queue depth grows when one cycle slows |
| Hindsight Learner | timed out 2026-04-28 14:59Z at ~16 min | 20-min cap may be tight under cold-start pip retry; concurrency: false means it does not skip the next slot |
| ml-feedback-retrain | dormant >30 days | cron schedule may be missing or workflow disabled — no recent firings recorded |

**Silent-failure surfaces seen but not surfaced:**
- `Hyro pipeline outcome (must not silently look healthy when steps fail)` — this *exists* in `audit-dashboard.yml` (good) but most adjacent workflows have no equivalent gate.
- `[ADV-RISK] / [SLIPPAGE] / [CORR] / [VOL_FILTER]` lines all output `0 picks ... checked` when upstream produces 0 picks (saw this in run `25076721843`). A 0-pick scanner cycle should be logged as a soft alert, not absorbed.

## Configuration smells

| Workflow | Smell | Recommended fix |
| --- | --- | --- |
| audit-dashboard.yml | `timeout-minutes: 115` | Trim to 60–75 min and let real failures surface. 115 min hides regressions. |
| audit-dashboard.yml | `Refresh prediction-market inputs` step contains 6 `\|\| echo "...failed (non-fatal)"` chains | Each `\|\| echo` swallows real errors. Convert at minimum to `\|\| { echo …; touch failure_marker; }` and aggregate at end. |
| audit-dashboard.yml | `continue-on-error: true` on `Auto-regenerate predictable + scanner AI-Challenge picks`, `Resolve active picks`, `Fetch stock prices`, `Run pre-scanners`, more | Each masks regressions; only the resolver clearly needs it. Audit list and demote to `false` where the step is required. |
| audit-dashboard.yml | direct `git push origin main` (line ~loop in commit step), bypasses `safe_push.sh` | Replace with `bash .github/scripts/safe_push.sh` for retry-with-backoff. |
| dynamic-alpha-engine.yml | direct `git push origin main` | same — not using `safe_push.sh`. |
| alpha-engine-bond, alpha-engine-etf, alpha-quant-stack, fix-battleground | direct `git push` | same fix. |
| 180 / 295 workflows (~61%) | no `concurrency:` block at all | Most cron jobs running ≥ hourly need at minimum `concurrency: { group: <name>, cancel-in-progress: false }` to avoid same-job races on `git push`. |
| audit-dashboard, dynamic-alpha-engine, feed-health, enhanced-ml-crypto | no `actions/upload-artifact` on failure | Add `if: failure()` artifact upload for `*.log`, `audit_dashboard/data/*.json`, `alpha_engine/data/scanner_*.log` so post-mortem doesn't require log-grepping the run page. |
| ci-tests.yml | matrix `['3.11', '3.12']` but `[1m]` SyntaxError lives in test source; failure is python-version-dependent | Either gate that test on `sys.version_info >= (3, 12)` or fix the f-string so both versions parse. |
| Across many workflows | `cron: '0 * * * *'` chosen 172 times → minute-0 storm | Stagger to `:03 :07 :11 :17 :23 :29 :31 :37 :41 :43 :47 :53 :59` or hash the workflow name into a 0-59 minute slot. |
| audit-dashboard + audit-drift-telemetry | both at `:10` | Move drift telemetry to `:55` (hour-edge) so the heavy dashboard doesn't compete for runner pool with the lightweight one. |

## Cron overlaps + race conditions

Distribution of cron minutes across 295 workflows:

| Minute | Workflow count |
| --- | --- |
| `0` (every hour at :00) | **172** |
| `30` | 27 |
| `15` | 20 |
| `*/30` | 13 |
| `5` | 7 |
| `35` | 6 |
| `10` | 6 |
| `*/15` | 5 |
| `45` | 4 |
| `7`, `25`, `37`, `52` | 3-4 each |

**Notable collisions:**

| Time | Workflows colliding | Risk |
| --- | --- | --- |
| `:00` every hour | 172 cron entries | Mass GitHub-hosted runner queue, push-storm to `main`, peer commit contention. Worst offender by far. |
| `:10` hourly | `audit-dashboard.yml`, `audit-drift-telemetry.yml`, `breakout-arena.yml`, `ema-retracement-scan.yml`, `analyst-tracker.yml` (`:15`), `incubator-strategies.yml` (`:15`), `claudes-test-portfolios.yml` (`*/30 → :00,:30`) | Audit dashboard's heavy job lands inside the 41-min run interval right when a half-dozen lightweight workflows pile on. |
| `:15` hourly+ | `analyst-tracker`, `incubator-strategies`, `crypto-test-portfolios`, `deploy-vetted-picks`, `ema-retracement-scan`, `correlation-monitor` (subset) | Plus the `*/30` jobs hit `:15` half the time. |
| `:30` half-hour | 27 workflows (incl. `*/30` jobs) | Smaller storm than `:00` but still queueable on weekday peaks. |

## Top-5 dispatchable fixes (ranked by impact)

1. **Fix the `tests/test_quan_engine_concurrency_cap.py:41` f-string.** One-character change (`'created_at'` → `"created_at"`). Restores green CI on `main` for the matrix's 3.11 leg, removing the largest single source of red runs in the repo (207 reachable failures). Highest impact, lowest risk.

2. **Trim `audit-dashboard.yml` `timeout-minutes` from 115 → 60 and split the resolver into its own scheduled workflow.** Today's 42-min avg + 115-min ceiling means a regression that doubles runtime is invisible until it bleeds into the next hour's cron. Splitting `universal_pick_resolver` (currently 20 min `continue-on-error`) into its own 25-min workflow that publishes a JSON artifact saves ~20 min from every dashboard build and surfaces resolver failures independently.

3. **Stagger the `:00` cron storm.** 172 workflows at minute 0 is straining GitHub's hosted runner pool *and* the repo's own push contention budget. A one-PR refactor that maps `cron[0]` to `(hash(workflow_name) % 60)` would reshape the load curve from a spike to a flatline. Suggested target: keep no more than 8 workflows in any 1-minute slot.

4. **Add `if: failure()` artifact uploads to the top-3 audit-relevant workflows** (`audit-dashboard.yml`, `dynamic-alpha-engine.yml`, `enhanced-ml-crypto.yml`). Currently each failure forces grepping run logs by hand; an artifact bundle with `audit_dashboard/data/*.json` + scanner stdout would cut MTTR by ~80%.

5. **Promote the silent `(non-fatal)` lines in `dynamic-alpha-engine.yml` to a Discord pipeline-health notification.** The scanner currently swallows `[KPI] / [CALIBRATION] / [SPC] / [PATTERN] / [RISK]` failures with `non-fatal` text and a 37-min runtime. Each is a quiet regression (the `'<' not supported between instances of 'NoneType' and 'NoneType'` at `[CALIBRATION] / [SPC] / [PATTERN]` is the *same* upstream bug — likely a missing-data branch returning `None` instead of a sentinel). Even a 1-line Discord ping per `non-fatal` block per cycle would have caught this on the first run.

## Methodology notes

- 295 workflow files counted via `ls .github/workflows/*.yml | wc -l`.
- Conclusion distribution from `gh run list --limit 1000 --json conclusion`.
- Failure cohorts from `gh run list --limit 500 --status failure --json workflowName,conclusion,createdAt`.
- Step-level fail/cancel triage via `gh api repos/.../actions/runs/<id>/jobs`.
- Failure-log extraction via `gh run view <id> --log-failed | grep -E 'error|Traceback|##\[error\]'`.
- Cron analysis via `grep -rn "cron:" .github/workflows/*.yml`.
- Concurrency / safe_push usage via `grep -L`/`grep -lE` over the workflow directory.
