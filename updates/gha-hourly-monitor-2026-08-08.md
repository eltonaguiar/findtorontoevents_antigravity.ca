# GHA Hourly Health Monitor — 2026-08-08

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

All 5 most-recent CI Tests runs on `main` are `failure`. Earliest captured run: 2026-08-08T07:17Z — CI has been red all day.

| Run ID | Time (UTC) | Conclusion |
|---|---|---|
| 31256228814 | 2026-08-08T12:46Z | failure |
| 31253573364 | 2026-08-08T10:48Z | failure |
| 31250963337 | 2026-08-08T09:36Z | failure |
| 31248569498 | 2026-08-08T08:30Z | failure |
| 31245817377 | 2026-08-08T07:17Z | failure |

**Failing tests (23 total — AUTHOR_FIX):**

Failure group 1 — Blacklist gate (`tests/test_blacklist_exec_gate_enforcement.py`, `tests/test_blacklist_leaderboard_filter.py`):
- `test_kimi_in_intake_blacklist` — `kimi_signal_tracking` not found in blacklist source list
- `test_passes_active_gate_rejects_kimi_source` — baseline fixture fails (kimi source passing through gate)
- `test_ranking_excludes_blacklisted_from_top_n` — `kimi_signal_tracking` leaking into top-2 ranking

Failure group 2 — Phase1 active gates (`tests/test_phase1_active_gates.py`): 20 failures across `Phase1DeadZoneGateTests`, `Phase1TimeOfDayGateTests`, `Phase1CombinedTests` — all `AssertionError: False is not true`. Suggests `passes_active_gate()` is returning False uniformly (gate logic broken or import/config changed).

Also noted: `alpha_engine/backtest_quant_algorithms.py` has `'invalid syntax' at line 1` (coverage step warning; not the direct test failure cause but signals a corrupted file on main).

Failing run URL: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31256228814

**Chronic workflows:** none detected — sampled last 100 global runs (30 unique workflows). Zero cancellations observed. All active bots (Gainer Capture, Copy Trader, Signal Engine, QUAN ENGINE, etc.) are returning `success`. Only anomaly: `robust-edge-miner` with 1 `failure`, not a cancellation pattern.

**Open PRs (9 open as of 13:00Z):**

| PR | Title | CI status | Recommended action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector (granular asset × strategy × TF cells) | Unknown (path-gated) | HOLD — CI Tests red on main; author should fix main first |
| #666 | fix(resolver): B1 backfill price guard at resolution-write | Unknown (path-gated) | HOLD — same |
| #665 | audit(stalled-producer-detector): v2.0+2 + health-step cron wiring (branch: `fix/ci-tests-drift-reconciliation`) | Likely CI-triggered | **AUTHOR_FIX** — branch name suggests this may relate to the active CI failure; author should confirm whether these tests were already red before this PR |
| #657 | feat(contract-test): cold-merge atomic contract-test gate | Unknown | HOLD |
| #600 | feat(edge): money-ready hunt — intrabar tools + 4-agent verdict | Unknown | HOLD |
| #595 | feat(validate): non-crypto intrabar replay scaffold | Unknown | HOLD |
| #581 | feat(audit): P2-9 /audit/model_portfolios.html roster page + investigations | Unknown | HOLD |
| #564 | docs: Audit Edge Hunt Action Plan & Deep Dive | Unknown | HOLD |
| #562 | feat(audit): edge hunt session docs, pass-hunter tools | Unknown | HOLD |

**Open PRs RED:** CI Tests main is RED with AUTHOR_FIX failures. PR #665 (`fix/ci-tests-drift-reconciliation`) is the most relevant — author should verify whether the failing tests (`test_phase1_active_gates`, `test_blacklist_exec_gate_enforcement`, `test_blacklist_leaderboard_filter`) are included in that branch's scope.

**Root cause analysis:**
1. `kimi_signal_tracking` missing from blacklist — likely removed from the source list in `alpha_engine/` without updating the test fixture or the actual blacklist enforcement config.
2. `test_phase1_active_gates` 20 failures — all returning `False is not true`; `passes_active_gate()` is not passing any pick through. Could be a broken import, a config change that tightened gate defaults, or a refactor that changed the function's call signature.
3. `backtest_quant_algorithms.py` syntax error at line 1 — secondary issue; file may have conflict markers or non-Python content committed.

**Action required:** author should fix 3 test modules:
1. Add `kimi_signal_tracking` back to the blacklist (or update test expectations to match current blacklist)
2. Diagnose `test_phase1_active_gates` — likely a broken import or changed gate API
3. Inspect `alpha_engine/backtest_quant_algorithms.py` line 1 for syntax/conflict markers

**Status change vs last recorded (2026-05-22 GREEN):** GREEN → RED. Committing.
