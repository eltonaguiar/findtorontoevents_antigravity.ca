# CI `test (3.11)` / `test (3.12)` Diagnosis — 2026-05-03

**Workflow:** `CI Tests` (jobs `test (3.11)` and `test (3.12)`)
**PRs investigated:** #615, #597, #608, #661
**Verdict:** **NO single shared root cause.** Each PR has independent failure modes, and `main` itself has 3 unrelated failures. Operator review required — fixes span 5+ files across 4 separate test surfaces.

---

## TL;DR

LL's hypothesis ("a single root cause likely unblocks all 4") is **falsified** by log evidence. The 4 PRs fail on 4 distinct surfaces:

| PR | Branch | Python | Failures | Failure surface |
|---|---|---|---|---|
| **#615** | `feat/b26-tradingagents-smoke-2026-05-02` | 3.12 | `test_quality_gates.py` (2) + `test_production_scanner_failover.py` (8) | normalize_exit_reason regression + `'dict' object has no attribute 'print'` |
| **#597** | `scanner-fixes-2026-05-01` | 3.11 | `test_events_staleness_filter.py` (4) + `test_quan_engine_concurrency_cap.py` (8) | Sentinel comment / concurrency cap absent in PR's branch |
| **#608** | `investigate/usdchf-concentration-2026-05-01` | 3.11 | `test_quality_gates.py` (2) | `normalize_exit_reason` returns `'LOST'`/`'WON'` instead of `'FORCE_CLOSED'` |
| **#661** | `infrastructure-modules-2026-05-02` | 3.11 | **89 collection errors**: `ImportError: cannot import name 'StrategyValidator' from 'alpha_engine.statistical_rigor'` | Missing class export in `alpha_engine/statistical_rigor.py` |

**Plus** `main` itself currently fails CI Tests (run `25287972498`):
- `tests/test_jpy_cross_buy_block.py::test_non_forex_jpy_symbol_not_blocked` (real bug — non-deterministic mutation in `passes_active_gate`)
- `tests/test_sports_endpoints_smoke.py::test_dashboard_returns_tier_breakdown` (sports DB connection failed — environmental)
- `tests/test_sports_endpoints_smoke.py::test_steam_and_arb_endpoints_respond` (sports DB connection failed — environmental)

---

## Per-PR forensic detail

### PR #615 — `test (3.12)` failures
Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25242009007/job/74029141757

```
FAILED tests/test_production_scanner_failover.py::TestFetchBinanceTicker::test_returns_correct_schema_for_known_symbol - AttributeError: 'dict' object has no attribute 'print'
... [×8 in test_production_scanner_failover.py — same AttributeError]
FAILED tests/test_quality_gates.py::test_normalize_exit_reason_lost_far_from_sl_becomes_force_closed - AssertionError: assert 'LOST' == 'FORCE_CLOSED'
FAILED tests/test_quality_gates.py::test_normalize_exit_reason_won_far_from_tp_becomes_force_closed - AssertionError: assert 'WON' == 'FORCE_CLOSED'
```

`'dict' object has no attribute 'print'` is a Python 3.12-strict failure pattern — a mock or dict was used where a logger/console was expected. Python 3.11 leniency may have hidden this. **Fix surface:** likely `production_scanner.py` printing via a dict mocked stub.

### PR #597 — `test (3.11)` failures
Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25236403157/job/74029158096

```
FAILED tests/test_events_staleness_filter.py::test_staleness_filter_sentinel_comment_present
FAILED tests/test_events_staleness_filter.py::test_staleness_filter_uses_today_iso_slice
FAILED tests/test_events_staleness_filter.py::test_staleness_filter_handles_multiple_date_fields
FAILED tests/test_events_staleness_filter.py::test_staleness_filter_runs_before_raw_events_assignment
FAILED tests/test_quan_engine_concurrency_cap.py:: [×8 of 8 tests]
```

Tests look for sentinel `Filter out past-dated events still tagged UPCOMING` in `index.html`; PR #597's branch removed/never had it. The concurrency-cap tests assert `len(out) == 1/2` but get `0` — the source under test is no-op'd on this branch. **Self-inflicted by branch state**, not shared regression.

### PR #608 — `test (3.11)` failures
Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25240556566/job/74029140858

```
FAILED tests/test_quality_gates.py::test_normalize_exit_reason_lost_far_from_sl_becomes_force_closed - AssertionError: assert 'LOST' == 'FORCE_CLOSED'
FAILED tests/test_quality_gates.py::test_normalize_exit_reason_won_far_from_tp_becomes_force_closed - AssertionError: assert 'WON' == 'FORCE_CLOSED'
```

Only 2 failures. `normalize_exit_reason` returns the raw status when the test expects `FORCE_CLOSED`. PR #608 either added a stricter test against current behavior, or removed a coercion path. Note: PR #597 PASSES these same tests — so this is a #608-specific regression, not a main-branch issue.

### PR #661 — `test (3.11)` failures (89 collection errors)
Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25247008947/job/74032897758

