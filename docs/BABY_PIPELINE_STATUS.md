# Baby Strategies Pipeline Status

**Generated programmatically at 2026-04-14 12:15 UTC from `baby_strategies/*.meta.json`. Do not edit manually.**

## Summary

- Strategies inventoried: **34**
- Wired into scanner: **0**
- In graveyard: **0**
- With real backtest results: **24**
- Profit factor ≥ 1.5 in backtest: **5**
- Non-strategy files excluded (runners/wrappers/framework): **8**

## Schema Note

The `.meta.json` schema does **not** contain an `asset_class` field — the original generator that reported "UNKNOWN" for every row was reading a key that isn't in the data. Asset class is not tracked per baby strategy at rest; it is inferred at runtime from the symbols the strategy chooses to emit. See `docs/ANTIGRAVITY_CROSSCHECK_2026-04-14.md`.

## Pipeline Inventory

| Strategy | Status | Type | Wired | WR | PF | Sharpe | N | Updated | Grave |
|---|---|---|---|---|---|---|---|---|---|
| `liquidation_cascade_contrarian` | awaiting_backtest | auto_detected | · | 100.0% | 999.00 | 0.00 | 1 | 2026-03-29 | · |
| `vol_scaled_keltner` | backtest_passed | auto_detected | · | 75.0% | 20.96 | 7.45 | 8 | 2026-03-29 | · |
| `multi_timeframe_ema_cloud` | backtest_passed | auto_detected | · | 72.4% | 6.95 | 7.46 | 29 | 2026-03-29 | · |
| `regime_sentinel_composite` | backtest_passed | auto_detected | · | 50.0% | 2.56 | 3.73 | 12 | 2026-03-29 | · |
| `keltner_rsi_confluence` | backtest_failed | auto_detected | · | 33.3% | 1.71 | 3.47 | 3 | 2026-03-29 | · |
| `moving_average_slope_momentum` | backtest_passed | auto_detected | · | 56.4% | 1.33 | 1.81 | 94 | 2026-03-29 | · |
| `rsi_pairs_arbitrage` | backtest_failed | auto_detected | · | 42.3% | 1.27 | 1.29 | 130 | 2026-03-29 | · |
| `logistic_microstructure` | backtest_failed | auto_detected | · | 46.8% | 1.14 | 0.62 | 62 | 2026-03-29 | · |
| `championship_strategies` | backtest_failed | auto_detected | · | 29.1% | 0.66 | -2.13 | 55 | 2026-03-29 | · |
| `adaptive_bollinger_momentum` | backtest_failed | auto_detected | · | 40.0% | 0.56 | -3.41 | 15 | 2026-03-29 | · |
| `volatility_regime_breakout` | backtest_failed | auto_detected | · | 44.4% | 0.47 | -4.43 | 9 | 2026-03-29 | · |
| `kama_volatility_adaptive` | backtest_failed | auto_detected | · | 25.0% | 0.46 | -6.25 | 4 | 2026-03-29 | · |
| `connors_r4_mean_reversion` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 1 | 2026-03-29 | · |
| `keltner_channel_reversion` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `price_roc_deep_dip_strategy` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `price_roc_mean_reversion_strategy` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `price_roc_quick_scalp_strategy` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `price_roc_slow_smoother_strategy` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `price_roc_trend_aligned_strategy` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `price_roc_vol_gate_strategy` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `rl_adaptive_strategy` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `stochastic_rsi_divergence` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `vwap_rsi_institutional` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `williams_percent_r_extreme` | awaiting_backtest | auto_detected | · | 0.0% | 0.00 | 0.00 | 0 | 2026-03-29 | · |
| `ait_manus_composite` | draft — not wired into scanner; requires forward-validation before promotion | composite | · | — | — | — | — | 2026-04-14 | · |
| `hoffman_new_strategy` | awaiting_backtest | auto_detected | · | — | — | — | 0 | 2026-03-29 | · |
| `hoffman_winning_combos` | awaiting_backtest | auto_detected | · | — | — | — | 0 | 2026-03-29 | · |
| `inverse_wrapper` | draft — not wired into scanner; forward-validate before activating | transformer | · | — | — | — | — | 2026-04-14 | · |
| `prop_firm_classics` | awaiting_backtest | auto_detected | · | — | — | — | 0 | 2026-03-29 | · |
| `prop_scalper_bb_squeeze` | awaiting_backtest | auto_detected | · | — | — | — | 0 | 2026-03-29 | · |
| `prop_scalper_orderflow` | awaiting_backtest | auto_detected | · | — | — | — | 0 | 2026-03-29 | · |
| `prop_scalper_vwap_reversion` | awaiting_backtest | auto_detected | · | — | — | — | 0 | 2026-03-29 | · |
| `rsi_div_scalper` | awaiting_backtest | auto_detected | · | — | — | — | 0 | 2026-03-29 | · |
| `supertrend_multi_timeframe` | awaiting_backtest | auto_detected | · | — | — | — | 0 | 2026-03-29 | · |

## Excluded Files (non-strategy runners / wrappers / framework code)

- `backtest_forward_proven`
- `backtest_framework_runner`
- `backtest_framework_runner_v2`
- `backtest_new_variations`
- `backtest_new_variations_proper`
- `forward_proven_variations`
- `strategy_framework_wrappers`
- `strategy_framework_wrappers_v2`

---
*Generated by `scripts/generate_baby_pipeline_status.py`.*
