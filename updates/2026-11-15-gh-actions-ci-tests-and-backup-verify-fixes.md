# GH Actions Fixes — CI Tests + Verified-pilot false-failure

**Date:** 2026-11-15
**Author:** Kilo (wire-fix-ghactions-pr-issues-v3)

## What was broken

`CI Tests` failed on every push with 8 deterministic assertion failures (not a hang,
not a timeout):

- `tests/test_m097_book_direction_conflict.py` — 7 of 8 tests
- `tests/test_dashboard_generator.py::test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive`

All failed with `assert False is True`: `passes_active_gate()` returned `False` when the
tests expected `True`.

## Root cause

Both tests use **CRYPTO LONG** fixtures but did not neutralize the cross-cutting
CRYPTO-LONG block gates that default ON in CI. In the CI environment
`CRYPTO_PRODUCTION_BLOCK_LONG=1` (repo variable) and/or M-036b
`CRYPTO_BUY_DIRECTION_GATE_ENABLED` are set, so `passes_active_gate()` rejected the
fixture *before* it reached the gate under test.

`tests/conftest.py` neutralizes these gates via `os.environ.setdefault(..., "0")`, but
`setdefault` is a no-op when the outer environment already sets them — which is exactly
what happens in CI (repo variable `CRYPTO_PRODUCTION_BLOCK_LONG=1`). Reproduced locally:

```
CRYPTO_PRODUCTION_BLOCK_LONG=1 python3 -m pytest tests/test_m097_book_direction_conflict.py
# → 7 failed, 1 passed  (same signature as CI)
```

## What changed

### `tests/test_m097_book_direction_conflict.py`
`_common_env(monkeypatch)` now also neutralizes the CRYPTO LONG gates so the fixture
isolates M-097 (mirrors `test_blacklist_exec_gate_enforcement._NEUTRALIZE` and
`test_phase1_active_gates._ClearPhase1Env`):

- `CRYPTO_PRODUCTION_BLOCK_LONG`, `CRYPTO_PRODUCTION_BLOCK_LONG_OVERRIDE`,
  `CRYPTO_BUY_DIRECTION_GATE_ENABLED`, `CRYPTO_SIZED_LONG_BLOCK`,
  `CRYPTO_UTC_HOUR_FILTER`, `ML_CRYPTO_PRED_LONG_REJECT`, `BTC_BEAR_LONG_REJECT`
  → all set to `"0"` via `monkeypatch.setenv`.

### `tests/test_dashboard_generator.py`
`test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive` now accepts
`monkeypatch` and neutralizes the same CRYPTO LONG gates before the assertion.

## Verification

- `CRYPTO_PRODUCTION_BLOCK_LONG=1 CRYPTO_BUY_DIRECTION_GATE_ENABLED=1 python3 -m pytest tests/test_m097_book_direction_conflict.py tests/test_dashboard_generator.py::test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive -q`
  → **9 passed** (previously 7 failed under the same env).
- `python3 -m pytest tests/test_m097_book_direction_conflict.py tests/test_dashboard_generator.py tests/test_crypto_gates_p0.py tests/test_blacklist_exec_gate_enforcement.py tests/test_phase1_active_gates.py -q`
  → **94 passed, 10 subtests passed** (no regression).

## Already fixed by peers (not part of this change)

During this session, parallel PRs landed and were merged/opened that cover the other
breakages — no duplication here:

- PR **#789** (merged to `main`): `backup-verify.yml` (fetch `dashboard_data.json` from
  production + issue dedup), `qa-market-validation.yml` API keys, snapshot-push rebase,
  Playwright `ubuntu-24.04` runners, `actions-failure-guardian`.
- PR **#790** (open): backup-verify dedup + forward-test push serialization + FTP cert.
- PR **#788** (open): the GHA/PR/issue audit deliverable + per-class profitability plan.

## Not done (deferred to owner)

- The 5 quote-chain API secrets (`FINNHUB_API_KEY`, `TIINGO_API_KEY`,
  `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`) required by
  `qa-market-validation.yml` (per user instruction to defer secrets).
- Secret rotation (5 open monthly reminders).

## Fix 2 — `Verified pilot daily` false failure on strategy admission

**Root cause:** `tools/run_verified_pilots_daily.py` runs
`tools/strategy_admit.py --strategy etf_dual_momentum --asset-class ETF --write` as one
of its steps, and gates the whole workflow on `all(returncode == 0)`. `strategy_admit.py`
exits `1` when the strategy is **REJECTED** — a legitimate, expected daily outcome (the
profitability audit found 0 strategies pass the 10-gate proof protocol). The workflow
therefore failed every night (`Wrote .../verified_pilots_daily_latest.json ok=False`,
exit 1), even though every pilot and stats step ran cleanly.

**Fix:** mark the `strategy_admit.py` step as non-gating (`gating=False`). The admission
verdict is a report, not a pipeline step; it stays visible in `reports/verified_pilots_daily_latest.json`
(returncode + stderr preserved) but no longer fails the workflow. Real pilot/stats crashes
still fail it (they remain gating).

**Verified:** `python3 -c "import ast; ast.parse(open('tools/run_verified_pilots_daily.py').read())"` OK.
