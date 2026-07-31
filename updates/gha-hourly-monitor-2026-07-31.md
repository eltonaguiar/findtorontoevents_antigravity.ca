# GHA Hourly Health Monitor — 2026-07-31

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

Runs (newest first, all on today 2026-07-31):
- `30632178900` failure — 12:51 UTC sha `11d8f7c9` — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30632178900
- `30628100606` failure — 11:44 UTC sha `51dc8fca`
- `30621595956` failure — 09:53 UTC sha `6aa22286`
- `30614234938` failure — 07:51 UTC sha `6f654cf3`
- `30608797292` failure — 06:08 UTC sha `503f624f`

**Failing tests (23 failed, identical on Python 3.11 and 3.12):**

Group 1 — Blacklist regression (`kimi_signal_tracking` missing from blacklist):
- `test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist` — `'kimi_signal_tracking' not found in [...]`
- `test_blacklist_exec_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source` — `False is not true`
- `test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n` — `top-2 leaked: {'kimi_signal_tracking', 'legit_a'}`

Group 2 — Phase1 gates regression (20 tests all return `False is not true`):
- All of `Phase1DeadZoneGateTests` (8 tests), `Phase1TimeOfDayGateTests` (9 tests), `Phase1CombinedTests` (2 tests in `test_phase1_active_gates.py`) — `passes_active_gate()` returning wrong value for all gate configurations.

Additional drift-step errors:
- `test_audit_metric_invariants.py::test_headline_total_pnl_is_the_compounded_value` — no collectors found (test renamed/deleted)
- `test_confidence_calibrator.py::CalibratorContractTests::test_no_op_when_flag_unset` — not found

**Chronic workflows:** None detected in 30-run main-branch sample. Full per-workflow scan skipped (362 active workflows; no per-workflow anomalies observed in sample).

**Open PRs RED:**
- **#667** (`feat/b5-forward-track-tool`) — test(3.11)+test(3.12) FAILURE → AUTHOR_FIX (same blacklist+phase1 regression)
- **#666** (`fix/b1-backfill-price-guard`) — test(3.11)+test(3.12) FAILURE → AUTHOR_FIX
- **#665** (`fix/ci-tests-drift-reconciliation`) — test(3.11)+test(3.12) FAILURE → AUTHOR_FIX
- **#600** (`worktree-equity-reachability-tp`) — test(3.11)+test(3.12) FAILURE → AUTHOR_FIX
- **#581** (`feat/minimax-next-steps-batch`) — test(3.11)+test(3.12) FAILURE → AUTHOR_FIX
- **#595** (`feat/intrabar-replay-noncrypto`) — no test job ran; scan/gitleaks/grep all pass
- **#657** (`feat/contract-test-cold-merge`) — no check runs found

**Action required:** operator/author should fix two independent regressions on main:
1. **`kimi_signal_tracking` removed from blacklist** — check `alpha_engine/blacklist.py` (or wherever the intake blacklist lives) and restore the entry; likely removed in a recent commit after sha `503f624f`.
2. **Phase1 gates broken** — `passes_active_gate()` returning `False` for all DeadZone + TimeOfDay tests. Likely a recent refactor of `alpha_engine/active_gates.py` or `smart_picks_engine.py` broke the gate logic (or env flag changed default). Check commits between `503f624f` and `11d8f7c9` on 2026-07-31.
