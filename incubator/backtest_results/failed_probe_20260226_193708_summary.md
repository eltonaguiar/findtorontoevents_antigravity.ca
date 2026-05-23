# Failed Strategy Robustness Probe Summary

- Source probe: `failed_probe_20260226_193708.json`
- Sweep source: `real_data_sweep_20260226_191055.json`
- Variant grid: `1h both/long/short + 1h tight + 1h wide + 4h both + 1d both`
- Probe settings: `bar_step=8`, `strategy_timeout_sec=8`

## Headline
- Candidates probed: **120**
- Total variant runs: **840**
- Strategies recovered (pass under at least one variant): **62 / 120 (51.7%)**
- Not recovered: **58**

## Recovery Mechanisms (non-base passes only)
- TP/SL tuning (`tp/sl=0.75` or `1.25`): **26**
- Direction filtering (`long-only`): **10**
- Timeframe shift (`4h`): **9**

## Unrecovered Breakdown
- All variants insufficient trades: **26**
- All variants failed risk/edge gates: **31**
- Timeout in at least one variant: **1**
- Timeout strategy: `codex_gpt5/crypto_hurst_volexpansion_breakout_v1`

## Recovered Via 4h Timeframe
- `web_ai/keltner_squeeze_breakout` | WR 66.67% | Sharpe 11.82 | DD 0.14% | trades 3
- `cursor_ai/crypto_liquidation_cluster_reversal_v1` | WR 52.38% | Sharpe 9.17 | DD 1.24% | trades 21
- `cursor_ai/funding_momentum` | WR 52.83% | Sharpe 5.90 | DD 3.54% | trades 53
- `cursor_ai/crossasset_btcspx_divergence_v1` | WR 52.94% | Sharpe 5.63 | DD 3.62% | trades 51
- `cursor_ai/social_sentiment_momentum_v1` | WR 47.17% | Sharpe 4.84 | DD 3.76% | trades 53
- `cursor_ai/defi_gov_activity_breakout_v1` | WR 47.17% | Sharpe 4.21 | DD 4.91% | trades 53
- `cursor_ai/crypto_kelly_position_sizing_v1` | WR 50.00% | Sharpe 3.23 | DD 7.04% | trades 24
- `team_alpha/crypto_kelly_adaptive_sizing_v1` | WR 50.00% | Sharpe 3.23 | DD 7.04% | trades 24
- `codex_gpt5/crypto_vwap_deviation_reversion_volfilter_v1` | WR 50.00% | Sharpe 1.94 | DD 0.88% | trades 4

## Recovered Via Long-Only
- `web_ai/crypto_soc_delta_divergence_a09_v1` | WR 70.00% | Sharpe 8.59 | DD 0.22% | trades 10
- `web_ai/crypto_soc_proxy_decoupling_a09_v1` | WR 66.67% | Sharpe 8.06 | DD 0.33% | trades 9
- `web_ai/crypto_soc_orderflow_absorption_a04_v1` | WR 60.00% | Sharpe 7.25 | DD 0.29% | trades 20
- `web_ai/crypto_soc_micro_noise_filter_a06_v1` | WR 66.67% | Sharpe 6.17 | DD 0.37% | trades 9
- `web_ai/crypto_soc_vol_expansion_index_a06_v1` | WR 62.50% | Sharpe 5.62 | DD 0.37% | trades 8
- `web_ai/crypto_soc_micro_noise_filter_a03_v1` | WR 60.00% | Sharpe 5.35 | DD 0.26% | trades 5
- `web_ai/crypto_soc_proxy_decoupling_a04_v1` | WR 50.00% | Sharpe 5.03 | DD 0.25% | trades 12
- `web_ai/crypto_soc_regime_filters_a06_v1` | WR 66.67% | Sharpe 4.38 | DD 0.57% | trades 12
- `web_ai/crypto_soc_dynamic_risk_heat_a03_v1` | WR 60.00% | Sharpe 2.31 | DD 0.26% | trades 5
- `codex_gpt5/crypto_keltner_compression_expansion_v1` | WR 46.67% | Sharpe 1.38 | DD 2.08% | trades 15

