# GitHub Issues, Stale PRs, and Broken GitHub Actions Cleanup (`2026-11-15`)

## Summary

Executed a three-stream triage and root-cause remediation across `eltonaguiar/findtorontoevents_antigravity.ca`:
1. **Duplicate & Resolved Issues**: Closed 6 duplicate, resolved, or obsolete open issues (`#668`, `#675`, `#685`, `#695`, `#748`, `#654`), leaving `#764` as the sole open canonical issue, and patched workflow issue generators (`secret-rotation-reminder.yml`, `data-pipeline-test.yml`) to prevent future duplicate spam.
2. **Stale & Redundant PRs**: Verified `#788` merged (`38e14069d`), squash-merged `#791` (`5c4835224`, porting non-superseded serialization & pilot diagnostics from `#790`), and closed `#790` with detailed triage notes (porting its unmerged `secret-rotation-reminder.yml` prior-month auto-close fix into this branch with `--slurp` pagination safety). Result: **0 open PRs**.
3. **Broken, Timed-Out, and Chronically Cancelled GitHub Actions**: Audited recent workflow runs on `main` (distinguishing PR `#786`/`#789` recoveries and intentional fail-loud monitors from remaining failures), then fixed **17 broken/timed-out/spamming workflows and underlying Python pipelines** cleanly in `.fix-wt`.

---

## 1. Issue Triage & Root-Cause Deduplication

### Issue Actions Taken
| Issue | Original Title | Disposition | Reason / Evidence |
|---|---|---|---|
| `#668` | `[Security] Monthly Secret Rotation Reminder — July 2026` | **Closed** (`not_planned`) | Superseded duplicate monthly reminder; referenced `#764` |
| `#675` | `[Security] Monthly Secret Rotation Reminder — August 2026` | **Closed** (`not_planned`) | Superseded duplicate monthly reminder; referenced `#764` |
| `#685` | `[Security] Monthly Secret Rotation Reminder — September 2026` | **Closed** (`not_planned`) | Superseded duplicate monthly reminder; referenced `#764` |
| `#695` | `[Security] Monthly Secret Rotation Reminder — October 2026` | **Closed** (`not_planned`) | Superseded duplicate monthly reminder; referenced `#764` |
| `#748` | `Production resolver predates _priceless_close -> exit_price=0.0 flat closes in recent_closed` | **Closed** (`completed`) | Verified `_priceless_close()` in `origin/main` `audit_trail/universal_pick_resolver.py` + `5d42f75fd9c` fallback + live `dashboard_data.json` (`3,500` `recent_closed` rows with `0` `exit_price==0.0` or `None`) |
| `#654` | `Weekly event gap scan: 2026-06-22 — DEGRADED (scrapers blocked, 56/10614 events, result unreliable)` | **Closed** (`not_planned`) | 5-month-old single web-container egress IP block; superseded by healthy daily `scrape-events.yml` (`13,835` events across 26 sources) |
| `#764` | `[Security] Monthly Secret Rotation Reminder — November 2026` | **Kept Open** | Active canonical checklist for current month (`- [ ]` items still pending) |

### Root-Cause Issue-Spam Fixes
- **`.github/workflows/secret-rotation-reminder.yml`**: Previously matched only the exact current-month title and left every prior month's issue open indefinitely. Now queries open issues via `gh api --paginate --slurp`, skips duplicate creation if current month's issue exists, and automatically closes all prior open `[Security] Monthly Secret Rotation Reminder` issues with a superseding comment referencing `#$CURRENT_NUM`.
- **`.github/workflows/data-pipeline-test.yml`**: `Alert on failures` step previously called `github.rest.issues.create()` unconditionally on every failure. Updated to look up existing open `data-pipeline` issues with matching title and post a comment instead of opening duplicates.

---

## 2. Stale PR Cleanup

