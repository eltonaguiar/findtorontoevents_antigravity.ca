# Google Antigravity 100 Backtest Summary

- Source: `google_antigravity_100_backtest_20260226_200608.json`
- Generated: `2026-02-26T20:06:08.384517`
- Data: `crypto_data.db`, pair `BTC/USDT`, bars `1808`, bar_step `2`

## Coverage
- Target strategies: **100**
- Tested: **100**
- Missing local: **0**
- Missing on `origin/main`: **0**

## Results
- Passed: **28**
- Failed: **71**
- Timeouts: **1**
- Errors: **0**
- Insufficient trades subset: **11**

## Top Passed (Sharpe-ranked)
- `trix_zero_cross` | Sharpe 11.39 | WR 60.00% | DD 0.07% | trades 5
- `sortino_gate_momentum` | Sharpe 7.73 | WR 50.00% | DD 0.75% | trades 12
- `skewness_gate` | Sharpe 7.72 | WR 66.67% | DD 0.80% | trades 6
- `volume_breakout_regime_switch` | Sharpe 5.52 | WR 66.67% | DD 0.97% | trades 3
- `ultimate_oscillator_reversal` | Sharpe 4.94 | WR 62.50% | DD 1.95% | trades 8
- `atr_percentile_gate` | Sharpe 4.49 | WR 57.14% | DD 0.63% | trades 28
- `chandelier_exit_reversal` | Sharpe 4.43 | WR 51.72% | DD 2.13% | trades 29
- `coppock_curve_signal` | Sharpe 4.38 | WR 66.67% | DD 2.24% | trades 21
- `narrow_range_nr7` | Sharpe 3.62 | WR 54.90% | DD 4.77% | trades 51
- `hammer_candle_filter` | Sharpe 3.43 | WR 61.54% | DD 1.53% | trades 13
- `quad_ema_cross` | Sharpe 3.35 | WR 54.05% | DD 1.87% | trades 37
- `mean_reversion_momentum` | Sharpe 3.12 | WR 54.00% | DD 2.13% | trades 50
- `rsi_mean_cross` | Sharpe 3.09 | WR 50.00% | DD 3.89% | trades 20
- `engulfing_pattern_filter` | Sharpe 2.90 | WR 47.06% | DD 1.51% | trades 34
- `volume_spike_reversal` | Sharpe 2.50 | WR 57.89% | DD 1.71% | trades 19

## Failed But Near Gate (Review Candidates)
- `consecutive_down_reversal` | Sharpe 0.13 | WR 45.00% | DD 2.38% | trades 20
- `cumulative_delta_proxy` | Sharpe 0.04 | WR 44.87% | DD 4.09% | trades 78
- `avg_directional_movement` | Sharpe 2.78 | WR 44.83% | DD 2.23% | trades 29
- `hurst_exponent_gate` | Sharpe 0.04 | WR 44.80% | DD 26.92% | trades 125
- `ema_ribbon_compression` | Sharpe 0.07 | WR 45.41% | DD 15.40% | trades 229
- `ema_crossover_pullback` | Sharpe -0.50 | WR 44.44% | DD 1.20% | trades 9
- `pivot_point_bounce` | Sharpe -0.39 | WR 44.37% | DD 29.49% | trades 471
- `opening_range_breakout` | Sharpe 0.39 | WR 44.03% | DD 9.86% | trades 134
- `range_contraction_revert` | Sharpe 1.78 | WR 43.90% | DD 4.67% | trades 41
- `smoothed_momentum_crossover` | Sharpe 1.03 | WR 43.75% | DD 5.01% | trades 32
- `multi_period_rsi_confluence` | Sharpe 0.27 | WR 46.58% | DD 24.21% | trades 73
- `swing_failure_pattern` | Sharpe -0.10 | WR 43.33% | DD 6.93% | trades 60
- `calmar_recovery_signal` | Sharpe -3.75 | WR 46.67% | DD 4.90% | trades 30
- `mean_distance_reversion` | Sharpe -0.59 | WR 43.20% | DD 39.14% | trades 125
- `elder_ray_bull_power` | Sharpe 2.12 | WR 43.18% | DD 5.86% | trades 44

## Timeout
- `return_autocorrelation` | message: `Strategy exceeded timeout (25s)` | duration 25.058s

## Notes
- This run validates that the canonical 100-strategy set is backtested on real data.
- Two non-canonical extras were excluded from this exact-100 run: `crossasset_spxbtc_zscore_divergence_v1`, `fear_greed_reversion`.