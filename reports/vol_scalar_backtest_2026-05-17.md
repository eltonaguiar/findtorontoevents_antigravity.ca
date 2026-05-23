# vol_scalar_cap Cohort-Replay Backtest (A3)

**Date:** 2026-05-17
**Harness:** `tools/vol_scalar_backtest.py`
**Function under test:** `alpha_engine/backtest/position_sizing.py::PositionSizer.volatility_target_size`, param `vol_scalar_cap=(lo, hi)`
**Acceptance bar:** `reports/action_items_plan_2026-05-17.md` — CAP arm must show **Sharpe lift >= +0.2** AND **MDD <= NOCAP**.

## What was tested

`vol_scalar_cap=(lo, hi)` clamps the raw inverse-vol scalar `target_vol / annualized_vol`
before the position-pct bounds. The A3 task was to build a harness that replays closed
COMMODITY + ETF picks through two sizing arms and decide whether the cap passes:

- **NOCAP** — `volatility_target_size(..., vol_scalar_cap=None)` (current production behaviour)
- **CAP**   — `volatility_target_size(..., vol_scalar_cap=(0.0, 2.0))` (recommended bounds from the docstring guard)

Each pick's realized `pnl_pct` is weighted by that arm's own `target_weight` output, then the
arm's total return, per-trade Sharpe (mean/std of the weighted-return series), and equity-curve
max drawdown are computed.

## Cohort

| field | value |
|---|---|
| source | `alpha_engine/data/closed_picks.json` |
| COMMODITY picks replayed | 354 |
| ETF picks replayed | **0 (none exist in the dataset)** |
| `annualized_vol` ATR-derived | 262 / 354 |
| `annualized_vol` per-class default | 92 / 354 |

## Results — NOCAP vs CAP

| metric | NOCAP | CAP(0.0, 2.0) | delta |
|---|---:|---:|---:|
| total return | 145.826% | 145.826% | 0.000% |
| Sharpe (per-trade) | 0.3989 | 0.3989 | +0.0000 |
| max drawdown | 39.077% | 39.077% | +0.000% |
| avg position weight | 24.886% | 24.886% | +0.000% |

**Sharpe lift: +0.0000** (bar: >= +0.2 → FAIL)
**MDD vs NOCAP:** <= NOCAP (ok)

## Verdict: INCONCLUSIVE

The cap **never bound** on this cohort, so the two arms are byte-identical and the
Sharpe-lift bar cannot be evaluated. This is a real, diagnosable result — not a harness bug.

**Why the cap never bound:** the raw inverse-vol scalar `0.15 / annualized_vol` across the
354 COMMODITY picks ranges **0.225 – 0.738 (mean 0.408)**. Every value is comfortably inside
`(0.0, 2.0)`:

- 0 picks have scalar > 2.0 → the `hi` cap (the real guard against a stale near-zero vol
  estimate blowing up a position) is never reached.
- 0 picks have scalar < 0.0 → the `lo` bound is never reached.

The `hi` cap is designed to catch a *stale near-zero vol estimate*. The COMMODITY cohort's
annualized vols are 0.20–0.67 (futures are genuinely volatile), so the scalar stays well
under 2.0. Separately, all 354 scalars exceed `max_position_pct = 0.25`, so the position-pct
clamp pins every pick at 0.25 in both arms — another reason the arms are identical.

## Data limitations (honest disclosure)

1. **No ETF picks exist.** `closed_picks.json` contains 0 rows with `asset_class == "ETF"`.
   The cohort is COMMODITY-only despite the task scoping COMMODITY + ETF. The harness handles
   ETF rows if/when they appear; today there are none.

2. **`annualized_vol` is derived, not stored.** The dataset has no `atr_14` and no
   realized-vol field. The harness derives annualized vol from daily ATR:
   `annualized_vol = (extra.atr / entry_price) * sqrt(252)`, clamped to `[0.05, 1.50]`.
   For the **92 / 354 picks (26%) with no `extra.atr`**, a per-asset-class default is used
   (COMMODITY = 0.35) and each such pick is counted and reported. A defaulted vol is a
   constant, so for those 92 picks the scalar is fixed (`0.15/0.35 ≈ 0.43`) — they cannot
   exercise the cap regardless.

3. **No stored `target_weight`.** The task referenced weighting by `target_weight`, but no
   pick carries that field. The harness uses each arm's *own* `volatility_target_size`
   output as the position weight — which is the correct cohort-replay design (it is exactly
   the quantity the cap modifies). It is not a stored historical weight.

4. **`PositionSizer.__init__` is broken** (`config.MAX_POSITION_PCT` may not exist). The
   harness bypasses `__init__` via `__new__` and sets `portfolio_value`, `min_position_pct`,
   `max_position_pct` directly, as instructed.

## Recommendation

The `vol_scalar_cap=(0.0, 2.0)` guard is **harmless** on the current COMMODITY cohort
(zero behaviour change) but its benefit is **unproven** because no historical pick triggers
it. To actually validate the +0.2 Sharpe-lift bar, the test needs a cohort that contains
stale/near-zero vol estimates (scalar > 2.0) — e.g. a regime-shift window or a synthetic
stress cohort with deliberately lagged vol. Until such data exists, ship the cap as an
opt-in sidecar (default `None`, no production behaviour change) and re-run this harness
when a qualifying cohort is available. The harness is now in place and re-runnable.

## Reproduce

```
python tools/vol_scalar_backtest.py
```