| PR | Title | Disposition | Notes |
|---|---|---|---|
| `#788` | `docs(final_v001): per-class profitability proof plan + GHA/PR/issue audit` | **Merged** (`38e14069d`) | Integrated cleanly on `main` |
| `#791` | `fix(ci): port unique parts of #790 (forward-test serialization, pilot diagnostics, review docs)` | **Squash-merged** (`5c4835224`) | Passed required checks; landed `forward-test-new-strategies.yml` concurrency + `tools/run_verified_pilots_daily.py` diagnostics + review docs |
| `#790` | `fix(ci): dedup backup-verify issues + serialize forward-test pushes` | **Closed** (`dc1e5711`, unmerged) | Auto-closed via `#791` with triage comment; `backup-verify.yml`/`sports-smoke-and-e2e.yml` superseded by `#789`/`#786`, unique `secret-rotation-reminder.yml` prior-month auto-close ported here |

Result: **0 open pull requests** remaining.

---

## 3. GitHub Actions Fixes

### Baseline Verified Already Healthy / Intentional Fail-Loud
- **Fixed in `#786`/`#789`**: `Sports endpoint smoke + Playwright` (`ubuntu-24.04` pin), `Backup Restore Verification` (live fetch + `SKIPPED` handling + issue dedup/auto-close), `actions-failure-guardian` (`FAILURE_GUARD_MAX_ATTEMPT: 3`, `FAILURE_GUARD_EXCLUDE`), `feed-health.yml`, and `Python 3.14` pandas workflows recovered on `main`.
- **Intentional Fail-Loud (untouched)**: `daily-price-refresh.yml` (superseded by `daily-prices-yf-refresh.yml`, kept fail-loud per `# UNMASK`) and `robust-edge-miner.yml` (intentionally exits 1 when new robust edge cells are discovered).

### Newly Fixed Workflows & Code Paths
1. **`QA Market Validation` (`alpha_engine/commodity_price_failover.py`, `alpha_engine/forex_price_failover.py`, `alpha_engine/equity_price_failover.py`, `tools/qa_ledger.py`, `.gitignore`, `data/*_cache/`)**:
   - **What was broken**: Tracked cache files from `2026-06-06` had their filesystem `mtime` reset on every `actions/checkout`, tricking `_cache_read()` mtime-TTL checks into serving stale prices; `tools/qa_ledger.py` also used disk cache instead of live validation.
   - **What changed**: Stamped `"_cached_at": time.time()` inside `_cache_write()` and enforced payload `_cached_at` expiry in `_cache_read()` across all three failover modules; added `use_cache: bool = True` to `fetch_commodity_price` and `fetch_forex_rate`; updated `tools/qa_ledger.py` to pass `use_cache=False`; removed 15 stale tracked cache JSONs (replaced with `.gitkeep`) and gitignored runtime cache JSONs.
2. **`Verified Pilot Daily` (`verified_strategies/paper_pilot/forex_carry_g10_pilot.py`)**:
   - **What was broken**: Step 10 crashed with `KeyError: 'basket'` (`run_one_shot()` omitted `"basket"`), `_write_basket_to_db` was defined below `if __name__ == "__main__":`, and raw `get_stocks_creds()` kwargs were passed straight to `pymysql.connect()`.
   - **What changed**: Included `"basket": legs` in `run_one_shot()`, moved `_write_basket_to_db` above `main()`, filtered `get_stocks_creds()` to valid `pymysql.connect` keys, and ensured `conn.close()` in `finally`.
3. **`Mirror Site` (`.github/workflows/mirror-site.yml`)**:
   - **What was broken**: `lftp mirror` choked on malformed remote `tmp/hot_trending_30m%2527%2522\'\".json` (`553 Prohibited file name`).
   - **What changed**: Added `--exclude='^tmp/'` to all three `lftp mirror` invocations.
4. **`Missed Opportunity Scan` (`.github/workflows/missed-opportunity-scan.yml` consumer `alpha_engine/missed_opportunity_analyzer.py`, `alpha_engine/data/wrong_guesses_log.json`, `alpha_engine/data/missed_gainers_log.json`)**:
   - **What was broken**: Hourly appends without deduplication bloated `wrong_guesses_log.json` past GitHub's 100 MB push limit (`~107.2 MB`, ~164x duplicate entries).
   - **What changed**: Added `_dedup_wrong_entries()` and `_dedup_missed_entries()` after `_prune_old_entries()` and compacted both tracked log JSONs under 2 MB total.
