# Fix: Pre-Existing CI Failures Blocking B10 UEPS KPI PR

**Date:** 2026-05-21  
**Branch:** `fix/preexisting-ci-failures-2026-05-21`  
**Scope:** CI configuration + test isolation  
**Related PR:** #1292 (B10 UEPS KPI panel)

## Problem

Five pre-existing test failures blocked PR #1292 (`B10: UEPS KPI panel`) from
merging. These failures are unrelated to B10 changes — they existed on main but
were invisible because CI's path filter (`tests/`, `paper_trading/**`, etc.) is
rarely triggered by data-only commits. When B10 touched `tests/test_dashboard_generator.py`,
CI ran and surfaced all five.

### Failure 1–3: `TestIntegration` in `tests/test_failover_system.py`

The `TestIntegration` class makes live API calls to yfinance, CoinGecko, and
Binance. In GitHub Actions (Ubuntu runner) these return HTTP 403 Forbidden —
the CI sandbox has no allow-listed external API access.

The class already carries `@pytest.mark.integration`. The CI workflow
(`ci-tests.yml`) previously ran pytest without a marker filter, so integration
tests always ran and always failed.

### Failure 4–5: `TestMoneyReadyVerdict` in `tests/test_money_ready_verdict.py`

Two tests (`test_money_ready_high_edge`, `test_m070_diversified_symbols_allow_money_ready`)
feed synthetic picks (WR=80%, PF=10, n=500) and assert verdict is
`MONEY_READY` or `WATCH`. They started failing after `_MDD_GATE_ENFORCE` was
set to `True` (2026-05-19, swarm-settled Q1 verdict).

Root causes (compound):
1. **Artificial pick ordering** — `_make_picks()` placed all 400 wins before
   100 losses. The resulting equity curve peaks at win 400 then drops for 100
   consecutive losses → rolling MDD = 88%, far above the COMMODITY 55%
   threshold.
2. **Unpatched `_load_dashboard_health`** — real dashboard data contains
   COMMODITY registry MDD ≈ 59% (also above threshold). Tests that patched
   `_load_picks` and `_load_blocked` but not `_load_dashboard_health` let live
   registry data bleed into what should be isolated unit tests.

## Fix

### `ci-tests.yml`

Added `-m "not integration and not network"` to the pytest invocation.
Integration and network tests require live API access; they belong in a
separate cron workflow, not the per-PR gate.

### `tests/test_money_ready_verdict.py`

Two changes:

1. **`_make_picks()` now shuffles with `random.Random(42)`** — wins and losses
   are interspersed, producing a realistic equity curve (rolling MDD ≈ 8%
   for the 80/20 mix). The seed is fixed for reproducibility.

2. **`test_money_ready_high_edge` and `test_m070_diversified_symbols_allow_money_ready`**
   add `with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):`
   — prevents live registry MDD data from contaminating verdict logic in unit
   tests. Pattern follows `test_blocked_strategies_excluded` (already had this
   mock since line 63).

## Verification

```
python -m pytest tests/ paper_trading/tests/ alpha_engine/tests/ tools/tests/ \
  -m "not integration and not network" -q
# → 5833 passed, 0 failed (Python 3.11.15, 2026-05-21)

python -m pytest tests/test_money_ready_verdict.py -v
# → 43 passed
```

## Next step

Once this PR merges, PR #1292 (B10) should have its branch updated to include
this fix — then CI should pass and B10 is ready for human review and merge.
