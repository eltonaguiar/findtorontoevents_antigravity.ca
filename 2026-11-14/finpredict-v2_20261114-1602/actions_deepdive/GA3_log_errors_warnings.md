# GA3 — Failure-Log Error/Warning Miner

**Scope:** `eltonaguiar/findtorontoevents_antigravity.ca` @ `main`, failures observed 2026-11-14T13:18Z–17:22Z (all inside the 48h window).
**Generated:** 2026-11-14 ~17:55Z. Source changes: none.

## Log hygiene verdict: FAIL

| Dimension | Verdict | Evidence |
|---|---|---|
| Log availability | PASS | 30/30 runs recovered. 16 came from `gh run view`; 14 returned 0 lines from both `--log-failed` and `--log` and were recovered from the Actions logs ZIP API. |
| Secret hygiene | PASS | Secret-pattern scan of all 30 excerpts found no `ghp_`/`gho_`/`ghs_`/`sk-`/`AKIA`/`xox*` tokens and no `password=`/`token=`/`api_key=` values. |
| Signal-to-noise | FAIL | 6,628 Binance `451 Client Error` lines across 15 alpha runs swamp the real terminal error. 14/30 runs had no `--log-failed` output at all. |
| Actionability | FAIL | The top failure (`KeyError: 'LONG'`) does not log the offending symbol/signal. 70 workflow files use `continue-on-error: true`, and several `|| true` / bare `except` paths swallow failures before they reach the log. |

## Method

1. Ran the required query with `--limit 500`; that window covered only 3.03h (14:41Z–17:44Z), so it was extended to `--limit 2000` to obtain the full 30 most-recent `failure` runs, all still within 48h.
2. For each run: `gh run view <id> --log-failed` and `gh run view <id> --log`. Where both were empty, `gh api repos/.../actions/runs/<id>/logs` (ZIP) was used.
3. Excerpts were normalized (timestamps/job prefixes/ANSI stripped), filtered to error/warning/HTTP/secret/git lines, deduped, and capped at **≤120 lines/run**. Files: `actions_deepdive/raw/GA3_logs/<runid>.txt` (30 files, max 120 lines each).
4. Root-cause clusters were assigned by terminal signature, then ranked by failed-run count in the window and audit-dashboard dependency.

## Cluster table (all 30 failures accounted for)

