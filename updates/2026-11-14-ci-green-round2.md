# 2026-11-14 — CI round 2: collection unblocked, four real failures exposed

Follow-up to `2026-11-14-ci-pandas-me-alias-and-b13-counts.md`. The first fix did
what it claimed — and then the light came on.

## What the first fix actually achieved

`freq="ME"` in `tests/test_combined_book_sleeves.py` was aborting the gating run
during **collection**, so zero tests executed. After PR #775 (merge `dcae3fdd502`):

```
collected 6720 items / 87 deselected / 10 skipped / 6633 selected
= 4 failed, 6573 passed, 64 skipped, 87 deselected, 2 xfailed in 160.32s =
```

**6,573 tests now run** where before none did. I had claimed only that it
"unblocks the suite" — that was correct, but it was not the same as green, and the
run after merging proved it: still failing, now for different reasons.

## The four failures

| test | error | cause |
|---|---|---|
| `test_combined_book_sleeves.py::test_trend_target_weights_sum_to_cap_fraction` | `ValueError: Invalid frequency: ME` | `combined_book/fetch.py:71` |
| `test_combined_book_fetch.py::test_monthly_returns_resamples_to_last_price` | same | same |
| `test_hc_after_cost_gate.py::test_stamp_null_strategy_sets_null_fields` | `assert 0.223 is None` | **my** class fallback |
| `test_hc_after_cost_gate.py::test_stamp_unknown_strategy_sets_null` | `assert 0.223 is None` | **my** class fallback |

### 1. A second `"ME"` alias, in source rather than a test

`combined_book/fetch.py:71` — `series.resample("ME").last()` — fails the same way on
the pinned pandas 2.1.4. Fixed to `pd.offsets.MonthEnd()`. There are further `"ME"`
call sites in backtest/research scripts (`comprehensive_backtest.py`,
`KIMI_RISEOFTHECLAW/rigorous_backtest.py`, `tools/research/*`, `references/*`); they
are not on the CI path and are left alone here rather than touched blind.

### 2. My own regression: the fallback sat in the wrong layer

`stamp_after_cost_fields` documents, and its tests assert, that an unindexed
strategy yields `None` in all three fields. My 2026-11-14 change put the per-class
fallback **inside** that `else` branch, so it stamped `0.223` where the contract
says `None`. Two tests caught it — which is the correct outcome for a function-level
contract.

**Fix:** the fallback moved to the caller (the per-pick normalization block), applied
only when `after_cost_net_per_trade` is still `None`:

```python
if _pick.get("after_cost_net_per_trade") is None:
    stamp_class_after_cost(_pick)
```

Production behaviour is unchanged — the field still gets a class-granularity value
instead of staying dead — while the function keeps the semantics its tests describe.

## Verification

- `pytest tests/test_hc_after_cost_gate.py tests/test_combined_book_fetch.py
  tests/test_combined_book_sleeves.py` — passes.
- The 66 stop-fill/cost-gate/COT tests still pass.
- `grep` confirms no `resample("ME")` / `freq="ME"` remains in either fixed module.
- CI confirmation is the run on this merge commit; it is the only place pandas 2.1.4
  behaviour can be observed, since this machine has 2.2.3.

## Lesson worth keeping

The first round reported "unblocks the suite" from a *local* run on a different
pandas than CI's. The honest measure of a CI fix is the CI run — and a green
collection is not a green suite. Both were stated as limitations; only the second
run could settle it.
