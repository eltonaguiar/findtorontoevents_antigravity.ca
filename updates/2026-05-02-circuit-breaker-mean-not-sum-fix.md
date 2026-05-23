# 2026-05-02 — Circuit Breaker `total_drawdown_pct` Fix (Issue #623)

## What was broken

`alpha_engine/risk_controls.check_circuit_breaker()` computed `realized_7d_pct` by **summing** per-pick `pnl_pct` values across all closed picks in the trailing 7-day window, then multiplying by 100. This produces a 5-figure "drawdown" with no portfolio meaning — the sum of N independent per-pick PnLs is N times too large for any realistic equal-weight portfolio interpretation.

**Concrete impact** (Issue #623):

- `circuit_breaker.json` on main: `total_drawdown_pct: -25465.5`, `recent_closed_count: 1579`, `triggered_at: 2026-04-23`
- Real underlying data: 966 picks closed since 2026-04-23 with average `pnl_pct = -0.186`
- Old formula: `sum(-0.186 × 966) × 100 = -17,950%` (close to the file's -25,465%; difference is 7-day window vs full lookback)
- Breaker locked in EMERGENCY for 8+ days — scanner refused to generate picks

This is a **separate bug** from PR #497's phantom-HALT fix (which was in `alpha_engine/performance_alerts.py`). The `risk_controls.py` summing pattern survived PR #497.

## What changed

### `alpha_engine/risk_controls.py:97-141` — replaced sum with clipped mean

Before:
```python
recent_pnl = sum(p.get("pnl_pct", 0) for p in recent if p.get("pnl_pct") is not None)
recent_pnl_pct = recent_pnl * 100.0
```

After:
```python
pnl_values = [
    max(-1.0, min(1.0, float(p["pnl_pct"])))   # clip to [-100%, +100%]
    for p in recent
    if p.get("pnl_pct") is not None
]
recent_pnl_mean = (sum(pnl_values) / len(pnl_values)) if pnl_values else 0.0
recent_pnl_pct = recent_pnl_mean * 100.0
```

**Same change applied to `unrealized_pct`** computation a few lines down (was the same sum-not-mean bug for active picks).

### Why the clip to [-1.0, 1.0]?

Investigation of the 966 post-2026-04-23 closed picks found **58 picks with `pnl_pct` stored as a percentage** (e.g., `-2.5`) instead of a fraction (`-0.025`). Without the clip, those 58 outliers drag the mean ~30 percentage points below reality.

The mixed-unit data corruption is a separate upstream issue (some source-system writer is emitting `pnl_pct` in % units rather than fractional). Tracked but not fixed in this PR; the clip is a safety net so the breaker doesn't get distorted by it.

## Why this is the right fix (not just "reset the breaker")

Per the existing memory `feedback_circuit_breaker_stale_state_leak`: simply flipping `status: EMERGENCY → NORMAL` without recomputing the underlying number leaves bad data in place. The 2026-04-27 stale-leak incident locked `alpha_engine_fast` for ~115h via the same anti-pattern (`max_picks=0` leaked from a stale state).

This PR does the structural fix: future `check_circuit_breaker()` runs (which happen on every scanner cycle) will write the corrected mean-based number to `circuit_breaker.json`, and the next scanner run will release the EMERGENCY lock automatically *if* the corrected drawdown is above -15%.

**Important caveat**: with the corrected formula, the mean per-pick `pnl_pct` over the last 7 days is **≈-18.58%** (after the 58-pick clip applies). That's STILL below the -15% EMERGENCY threshold (`CB_EMERGENCY_PCT = -15.0`). Even with this fix, the breaker should remain EMERGENCY on the next scanner cycle — there is a real loss signal, not just a display bug.

If the on-disk -25,465.5% needs to be cleared before the next scanner run, do it via a **separate one-line PR** that re-runs `check_circuit_breaker()` against current `closed_picks.json` and writes the result. Do NOT manually flip `status` to NORMAL without recompute (that's the same anti-pattern as PR #615).

## Wiring

`check_circuit_breaker()` is called from `alpha_engine/production_scanner.py` on every scanner cycle. No additional wire-up required.

## Test plan

`tests/test_risk_controls_circuit_breaker_mean.py` — 9 tests, all passing locally:

| Test | Pins |
|---|---|
| `test_drawdown_is_mean_not_sum_of_pnl_pct` | 100 picks @ -2% → -2% drawdown (was -200%) |
| `test_drawdown_with_966_picks_at_minus_5pct_yields_minus_5pct_not_minus_4830pct` | Issue #623 scenario |
| `test_mixed_unit_pnl_pct_is_clipped_before_averaging` | 58-pick outlier pollution |
| `test_emergency_threshold_still_fires_on_real_loss` | -16% mean still trips EMERGENCY (no false-NORMAL) |
| `test_normal_status_on_winning_picks` | Sanity: +1% mean = NORMAL |
| `test_picks_outside_7d_window_excluded` | Window boundary correctness |
| `test_unrealized_also_uses_mean_not_sum` | Same fix on active picks |
| `test_empty_inputs_produce_normal_status` | No-data path |
| `test_picks_with_none_pnl_pct_skipped` | None-handling preserved |

## Cross-links

- Issue #623 — context + same-day SLA
- Memory: `feedback_phantom_halt_alert_bug` (related but separate bug, fixed by PR #497)
- Memory: `feedback_circuit_breaker_stale_state_leak` (don't naive-reset)
- PR #615 — its `circuit_breaker.json` reset (status flip only) is the wrong fix for the same issue. After this PR lands, that part of #615 should still be reverted; the resolver/stdout work in #615 still has the `__builtins__.print` bug to address separately.
- PR #497 — phantom HALT + stale-state leak fixes for `performance_alerts.py` and `circuit_breaker_aggregator.py` (different files than this PR)

## Next-up follow-ups (separate PRs)

1. **Find and fix the upstream pnl_pct unit corruption** — 58/966 picks have `pnl_pct` in percentage units. Trace via `_resolved_asset_class` or `source_system` to identify the writer and add a normalization at the source.
2. **One-shot recompute of `circuit_breaker.json`** — once this PR lands, run `python -c "from alpha_engine.risk_controls import check_circuit_breaker; from alpha_engine.outcome_resolver import _load_closed_picks; check_circuit_breaker([], _load_closed_picks())"` (or similar) to write the corrected number on demand.
3. **Consider allocation-weighted drawdown** — mean per-pick PnL is a rough approximation. A truly accurate portfolio drawdown would weight by `allocation` per pick, or compute from a portfolio equity curve. Out of scope for this safety fix.
