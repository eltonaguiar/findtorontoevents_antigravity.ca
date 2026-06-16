# GHA Hourly Health Monitor — 2026-06-16

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Chronic workflows:**
- `Outcome Resolver  Validate Unresolved Picks` — **15/15 consecutive failures** spanning ~28h (2026-06-15T08:29Z → 2026-06-16T12:56Z, run IDs 27533864213–27619095117). Not cancellation — persistent `UnboundLocalError` bug. Root cause: `audit_trail/backfill_local_sources.py:189` references `is_emission_allowed` before it is bound in scope.

**Open PRs RED:** None — 23 open PRs were not assessed for individual CI status (no per-PR CI check rollup available via this run). All open PRs are from 2026-06-12/13.

**Action required:**
1. **AUTHOR_FIX (CI Tests — RED):** `tests/test_money_ready_verdict.py:331` — `test_shadow_mode_stamps_quarantine_fields` calls `money_ready_verdict()` which hits the live FRED API via `fred_macro_context.py → bond_data_fred.py:_call_with_timeout` and times out every run. Fix: mock `fetch_fred_series` / `get_macro_context` in this test so CI does not depend on outbound FRED connectivity. Failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27614885657 (Python 3.11 + 3.12 both fail identically).
2. **AUTHOR_FIX (Outcome Resolver — chronic):** `audit_trail/backfill_local_sources.py:189` — `UnboundLocalError: cannot access local variable 'is_emission_allowed' where it is not associated with a value`. The function is used but not accessible in that scope (likely a missing import, or a conditional branch that never assigns it). Failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27619095117
3. **Secondary note:** `alpha_engine/backtest_quant_algorithms.py` has `'invalid syntax' at line 1` (coverage parse failure — not the direct cause of CI failure but indicates a corrupt/placeholder file on main).

**Most recently merged PR:** #566 — `fix: P0 — kill gate wiring, pick ID double-stamp, kimi_riseoftheclaw disable` (merged 2026-06-13T17:50:40Z)

**Last monitor run before this session:** 2026-05-22 (25-day gap — first automated run in ~3.5 weeks)
