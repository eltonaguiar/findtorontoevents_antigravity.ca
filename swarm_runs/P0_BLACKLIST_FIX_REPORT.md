# P0 BLACKLIST FIX — Verification + Regression Test Report

**Date:** 2026-05-03 17:17 UTC
**Operator:** Claude Opus 4.7 (1M context) on `e:\findtorontoevents_antigravity.ca`
**Source task:** P0 surfaced by peer audit (PR #739 → `reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md` §5)

## TL;DR

The surgical 3-5 line guard at `smart_picks_engine.score_pick` and
`outcome_resolver.resolve_single_pick` was **already shipped earlier today
in PR #740** (commit `73d49c3fd78`, merged 06:30 UTC). Peer summary at
session start ("PR #740 (blacklist enforce → CRYPTO PF 1.24→1.25 measured
lift)") corroborates.

This report documents:

1. **Verification** that the fix matches the spec exactly (it does).
2. **Regression test** I added afterward (`tests/test_blacklist_enforcement.py`, 9
   tests, 9/9 PASS) — committed as `f7769d480e8` and pushed to main.
3. **Swarm review** of the original fix diff — 2/2 engines (deepseek + xai)
   verdict **MERGE**, fabrication risk **LOW**.

## Files changed

### Already shipped in PR #740 (commit `73d49c3fd78`)

- `alpha_engine/smart_picks_engine.py` — +14 lines at `score_pick` (~L754).
  Returns `{"_filter": "blacklisted_strategy"}` BEFORE scoring, after the
  existing `missing_source` provenance check. Pattern matches surrounding
  `_filter`-based filter style.
- `alpha_engine/outcome_resolver.py` — +18 lines at `resolve_single_pick`
  (~L666). Marks blacklisted picks `status=CLOSED, exit_reason=BLACKLISTED,
  pnl_pct=0.0` so they neutralize cleanly in PF/WR aggregates while remaining
  in storage for forensic visibility.

Both gates use `try/except` import guard around `BLACKLISTED_STRATEGIES`
(defensive — if config import fails for any reason, fall back to empty list
rather than crash the resolver/scorer). Both use `.strip().lower()`
case-insensitive comparison.

### New this session (commit `f7769d480e8`, pushed)

- `tests/test_blacklist_enforcement.py` — +106 lines, 9 test cases:
  - `test_blacklist_constant_contains_quan_engine_scalp` — guard-rail on the
    config constant.
  - `test_score_pick_rejects_blacklisted_strategies` — parametrized over all 3
    blacklisted strategies; asserts `_filter == "blacklisted_strategy"`.
  - `test_resolve_single_pick_neutralizes_blacklisted_strategies` — parametrized
    over all 3; asserts `status=CLOSED`, `exit_reason=BLACKLISTED`, `pnl_pct=0.0`,
    and presence of `_blacklist_reason` diagnostic field.
  - `test_score_pick_allows_non_blacklisted_strategy` — negative control
    (`dna_winner` not filtered for blacklist).
  - `test_resolve_single_pick_allows_non_blacklisted_strategy` — negative control.
- `.gitignore` — added `!swarm_runs/P0_BLACKLIST_FIX_REPORT.md` exception.

## Test results

```
$ python -m py_compile alpha_engine/smart_picks_engine.py alpha_engine/outcome_resolver.py
rc=0

$ python -m pytest -xvs tests/test_blacklist_enforcement.py
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0
collected 9 items

tests/test_blacklist_enforcement.py::test_blacklist_constant_contains_quan_engine_scalp PASSED
tests/test_blacklist_enforcement.py::test_score_pick_rejects_blacklisted_strategies[binance_smart_money] PASSED
tests/test_blacklist_enforcement.py::test_score_pick_rejects_blacklisted_strategies[hl_funding_fade] PASSED
tests/test_blacklist_enforcement.py::test_score_pick_rejects_blacklisted_strategies[quan_engine_scalp] PASSED
tests/test_blacklist_enforcement.py::test_resolve_single_pick_neutralizes_blacklisted_strategies[binance_smart_money] PASSED
tests/test_blacklist_enforcement.py::test_resolve_single_pick_neutralizes_blacklisted_strategies[hl_funding_fade] PASSED
tests/test_blacklist_enforcement.py::test_resolve_single_pick_neutralizes_blacklisted_strategies[quan_engine_scalp] PASSED
tests/test_blacklist_enforcement.py::test_score_pick_allows_non_blacklisted_strategy PASSED
tests/test_blacklist_enforcement.py::test_resolve_single_pick_allows_non_blacklisted_strategy PASSED

============================== 9 passed in 1.11s ==============================
```

## Swarm review verdict

**Output:** `swarm_runs/p0_blacklist_review/`
**Cost:** $0.0655 (cap $0.10)
**Method:** Inline-diff-injection brief — diff embedded in prompt, no `gh` calls — per `swarm_runs/PR_REVIEW_ABORTED.md` mitigation.

| Engine | Model | Verdict | Fabrication Risk |
|--------|-------|---------|------------------|
| deepseek | deepseek-v4-flash | **MERGE** | LOW |
| xai | grok-3 | **MERGE** | LOW |

Both engines flagged the same LOW-severity nit: `pnl_pct=0.0` for blacklisted
resolved picks may distort aggregate PnL if downstream code does not
exclude `exit_reason=BLACKLISTED`. Acceptance: this is intentional — the
0.0 contribution is *strictly better* than the contaminated negative PnL
that motivated the fix, and the `exit_reason` tag gives downstream
aggregators a clean opt-out hook.

deepseek noted the case-insensitive lower() set comprehension is
"redundant but harmless" if config values are already lowercase — by
inspection, they are, so it's a no-op safety belt.

xai noted potential edge cases in strategy naming (special chars / partial
matches) — accepted as a non-issue: `BLACKLISTED_STRATEGIES` is a small
exact-match set of 3 well-defined names.

## Expected blast-radius reduction

- **Today (pre-fix baseline):** 71.1% of `closed_picks.json` (5,293 / 7,445)
  carry `strategy = quan_engine_scalp`. Of those, 3,517 (post-2026-04-02)
  bypassed the blacklist and contaminated CRYPTO aggregates with
  -600.3% sum PnL / 32.7% WR over 3 weeks.
- **After fix:** new picks cannot enter the scoring pipeline if blacklisted
  (`smart_picks_engine` gate). Newly-resolved picks are neutralized
  (`outcome_resolver` gate) — the existing 5,293 historical rows are NOT
  modified per spec, but their forward contribution drops to zero on next
  resolution pass.
- **Measured (per peer at session start):** CRYPTO PF lift from 1.24 → 1.25
  in the first cycle post-merge.
- **Target:** CRYPTO PF should continue lifting toward Tier-2 (>1.5) as
  the historical contamination rolls off the dashboard's rolling window
  and only-clean picks accumulate.

## Action items

1. **Monitor `audit_dashboard/data/dashboard_data.json` at 4h / 24h / 48h /
   7d post-merge** — track `performance.asset_class_health.CRYPTO.profit_factor`
   for continued lift. If PF stalls or regresses, investigate whether the
   gate is firing (search logs for `Filtered <sym>: blacklisted strategy`).
2. **Confirm `closed_picks.json` count of `quan_engine_scalp` does NOT grow.**
   At baseline 5,293 — should remain at 5,293 (or grow only via picks already
   in flight before the fix). Periodic check command:
   ```
   python -c "import json; rows=json.load(open('alpha_engine/data/closed_picks.json'))['picks']; print('quan_engine_scalp:', sum(1 for r in rows if r.get('strategy')=='quan_engine_scalp'))"
   ```

## Verification at session-end

- `git log --oneline -1` → `f7769d480e8 test(p0): regression tests for BLACKLISTED_STRATEGIES enforcement`
- Push verification: `e1b245cb6bd..f7769d480e8  main -> main` (single rebase-loop attempt, OK)
- Swarm `_calls.jsonl` not present in this swarm tool (legacy artifact); per-engine logs at `swarm_runs/p0_blacklist_review/{deepseek,xai}.json` with HTTP 200 + retry_count=0 = HEALTHY.

## TODO / partial

None. Fix verified shipped, regression test pushed, swarm review unanimous MERGE.
