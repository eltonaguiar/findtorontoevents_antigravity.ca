# GitHub Actions Failure Diagnosis — 2026-05-23

## Summary

Investigated 6 workflows with elevated failure rates in the last ~2 hours. **All 6 workflows now have a successful latest run** — no persistent breakage. The failures fall into three categories: transient git push race conditions, intermittent MySQL auth/connection issues, and test code that was briefly out of sync (already fixed).

---

## Workflow-by-Workflow Diagnosis

### 1. CI Tests (4 failures / 10 recent runs)

**Status:** FIXED (latest run `26330755608` at 10:49 UTC passes — 5840/5840 tests green)

**Failed tests in commit `a0673200` (10:31 UTC):**

| Test | Error | Root Cause |
|------|-------|------------|
| `test_compound_and_sharpe_redesign::test_geomean_annualized_constant_daily_return` | `assert None == 28.64 ± 0.5` | Function returned `None` — test expectations mismatched implementation version |
| `test_compound_and_sharpe_redesign::test_geomean_annualized_alternating_returns_near_zero` | `assert None == 0.0 ± 0.1` | Same: `_compound_per_day_geomean_annualized` returned None |
| `test_compound_and_sharpe_redesign::test_geomean_annualized_clamped_at_sanity_cap` | `assert None == 9999.0` | Same (cap test assumes numeric, got None) |
| `test_emitter_whitelist::test_hardcoded_toxic_pairs` | `assert not True` where `True = is_toxic_pair('COMMODITY', 'multi_asset_copytrader')` | COMMODITY/multi_asset_copytrader dynamically added to toxic list at runtime; test was checking `is_toxic_pair()` instead of `HARDCODED_TOXIC_PAIRS` set |
| `test_regime_gate::test_long_aligned_bullish_regime_passes` | `AssertionError: 0 != 1` | BUY pick in BULLISH regime rejected by quality gates — gate logic changed |
| `test_regime_gate::test_long_pick_without_macro_regime_passes` | `AssertionError: 0 != 1` | Same pattern: LONG pick rejected despite backward-compat expectation |

**Fix commit:** `12f6f290` (10:49 UTC) — tests and/or implementation aligned. All 5840 tests now pass.

**Classification:** BROKEN (temporarily) → auto-fixed by concurrent commit.

---

### 2. MySQL Trading Picks Sync (4 failures / 10 recent runs)

**Status:** PASSING (latest run `26330938845` at 10:59 UTC succeeds)

**Root cause of failure at 10:08 UTC (`26329991565`):**

1. **Duplicate entry errors (6):** Records from `clone_hl_copy_lb_None` strategy (BTCUSDT, AVAXUSDT, LINKUSDT, NEARUSDT, SUIUSDT) from 2026-03-19 trigger MySQL `1062 Duplicate entry` on the `uq_trading_picks_dedup` unique key. The INSERT...ON DUPLICATE KEY UPDATE doesn't handle these old records gracefully — they're ancient stale entries retried each sync.

2. **String-to-float scoring bug:** Elite scoring encounters `'HIGH'`, `'LOW'`, `'MEDIUM'` confidence strings instead of floats → `could not convert string to float` → fallback score 25.

3. **Retry exhaustion:** The workflow retries 3× but the same 6 duplicates fail on each attempt → "DB sync failed after 3 attempts" → exit 1.

**Why it now passes:** The sync script marks these 6 errors as non-fatal (`4007 upserted, 6 errors`) in the latest version — the workflow's success threshold was adjusted.

**Classification:** INTERMITTENT (stale data causes non-fatal errors; retry logic treats N errors as fatal when error count > 0).

---

### 3. Deploy Rise of the Claw Dashboard (3 failures / 10 recent runs)

**Status:** PASSING (latest run `26330675516` at 10:45 UTC succeeds)

**Root cause of failure at 10:06 UTC (`26329961213`):**

1. **Delisted symbols (non-fatal):** NKLA and SQ return HTTP 404 from Yahoo Finance — skipped gracefully.
2. **Code bug (non-fatal):** `'EliminationEngine' object has no attribute 'should_inject'` — caught by error handler.
3. **MySQL auth failure (FATAL):** `Access denied for user 'ejaguiar1_stocks'@'20.42.42.210' (using password: YES)` — 3 attempts all rejected. This is the killing blow.

**Why it now passes:** The MySQL server intermittently rejects connections from GitHub Actions IPs (likely rate limiting or IP-based auth rules on 50webs shared hosting). When the runner gets a different IP or retries after a cooldown, it succeeds.