| # | Root cause | Failed runs | Affected workflows | Sample run IDs | Error excerpt (trimmed) | Feeds audit dashboard |
|---|---|---|---|---|---|---|
| A | `KeyError: 'LONG'` — forex conflict resolver indexes a BUY/SELL-only dict with `LONG`/`SHORT` | **15** (50%) | ALPHA ENGINE - Dynamic Runner (Cloud or Local) ×8; ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds ×7 | `43617643018`, `43616386010`, `43614960770` | `scanner.py:2942` → `_forex_by_sym[s["symbol"]][sig_type].append(s)` → `KeyError: 'LONG'` → exit 1 | **Yes — primary pick source** |
| B | pandas built from source on **Python 3.14**; `_PyLong_AsByteArray` ABI mismatch. `setup-python` installs 3.11.18 but `update-environment: false` leaves `pip`/`python` on system 3.14 | **7** | Forward Test; Live Trading Bot (×3 variants); Crypto Picks Dispatch; Market Beating System; Signal Tracking & Validation | `43613794351`, `43613629628`, `43603128044` | `pandas/_libs/tslibs/base.cpython-314...: error: too few arguments to function '_PyLong_AsByteArray'; expected 6, have 5` → `metadata-generation-failed` | Indirect (blocks pick producers/validators) |
| C | Playwright 1.58.2 does not support the runner OS `ubuntu26.04-x64` | **5** | Sports endpoint smoke + Playwright | `43620352180`, `43609430834`, `43599098929` | `Cannot install dependencies for ubuntu26.04-x64 with Playwright 1.58.2!` / `Playwright does not support chromium on ubuntu26.04-x64` | No |
| D | pandas 2.2+ alias `ME` used against pinned `pandas==2.1.4` (alias introduced in 2.2) | **2** | CI Tests (matrix 3.11 + 3.12) | `43615290049`, `43605861085` | `ERROR collecting tests/test_combined_book_sleeves.py` → `KeyError: 'ME'` → `ValueError: Invalid frequency: ME` | Indirect (CI gate) |
| E | Commit contains a 100.22 MB JSON file, over GitHub's 100 MB hard limit | **1** | Missed Opportunity Analyzer Hourly Self-Improvement | `43620744998` | `File alpha_engine/data/wrong_guesses_log.json is 100.22 MB; this exceeds GitHub's file size limit of 100.00 MB` → `pre-receive hook declined` | Indirect |

**Window totals:** 30 failed runs in 4.07h ≈ **7.4 failures/hour**. Linear extrapolation (rough, cron cadence varies): ~176 failed runs/day.

## Warnings / degradations that did **not** fail the run

| Warning / degradation | Occurrences | Runs | Notes |
|---|---|---|---|
| Binance HTTP **451** (geo-restriction) on `fapi*.binance.com` | 6,628 | 15 alpha runs | `coinalyze_client.py:65`; failover degrades data, does not abort |
| CoinMetrics HTTP **403** on `community-api.coinmetrics.io` | 30 | 15 alpha runs | `coinmetrics_signal.py:48` opens a circuit breaker after 3 misses |
| Binance HTTP **429** Too Many Requests on `/futures/data/globalLongShortAccountRatio` | 20 | 2 alpha runs | `fapi1`/`fapi2` fallbacks also throttled |
| Yahoo quote **404** for non-existent tickers `THE1-USD`, `POPCAT1-USD` | 7 | 6 alpha runs | Data-quality noise; symbol list should be pruned |
| `XGBoost not available` / `LightGBM not available` → RandomForest fallback | 7 + 7 | 7 FAST alpha runs | ML ranking quality silently downgraded |
| XGBoost internal `error_msg.h:83` UserWarning | 8 | alpha runs | Non-fatal |
| `Kill switch: WARNING -- Dead features: 30/32 (94%) -- health_score=0.06` | 15 | 15 alpha runs | ML feature pipeline is effectively dead; separate from the crash |
| Node.js 20 deprecation: `actions/upload-artifact@v5` forced to Node 24 | 2 | 2 CI runs | Upgrade/pin action or accept forced runtime |
| `DeprecationWarning: The punycode module is deprecated` (DEP0040) | 13 | 7 runs | Node/npm dependency |
| `SyntaxWarning: invalid escape sequence '\B'` | 2 | 2 CI runs | `tests/test_equity_price_failover_cache_path.py:53` |
| Playwright "OS not officially supported … ubuntu26.04-x64" | 5 | 5 Sports runs | Precursor to cluster C |
| Skipped tests: `No module named 'torch'`, `No module named 'pydantic'` | 2 | 2 CI runs | Coverage blind spots, not failures |
| `FRED_API_KEY not set` | 15 | 15 alpha runs | Macro factors silently unavailable |
| `CRYPTOPANIC_API_KEY` not set; Whale Alert/Etherscan/Arkham "no API key" | 15 | 15 alpha runs | Sentiment/whale signals silently skipped |

No `::warning::` workflow-command annotations and no `set-output` deprecations were found. The only error annotations were the generic `##[error]Process completed with exit code 1`.

## Missing secrets / env vars (names only; values never printed)

| Variable | Symptom | Runs |
|---|---|---|
| `FRED_API_KEY` | `fred_json failed for DTWEXBGS/DGS10/DGS2/T10Y2Y/FEDFUNDS/VIXCLS` | 15 alpha runs |
| `CRYPTOPANIC_API_KEY` | `CryptoPanic: no API key set` | 15 alpha runs |
| Whale Alert / Etherscan / Arkham API keys | `Skipped (no API key)` | 15 alpha runs |

