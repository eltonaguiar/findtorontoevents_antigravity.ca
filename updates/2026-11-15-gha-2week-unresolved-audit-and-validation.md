# GitHub Actions 14-Day Audit, Failure/Warning Fixes & Validation (2026-11-15)

**Worktree:** `.fix-wt` (rebased cleanly onto `origin/main`)  
**Scope:** Fix all remaining failing, cancelled, and noisy GitHub Actions workflows, broken Python scripts, test warnings, and guardian detection gaps; validate YAML/bash/Python syntax and pytest locally, deploy to `main`, triage open PRs, and verify post-fix live `workflow_dispatch` runs.

---

## 1. Root Causes Fixed

### A. `verified-pilot-daily.yml` & Paper Pilot Scripts
- **`verified_strategies/paper_pilot/etf_dual_momentum_pilot.py`**: Restored intact 177-line source from `a36f0dd15cc` after commit `aad007fe88c` accidentally truncated lines 1–170 (causing `IndentationError` on line 1), and ensured `.item()` scalar unwrapping in both `_last_close()` and `_twelve_month_returns()`.
- **`verified_strategies/paper_pilot/forex_carry_g10_pilot.py`**: Wrapped `_write_basket_to_db(result["basket"])` in `try/except Exception` so CI environments without MySQL credentials/driver fail open cleanly while still writing JSON logs/state.
- **`tools/run_verified_pilots_daily.py`**: Added `gating: bool = True` to `_run(...)` and set `gating=False` on `tools/strategy_admit.py --strategy etf_dual_momentum --asset-class ETF --write` so expected daily `REJECT` admissibility status (exit code `1`) does not fail the entire pilot job.
- **`.github/workflows/verified-pilot-daily.yml`**: Added `pymysql` to `pip install`, upgraded `checkout`/`setup-python`/`upload-artifact` to `@v6`, and switched checkout to `fetch-depth: 1` with `filter: blob:none`.

### B. Corrupted Python Files (`SyntaxError` / `CoverageWarning`)
- **`alpha_engine/backtest_quant_algorithms.py`**: Replaced single corrupted line (`IsADirectoryErrorCHATWITHIT...`) with a clean importable stub docstring (`0` external callers).
- **`alpha_engine/copytrader_integration.py`**: Stripped trailing XML/tool markup (`</content><parameter...>`) after `send_to_redis_bus(signal)`.
- **`alpha_engine/equity_rsi_divergence_mr_old.py`**: Stripped trailing XML/tool markup after `return signals`.
- **`alpha_engine/high_conviction_enhancements.py`**: Stripped trailing XML/tool markup after `return alerts`.
- **`tools/picks_now_forward_tracker.py`**: Closed truncated `CREATE TABLE IF NOT EXISTS picks_now_emits` SQL statement (`...emi` left by `afe231ded10`, `0` external callers) and added minimal `main()` compatibility entry point.

### C. CI Test Warnings, Stale Quarantine & Env Gate Isolation
- **`tests/test_corr_pipeline.py`**: Replaced `return True`/`return False` in `test_correlation_engine`, `test_data_lag_monitor`, and `test_schema_validation` with exceptions/assertions (`None` return), replaced hardcoded `'python3'` subprocess calls with `sys.executable`, and updated `main()` to run via exception handling (eliminates `PytestReturnNotNoneWarning`).
- **`tests/test_equity_price_failover_cache_path.py`**: Converted `"FOO\BAR"` literal to raw string `r"FOO\BAR"` (eliminates `SyntaxWarning: "\B" is an invalid escape sequence`).
- **`alpha_engine/validation/sharpe_metrics.py`**: Guarded `_sharpe_std_error()` against constant or near-zero-variance series (`np.ptp(arr) == 0.0 or np.std(arr) < 1e-12`) and small `n` before calling `scipy.stats.skew`/`kurtosis` (eliminates SciPy `RuntimeWarning`).
- **`tests/test_dashboard_generator.py` & `tests/test_m097_book_direction_conflict.py`**: Neutralized cross-cutting `CRYPTO_*` LONG block env vars (`CRYPTO_PRODUCTION_BLOCK_LONG`, `CRYPTO_PRODUCTION_BLOCK_LONG_OVERRIDE`, `CRYPTO_BUY_DIRECTION_GATE_ENABLED`, `CRYPTO_SIZED_LONG_BLOCK`, `CRYPTO_UTC_HOUR_FILTER`, `ML_CRYPTO_PRED_LONG_REJECT`, `BTC_BEAR_LONG_REJECT`) via `monkeypatch.setenv(..., "0")`.
- **`.github/workflows/ci-tests.yml`**: Removed stale nonexistent `tests/test_confidence_calibrator.py::CalibratorContractTests::test_no_op_when_flag_unset` from `known_drift_tests.txt` (`test_no_op_when_explicitly_disabled` passes in the gating suite).

