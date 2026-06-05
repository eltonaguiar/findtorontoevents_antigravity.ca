# Strategy Tier Tracker — 2026-06-05T14:06:16.035046+00:00

Source: `audit_dashboard/data/pf_registry.json` generated `2026-06-05T13:54:47Z`

Tier thresholds (CLAUDE.md MAJOR GOALS): T1 PF>2.0/WR>55; T2 PF>1.5/WR>50; T3 PF>1.2/WR>45; min n=30 for any tier.

## COMMODITY

**Class verdict:** INSUFFICIENT_DATA (n=6)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `commodity_tsmom_12m` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `cta_golden_cross` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `feature_signals` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `multi_asset_copytrader` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `regime_terminal` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |

## CRYPTO

**Class verdict:** FAIL  (n=301, PF=0.99, WR=34.6%)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `UNKNOWN` | 40  | 12  | 28  | 30.0  | 3.12  | FAIL |  |
| `copy_trader_clones` | 34  | 15  | 19  | 44.1  | 0.78  | FAIL |  |
| `copy_trader_intel` | 32  | 0   | 32  | 0.0   | 0.00  | FAIL |  |
| `crypto_liquidity_wick_reversal_v1` | 30  | 18  | 12  | 60.0  | 1.55  | T2 (Institutional) |  |
| `atr_percentile_gate` | 29  | 17  | 12  | 58.6  | 1.10  | FAIL |  |
| `battleground_luxalgo` | 26  | 13  | 13  | 50.0  | 3.98  | T3 (Marginal) |  |
| `ml_breakout` | 21  | 0   | 21  | 0.0   | 0.00  | FAIL |  |
| `multi_period_rsi_confluence_eth` | 16  | 7   | 9   | 43.8  | 0.43  | INSUFF_N (n=16) |  |
| `drawdown_recovery_rsi_eth` | 9   | 5   | 4   | 55.6  | 3.39  | INSUFF_N (n=9) |  |
| `beta_adjusted_residual_momentum` | 9   | 2   | 7   | 22.2  | 0.46  | INSUFF_N (n=9) |  |
| `hoffman_ema_trend` | 5   | 1   | 4   | 20.0  | 0.19  | INSUFF_N (n=5) |  |
| `copy_trader_bybit` | 5   | 0   | 5   | 0.0   | 0.00  | INSUFF_N (n=5) |  |
| `ml_strategy_reviver_inverse` | 4   | 2   | 2   | 50.0  | 0.64  | INSUFF_N (n=4) |  |
| `drawdown_recovery_rsi_sol` | 3   | 1   | 2   | 33.3  | 0.88  | INSUFF_N (n=3) |  |
| `cnn_lite_pattern_signal` | 3   | 1   | 2   | 33.3  | 0.02  | INSUFF_N (n=3) |  |
| `cusum_regime` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `gru_attention` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `ai_ema_pullback` | 2   | 1   | 1   | 50.0  | 1.26  | INSUFF_N (n=2) |  |
| `cross_sectional_reversal` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `genome_mutations` | 2   | 2   | 0   | 100.0 | —     | INSUFF_N (n=2) | no_losses |
| `obv_divergence_breakout` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `ornstein_uhlenbeck` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `spot_perp_basis_arb` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `triple_supertrend` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `cointegration_pairs` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `community_ema_9_21_rsi_crypto` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `connors_rsi2` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `copy_trader_polymarket` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `cta_golden_cross` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `cusum_regime_scalp_equity` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `disposition_effect_contrarian` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `drawdown_recovery_rsi_xrp` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `entropy_regime_breakout` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `genome_mutation_lab` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `hoffman_keltner_expansion` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `macd_rsi_multi_tf` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `mega_mutation` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `proven_triple_ema_pullback` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `whale_accumulation_detector` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## EQUITY

**Class verdict:** INSUFFICIENT_DATA (n=45)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `regime_terminal` | 17  | 3   | 14  | 17.6  | 0.19  | INSUFF_N (n=17) |  |
| `multi_asset_copytrader` | 12  | 1   | 11  | 8.3   | 0.13  | INSUFF_N (n=12) |  |
| `stocks_rsi2_pullback` | 5   | 5   | 0   | 100.0 | —     | INSUFF_N (n=5) | no_losses |
| `regime_mild_bear` | 3   | 2   | 1   | 66.7  | 11.66 | INSUFF_N (n=3) |  |
| `regime_accumulation` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `cta_golden_cross` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `cta_replicator` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `forex_copy_trader` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `regime_mild_bull` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `stocks_ema_golden_cross` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## ETF

**Class verdict:** INSUFFICIENT_DATA (n=11)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `cta_golden_cross` | 7   | 5   | 2   | 71.4  | 0.56  | INSUFF_N (n=7) |  |
| `cta_donchian_55` | 2   | 2   | 0   | 100.0 | —     | INSUFF_N (n=2) | no_losses |
| `etf_scanner` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `regime_accumulation` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## FOREX

**Class verdict:** INSUFFICIENT_DATA (n=22)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 11  | 1   | 10  | 9.1   | 0.21  | INSUFF_N (n=11) |  |
| `cta_replicator` | 6   | 0   | 6   | 0.0   | 0.00  | INSUFF_N (n=6) |  |
| `multi_asset_copytrader` | 3   | 3   | 0   | 100.0 | —     | INSUFF_N (n=3) | no_losses |
| `regime_strong_bear` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `regime_terminal` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## FUTURES

**Class verdict:** INSUFFICIENT_DATA (n=15)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 11  | 1   | 10  | 9.1   | 0.48  | INSUFF_N (n=11) |  |
| `futures_cross_asset_momentum` | 4   | 0   | 4   | 0.0   | 0.00  | INSUFF_N (n=4) |  |

## PENNY_STOCK

**Class verdict:** INSUFFICIENT_DATA (n=1)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## UNKNOWN

**Class verdict:** INSUFFICIENT_DATA (n=6)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `vt_equity_two_day_rsi_reversal` | 4   | 4   | 0   | 100.0 | —     | INSUFF_N (n=4) | no_losses |
| `commodity_rsi_divergence` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `momentum_rider_base` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |

---
Read-only report. Source of truth is pf_registry.json; do not recompute PF from raw picks.