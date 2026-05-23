
## Inputs
- payload: E:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json
- recent_closed rows (raw): 3500
- recent_closed rows after blacklist filter: 3150 (dropped 350)
- active_raw rows: 171
- blacklist filter: drops COMMODITY rows whose symbol is in COMMODITY_BLACKLIST
  (PR #535 sub-class kill — those rows can no longer be replicated by the live gate)

## Closed Performance By Asset Class
| Asset Class | n | WR | PF | Sum PnL% |
|---|---:|---:|---:|---:|
| CRYPTO | 1524 | 40.6% | 1.051 | 61.886 |
| FOREX | 778 | 49.7% | 1.347 | 11.843 |
| EQUITY | 425 | 50.1% | 1.272 | 188.163 |
| COMMODITY | 315 | 44.8% | 1.161 | 4.917 |
| ETF | 83 | 51.8% | 1.131 | 12.891 |
| BOND | 20 | 50.0% | 1.720 | 3.411 |
| UNKNOWN | 3 | 100.0% | inf | 0.225 |
| FUTURES | 2 | 100.0% | inf | 0.001 |

## Recent Windows
| Asset Class | Window | n | WR | PF | Sum PnL% |
|---|---:|---:|---:|---:|---:|
| BOND | 30 | 20 | 50.0% | 1.720 | 3.411 |
| BOND | 100 | 20 | 50.0% | 1.720 | 3.411 |
| BOND | 250 | 20 | 50.0% | 1.720 | 3.411 |
| COMMODITY | 30 | 30 | 43.3% | 4.308 | 16.510 |
| COMMODITY | 100 | 100 | 46.0% | 1.687 | 14.171 |
| COMMODITY | 250 | 250 | 44.8% | 1.652 | 13.920 |
| CRYPTO | 30 | 30 | 33.3% | 0.581 | -24.039 |
| CRYPTO | 100 | 100 | 35.0% | 0.621 | -46.819 |
| CRYPTO | 250 | 250 | 42.0% | 1.006 | 1.606 |
| EQUITY | 30 | 30 | 33.3% | 0.865 | -11.222 |
| EQUITY | 100 | 100 | 43.0% | 1.002 | 0.359 |
| EQUITY | 250 | 250 | 48.4% | 1.147 | 61.382 |
| ETF | 30 | 30 | 36.7% | 0.456 | -21.454 |
| ETF | 100 | 83 | 51.8% | 1.131 | 12.891 |
| ETF | 250 | 83 | 51.8% | 1.131 | 12.891 |
| FOREX | 30 | 30 | 43.3% | 1.845 | 0.623 |
| FOREX | 100 | 100 | 39.0% | 0.939 | -0.247 |
| FOREX | 250 | 250 | 53.2% | 2.457 | 16.664 |
| FUTURES | 30 | 2 | 100.0% | inf | 0.001 |
| FUTURES | 100 | 2 | 100.0% | inf | 0.001 |
| FUTURES | 250 | 2 | 100.0% | inf | 0.001 |
| UNKNOWN | 30 | 3 | 100.0% | inf | 0.225 |
| UNKNOWN | 100 | 3 | 100.0% | inf | 0.225 |
| UNKNOWN | 250 | 3 | 100.0% | inf | 0.225 |

## Top Strategy Pockets (min n=12, positive aggregate PnL)
| Asset Class | Strategy | Direction | n | WR | PF | Sum PnL% |
|---|---|---|---:|---:|---:|---:|
| COMMODITY | cta_golden_cross_200 | LONG | 25 | 44.0% | 1.214 | 0.006 |
| COMMODITY | futures_momentum | SHORT | 99 | 41.4% | 1.200 | 5.800 |
| CRYPTO | st_fear_greed_contrarian | LONG | 17 | 94.1% | 49.000 | 20.055 |
| CRYPTO | atr_percentile_gate | LONG | 22 | 95.5% | 13.510 | 9.269 |
| CRYPTO | mega_mutation_macd_rsi_m048 | LONG | 17 | 88.2% | 11.528 | 78.921 |
| CRYPTO | MeanReversionBB | SHORT | 17 | 64.7% | 3.248 | 22.840 |
| CRYPTO | vwap_deviation_reversion_sol_v1 | SHORT | 12 | 66.7% | 2.722 | 6.072 |
| EQUITY | rs-breakout-scout | LONG | 18 | 77.8% | 6.700 | 46.464 |
| EQUITY | Breakout Momentum | LONG | 38 | 57.9% | 1.528 | 31.140 |
| EQUITY | quality-minus-junk | LONG | 18 | 61.1% | 1.435 | 8.704 |
| EQUITY | Bollinger MR | LONG | 58 | 44.8% | 1.309 | 25.110 |
| EQUITY | stocks_rsi2_pullback | LONG | 39 | 56.4% | 1.306 | 9.678 |
| ETF | intermarket-flow-scout | LONG | 12 | 58.3% | 1.771 | 8.963 |
| ETF | quality-minus-junk | LONG | 12 | 50.0% | 1.051 | 0.881 |
| FOREX | cta_cross_asset_tsmom | SHORT | 28 | 64.3% | 4.840 | 3.099 |
| FOREX | non_crypto_consensus | SHORT | 87 | 59.8% | 2.031 | 0.033 |
| FOREX | fx_smart_carry_trade_momentum | LONG | 21 | 42.9% | 1.263 | 0.401 |
| FOREX | cta_cross_asset_tsmom | LONG | 39 | 43.6% | 1.235 | 0.799 |
| FOREX | forex_rsi2_mean_reversion | LONG | 198 | 46.5% | 1.106 | 0.867 |

## Field Separation (rank-tertiles)
| Asset Class | Field | Bucket | n | WR | PF | Sum PnL% |
|---|---|---|---:|---:|---:|---:|
| EQUITY | trust_score | low | 141 | 36.9% | 0.595 | -123.599 |
| EQUITY | trust_score | mid | 142 | 49.3% | 1.361 | 82.715 |
| EQUITY | trust_score | high | 142 | 64.1% | 2.465 | 229.046 |
| EQUITY | strat_fwd_wr | low | 141 | 26.2% | 0.478 | -198.317 |
| EQUITY | strat_fwd_wr | mid | 142 | 51.4% | 1.502 | 102.352 |
| EQUITY | strat_fwd_wr | high | 142 | 72.5% | 3.658 | 284.129 |
| EQUITY | strat_fwd_pf | low | 136 | 29.4% | 0.427 | -191.031 |
| EQUITY | strat_fwd_pf | mid | 136 | 56.6% | 1.410 | 78.777 |
| EQUITY | strat_fwd_pf | high | 137 | 59.9% | 3.009 | 277.510 |
| EQUITY | confidence | low | 141 | 51.1% | 1.448 | 112.719 |
| EQUITY | confidence | mid | 142 | 40.8% | 0.924 | -18.829 |
| EQUITY | confidence | high | 142 | 58.5% | 1.489 | 94.273 |
| ETF | trust_score | low | 27 | 25.9% | 0.510 | -23.438 |
| ETF | trust_score | mid | 28 | 53.6% | 1.197 | 6.059 |
| ETF | trust_score | high | 28 | 75.0% | 2.509 | 30.270 |
| ETF | strat_fwd_wr | low | 27 | 22.2% | 0.290 | -31.939 |
| ETF | strat_fwd_wr | mid | 28 | 53.6% | 1.325 | 12.809 |
| ETF | strat_fwd_wr | high | 28 | 78.6% | 3.247 | 32.022 |
| ETF | strat_fwd_pf | low | 26 | 30.8% | 0.192 | -33.080 |
| ETF | strat_fwd_pf | mid | 26 | 65.4% | 2.323 | 27.338 |
| ETF | strat_fwd_pf | high | 27 | 51.9% | 1.209 | 7.742 |
| ETF | confidence | low | 27 | 77.8% | 2.842 | 42.960 |
| ETF | confidence | mid | 28 | 17.9% | 0.271 | -37.570 |
| ETF | confidence | high | 28 | 60.7% | 1.315 | 7.501 |
| FOREX | trust_score | low | 259 | 42.9% | 0.806 | -2.413 |
| FOREX | trust_score | mid | 259 | 50.6% | 1.109 | 1.100 |
| FOREX | trust_score | high | 260 | 55.8% | 2.135 | 13.156 |
| FOREX | strat_fwd_wr | low | 259 | 39.8% | 0.345 | -11.903 |
| FOREX | strat_fwd_wr | mid | 259 | 49.8% | 2.121 | 6.781 |
| FOREX | strat_fwd_wr | high | 260 | 59.6% | 2.707 | 16.965 |
| FOREX | strat_fwd_pf | low | 255 | 50.6% | 0.736 | -3.591 |
| FOREX | strat_fwd_pf | mid | 256 | 45.3% | 0.986 | -0.173 |
| FOREX | strat_fwd_pf | high | 256 | 51.2% | 2.696 | 13.208 |
| FOREX | confidence | low | 259 | 47.1% | 1.087 | 2.139 |
| FOREX | confidence | mid | 259 | 51.4% | 3.249 | 4.727 |
| FOREX | confidence | high | 260 | 50.8% | 1.662 | 4.977 |
| COMMODITY | trust_score | low | 105 | 48.6% | 0.017 | -9.798 |
| COMMODITY | trust_score | mid | 105 | 38.1% | 0.632 | -0.234 |
| COMMODITY | trust_score | high | 105 | 47.6% | 1.753 | 14.949 |
| COMMODITY | strat_fwd_wr | low | 105 | 45.7% | 0.016 | -9.780 |
| COMMODITY | strat_fwd_wr | mid | 105 | 48.6% | 0.836 | -0.061 |
| COMMODITY | strat_fwd_wr | high | 105 | 40.0% | 1.733 | 14.758 |
| COMMODITY | strat_fwd_pf | low | 105 | 45.7% | 0.016 | -9.780 |
| COMMODITY | strat_fwd_pf | mid | 105 | 48.6% | 0.836 | -0.061 |
| COMMODITY | strat_fwd_pf | high | 105 | 40.0% | 1.733 | 14.758 |
| COMMODITY | confidence | low | 105 | 36.2% | 0.371 | -11.936 |
| COMMODITY | confidence | mid | 105 | 51.4% | 15.464 | 4.424 |
| COMMODITY | confidence | high | 105 | 46.7% | 2.113 | 12.429 |
| CRYPTO | trust_score | low | 508 | 29.1% | 0.724 | -92.904 |
| CRYPTO | trust_score | mid | 508 | 38.8% | 0.828 | -86.386 |
| CRYPTO | trust_score | high | 508 | 53.9% | 1.656 | 241.175 |
| CRYPTO | strat_fwd_wr | low | 508 | 29.5% | 0.587 | -131.411 |
| CRYPTO | strat_fwd_wr | mid | 508 | 39.8% | 0.945 | -26.155 |
| CRYPTO | strat_fwd_wr | high | 508 | 52.6% | 1.529 | 219.452 |
| CRYPTO | strat_fwd_pf | low | 497 | 28.6% | 0.541 | -184.100 |
| CRYPTO | strat_fwd_pf | mid | 498 | 44.4% | 1.070 | 24.194 |
| CRYPTO | strat_fwd_pf | high | 498 | 48.6% | 1.514 | 219.227 |
| CRYPTO | confidence | low | 508 | 42.7% | 0.940 | -21.261 |
| CRYPTO | confidence | mid | 508 | 39.6% | 1.187 | 62.685 |
| CRYPTO | confidence | high | 508 | 39.6% | 1.039 | 20.462 |

## Active Raw Mix
| Asset Class | Active Raw | Top Strategies |
|---|---:|---|
| CRYPTO | 116 | enhanced_ml_A_xgboost (27), super signal (super) via claude_gainer_st (9), luxalgo_confluence (9), super signal (strong) via ml_crypto_pred (6), quan_engine (6) |
| EQUITY | 24 | regime_terminal (10), smart_money_consensus (4), adx-trend-scout (2), rs-breakout-scout (1), mtf-align-scout (1) |
| FOREX | 18 | non_crypto_consensus (6), forex_rsi2_mean_reversion (3), fx_smart_carry_trade_momentum (3), regime_terminal (2), forex-rsi-ema-scout (2) |
| COMMODITY | 6 | non_crypto_consensus (4), cftc_cot_commercial_signal (2) |
| SPORTS | 4 | value_bet (4) |
| ETF | 3 | super signal (strong) via kimi (2), adx-trend-scout (1) |

## UEPS / PEAD Status
- ueps_picks.generated_at: 2026-04-30T17:02:55.485318+00:00
- ueps summary: {'n_long': 30, 'n_short': 0, 'n_swing': 0}
- active_picks rows: 157
- active long_term_value rows: 0
- active PEAD-like rows: 0
- recent_closed PEAD-like rows: 8
- PEAD-like closed strategies: ['post-earnings-rev-scout']

Done.