### D. Workflow Cancellations, Push Races, Stale Checks & Warnings
- **`.github/workflows/academic-strategies-daily.yml`**: Added `filter: blob:none` checkout and replaced `git pull --rebase || true` retry loop with bounded `git fetch --quiet --depth=1 --filter=blob:none origin main` + `git rebase --quiet` + `git rebase --abort` fallback + explicit push failure check.
- **`.github/workflows/daily-top-picks-filter.yml`**: Upgraded `checkout@v6` (`fetch-depth: 1`, `filter: blob:none`), `setup-python@v6`, and replaced bare `git pull --rebase` with bounded `git fetch --filter=blob:none && git rebase && git push`.
- **`.github/workflows/picks-now-refresh.yml`**: Upgraded `setup-python@v6` and added `--filter=blob:none` to Step 13 `git fetch`.
- **`.github/workflows/stocksunify2-pull.yml`**: Added `filter: blob:none` to `fetch-depth: 0` checkout (prevents 5-minute timeout cancellation on clone).
- **`.github/workflows/value_screener_weekly.yml`**: Changed read-only `permissions: contents: read` checkout from `fetch-depth: 0` to `fetch-depth: 1` + `filter: blob:none`.
- **`.github/workflows/branch-large-file-dup-guard.yml`**: Scoped `concurrency.group` to `branch-large-file-dup-guard-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}` so unrelated branches/events no longer cancel each other.
- **`.github/workflows/model-picks-emission.yml`**: Upgraded actions to `@v6` with `filter: blob:none` and replaced bare `git push origin main` with `bash .github/scripts/safe_push.sh`.
- **`.github/workflows/audit-dashboard.yml`**:
  1. Optimized `upload_research_tree()` to cache `ensured_dirs` per FTP connection and skip historical `run_YYYY-MM-DD...` directories older than 3 days (overridable via `UPLOAD_ALL_RESEARCH=1`), eliminating ~55 minutes of redundant hourly transfers across 3 FTP mirrors that caused every other cron run to cancel.
  2. Replaced hardcoded `'2026-05-(1[6-9]|2[0-9])'` banner freshness regex with dynamic UTC today/yesterday check.
  3. Wrapped `python -m alpha_engine.walkforward_validator` step `run:` in YAML block scalar `|` so `#45)"` inside the fallback warning string is not truncated by YAML comment parsing.
- **`.github/workflows/sports-betting-refresh.yml`**: Removed invalid `token:` input (caused `Unexpected input(s) 'token'` annotation) and `--force-with-lease` from `stefanzweifel/git-auto-commit-action@v5`.
- **`.github/workflows/audit-drift-telemetry.yml`**: Switched Binance health ping URL from US geo-blocked `https://api.binance.com/api/v3/ping` (HTTP 451) to `https://data-api.binance.vision/api/v3/ping` (HTTP 200).
- **`.github/workflows/feed-health.yml`**: Added `python -m pip install -q numpy requests` before `python audit_trail/feed_health_check.py --once`.
- **`scripts/actions_failure_guardian.py`**: Raised `detect_masked_failures` default `max_runs` (`FAILURE_GUARD_MASKED_MAX_RUNS`) from `40` to `120` and added bounded check-run annotation inspection (`annotation_level == "failure"`).
- **Repo-wide workflow hardening**: Added `filter: blob:none` to 22 active `fetch-depth: 0` checkout blocks and upgraded `actions/{checkout,setup-python,upload-artifact,download-artifact}` `@v1-v5` references to `@v6` across 65 workflow files.

---

## 2. Local Verification (Pre-Push)
- `yaml` strict duplicate-key parse across all 362 workflows in `.github/workflows/`: **362 checked, 0 errors**.
- `py_compile` across all 14 modified/fixed Python files: **14/14 compiled cleanly**.
- Direct script execution: `python tests/test_corr_pipeline.py` exited **0**.
- Guardian unit test: `detect_masked_failures` stubbed check-run annotation test **PASS**.
- `pytest tests/test_corr_pipeline.py tests/test_equity_price_failover_cache_path.py tests/test_statistical_rigor.py tests/test_hedge_fund_gap_fillers.py tests/test_confidence_calibrator.py tests/test_dashboard_generator.py tests/test_m097_book_direction_conflict.py tests/test_audit_metric_invariants.py -v`: **91 passed, 1 xfailed, 1 xpassed, 0 warnings** (after reverting/ignoring unrelated files and running in `.fix-wt`).

---

## 3. Live GitHub Actions Validation (Post-Reset — Pending / In Progress)
*(Will be populated with PR triage outcomes, post-fix `workflow_dispatch` run IDs, durations, conclusions, and annotation checks after `09:15:10Z` REST quota reset.)*

