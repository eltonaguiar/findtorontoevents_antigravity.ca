# GHA Hourly Health Monitor — 2026-07-12

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

All 30 queried runs on `main` are failures — continuous RED streak since **2026-07-11T03:43Z** (36+ hours, 30+ runs). Most recent failing run: [29192257637](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29192257637) (2026-07-12T12:13Z, attempt 3 — already re-run twice, still failing).

**Failing step:** `Run all tests (gating — known-drift quarantined)` (step 8) on both `test (3.11)` and `test (3.12)` jobs.

**Failing tests (23 total — all AUTHOR_FIX, not infra flakes):**

| File | Test | Error |
|---|---|---|
| `tests/test_blacklist_exec_gate_enforcement.py` | `test_kimi_in_intake_blacklist` | `'kimi_signal_tracking'` not found in blacklist — was removed from blacklist after test was written |
| `tests/test_blacklist_exec_gate_enforcement.py` | `test_passes_active_gate_rejects_kimi_source` | baseline fixture fails (depends on kimi being blacklisted) |
| `tests/test_blacklist_leaderboard_filter.py` | `test_ranking_excludes_blacklisted_from_top_n` | `kimi_signal_tracking` leaked into top-N — same root cause |
| `tests/test_phase1_active_gates.py` | 20 tests (all `Phase1DeadZoneGateTests` + `Phase1TimeOfDayGateTests` + `Phase1CombinedTests`) | `AssertionError: False is not true` — `passes_active_gate()` returning `False` for all scenarios that should PASS |

**Root causes (2 distinct, both AUTHOR_FIX):**
1. **`kimi_signal_tracking` blacklist removal** — a bot commit removed this source from the blacklist config after the tests were written against it. Fix: either re-add `kimi_signal_tracking` to the blacklist or update the 3 test assertions to reflect the new intentional state.
2. **`passes_active_gate()` regression** — all Phase1 gate tests that expect the gate to PASS are returning `False`. This is a broad functional regression across `DeadZoneGate`, `TimeOfDayGate`, and combined tests. Likely caused by a bot commit that changed gate logic or default config to be overly restrictive. Fix: investigate `alpha_engine/active_gates.py` (or equivalent) for a recent change that inverted or over-tightened the gate.

**Chronic workflows:** none  
- `Sports endpoint smoke + Playwright`: 25/30 success, 5 cancelled (transient, not chronic — latest run 12:34Z is SUCCESS, 10 consecutive successes)  
- `Unified Audit Dashboard`: 27/30 success, 1 cancelled, 2 in_progress — healthy  
- No workflow meets the chronic-cancellation threshold (≥4 cancels in last 15 runs with 0 successes)

**Open PRs RED:**

| PR | Title | CI Tests | Recommended action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | `test (3.11)` ❌ `test (3.12)` ❌ (same 23-test failures as main) | AUTHOR_FIX — same root causes; fix on main first, then rebase PR |
| #666 | fix(resolver): B1 backfill price guard | `test (3.11)` ❌ `test (3.12)` ❌ (same failures) | AUTHOR_FIX — same root causes; fix on main first, then rebase PR |

Other open PRs (#665, #657, #600, #595, #581, #564, #562) were not checked but are older branches likely affected by the same main breakage.

**Action required:** OPERATOR should fix main CI.
- Fix 1 (blacklist): Determine if `kimi_signal_tracking` removal was intentional. If yes, update `tests/test_blacklist_exec_gate_enforcement.py` and `tests/test_blacklist_leaderboard_filter.py` to remove assertions about it. If not, re-add it to the blacklist.
- Fix 2 (gates): Investigate `passes_active_gate()` — find the bot commit that changed gate logic/config (first failure 2026-07-11T03:43Z) and revert or patch. The broad failure across all gate scenarios (dead zone, time-of-day, combined, env-override) suggests a global gate flag or default was changed.

**Status change vs 2026-05-22 (last run):** GREEN → **RED** (verdict changed — 50-day monitor gap; CI has been broken since 2026-07-11T03:43Z).
