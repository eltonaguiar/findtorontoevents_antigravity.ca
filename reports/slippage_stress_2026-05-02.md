# Slippage Stress Test — 2026-05-02 (ALL)

## Summary

- **Closed picks loaded:** 3500
- **Strategy buckets tested (n≥5):** 89
- **Survives 2× volume:** 26 strategies ✅
- **Fails at 2× volume:** 25 strategies ⚠️
- **Already losing (paper):** 38 strategies ❌
- **Insufficient data (<n=5):** 160 strategies 🔍

> Model: Linear market impact model (conservative/worst-case). 2× volume = 2× round-trip cost. Square-root model (Almgren-Chriss) would give ~1.41× at 2× volume.

## Strategies that survive 2× volume-spike slippage

| Strategy | Class | n | Paper WR | Paper PF | Paper ΣPnL | 1× Net ΣPnL | 2× Net ΣPnL | Breakeven Mult |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| claude_ml_moderate_mut | CRYPTO | 52 | 67.31% | 3.334 | 61.01% | 45.41% | 29.81% | 3.91 |
| stocks_rsi2_pullback | EQUITY | 39 | 56.41% | 1.3062 | 9.68% | 5.78% | 1.88% | 2.48 |
| cftc_cot_commercial_signal | COMMODITY | 32 | 68.75% | 3.5036 | 38.45% | 33.65% | 28.85% | 8.01 |
| MeanReversionBB | CRYPTO | 30 | 70.0% | 3.7091 | 40.61% | 31.61% | 22.61% | 4.51 |
| quality-minus-junk | EQUITY | 18 | 61.11% | 1.4354 | 8.70% | 6.90% | 5.10% | 4.84 |
| rs-breakout-scout | EQUITY | 18 | 77.78% | 6.7002 | 46.46% | 44.66% | 42.86% | 25.81 |
| mega_mutation_macd_rsi_m048 | CRYPTO | 17 | 88.24% | 11.5276 | 78.92% | 73.82% | 68.72% | 15.47 |
| forex-rsi-ema-scout | FOREX | 15 | 53.33% | 1.9886 | 3.54% | 2.34% | 1.14% | 2.95 |
| MomentumEMA | CRYPTO | 12 | 58.33% | 2.3871 | 11.18% | 7.58% | 3.98% | 3.11 |
| intermarket-flow-scout | ETF | 12 | 58.33% | 1.7707 | 8.96% | 7.76% | 6.56% | 7.47 |
| multi_period_rsi_confluence_eth | CRYPTO | 11 | 81.82% | 5.2423 | 8.99% | 5.69% | 2.39% | 2.72 |
| price-accel-scout | EQUITY | 11 | 63.64% | 5.0829 | 37.21% | 36.11% | 35.01% | 33.83 |
| vol-contraction-scout | EQUITY | 11 | 72.73% | 3.6654 | 25.15% | 24.05% | 22.95% | 22.86 |
| donchian-stock-breakout | EQUITY | 10 | 80.0% | 6.8727 | 59.25% | 58.25% | 57.25% | 59.25 |
| rsi-divergence-scout | EQUITY | 10 | 50.0% | 2.5622 | 19.91% | 18.91% | 17.91% | 19.91 |
| fx_smart_forex_rsi2_mean_reversion | FOREX | 9 | 77.78% | 671.5333 | 2.01% | 1.29% | 0.57% | 2.79 |
| futures_momentum | BOND | 8 | 50.0% | 25.9008 | 4.94% | 4.54% | 4.14% | 12.36 |
| post-earnings-rev-scout | EQUITY | 8 | 62.5% | 1.1557 | 2.29% | 1.49% | 0.69% | 2.86 |
| ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | CRYPTO | 7 | 100.0% | inf | 19.39% | 17.29% | 15.19% | 9.23 |
| mtf-align-scout | EQUITY | 7 | 85.71% | 7.2378 | 34.41% | 33.71% | 33.01% | 49.15 |
| whale-accum-scout | EQUITY | 7 | 57.14% | 2.1221 | 13.17% | 12.47% | 11.77% | 18.82 |
| markov_zone_transition | EQUITY | 6 | 100.0% | inf | 1.98% | 1.38% | 0.78% | 3.3 |
| multi_period_rsi_confluence_xrp | CRYPTO | 6 | 100.0% | inf | 7.92% | 6.12% | 4.32% | 4.4 |
| adx-trend-scout | ETF | 5 | 100.0% | inf | 8.77% | 8.27% | 7.77% | 17.54 |
| ml_enhanced_WLDUSDT | CRYPTO | 5 | 60.0% | 2.25 | 5.00% | 3.50% | 2.00% | 3.33 |
| rs-breakout-scout | ETF | 5 | 100.0% | inf | 16.31% | 15.81% | 15.31% | 32.61 |

## Strategies that fail at 2× volume-spike (but profitable on paper)

