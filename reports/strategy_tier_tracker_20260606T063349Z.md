# Strategy Tier Tracker — 2026-06-06T06:33:49.705996+00:00

Source: `audit_dashboard/data/pf_registry.json` generated `2026-06-06T03:43:54Z`

Tier thresholds (CLAUDE.md MAJOR GOALS): T1 PF>2.0/WR>55; T2 PF>1.5/WR>50; T3 PF>1.2/WR>45; min n=30 for any tier.

## COMMODITY

**Class verdict:** INSUFFICIENT_DATA (n=15)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `cftc_socrata` | 5   | 0   | 5   | 0.0   | 0.00  | INSUFF_N (n=5) |  |
| `commodity_tsmom_12m` | 4   | 1   | 3   | 25.0  | 0.62  | INSUFF_N (n=4) |  |
| `commodity_rsi_divergence` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `cta_golden_cross` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `feature_signals` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `metals_mean_reversion` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `multi_asset_copytrader` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `regime_terminal` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |

## CRYPTO

**Class verdict:** FAIL  (n=252, PF=0.95, WR=32.5%)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `copy_trader_clones` | 34  | 15  | 19  | 44.1  | 0.78  | FAIL |  |
| `copy_trader_intel` | 32  | 0   | 32  | 0.0   | 0.00  | FAIL |  |
| `crypto_liquidity_wick_reversal_v1` | 30  | 18  | 12  | 60.0  | 1.55  | T2 (Institutional) |  |
| `atr_percentile_gate` | 29  | 17  | 12  | 58.6  | 1.10  | INSUFF_N (n=29) |  |
| `UNKNOWN` | 24  | 0   | 24  | 0.0   | 0.00  | INSUFF_N (n=24) |  |
| `ml_breakout` | 21  | 0   | 21  | 0.0   | 0.00  | INSUFF_N (n=21) |  |
| `multi_period_rsi_confluence_eth` | 16  | 7   | 9   | 43.8  | 0.43  | INSUFF_N (n=16) |  |
| `battleground_luxalgo` | 10  | 6   | 4   | 60.0  | 1.43  | INSUFF_N (n=10) |  |
| `drawdown_recovery_rsi_eth` | 9   | 5   | 4   | 55.6  | 3.39  | INSUFF_N (n=9) |  |
| `beta_adjusted_residual_momentum` | 9   | 2   | 7   | 22.2  | 0.46  | INSUFF_N (n=9) |  |
| `ml_strategy_reviver_inverse` | 6   | 3   | 3   | 50.0  | 0.41  | INSUFF_N (n=6) |  |
| `copy_trader_bybit` | 5   | 0   | 5   | 0.0   | 0.00  | INSUFF_N (n=5) |  |
| `hoffman_ema_trend` | 4   | 1   | 3   | 25.0  | 0.22  | INSUFF_N (n=4) |  |
| `drawdown_recovery_rsi_sol` | 3   | 1   | 2   | 33.3  | 0.88  | INSUFF_N (n=3) |  |
| `gru_attention` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `ornstein_uhlenbeck` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `triple_supertrend` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `ag_vt_pattern_sweep` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `ai_ema_pullback` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `cnn_lite_pattern_signal` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `connors_rsi2` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `cta_golden_cross` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `drawdown_recovery_rsi_xrp` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `genome_mutation_lab` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `genome_mutations` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `inverse_ml_enhanced_BTCUSDT_15m_D` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `inverse_ml_enhanced_RENDERUSDT_4h_D` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `mega_mutation` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `obv_divergence_breakout` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `whale_accumulation_detector` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## EQUITY

**Class verdict:** T2 (Institutional)  (n=71, PF=1.84, WR=53.5%)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_copytrader` | 21  | 16  | 5   | 76.2  | 5.91  | INSUFF_N (n=21) |  |
| `regime_terminal` | 17  | 3   | 14  | 17.6  | 0.26  | INSUFF_N (n=17) |  |
| `UNKNOWN` | 15  | 11  | 4   | 73.3  | 4.92  | INSUFF_N (n=15) |  |
| `cta_replicator` | 6   | 0   | 6   | 0.0   | 0.00  | INSUFF_N (n=6) |  |
| `vt_equity_two_day_rsi_reversal` | 4   | 4   | 0   | 100.0 | —     | INSUFF_N (n=4) | no_losses |
| `momentum_rider_base` | 3   | 2   | 1   | 66.7  | 10.25 | INSUFF_N (n=3) |  |
| `cta_golden_cross` | 3   | 1   | 2   | 33.3  | 0.74  | INSUFF_N (n=3) |  |
| `stocks_ema_golden_cross` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `stocks_rsi2_pullback` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |

## ETF

**Class verdict:** INSUFFICIENT_DATA (n=18)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `cta_golden_cross` | 6   | 4   | 2   | 66.7  | 0.55  | INSUFF_N (n=6) |  |
| `etf_all_strategies` | 5   | 0   | 5   | 0.0   | 0.00  | INSUFF_N (n=5) |  |
| `etf_scanner` | 4   | 0   | 4   | 0.0   | 0.00  | INSUFF_N (n=4) |  |
| `cta_donchian_55` | 2   | 2   | 0   | 100.0 | —     | INSUFF_N (n=2) | no_losses |
| `regime_accumulation` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## FOREX

**Class verdict:** INSUFFICIENT_DATA (n=22)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 11  | 1   | 10  | 9.1   | 0.21  | INSUFF_N (n=11) |  |
| `multi_asset_copytrader` | 6   | 3   | 3   | 50.0  | 0.90  | INSUFF_N (n=6) |  |
| `cta_replicator` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `forex_zscore_200d_fade` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `regime_terminal` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## FUTURES

**Class verdict:** INSUFFICIENT_DATA (n=15)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 11  | 1   | 10  | 9.1   | 0.48  | INSUFF_N (n=11) |  |
| `futures_cross_asset_momentum` | 4   | 1   | 3   | 25.0  | 0.10  | INSUFF_N (n=4) |  |

## PENNY_STOCK

**Class verdict:** INSUFFICIENT_DATA (n=1)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

---
Read-only report. Source of truth is pf_registry.json; do not recompute PF from raw picks.