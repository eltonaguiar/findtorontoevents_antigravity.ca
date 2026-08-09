# GHA Hourly Health Monitor — 2026-08-09

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 10):** 0 success, 10 failure, 0 in_progress

> All 30 returned runs (spanning 2026-08-07 23:42Z → 2026-08-09 11:53Z) are failures.
> Run attempts: most are attempt 2–4, confirming re-runs do not clear the failure.
> Latest failing run: #2098 id=31311904446 sha=f442e00a, triggered at 2026-08-09 11:53Z.

**Chronic workflows:** none (no chronic-cancellation pattern; see note on robust-edge-miner below)

**Open PRs RED:** Unable to fetch per-PR CI rollup in this run — 9 open PRs present (see PR list below). Recommend checking manually if any target main.

Open PRs (all targeting main):
- #667 feat(b5): forward-track cell selector
- #666 fix(resolver): B1 backfill price guard
- #665 audit(stalled-producer-detector): v2.0+2
- #657 feat(contract-test): cold-merge atomic gate
- #600 feat(edge): money-ready hunt
- #595 feat(validate): non-crypto intrabar replay
- #581 feat(audit): model_portfolios.html
- #564 docs: Audit Edge Hunt Action Plan
- #562 feat(audit): edge hunt session docs

**Action required:** AUTHOR_FIX — 23 tests failing in `test (3.11)` and `test (3.12)` jobs

---

### Failure root cause (run #2098, job 93246543924, step 8 "Run all tests")

```
= 23 failed, 6211 passed, 61 skipped, 85 deselected, 2 xfailed, 32 warnings in 157.28s =
```

**Group A — kimi_signal_tracking blacklist leak (3 tests, AUTHOR_FIX):**
- `test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist`
  — `'kimi_signal_tracking'` not found in the blacklist source list
- `test_blacklist_exec_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source`
  — baseline fixture returns False (gate not rejecting the source)
- `test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n`
  — `kimi_signal_tracking` leaked into top-2 result set

**Group B — Phase1 active gates all returning False (20 tests, AUTHOR_FIX):**
- All `Phase1DeadZoneGateTests`, `Phase1TimeOfDayGateTests`, `Phase1CombinedTests` in
  `test_phase1_active_gates.py` fail with `AssertionError: False is not true`
- Affects: deadzone boundary, env overrides, disable flag, confidence passthrough, TOD gate,
  shadow-mode tagging — every gate variant fails

**Secondary signal:** `alpha_engine/backtest_quant_algorithms.py` — `invalid syntax at line 1`
(coverage parse warning; not a gating failure but file is broken)

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31311904446

---

### Persistent-failure workflows (non-cancellation)

**robust-edge-miner** — 30/30 consecutive failures across 14+ days (2026-07-26 → 2026-08-09).
Runs twice daily. Does NOT trigger the chronic-cancellation threshold (all `failure`, 0 `cancelled`).
Recommend investigating separately — likely a broken dependency or missing secret.

---

### Notes

- CI Tests workflow: `.github/workflows/ci-tests.yml` (id 282011873), active
- Most recently merged PR: #622 "feat(honest-kill-switch)" merged 2026-06-24
- No status transition to track (first run of the day file); sustained RED since ≥ 2026-08-07 00:30Z