## Recovered Via TP/SL Tuning (1h both)
- `web_ai/body_ratio_reversal` | tp/sl=0.75 | WR 50.00% | Sharpe 4.06 | DD 0.85% | trades 4
- `web_ai/atr_regime_rsi` | tp/sl=0.75 | WR 45.83% | Sharpe 3.95 | DD 2.16% | trades 24
- `codex_gpt5/crypto_roc_acceleration_trend_v1` | tp/sl=0.75 | WR 69.23% | Sharpe 3.89 | DD 1.25% | trades 13
- `web_ai/crypto_soc_proxy_decoupling_a05_v1` | tp/sl=0.75 | WR 54.55% | Sharpe 3.77 | DD 0.72% | trades 11
- `web_ai/crypto_soc_delta_divergence_a03_v1` | tp/sl=0.75 | WR 66.67% | Sharpe 3.41 | DD 1.65% | trades 12
- `web_ai/crypto_soc_delta_divergence_a05_v1` | tp/sl=0.75 | WR 50.00% | Sharpe 2.95 | DD 0.73% | trades 12
- `web_ai/donchian_midline_bounce` | tp/sl=0.75 | WR 45.00% | Sharpe 2.80 | DD 1.29% | trades 20
- `codex_gpt5/crypto_bayesian_regime_transition_momentum_v1` | tp/sl=0.75 | WR 48.57% | Sharpe 2.47 | DD 0.98% | trades 35
- `web_ai/crypto_soc_orderflow_absorption_a08_v1` | tp/sl=0.75 | WR 48.00% | Sharpe 2.40 | DD 2.49% | trades 25
- `codex_gpt5/crypto_kalman_trend_residual_reversion_v1` | tp/sl=0.75 | WR 45.16% | Sharpe 2.16 | DD 3.53% | trades 31
- `web_ai/ema_slope_divergence` | tp/sl=0.75 | WR 50.00% | Sharpe 1.76 | DD 1.65% | trades 16
- `web_ai/crypto_soc_orderflow_absorption_a05_v1` | tp/sl=0.75 | WR 50.00% | Sharpe 1.61 | DD 2.01% | trades 22
- `cursor_ai/crypto_rsi_whaleconfirmed_v1` | tp/sl=0.75 | WR 50.00% | Sharpe 1.59 | DD 2.20% | trades 36
- `web_ai/ema_ribbon_compression` | tp/sl=0.75 | WR 45.76% | Sharpe 1.48 | DD 2.86% | trades 59
- `web_ai/crypto_soc_orderflow_absorption_a07_v1` | tp/sl=0.75 | WR 53.57% | Sharpe 1.02 | DD 2.45% | trades 28
- `codex_gpt5/crypto_liquidity_wick_reversal_v1` | tp/sl=1.25 | WR 80.00% | Sharpe 9.00 | DD 0.07% | trades 5
- `web_ai/crypto_soc_regime_filters_a08_v1` | tp/sl=1.25 | WR 55.56% | Sharpe 6.15 | DD 0.35% | trades 9
- `web_ai/crypto_soc_vol_expansion_index_a04_v1` | tp/sl=1.25 | WR 50.00% | Sharpe 5.22 | DD 0.35% | trades 8
- `codex_gpt5/crossasset_btceth_beta_dispersion_v1` | tp/sl=1.25 | WR 47.06% | Sharpe 5.07 | DD 1.11% | trades 17
- `web_ai/range_contraction_revert` | tp/sl=1.25 | WR 46.15% | Sharpe 4.54 | DD 2.53% | trades 13
- `web_ai/crypto_soc_micro_noise_filter_a08_v1` | tp/sl=1.25 | WR 57.14% | Sharpe 4.45 | DD 0.35% | trades 7
- `web_ai/momentum_percentile_rank` | tp/sl=1.25 | WR 50.00% | Sharpe 2.95 | DD 2.47% | trades 24
- `web_ai/drawdown_recovery_rsi` | tp/sl=1.25 | WR 46.15% | Sharpe 2.68 | DD 5.98% | trades 13
- `web_ai/zscore_mean_reversion` | tp/sl=1.25 | WR 46.67% | Sharpe 2.13 | DD 3.30% | trades 15
- `web_ai/crypto_soc_orderflow_absorption_a01_v1` | tp/sl=1.25 | WR 65.52% | Sharpe 1.67 | DD 2.79% | trades 29
- `web_ai/crypto_soc_proxy_decoupling_a08_v1` | tp/sl=1.25 | WR 50.00% | Sharpe 1.37 | DD 2.70% | trades 16

