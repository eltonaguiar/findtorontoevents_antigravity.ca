# GHA Hourly Health Monitor — 2026-07-13

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** No standalone "CI Tests" workflow exists in this repo (362 workflows scanned; the paper_trading + alpha_engine test suite runs on PR checks only, not as a named "CI Tests" main-branch workflow). All scheduled main-branch workflows in the last 30 runs: success / in_progress (0 failures).

**Key scheduled workflow health (last 15 runs):**
- Unified Audit Dashboard (`audit-dashboard.yml`): 14 success, 1 in_progress — **GREEN**
- Sports endpoint smoke + Playwright (`sports-smoke-and-e2e.yml`): 10 success, 4 cancelled, 0 failure — **MOSTLY HEALTHY** (3 consecutive cancels Jul 12 20:30-23:33 UTC; likely overlap/superseded runs; latest completed = success at 11:23 UTC)

**Chronic workflows:** none — Sports cancellation burst (4/15) does not meet chronic criteria because latest completed run is `success`.

**Open PRs RED (test failures on `test (3.11)` + `test (3.12)`):**

- **PR #667** — `feat/b5-forward-track-tool-20260624-151517` — [feat(b5): forward-track cell selector]
  - `FAILED tests/test_select_forward_track_candidates.py::test_g_load_pick_funnel_real` — **AUTHOR_FIX**: test hardcodes `/home/eaguiar2015/findtorontoevents_antigravity.ca/` (LAN path); needs `pytest.skip` guard when file absent on CI runner
  - `FAILED tests/test_select_forward_track_candidates.py::test_h_live_data_smoke_run_only_no_write` — **AUTHOR_FIX**: same hardcoded LAN path (PR description noted this test is "conditional on machine availability" but skip guard is not present)
  - `FAILED tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` — **AUTHOR_FIX**: `assert 100.5 == 106.25` (commodity TP/SL policy mismatch; appears pre-existing on main, not caused by this PR)
  - Result: `3 failed, 6213 passed, 61 skipped` — run [28109985534](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28109985534)

- **PR #666** — `feat/b1-backfill-price-guard-2026-06-24-150302` — [fix(resolver): B1 backfill price guard]
  - `FAILED test (3.11)` + `FAILED test (3.12)` — **AUTHOR_FIX**: At minimum the same `test_tpsl_policy` commodity assertion failure; run [28108849365](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28108849365)

**Action required:** PR authors should fix:
1. `tests/test_select_forward_track_candidates.py` — add `pytest.skip` when `pick_funnel_90d.json` is absent (tests `test_g` and `test_h`). The PR description says the file is gitignored and the test is conditional on machine availability — the skip guard just needs to actually trigger on the CI runner.
2. `tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` — investigate commodity TP/SL policy mismatch (`100.5 vs 106.25`). This failure appears on both #666 and #667 branches and is likely a pre-existing main regression that needs a separate fix or the test expectation needs updating.
