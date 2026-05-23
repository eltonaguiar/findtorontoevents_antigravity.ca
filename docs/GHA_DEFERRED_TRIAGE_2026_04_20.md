# GHA Deferred-Failure Triage — 2026-04-20

Scope: workflows Cursor deferred. Excludes `ci-tests.yml` (Cursor: fixture staleness) and `weekly_score_quartile_spread.yml` (Cursor: numpy fix in `2e7c5421d`).

## 1. Per-workflow failures

| Workflow | Last-failure run | Root cause | Severity |
|---|---|---|---|
| ALPHA ENGINE — Dynamic Runner (Cloud or Local) | 24664791457 (2026-04-20 11:48Z) | Step **"Commit results"** → `ERROR: All push attempts failed`. Run itself passed (Run Alpha Engine ✓). Push-lock contention. | Low (self-heals; success 13:21Z) |
| ALPHA ENGINE — Live Autonomous Scanner | 24490037788 (2026-04-16 03:14Z) | Step **"Full cycle (validate + generate + tweak)"** → `NameError: name 'commodity' is not defined` in forward validator. Real code bug. Also incidental `TypeError: Object of type bool is not JSON serializable`, `TypeError: can't compare offset-naive and offset-aware datetimes`, sklearn `ValueError: y contains 1 class` (single-class training data). | Medium — code bug; later runs unblocked (last success 2026-04-20 12:39Z) but `NameError` recurrence likely when that branch re-enters |
| Unified Audit Dashboard | 24643652333 (2026-04-20 01:02Z) | Step **"Commit updated data"** → `ERROR: All push attempts failed — another workflow likely has the lock`. All 20+ data steps passed. Push-lock contention. | Low (self-heals; success 13:48Z) |
| Deploy findtorontoevents.ca core site | 24611185333 (2026-04-18 18:33Z) | Step **"Verify deployment"** → `urllib.error.HTTPError: HTTP Error 412: Precondition Failed` fetching `https://findtorontoevents.ca/index.html?<cache_bust>`. 50webs FTP upload succeeded; verifier's conditional-GET headers (If-None-Match / If-Modified-Since) tripped 412 at origin. | Medium — masks real verification; last success 2026-04-20 12:49Z |
| Rapid Fire — NOW Scanner | last failure 23674901949 (2026-03-28 03:04Z) — **>14d, logs aged out** | N/A — last success 2026-04-20 14:21Z, workflow healthy | None |
| Multi-Asset Copytrader Scanner v2 | last failure 23449287829 (2026-03-23 17:33Z) — **>14d, logs aged out** | N/A — last success 2026-04-20 14:40Z, workflow healthy | None |

## 2. Shared-cause analysis

**Push-lock contention is the dominant cross-workflow failure mode today.** Both the latest Dynamic Runner and Unified Audit Dashboard failures are auto-commit collisions on `main`, not real pipeline faults. The common message `ERROR: All push attempts failed` (and `another workflow likely has the lock`) comes from the shared commit/push wrapper. With Unified Audit running hourly at `:10` for ~45 min and Dynamic Runner + many other scheduled writers commiting data artefacts concurrently, the retry budget is exhausted. This is the **"push-lock contention" issue** the brief flagged — it does affect these two. Rapid Fire, Copytrader v2, and Deploy are NOT push-lock issues. Live Autonomous is a distinct code bug.

Secondary shared theme: **Binance region block** — `451 Client Error` on `fapi.binance.com/...` in the Live Autonomous log (2026-04-16). The repo's 3+ endpoint fallback chain (CoinGecko→KuCoin→CryptoCompare) already handles this; CoinGecko is also throwing `429 Too Many Requests` in the Dynamic Runner log. Rate-limit pressure is elevated but non-fatal.

## 3. Deprecated-action inventory

Actually deprecated (pre-Node-20, currently marked deprecated by GitHub):