| Strategy | Class | n | Paper ΣPnL | 2× Net ΣPnL | Breakeven Mult |
|---|---|---:|---:|---:|---:|
| forex_rsi2_mean_reversion | FOREX | 616 | 17.10% | -81.46% | 0.35 |
| luxalgo_confluence | CRYPTO | 249 | 115.07% | -34.33% | 1.54 |
| non_crypto_consensus | FOREX | 114 | 0.03% | -18.21% | — |
| strong consensus (alpha_engine, ml_crypto_pred) | CRYPTO | 92 | 31.31% | -23.89% | 1.13 |
| cta_cross_asset_tsmom | COMMODITY | 32 | 1.90% | -7.70% | 0.4 |
| fx_smart_carry_trade_momentum | FOREX | 25 | 0.30% | -3.70% | 0.15 |
| atr_percentile_gate | CRYPTO | 24 | 7.83% | -6.58% | 1.09 |
| vwap_deviation_reversion_eth_v1 | CRYPTO | 24 | 2.09% | -12.31% | 0.29 |
| signal_engine_momentum_mut | CRYPTO | 21 | 0.40% | -12.20% | 0.06 |
| vwap_deviation_reversion_sol_v1 | CRYPTO | 16 | 5.44% | -4.16% | 1.13 |
| crypto_adx_pullback_trendresume_v1 | CRYPTO | 13 | 0.28% | -7.52% | 0.07 |
| combined_confidence | FOREX | 12 | 1.65% | -0.27% | 1.72 |
| quality-minus-junk | ETF | 12 | 0.88% | -1.52% | 0.73 |
| cta_fx_multifactor | FOREX | 11 | 0.02% | -1.74% | 0.03 |
| crypto_vwap_deviation_reversion_volfilter_v1 | CRYPTO | 10 | 0.46% | -5.54% | 0.15 |
| mean_reversion_momentum | CRYPTO | 9 | 0.39% | -5.01% | 0.14 |
| mega_mutation_ema_momentum_m006 | CRYPTO | 9 | 0.72% | -4.68% | 0.27 |
| ml_enhanced_APEUSDT | CRYPTO | 8 | 4.00% | -0.80% | 1.67 |
| ml_enhanced_ADAUSDT_15m_B_lightgbm | CRYPTO | 7 | 0.94% | -3.26% | 0.45 |
| vwap_deviation_reversion_xrp_v1 | CRYPTO | 7 | 3.48% | -0.72% | 1.66 |
| adx-trend-scout | EQUITY | 6 | 0.90% | -0.30% | 1.5 |
| ml_enhanced_FETUSDT_15m_B_lightgbm | CRYPTO | 6 | 2.71% | -0.89% | 1.51 |
| RSI Divergence Scalp | CRYPTO | 5 | 1.00% | -2.00% | 0.67 |
| cci-crypto-reversal | CRYPTO | 5 | 2.33% | -0.67% | 1.55 |
| crypto_soc_delta_divergence_a01_v1 | CRYPTO | 5 | 2.82% | -0.18% | 1.88 |

## Already-losing strategies (paper PnL ≤ 0)

| Strategy | Class | n | Paper ΣPnL |
|---|---|---:|---:|
| futures_momentum | COMMODITY | 504 | -19.77% |
| quan_engine | CRYPTO | 314 | -24.02% |
| unknown | CRYPTO | 77 | -46.94% |
| forex_carry_momentum | FOREX | 66 | -26.96% |
| cta_commodity_momentum_term | COMMODITY | 46 | -4.29% |
| ensemble | CRYPTO | 45 | -4.73% |
| crypto_kalman_trend_residual_reversion_v1 | CRYPTO | 39 | -1.73% |
| macd_rsi_confluence | CRYPTO | 36 | -12.00% |
| crypto_mtf_ema_slope_alignment_v1 | CRYPTO | 35 | -4.91% |
| cta_cross_asset_tsmom | FOREX | 27 | -0.60% |
| cta_golden_cross_200 | COMMODITY | 26 | -0.02% |
| crypto_choppiness_regime_switch_v1 | CRYPTO | 19 | -4.43% |
| gainer_compression_relaxed_mut | CRYPTO | 17 | -13.96% |
| goldmine_6x_consensus | EQUITY | 17 | -58.71% |
| battleground_ml_relaxed_mut | CRYPTO | 15 | -14.50% |
| cot_positioning | COMMODITY | 15 | -4.37% |
| rapid_momentum_filter_mut | CRYPTO | 15 | -5.93% |
| rapid_rsi_filter_mut | CRYPTO | 11 | -1.50% |
| unknown | FOREX | 11 | -1.70% |
| quality-momentum-scout | EQUITY | 10 | -0.34% |
| crypto_shortterm_nr_er_adx_ignition_v1 | CRYPTO | 9 | -1.90% |
| ml_enhanced_TIAUSDT | CRYPTO | 8 | -6.00% |
| AuditEnsemble_LONG | CRYPTO | 7 | -5.91% |
| extreme_fear | EQUITY | 7 | -1.50% |
| battleground_rsi_no_regime_mut | CRYPTO | 6 | -7.05% |
| keltner_compression_expansion_xrp_v1 | CRYPTO | 6 | -3.56% |
| macd-hidden-div-scout | EQUITY | 6 | -9.98% |
| ml_enhanced_STRKUSDT_15m_D_ensemble_stack | CRYPTO | 6 | -5.63% |
| rsi_bounce | CRYPTO | 6 | -8.75% |
| betting-against-beta | BOND | 5 | -1.93% |
| call-surge-scout | EQUITY | 5 | -13.20% |
| connors_rsi2 | COMMODITY | 5 | -2.39% |
| crypto_soc_orderflow_absorption_a01_v1 | CRYPTO | 5 | -3.76% |
| goldmine_5x_consensus | EQUITY | 5 | -0.31% |
| intermarket-flow-scout | EQUITY | 5 | -0.99% |
| ml_enhanced_CHZUSDT | CRYPTO | 5 | 0.00% |
| ml_enhanced_DOGEUSDT_15m_D_ensemble_stack | CRYPTO | 5 | -3.92% |
| smart_money_accumulation | EQUITY | 5 | -18.93% |

---
*Generated by `tools/slippage_stress_test.py` — 2026-05-02T10:33:12.609231+00:00*

> OPT-IN SIDECAR. Wiring plan: dashboard_generator.py → picks.slippage_stress payload section in B14-dashboard-panel PR (target: 2026-05-16).