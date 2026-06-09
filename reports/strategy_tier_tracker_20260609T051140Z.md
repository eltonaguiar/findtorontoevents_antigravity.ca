# Strategy Tier Tracker — 2026-06-09T05:11:40.392500+00:00

Source: `audit_dashboard/data/pf_registry.json` generated `2026-06-09T04:46:43Z`

Tier thresholds (CLAUDE.md MAJOR GOALS): T1 PF>2.0/WR>55; T2 PF>1.5/WR>50; T3 PF>1.2/WR>45; min n=30 for any tier.

## BOND

**Class verdict:** INSUFFICIENT_DATA (n=1)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `bond_tips_breakeven` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |

## CHEAP_STOCKS

**Class verdict:** INSUFFICIENT_DATA (n=4)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `cheap_stock_cross_momentum_winner` | 4   | 2   | 2   | 50.0  | 1.03  | INSUFF_N (n=4) |  |

## COMMODITY

**Class verdict:** INSUFFICIENT_DATA (n=18)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `commodity_tsmom_12m` | 5   | 2   | 3   | 40.0  | 0.92  | INSUFF_N (n=5) |  |
| `cftc_socrata` | 5   | 0   | 5   | 0.0   | 0.00  | INSUFF_N (n=5) |  |
| `feature_signals` | 3   | 1   | 2   | 33.3  | 0.30  | INSUFF_N (n=3) |  |
| `commodity_cross_momentum_winner` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `metals_mean_reversion` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `multi_asset_copytrader` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |

## CRYPTO

**Class verdict:** FAIL  (n=258, PF=0.94, WR=32.6%)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `copy_trader_clones` | 34  | 15  | 19  | 44.1  | 0.78  | FAIL |  |
| `copy_trader_intel` | 32  | 0   | 32  | 0.0   | 0.00  | FAIL |  |
| `crypto_liquidity_wick_reversal_v1` | 30  | 18  | 12  | 60.0  | 1.55  | T2 (Institutional) |  |
| `atr_percentile_gate` | 29  | 17  | 12  | 58.6  | 1.10  | INSUFF_N (n=29) |  |
| `UNKNOWN` | 24  | 0   | 24  | 0.0   | 0.00  | INSUFF_N (n=24) |  |
| `ml_breakout` | 21  | 0   | 21  | 0.0   | 0.00  | INSUFF_N (n=21) |  |
| `multi_period_rsi_confluence_eth` | 16  | 7   | 9   | 43.8  | 0.43  | INSUFF_N (n=16) |  |
| `battleground_luxalgo` | 11  | 7   | 4   | 63.6  | 2.93  | INSUFF_N (n=11) |  |
| `drawdown_recovery_rsi_eth` | 9   | 5   | 4   | 55.6  | 3.39  | INSUFF_N (n=9) |  |
| `ml_strategy_reviver_inverse` | 7   | 2   | 5   | 28.6  | 0.03  | INSUFF_N (n=7) |  |
| `beta_adjusted_residual_momentum` | 6   | 1   | 5   | 16.7  | 0.23  | INSUFF_N (n=6) |  |
| `alpha_engine` | 5   | 1   | 4   | 20.0  | 0.18  | INSUFF_N (n=5) |  |
| `copy_trader_bybit` | 5   | 0   | 5   | 0.0   | 0.00  | INSUFF_N (n=5) |  |
| `drawdown_recovery_rsi_sol` | 3   | 1   | 2   | 33.3  | 0.88  | INSUFF_N (n=3) |  |
| `B_flip_PriceRocMeanReversion` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `gru_attention` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `hoffman_ema_trend` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `inverse_ml_enhanced_RENDERUSDT_4h_D` | 3   | 3   | 0   | 100.0 | —     | INSUFF_N (n=3) | no_losses |
| `luxalgo_confluence` | 2   | 2   | 0   | 100.0 | —     | INSUFF_N (n=2) | no_losses |
| `ornstein_uhlenbeck` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `ag_vt_pattern_sweep` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `connors_rsi2` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `cta_golden_cross` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `drawdown_recovery_rsi_xrp` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `futures_cross_asset_momentum` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `genome` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `genome_mutation_lab` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `inverse_ml_enhanced_BTCUSDT_15m_D` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `mega_mutation` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `rapid_trend_only_mut` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## EQUITY

**Class verdict:** T1 (Renaissance)  (n=62, PF=2.08, WR=58.1%)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_copytrader` | 20  | 16  | 4   | 80.0  | 7.30  | INSUFF_N (n=20) |  |
| `UNKNOWN` | 13  | 11  | 2   | 84.6  | 9.80  | INSUFF_N (n=13) |  |
| `regime_terminal` | 12  | 3   | 9   | 25.0  | 0.36  | INSUFF_N (n=12) |  |
| `cta_replicator` | 6   | 0   | 6   | 0.0   | 0.00  | INSUFF_N (n=6) |  |
| `vt_equity_two_day_rsi_reversal` | 4   | 4   | 0   | 100.0 | —     | INSUFF_N (n=4) | no_losses |
| `cta_golden_cross` | 3   | 1   | 2   | 33.3  | 0.74  | INSUFF_N (n=3) |  |
| `momentum_rider_base` | 2   | 1   | 1   | 50.0  | 7.93  | INSUFF_N (n=2) |  |
| `equity_sector_rotation_winner` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `stocks_ema_golden_cross` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## ETF

**Class verdict:** INSUFFICIENT_DATA (n=18)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `etf_all_strategies` | 5   | 0   | 5   | 0.0   | 0.00  | INSUFF_N (n=5) |  |
| `etf_scanner` | 4   | 0   | 4   | 0.0   | 0.00  | INSUFF_N (n=4) |  |
| `cta_golden_cross` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `etf_risk_parity` | 2   | 2   | 0   | 100.0 | —     | INSUFF_N (n=2) | no_losses |
| `etf_sector_momentum_rotation` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `etf_country_rotation` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `etf_sector_momentum_winner` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `regime_accumulation` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## FOREX

**Class verdict:** INSUFFICIENT_DATA (n=24)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 11  | 1   | 10  | 9.1   | 0.21  | INSUFF_N (n=11) |  |
| `multi_asset_copytrader` | 7   | 3   | 4   | 42.9  | 0.74  | INSUFF_N (n=7) |  |
| `fx_carry_vix_regime` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `forex_copy_trader` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `forex_zscore_200d_fade` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `fx_dxy_divergence` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `regime_terminal` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## FUTURES

**Class verdict:** INSUFFICIENT_DATA (n=18)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 11  | 1   | 10  | 9.1   | 0.48  | INSUFF_N (n=11) |  |
| `futures_cross_asset_momentum` | 4   | 3   | 1   | 75.0  | 3.86  | INSUFF_N (n=4) |  |
| `futures_tsmom_winner` | 3   | 2   | 1   | 66.7  | 3.14  | INSUFF_N (n=3) |  |

## PENNY_STOCK

**Class verdict:** INSUFFICIENT_DATA (n=1)

| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `multi_asset_scanner` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

---
Read-only report. Source of truth is pf_registry.json; do not recompute PF from raw picks.