These are degradations, not the cause of any of the 30 failures.

## Silent-failure list

| Pattern | Location | Effect |
|---|---|---|
| `git add ... 2>/dev/null || true` | `.github/workflows/missed-opportunity-scan.yml:42-44` | Missing/oversized files are silently staged; the 100 MB file then fails at push (cluster E) |
| `git commit ... || true` | `.github/workflows/live_trading_canada_free.yml:98`, `.github/workflows/live_trading_canada.yml:91` | Commit failures never fail the job |
| `git add ... || true` / `git pull --rebase ... || true` | `.github/workflows/forward_test.yml:110-115` | Result persistence can fail silently |
| `python -m coverage report ... || true` | `.github/workflows/ci-tests.yml:249` | Coverage reporting failures hidden |
| `continue-on-error: true` | 70 workflow files (e.g. `ai-tournament-pipeline.yml`, `copy-trader-intelligence.yml`, `worldclass-pipeline.yml`) | Steps can fail without failing the run, so failures never appear in `failure` lists |
| Per-strategy `except Exception as e: print(f"  [{name}] ERROR: {e}")` | `alpha_engine/scanner.py:2377-2378` | Any strategy can fail and the scan still "succeeds" |
| Bare `except Exception: pass` / fallback returns | `alpha_engine/scanner.py:649`, `:939`, and the ML-feature enrichment loop (`~2820`) | Missing features/regime data silently become `None` |
| `except ValueError: pass` around status prints | `alpha_engine/scanner.py:2693`, `:2712` | Secondary generators can emit without any log line |

## HTTP / API errors with domain

| Status | Domain / URL | Runs | Fatal? |
|---|---|---|---|
| 451 | `fapi.binance.com`, `fapi1/fapi2.binance.com`, `api*.binance.com` | 15 | No |
| 403 | `community-api.coinmetrics.io/v4/timeseries/asset-metrics` | 15 | No (circuit breaker) |
| 429 | `fapi1/fapi2.binance.com/futures/data/globalLongShortAccountRatio` | 2 | No |
| 404 | Yahoo `quoteSummary` for `THE1-USD`, `POPCAT1-USD` | 6 | No |

## Ranked fixes

| Rank | Fix | Exact location | Failed runs explained | Effort | Notes |
|---|---|---|---|---|---|
| 1 | Normalize `signal_type` before indexing the forex map; accept `LONG`/`SHORT` as aliases of `BUY`/`SELL` (or key the defaultdict for all four values) | `alpha_engine/scanner.py:2941-2942` | **15 / 30** | 1 line | Defensive fix works regardless of which upstream emitter produces `LONG` |
| 2 | Remove `update-environment: false` (or use `python -m pip` consistently) so `pip` uses the 3.11 interpreter that `setup-python` installed | `forward_test.yml:33`, `live_trading.yml:29`, `live_trading_canada.yml:33`, `live_trading_canada_free.yml:43`, `picks_dispatch.yml:24`, `market_beating.yml:35`, `signal_tracking.yml:35` | 7 / 30 | 7 mechanical edits | Also removes the 100-minute source-build cost per run |
| 3 | Pin the Sports smoke job to a supported runner (`ubuntu-24.04`) or upgrade/pin Playwright to a release that supports 26.04 | `.github/workflows/sports-smoke-and-e2e.yml:53` (runner) and `:86` (`playwright install`) | 5 / 30 | 1 line | Package pin is `@playwright/test ^1.58.2` in `package.json:20` |
| 4 | Replace `freq="ME"` with a pandas-2.1-compatible alias (`"M"`), or bump `pandas==2.1.4` to `>=2.2` | `tests/test_combined_book_sleeves.py:17` (alias) and `requirements.txt:2` (pin) | 2 / 30 | 1 line (or dependency bump) | Bumping pandas must be coordinated with numpy pin |
| 5 | Stop committing `wrong_guesses_log.json`; add to `.gitignore` + `git rm --cached`, move to LFS, or trim/rotate it below 100 MB | `.github/workflows/missed-opportunity-scan.yml:43` and `alpha_engine/data/wrong_guesses_log.json` | 1 / 30 | Small | File is already tracked and ~100 MB locally; history may still need LFS |

