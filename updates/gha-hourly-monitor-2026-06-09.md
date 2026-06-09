# GHA Hourly Health Monitor — 2026-06-09

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

> All 30 sampled runs on main are failure (earliest in sample: 2026-06-06T21:41Z). Failure has been continuous for ~15+ hours today (first run at 03:04 UTC, latest at 12:01 UTC).

**Chronic workflows:** none

> Scanned: CI Tests, Claude Gainer ML Live Scanner, Conflict Marker Check, Sports endpoint smoke + Playwright. All non-CI workflows healthy with 100% success rates and recent completions within the last 48h.

**Open PRs RED:** none

> 1 open PR: #553 "feat(picks-now): multi-factor quant screener". Its check runs (security scans, drift) are all green. CI Tests does not run against this PR's head commit — no CI Tests failure attributed here.

**Failing tests (29 failed, 6127 passed — run 27204694560 @ 12:01 UTC):**

| File | # Failures | Pattern |
|---|---|---|
| `tests/test_money_ready_verdict.py` | 7 | M-070 concentration gate: verdict returns `NOT_READY` when `WATCH`/`MONEY_READY` expected |
| `tests/test_mysql_sync_category_inference.py` | 7 | Category normalization: code emits `'CRYPTO'` (uppercase) but tests expect `'crypto'` (lowercase) |
| `tests/test_quality_gates.py` | 2 | `FOREX_HARD_DISABLE` not defaulting ON; `cta_replicator` FOREX not blocked |
| `tests/test_ns_c_e_exec_gate_filters.py` | 1 | `FOREX_HARD_DISABLE` env read returns `None` instead of truthy |
| `tests/test_pf_registry_tournament_db.py` | 1 | Tournament loader: `assert 0 == 2` |
| `tests/test_stocks_7_classifier_override.py` | 1 | `BTCUSDT` tag: `'CRYPTO'` vs expected `'crypto'` |

**Secondary issue:** `alpha_engine/backtest_quant_algorithms.py` has an `invalid syntax` at line 1 (caught by coverage parser — not the pytest failure cause but warrants immediate fix).

**Root cause classification: AUTHOR_FIX**

Two distinct failure clusters:
1. **Case normalization regression** — something changed asset-class/category strings to uppercase (`'CRYPTO'` → `'crypto'`). Seven tests in `test_mysql_sync_category_inference.py` and `test_stocks_7_classifier_override.py` all show the same `'CRYPTO' == 'crypto'` mismatch. Either the production code was changed to emit uppercase, or the tests were written with the wrong expectation. Most likely a PR normalized category strings without updating tests (or vice versa).
2. **Gate/verdict logic regression** — `FOREX_HARD_DISABLE` defaults changed, and the M-070 money-ready concentration gate is returning `NOT_READY` instead of `WATCH` for scenarios that should be allowed through. Likely the same PR that added PEAD shadow cron + equity blocks (#552, merged 2026-06-05) altered gate defaults or concentration thresholds.

**Earliest failure in sample:** run 27020654009 at 2026-06-06T21:41Z — the day after PR #552 merged (2026-06-05T14:42Z). Strongest suspicion: PR #552 introduced the regression.

**Most recently merged PR:** #552 "feat(ops): PEAD shadow cron + EQUITY dragger blocks" — merged 2026-06-05T14:42Z (eltonaguiar)

**Action required:** Author should fix main.

Fix #553 depends on main being green first (PR is only 3 days old with no CI Tests gate on it). Priority fixes:
1. Fix `alpha_engine/backtest_quant_algorithms.py` syntax error at line 1
2. Reconcile category string case (`'CRYPTO'` vs `'crypto'`) across production code and tests
3. Restore `FOREX_HARD_DISABLE` default-ON behaviour
4. Verify M-070 money-ready concentration gate thresholds match test expectations

**Run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27204694560
