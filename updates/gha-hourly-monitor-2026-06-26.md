# GHA Hourly Health Monitor — 2026-06-26

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

> All 30 available runs (spanning 2026-06-24T19:42Z → 2026-06-26T11:54Z) are
> failures — approximately 40+ consecutive hours of unbroken CI failure on main.
> Run numbers: #1229 through #1258.

**Failing tests (24 total, both py3.11 and py3.12 matrix legs fail):**

| Test | Error |
|---|---|
| `test_blacklist_exec_gate_enforcement.py::test_kimi_in_intake_blacklist` | `'kimi_signal_tracking' not found in blacklist` |
| `test_blacklist_exec_gate_enforcement.py::test_passes_active_gate_rejects_kimi_source` | `baseline fixture fails (false is not true)` |
| `test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n` | `kimi_signal_tracking leaked into top-N` |
| `test_phase1_active_gates.py` (18 tests) | All: `AssertionError: False is not true` — gate returning False across DeadZone, TimeOfDay, Combined suites |
| `test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` | `assert 100.5 == 106.25` — wrong commodity TP/SL |

**Likely root cause:** PR #622 merged at 2026-06-24T15:45Z — "feat(honest-kill-switch): 5-commit worktree push — per-class thresholds, gotjob expansion, action plan". Commits include `fix(kill-switch): dual-source query + unblock false kills + inverse pilot + DNA engine fix` and `feat(honest-kill-switch): per-asset-class thresholds + dashboard wiring`. The per-class threshold changes broke commodity TP/SL defaults; the "inverse pilot" / gate changes caused all phase1 active gate tests to flip False; and `kimi_signal_tracking` was not added to `BLOCKED_SOURCE_SYSTEMS`.

**Failing run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28236382822

**Chronic workflows:** none detected (sports smoke 30/30 success, no cancellation-only workflows found)

**Open PRs RED:** PRs #667, #666, #665, #657, #600, #595, #581, #564, #562 all target main — all will have failing CI Tests due to the same broken main. Classification: **AUTHOR_FIX** required on main before these PRs can pass CI.

**Action required:** Author should fix main — the three test areas to patch are:
1. Add `kimi_signal_tracking` to `BLOCKED_SOURCE_SYSTEMS` (blacklist tests)
2. Investigate phase1 active gates regression (`passes_active_gate` / dead-zone gate returning `False`) — likely from the "inverse pilot" or "unblock false kills" change in PR #622
3. Fix commodity TP/SL policy defaults (target value is `106.25`, got `100.5`)

Then push a fix commit to main to unblock all open PRs.