## Top Sharpe Lifts vs Baseline (1h both tp/sl=1.0)
- `web_ai/keltner_squeeze_breakout` | ΔSharpe 46.08 | ΔWR 66.67% | best `4h both tp/sl=1.0` | base `failed` (-34.26, 0.00%)
- `web_ai/body_ratio_reversal` | ΔSharpe 19.48 | ΔWR 25.00% | best `1h both tp/sl=0.75` | base `failed` (-15.42, 25.00%)
- `web_ai/crypto_soc_micro_noise_filter_a03_v1` | ΔSharpe 10.95 | ΔWR 10.00% | best `1h long tp/sl=1.0` | base `failed` (-5.60, 50.00%)
- `web_ai/crypto_soc_delta_divergence_a09_v1` | ΔSharpe 10.11 | ΔWR 11.67% | best `1h long tp/sl=1.0` | base `failed` (-1.52, 58.33%)
- `web_ai/crypto_soc_proxy_decoupling_a09_v1` | ΔSharpe 9.48 | ΔWR 12.12% | best `1h long tp/sl=1.0` | base `failed` (-1.42, 54.55%)
- `web_ai/crypto_soc_micro_noise_filter_a06_v1` | ΔSharpe 9.47 | ΔWR 6.67% | best `1h long tp/sl=1.0` | base `failed` (-3.30, 60.00%)
- `web_ai/crypto_soc_vol_expansion_index_a06_v1` | ΔSharpe 9.36 | ΔWR 6.94% | best `1h long tp/sl=1.0` | base `failed` (-3.75, 55.56%)
- `web_ai/crypto_soc_dynamic_risk_heat_a03_v1` | ΔSharpe 8.88 | ΔWR 10.00% | best `1h long tp/sl=1.0` | base `failed` (-6.57, 50.00%)
- `web_ai/crypto_soc_proxy_decoupling_a05_v1` | ΔSharpe 8.58 | ΔWR 0.00% | best `1h both tp/sl=0.75` | base `failed` (-4.80, 54.55%)
- `web_ai/crypto_soc_orderflow_absorption_a04_v1` | ΔSharpe 8.40 | ΔWR 11.85% | best `1h long tp/sl=1.0` | base `failed` (-1.15, 48.15%)
- `web_ai/crypto_soc_delta_divergence_a05_v1` | ΔSharpe 8.38 | ΔWR 0.00% | best `1h both tp/sl=0.75` | base `failed` (-5.43, 50.00%)
- `cursor_ai/crypto_liquidation_cluster_reversal_v1` | ΔSharpe 7.93 | ΔWR 15.28% | best `4h both tp/sl=1.0` | base `failed` (1.24, 37.10%)
- `codex_gpt5/crypto_roc_acceleration_trend_v1` | ΔSharpe 6.20 | ΔWR 7.69% | best `1h both tp/sl=0.75` | base `failed` (-2.31, 61.54%)
- `web_ai/crypto_soc_proxy_decoupling_a04_v1` | ΔSharpe 6.01 | ΔWR 3.85% | best `1h long tp/sl=1.0` | base `failed` (-0.98, 46.15%)
- `codex_gpt5/crossasset_btceth_beta_dispersion_v1` | ΔSharpe 5.47 | ΔWR 5.88% | best `1h both tp/sl=1.25` | base `failed` (-0.40, 41.18%)

## Recommended Pipeline Changes
- Reclassify `0 trades` outcomes as `insufficient_data`, not `backtest_failed`.
- Run a secondary auto-probe for any failed strategy: `long-only`, `tp/sl=0.75`, `tp/sl=1.25`, `4h both`.
- Promote strategy to `variant_passed` if any secondary variant passes core gates.
- Keep hard `backtest_error` for true runtime timeouts/exceptions only.