```
ImportError: cannot import name 'StrategyValidator' from 'alpha_engine.statistical_rigor'
[×89 across most of the test suite]
```

Verified locally: `grep -n "class StrategyValidator\|def StrategyValidator" alpha_engine/statistical_rigor.py` → **no matches**. The PR's branch presumably renamed/removed `StrategyValidator` (likely the "Track Calculator, PSR/DSR Validation, Decay Tracker" infrastructure refactor) but did not update the dozens of test modules that import it. **PR-specific, not a shared bug** — only #661 imports `StrategyValidator` from this path.

### Main branch — current CI Tests failure (run `25287972498`)
```
FAILED tests/test_jpy_cross_buy_block.py::test_non_forex_jpy_symbol_not_blocked - assert True == False
FAILED tests/test_sports_endpoints_smoke.py::test_dashboard_returns_tier_breakdown
FAILED tests/test_sports_endpoints_smoke.py::test_steam_and_arb_endpoints_respond
```

The `test_non_forex_jpy_symbol_not_blocked` failure is a real bug:
- Test: makes EQUITY-tagged EURJPY=X pick, calls `passes_active_gate(pick)` twice (default env, then `JPY_CROSS_BUY_KILL_DISABLED=1`), asserts both return same value.
- Result: `result_default=True, result_disabled=False` — the second call mutated something.
- Root cause hint: the `test_usdjpy_buy_allowed` docstring (lines 99-104) explicitly notes the time-of-day dead-zone penalty mutates `pick._penalties` (shallow copies share the list reference). Same pattern is biting `test_non_forex_jpy_symbol_not_blocked` because it reuses the same `pick` dict for both calls instead of building two fresh picks.
- Fix candidates: (a) test-side fix — build two fresh `_forex_pick(...)` instances like `test_usdjpy_buy_allowed` does, OR (b) prod-side fix — make `passes_active_gate` not mutate `pick`.

Sports failures are infra-flake (Sports DB connection refused). Not a code regression.

---

## Why no single fix unblocks all 4 PRs

- #615 needs a Python 3.12 mock fix in `test_production_scanner_failover.py` setup (or production scanner stub).
- #597 needs sentinel-comment/concurrency-cap source restored on its branch.
- #608 needs `audit_trail/quality_gates.py::normalize_exit_reason` updated to coerce LOST/WON → FORCE_CLOSED on far-from-target conditions (or its tests adjusted).
- #661 needs `StrategyValidator` re-exported from `alpha_engine/statistical_rigor.py` (or all 89 test imports updated).

These touch **5+ files across 4 modules**: `production_scanner.py`, `quality_gates.py`, `template.html` + concurrency-cap source, `statistical_rigor.py`, and the JPY test/quality-gates pair. Far beyond the ≤30 LOC / ≤2 file budget.

---

## Recommended unblock sequence (operator decides)

| Priority | PR | Action | Estimated effort |
|---|---|---|---|
| P0 | main | Fix `test_jpy_cross_buy_block.py::test_non_forex_jpy_symbol_not_blocked` (build 2 fresh picks, mirror `test_usdjpy_buy_allowed` pattern) — **3 LOC test fix** | 5 min |
| P0 | main | Quarantine `test_sports_endpoints_smoke.py` DB-dependent tests with skip-on-conn-refused (consistent with the existing `transient infra flake` skips at lines 92) | 10 min |
| P1 | #661 | Either re-export `StrategyValidator` in `alpha_engine/statistical_rigor.py`, OR rebase/merge `main` if `main` already has the class | 15-30 min |
| P1 | #608 | Investigate `normalize_exit_reason` semantics — does `main`'s function return FORCE_CLOSED for far-from-target rows? If yes, #608 broke it. If no, #608 added new tests for a feature it didn't ship | 15-30 min |
| P1 | #615 | Find the 3.12 `dict.print` AttributeError site (likely a dict-typed `console`/`logger` stub). Single-line `Mock()` fix | 10-15 min |
| P2 | #597 | Branch is stale vs main on date-staleness filter + concurrency cap. Rebase + restore sentinel | 20 min |

**No single-commit "main" fix unblocks all 4.** The single fix that DOES help is the `test_jpy_cross_buy_block.py` 3-LOC test fix, which restores `main`'s green CI baseline so each PR's own re-run shows only that PR's failures.

---

## Fix shipped: NEEDS_OPERATOR_REVIEW

Per task constraints (≤30 LOC, ≤2 files, 100% confidence): I am **not shipping a fix**. The minimum-viable path forward is per-PR remediation as outlined above. The closest single-commit candidate (the JPY test fix) only restores main; it does not unblock any of the 4 PRs.

---

## Re-verification plan

After main goes green again:
1. Each PR will re-run CI on its next push or via `gh pr update-branch <N>`.
2. Each PR will then show ONLY its own failures (the table at top).
3. None of the 4 PRs will go green from a main-only fix — each needs its own remediation commit.

**Estimated PR unblock count from a single main fix: 0/4.**
