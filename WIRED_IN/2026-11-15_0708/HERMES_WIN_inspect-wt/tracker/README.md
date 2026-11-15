# Prediction Tracker

Cadence scales with the prediction horizon (per the self-engineering protocol §4):

| Horizon | Cadence | File |
|---|---|---|
| ≤ 1 day (intraday/scalp) | every bar/trade | `intraday_YYYYMM.csv` (jsonl also fine) |
| 1 day – 3 months (swing/day) | daily | `predictions_tracker.csv` |
| > 3 months (position/alloc) | weekly | `weekly_report_YYYYWW.md` |

## Canonical columns (`predictions_tracker.csv`)

`timestamp_utc, asset_class, symbol, strategy_id, regime, direction, entry_price,
expected_return_pct, tp_price, sl_price, horizon_days, confidence, position_size_pct,
benchmark, benchmark_return_pct, fees_pct, slippage_pct, exit_price, exit_reason,
realized_return_pct, excess_vs_benchmark_pct, hit_1_0, run_id, notes`

## Non-negotiable rules

1. **Append-only.** Never edit a past row. Corrections are new rows with a `correction_of` note.
2. **Every row carries its benchmark.** A pick without `benchmark` + `benchmark_return_pct` is unscoreable and must be rejected at write time.
3. **Fees and slippage are recorded per row,** not applied later. Cost-adjusted return is the only return that counts.
4. **`hit_1_0`** = 1 if `realized_return_pct > 0` AND `excess_vs_benchmark_pct > 0`; else 0. Both tests, not one.
5. **Every live pick on the audit dashboard must map to a `run_id` here.** If it can't be matched, it isn't a tracked prediction — it's an anecdote.
6. **`run_id`** threads back to `experiments/<run_id>/` so the exact code + parameters that produced the pick are recoverable.

## Scoring (weekly)

- Rolling 20-pick excess return vs benchmark; report mean, t-stat, % positive
- Hit rate on `hit_1_0` (dual condition), not raw win rate
- Live vs backtest divergence — if forward PF < 0.8 × backtest PF after 30 trades, the candidate is demoted to near-miss and stops consuming capital

Use `tracker/score_tracker.py` (add when first rows exist) to compute these mechanically — never by hand.
