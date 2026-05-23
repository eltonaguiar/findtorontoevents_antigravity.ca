# Incubator Backtest Realism Audit (2026-02-27)

Generated: 2026-02-27 00:26 UTC

## Executive Summary
- Strategy files scanned: 225
- Meta files scanned: 184
- Latest real-data sweep rows: 180 (passed=60, failed=105)
- Code-level classification: {'synthetic_or_demo_signals': 75, 'mixed_signals': 2, 'real_data_claimed': 148}

## Provenance Coverage (Meta)
- `backtest_metrics.data_source` present: 182/184
- Numeric backtest metrics present: 153/184
- Both data source + numeric metrics: 153/184

## Interpretation
- `real_data_sweep_runner.py` uses real BTC OHLCV from SQLite (`crypto_data.db`).
- Cross-asset series (SPX/DXY/VIX) in sweep are deterministic proxies derived from BTC, not direct external market feeds.
- Many strategy files contain synthetic/demo blocks in `__main__` or test sections; this does not automatically mean production backtest metrics are synthetic, but it is a realism risk if those paths are used for validation.

## High-Risk / Needs Review (Code Signals)
- Criteria: file classified as `synthetic_or_demo_signals`, `mixed_signals`, or `unknown_no_evidence`.
- Count: 77

- synthetic_or_demo_signals: `incubator/agents/antigravity_01/crypto_vwap_volprofile_reversion_v1.py`
- mixed_signals: `incubator/agents/claude_code_01/crossasset_btcspx_corrbreakdown_v1.py`
- synthetic_or_demo_signals: `incubator/agents/codex_gpt5/crossasset_btceth_beta_dispersion_v1.py`
- synthetic_or_demo_signals: `incubator/agents/codex_gpt5/crypto_adx_pullback_trendresume_v1.py`
- synthetic_or_demo_signals: `incubator/agents/codex_gpt5/crypto_bayesian_regime_transition_momentum_v1.py`
- synthetic_or_demo_signals: `incubator/agents/codex_gpt5/crypto_choppiness_regime_switch_v1.py`
- synthetic_or_demo_signals: `incubator/agents/codex_gpt5/crypto_donchian_atr_breakout_retest_v1.py`
- synthetic_or_demo_signals: `incubator/agents/codex_gpt5/crypto_drawdown_convexity_recovery_v1.py`
- mixed_signals: `incubator/agents/team_alpha/crypto_correlation_breakdown_momentum_v1.py`
- synthetic_or_demo_signals: `incubator/agents/team_alpha/crypto_fvg_reclaim_hunter_v1.py`
- synthetic_or_demo_signals: `incubator/agents/team_alpha/crypto_kelly_adaptive_sizing_v1.py`
- synthetic_or_demo_signals: `incubator/agents/team_alpha/crypto_liquidity_sweep_absorption_v1.py`
- synthetic_or_demo_signals: `incubator/agents/team_alpha/crypto_microstructure_imbalance_v1.py`
- synthetic_or_demo_signals: `incubator/agents/team_alpha/crypto_shadow_unicorn_gate_v1.py`
- synthetic_or_demo_signals: `incubator/agents/team_alpha/crypto_volatility_contraction_fear_v1.py`
- synthetic_or_demo_signals: `incubator/agents/team_alpha/crypto_volume_profile_fvg_v1.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/adx_rising_gate.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/atr_expansion_momentum.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/body_ratio_reversal.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/bollinger_width_percentile.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/calmar_recovery_signal.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/choppiness_filter_entry.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/close_location_value.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/consecutive_down_reversal.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/crossasset_spxbtc_zscore_divergence_v1.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/cumulative_delta_proxy.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/donchian_midline_bounce.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/double_bottom_detector.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/dual_atr_regime.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/dual_timeframe_momentum.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/ema_crossover_pullback.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/ema_ribbon_compression.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/ema_slope_divergence.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/engulfing_pattern_filter.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/entropy_low_entry.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/exhaustion_candle.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/gap_fill_reversion.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/hammer_candle_filter.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/hh_hl_trend_follow.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/hurst_exponent_gate.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/inside_bar_breakout.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/keltner_squeeze_breakout.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/kurtosis_regime.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/mean_distance_reversion.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/momentum_divergence_rsi.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/momentum_percentile_rank.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/momentum_stall_reversal.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/narrow_range_nr7.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/obv_divergence.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/parabolic_stop_reversal.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/pivot_point_bounce.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/price_acceleration_gate.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/price_channel_squeeze.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/range_contraction_revert.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/range_expansion_alert.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/relative_volume_breakout.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/retest_support_level.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/return_autocorrelation.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/roc_acceleration_trend.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/rolling_sharpe_gate.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/rsi_velocity_cross.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/skewness_gate.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/sortino_gate_momentum.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/stochastic_divergence.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/supertrend_proxy.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/swing_failure_pattern.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/trend_intensity_index.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/triple_ema_alignment.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/variance_ratio_reversion.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/volatility_mean_reversion.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/volume_dry_up_breakout.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/volume_profile_poc.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/volume_spike_reversal.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/volume_weighted_rsi.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/vwap_deviation_snap.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/williams_r_extreme.py`
- synthetic_or_demo_signals: `incubator/agents/web_ai/zscore_mean_reversion.py`

## Missing `data_source` in Meta
- Count: 2
- `incubator/agents/antigravity_01/crypto_vwap_volprofile_reversion_v1.py.meta.json`
- `incubator/agents/web_ai/crossasset_spxbtc_zscore_divergence_v1.py.meta.json`