- `.github/workflows/deploy-pages.yml:121` — `actions/upload-pages-artifact@v3`
- `.github/workflows/deploy-pages.yml.disabled:85` — `actions/upload-pages-artifact@v3` (disabled file, informational)
- `.github/workflows/deploy-riseoftheclaw.yml:592` — `actions/upload-pages-artifact@v3`
- `.github/workflows/dna_strategy_pipeline.yml:71` — `actions/cache@v3`
- `.github/workflows/dna_strategy_pipeline.yml:123` — `actions/cache@v3`

Cursor-flagged `actions/cache@v4` / `actions/upload-artifact@v4` usages are **not yet deprecated** (they are the current Node-20 versions). Inventory kept for future migration (~46 `@v4` usages across ~35 files — see `.github/workflows/*.yml` Grep for `actions/(cache|upload-artifact|download-artifact|setup-python|setup-node)@v4`). No action required today.

No `@v1` or `@v2` references found.

## 4. Cron coverage — stale last-success (>48h)

247 scheduled workflows scanned. Notable stale:

- **No successful run ever:** `bond-agent.yml`, `genome-evolution.yml`, `torontoevent-backtest-and-deploy-ROOCODE.yml`, `weekly_score_quartile_spread.yml` (Cursor owns last one).
- **Very stale (>400h):** `asterdex-paper-trader.yml` (1216h), `send-event-notifications.yml` (1393h), `dna_strategy_pipeline.yml` (1066h), `paper-trading.yml` (1017h), `mercury2-fast-scan.yml` (918h), `ml-battleground-*.yml` (×8, all ~917h since 2026-03-13), `fast-stocks-competition.yml` (908h), `ml-monthly-retrain.yml` (465h, monthly OK), `monthly-tournament.yml` (464h, monthly OK), `claudes-test-portfolios.yml` (643h), `live-position-monitor.yml` (574h).
- **Recently stale (48–210h):** `alpha-suite-daily-refresh.yml` (65h), `daily-miracle-scan.yml` (63h), `daily-price-refresh.yml` (60h), `etf-agent.yml` (72h), `news-video-healthcheck.yml` (95h), `overnight-mutations.yml` (60h), `stocks-daily.yml` (65h), `stocks-daily-stocksunify.yml` (65h), `taste-profile-scan.yml` (202h), `weekly-strategy-scorecard.yml` (206h, weekly OK).

Monthly/weekly workflows (`ml-monthly-retrain`, `monthly-tournament`, `weekly-strategy-scorecard`) explain themselves. The 8× `ml-battleground-*` cluster all stopping simultaneously on 2026-03-13 suggests a shared dependency/secret broke that day — worth single-point investigation rather than 8 separate fixes.

## 5. Recommendations (ranked by impact vs. effort)

1. **Fix the `commodity` NameError in forward validator** (Live Autonomous Scanner). Localized code bug; high recurrence risk. Effort: low. Grep for `commodity` in the forward-validator module called by the "Full cycle" step — the 2026-04-16 run trace pinpoints the frame.
2. **Fix Deploy-core verifier 412 handling.** The verifier's conditional-GET is incorrect for 50webs; either strip `If-*` headers or treat 412 as "content unchanged = pass". Effort: trivial (one-line in the verify script). Unblocks deploy alerts.
3. **Stagger auto-commit windows to reduce push-lock contention.** Unified Audit (hourly :10) and Dynamic Runner overlap heavily. Shift Dynamic Runner off :00 boundary, or consolidate via a single "commit collector" job. Effort: medium; eliminates a recurring class of false failures affecting both workflows and likely others with `Commit updated data` steps.
4. **Investigate the 2026-03-13 ml-battleground cluster death** as one issue — all 8 workflows stopped together. Effort: low (single git log check around that date). Huge fix-count payoff.
5. **Migrate `actions/cache@v3` → `@v4`** in `dna_strategy_pipeline.yml` (2 lines) and `actions/upload-pages-artifact@v3` → `@v4` in 2 active files. Effort: trivial; silences deprecation annotations before they become hard failures.
6. **Defer:** Rapid Fire and Copytrader v2 are healthy (successful runs within last 2h); the old failures in the recurrence list are noise.

Not committed; diagnosis only.