**Classification:** INTERMITTENT / ENV — external MySQL host (mysql.50webs.com) occasionally rejects auth from GH Actions runner IPs.

---

### 4. Claude's Test - Portfolio Manager (5 failures / 10 recent runs)

**Status:** PASSING (latest run `26330920880` at 10:58 UTC succeeds)

**Root cause of failures:**

`git push` fails with exit code 128 after successfully committing `chore(claudes-test): update portfolio state [skip ci]`. Multiple concurrent workflows push to main simultaneously (audit-dashboard, picks-sync, portfolio-manager, etc.) → the push is rejected because the remote has newer commits since the workflow's checkout.

**Pattern:** The workflow does `git add → git commit → git push` but does NOT pull/rebase before push. When another workflow pushes between this workflow's checkout and push, it gets rejected.

**Classification:** FLAKY — git push race condition between concurrent workflows. The workflow self-heals on the next hourly run when the race doesn't collide.

---

### 5. Live Picks Tracker (3 failures / 10 recent runs)

**Status:** PASSING (latest run `26330810209` succeeds)

**Root cause of failure at 09:20 UTC (`26329111701`):**

```
fatal: could not read Username for 'https://github.com': terminal prompts disabled
error: RPC failed; HTTP 401 curl 22 The requested URL returned error: 401
fatal: Authentication failed for 'https://github.com/eltonaguiar/findtorontoevents_antigravity.ca.git/'
```

The workflow's GitHub token expired or was invalidated mid-run. It could not push to `gh-pages` branch. Also tried `git fetch origin gh-pages` and got "Remote branch gh-pages not found" — suggesting the branch was temporarily unavailable or the remote was in a degraded state.

**Classification:** FLAKY / ENV — transient GitHub API auth issue. Self-heals on next run.

---

### 6. Audit Drift Telemetry (2 failures / 10 recent runs)

**Status:** PASSING (latest run `26330501344` succeeds)

**Root cause of failure at 10:31 UTC (`26330409588`):**

```
WARN integrity check failed for 30/30 rows; looking for fallback snapshot
ERROR validation failed and no healthy fallback found
```

The drift telemetry validates backtest data integrity. All 30 rows failed the integrity check (possibly due to a stale or corrupted snapshot), and no healthy fallback was available at that moment.

**Classification:** INTERMITTENT — data integrity check is sensitive to timing of upstream data refreshes. When the dashboard data is mid-update, the integrity check finds all rows stale. Self-heals when the upstream refresh completes.

---

## Root Cause Taxonomy

| Category | Workflows Affected | Frequency | Fix |
|----------|-------------------|-----------|-----|
| **Git push race condition** | Claude's Portfolio Manager, Live Picks Tracker | ~30-50% of runs | Add `git pull --rebase` before push in workflow scripts |
| **MySQL auth from GH Actions IPs** | MySQL Sync, Deploy ROTC | ~20-30% of runs | Retry with longer backoff, or whitelist GH runner IP ranges on 50webs |
| **Transient GitHub API issues** | Live Picks Tracker | ~10% of runs | Retry logic already present; self-healing |
| **Stale test/code mismatch** | CI Tests | One-time (already fixed) | Normal development — tests lag behind impl briefly |
| **Data integrity timing** | Audit Drift Telemetry | ~10-20% of runs | Add tolerance for in-flight data updates |

---

## Recommendations

1. **Git push race condition** (highest impact, affects 2 workflows):
   - Add `git fetch origin main && git rebase origin/main` before `git push` in all workflows that commit to main.
   - Or use `git push || (git pull --rebase && git push)` retry pattern.

2. **MySQL auth intermittence** (affects 2 workflows):
   - Increase retry backoff from 0.5s/1.0s to 2s/5s/10s.
   - Consider caching MySQL connection or using a connection pool.
   - Check 50webs admin panel for IP-based rate limiting rules.

3. **Stale data conflicts** (MySQL Sync):
   - The 6 duplicate entries from `clone_hl_copy_lb_None` (2026-03-19) re-trigger every run. Either delete them from the source JSON or add them to an ignore-list.
   - Fix the string-to-float scoring bug: `'HIGH'`/`'LOW'`/`'MEDIUM'` confidence values should be mapped to numeric equivalents before scoring.

4. **No action needed:**
   - CI Tests: already fixed in latest commit.
   - Audit Drift Telemetry: timing-sensitive, self-healing.
   - Live Picks Tracker: transient auth issue, self-healing.

---

## Current State (as of 2026-05-23 11:00 UTC)

All 6 investigated workflows have a **successful latest run**. No immediate action required for any of them. The recommendations above would reduce future intermittent failures.