### Highest-value single fix

**`alpha_engine/scanner.py:2941-2942`** is the highest-value fix.

- It explains **15 of 30 failed runs (50%)** in the observed 4.07h window, i.e. **~3.7 failed runs/hour, ~88/day** by linear extrapolation.
- Those 15 runs consumed **558 runner-minutes (~9.3 runner-hours)**, average **37.2 min** of wasted compute per run — the crash happens at the end of `run_generation()`, after the expensive scan/ML work (`forward_validator.py:2067` → `scanner.py:2942`).
- It blocks both ALPHA ENGINE workflows, which are the primary producers of picks consumed by `audit_trail/dashboard_generator.py` (reads `alpha_engine/data/active_picks.json`, `smart_picks.json`). A crash means no fresh picks for that cycle, so this is also the largest audit-dashboard blast radius.
- The fix is defensive and does not require identifying the emitter: coerce `LONG→BUY` and `SHORT→SELL` before `_forex_by_sym[...]` indexing, exactly as `_normalize_signal_type()` already does at `scanner.py:2059-2067`.

Runner-up by compute: cluster B wastes **715 runner-minutes (~11.9h)** across 7 runs (avg 102 min), slightly more compute than cluster A, but half the failed-run count and less direct dashboard impact.

## UNVERIFIED markers

- **UNVERIFIED:** the upstream producer that sets `signal_type: "LONG"` on a `category: "forex"` signal. The crash site is verified, but the offending symbol/signal is not logged. Repo search found no forex emitter that writes `signal_type: LONG` as a literal; candidates are dynamically assembled or mutated picks. This does not block the recommended defensive fix.
- **UNVERIFIED:** whether `wrong_guesses_log.json` must be retained at full size for downstream consumers; if not, deletion is cheaper than LFS.

## Run index (30/30)

| Run ID | Workflow | Cluster |
|---|---|---|
| 43620744998 | Missed Opportunity Analyzer Hourly Self-Improvement | E |
| 43620352180 | Sports endpoint smoke + Playwright | C |
| 43617643018 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | A |
| 43616386010 | ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | A |
| 43615290049 | CI Tests | D |
| 43614960770 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | A |
| 43614883408 | Sports endpoint smoke + Playwright | C |
| 43614165537 | ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | A |
| 43613794351 | Forward Test - Strategy Validation | B |
| 43613787653 | Live Trading Bot - Canada Edition (FREE Data) | B |
| 43613779808 | Live Trading Bot - Canada Edition | B |
| 43613629628 | Live Trading Bot | B |
| 43613459896 | Crypto Picks Dispatch | B |
| 43612197130 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | A |
| 43610957736 | ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | A |
| 43609547717 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | A |
| 43609430834 | Sports endpoint smoke + Playwright | C |
| 43608586741 | ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | A |
| 43606815294 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | A |
| 43605861085 | CI Tests | D |
| 43605607406 | ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | A |
| 43604242880 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | A |
| 43604146732 | Sports endpoint smoke + Playwright | C |
| 43603351368 | ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | A |
| 43603128044 | Market Beating System - Crypto & Forex Priority | B |
| 43602685216 | Signal Tracking & Validation - Beat the Market | B |
| 43601647036 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | A |
| 43600472115 | ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | A |
| 43599170690 | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | A |
| 43599098929 | Sports endpoint smoke + Playwright | C |

**Excerpt store:** `actions_deepdive/raw/GA3_logs/` — 30 files, ≤120 lines each, secrets redacted/absent.
