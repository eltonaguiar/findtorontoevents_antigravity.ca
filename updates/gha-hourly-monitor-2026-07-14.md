# GHA Hourly Health Monitor — 2026-07-14

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5 on main):** 0 success, 5 failure, 0 in_progress (run at 11:58, 10:57, 09:56, 08:52, 07:38 UTC all failed; 9+ failures today total, 18+ failures on 2026-07-13 — persistent, not a new regression)

**Failing run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29330791428

**Failing tests (24 failures, same on Python 3.11 and 3.12):**

| Test file | Count | Root cause |
|---|---|---|
| `test_blacklist_exec_gate_enforcement.py` | 2 | `kimi_signal_tracking` absent from BLOCKED_SOURCE_SYSTEMS list; `passes_active_gate` baseline fixture broken |
| `test_blacklist_leaderboard_filter.py` | 1 | `kimi_signal_tracking` leaking through top-N ranking filter |
| `test_phase1_active_gates.py` | 20 | ALL Phase1 gate tests (DeadZone 8 + TimeOfDay 10 + Combined 2) return `False` when should return `True`; entire `Phase1GateEngine` appears broken on main |
| `test_tpsl_policy.py` | 1 | Commodity TP/SL policy default drift: expected `106.25`, got `100.5` |

Score: `24 failed, 6210 passed, 61 skipped` (both matrix legs)

**Chronic workflows:** none

**Open PRs RED (CI Tests failing):**

| PR | Title | CI Status | Recommended Action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | test(3.11) FAIL, test(3.12) FAIL | AUTHOR_FIX — same 24 tests as main; fix main first, then rebase |
| #666 | fix(resolver): B1 backfill price guard | test(3.11) FAIL, test(3.12) FAIL | AUTHOR_FIX — same root cause |
| #665 | audit(stalled-producer-detector): v2.0+2 | test(3.11) FAIL, test(3.12) FAIL | AUTHOR_FIX — ironically named; same root cause |

PRs #657 (has `[skip ci]` tag), #600, #595, #581, #564 not re-checked (checks run on branch HEAD at open time, not continuously rebased).

**Action required:** AUTHOR_FIX on main — three independent failure clusters:
1. Add `kimi_signal_tracking` to `BLOCKED_SOURCE_SYSTEMS` in `alpha_engine/emitter_discipline.py` (or wherever the intake blacklist is maintained).
2. Investigate `alpha_engine/phase1_active_gates.py` (or equivalent) — `passes_active_gate()` / `Phase1GateEngine` returning `False` for every gate scenario including env-disable and shadow-mode paths.
3. Fix commodity TP/SL policy default in `alpha_engine/tpsl_policy.py` (or equivalent) — commodity default shifted from `106.25` to `100.5`.