5. **`Outcome Resolver` (`.github/workflows/outcome-resolver.yml`, `audit_trail/backfill_local_sources.py`)**:
   - **What was broken**: Row-by-row `autocommit=True` inserts over remote TCP caused 10/10 runs to hit the 15-minute cancellation timeout.
   - **What changed**: Batched inserts into chunks of 500 via `executemany` with `autocommit=False`, per-chunk commits, and per-row error-isolation fallback while preserving all emission-gate and NULL-timestamp checks; raised workflow `timeout-minutes` from `15` to `25`.
6. **`Daily Prices YF Refresh` (`.github/workflows/daily-prices-yf-refresh.yml`, `tools/refresh_daily_prices_yf.py`)**:
   - **What was broken**: Hardcoded `/home/eaguiar2015/...` `sys.path` caused `ModuleNotFoundError: No module named 'tools'` on GitHub runners.
   - **What changed**: Resolved repo root dynamically via `Path(__file__).resolve().parents[1]`, added `PYTHONPATH: ${{ github.workspace }}`, and updated checkout/python setup to `@v6` with `filter: blob:none`.
7. **`rsi5070-forward-snapshot.yml` & `operator-review-today.yml`**:
   - **What was broken**: Shared `concurrency: group: dashboard-publish` behind hourly 35–115m `audit-dashboard.yml` caused concurrency eviction (`cancelled`), and `operator-review-today.yml` pushed via manual `git push origin main` loops.
   - **What changed**: Isolated into independent concurrency groups (`rsi5070-forward-snapshot`, `operator-review-today`), staggered `operator-review-today.yml` to `30 7 * * *`, and standardized on `safe_push.sh`.
8. **`Secret Scan` (`.github/workflows/secret-scan.yml`, `.gitleaks.toml`)**:
   - **What was broken**: Scheduled runs used `gitleaks-action@v2` over full history on `blob:none` partial clones, triggering lazy fetches across ~19 GB of history until the 30-minute timeout.
   - **What changed**: Retained `gitleaks-action@v2` diff scan for `pull_request` events; switched `schedule`/`workflow_dispatch` to SHA256-verified Gitleaks CLI running `gitleaks dir .` (HEAD tree) + `gitleaks git . --log-opts="--since=48.hours.ago --no-merges"`.
9. **Partial-Clone (`filter: blob:none`), `TOKEN_FOR_PUSH`, & `safe_push.sh` Standardization**:
   - Updated `.github/workflows/blacklist-reconciler.yml`, `edge-stability-daily.yml`, `forward-test-new-strategies.yml`, `now-scanner.yml`, `pead-shadow-collector.yml`, `picks-now-refresh.yml`, `sign-coherence-gate.yml`, `strategy-funnel-hourly.yml`, and `swarm-pick-review.yml` to eliminate ~19 GB full-history fetches under tight timeouts and eliminate fragile custom push loops.

---

## 4. Verification

- **YAML Parsing (`yaml.safe_load`)**: All **362** workflows in `.github/workflows/*.yml` parsed without error.
- **Shell Syntax (`C:\Program Files\Git\bin\bash.exe -n`)**: All **82** shell `run:` steps across all **17** modified workflow files passed syntax validation.
- **TOML & Python Syntax**: `.gitleaks.toml` (`tomllib.loads`) and all **12** modified/added `.py` files (`py_compile`) passed.
- **Pytest Regression Suite**: Executed 10 test modules (`test_equity_price_failover.py`, `test_equity_price_failover_cache_path.py`, `test_failover_cache_staleness.py`, `test_forex_carry_g10_pilot.py`, `test_missed_opportunity_dedup.py`, `test_backfill_local_sources_batch.py`, `test_backfill_local_sources_asset_class.py`, `test_backfill_provenance.py`, `test_backfill_resolved_pnl.py`, `test_guardian_masked_failures.py`) — **81 passed in 2.79s** (mocked DB/network unit tests).
- **Live GitHub State**: Re-verified via `gh api` — **1 open issue** (`#764`) and **0 open PRs**.
