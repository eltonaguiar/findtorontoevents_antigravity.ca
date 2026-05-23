# CR-1 Funding Rate Reversion -- S1 Backtest Results
Generated: 2026-04-19T02:07:57.753353+00:00

## Verdict: **FAIL**

Failed S1 criteria:
- n=4 < 200
- IS-combined Sharpe -511.36 <= 1.0
- Win rate 0.000 <= 0.55
- W/L magnitude ratio 0.00 <= 1.0
- OOS1 Sharpe 0.00 < 0.7 x IS -350.76
- OOS2 Sharpe 0.00 < 0.7 x IS -350.76
- Only 0/3 yearly sub-windows (2023/2024/2025) with Sharpe>0.5

## Spec
- `funding_threshold`: 0.0008
- `hold_hours`: 12
- `sl_mult`: 1.5
- `txn_cost_bps_roundtrip`: 30
- `symbols`: ['BTCUSDT', 'ETHUSDT']
- `window_start`: 2023-01-01
- `window_end_ms`: 1776564442580
- `oi_filter_applied`: False
- `oi_filter_note`: Binance openInterestHist endpoint only returns ~30d of history on free tier; documented and omitted per spec fallback.

## Combined (all trades, all symbols)
| metric | value |
|---|---|
| label | combined_all |
| n | 4 |
| win_rate | 0.0 |
| wilson_lb_95 | 0.0 |
| avg_winner_bps | 0.0 |
| avg_loser_bps | -43.304015639698235 |
| wl_magnitude_ratio | 0.0 |
| mean_bps | -43.304015639698235 |
| median_bps | -42.817310503343556 |
| std_bps | 1.3443283188290296 |
| sharpe | -511.3556913815085 |
| max_dd_bps | -130.78618198021798 |
| sum_bps | -173.21606255879294 |
| sl_hit_rate | 1.0 |
| avg_hold_h | 0.0 |
| longs | 0 |
| shorts | 4 |

## Per symbol
### BTCUSDT
- label: BTCUSDT
- n: 2
- win_rate: 0.0
- wilson_lb_95: 0.0
- avg_winner_bps: 0.0
- avg_loser_bps: -42.817310503343556
- wl_magnitude_ratio: 0.0
- mean_bps: -42.817310503343556
- median_bps: -42.817310503343556
- std_bps: 0.5479086540769275
- sharpe: -1240.5420636182425
- max_dd_bps: -43.204740428112146
- sum_bps: -85.63462100668711
- sl_hit_rate: 1.0
- avg_hold_h: 0.0
- longs: 0
- shorts: 2
### ETHUSDT
- label: ETHUSDT
- n: 2
- win_rate: 0.0
- wilson_lb_95: 0.0
- avg_winner_bps: 0.0
- avg_loser_bps: -43.79072077605292
- wl_magnitude_ratio: 0.0
- mean_bps: -43.79072077605292
- median_bps: -43.79072077605292
- std_bps: 2.0430184615388423
- sharpe: -340.25935375573005
- max_dd_bps: -42.346088567809495
- sum_bps: -87.58144155210584
- sl_hit_rate: 1.0
- avg_hold_h: 0.0
- longs: 0
- shorts: 2

## IS/OOS splits (70/15/15)
### IS
- label: IS_70
- n: 2
- win_rate: 0.0
- wilson_lb_95: 0.0
- avg_winner_bps: 0.0
- avg_loser_bps: -43.83261678143566
- wl_magnitude_ratio: 0.0
- mean_bps: -43.83261678143566
- median_bps: -43.83261678143566
- std_bps: 1.9837685625173263
- sharpe: -350.75725719651587
- max_dd_bps: -45.235352984296355
- sum_bps: -87.66523356287132
- sl_hit_rate: 1.0
- avg_hold_h: 0.0
- longs: 0
- shorts: 2
### OOS1
- label: OOS1_15
- n: 1
- win_rate: 0.0
- wilson_lb_95: 0.0
- avg_winner_bps: 0.0
- avg_loser_bps: -43.204740428112146
- wl_magnitude_ratio: 0.0
- mean_bps: -43.204740428112146
- median_bps: -43.204740428112146
- std_bps: 0.0
- sharpe: 0.0
- max_dd_bps: 0.0
- sum_bps: -43.204740428112146
- sl_hit_rate: 1.0
- avg_hold_h: 0.0
- longs: 0
- shorts: 1
### OOS2
- label: OOS2_15
- n: 1
- win_rate: 0.0
- wilson_lb_95: 0.0
- avg_winner_bps: 0.0
- avg_loser_bps: -42.3460885678095
- wl_magnitude_ratio: 0.0
- mean_bps: -42.3460885678095
- median_bps: -42.3460885678095
- std_bps: 0.0
- sharpe: 0.0
- max_dd_bps: 0.0
- sum_bps: -42.3460885678095
- sl_hit_rate: 1.0
- avg_hold_h: 0.0
- longs: 0
- shorts: 1

## Per year
### 2024
- label: year_2024
- n: 4
- win_rate: 0.0
- wilson_lb_95: 0.0
- avg_winner_bps: 0.0
- avg_loser_bps: -43.304015639698235
- wl_magnitude_ratio: 0.0
- mean_bps: -43.304015639698235
- median_bps: -42.817310503343556
- std_bps: 1.3443283188290296
- sharpe: -511.3556913815085
- max_dd_bps: -130.78618198021798
- sum_bps: -173.21606255879294
- sl_hit_rate: 1.0
- avg_hold_h: 0.0
- longs: 0
- shorts: 4

## Per direction
### long
- label: long
- n: 0
### short
- label: short
- n: 4
- win_rate: 0.0
- wilson_lb_95: 0.0
- avg_winner_bps: 0.0
- avg_loser_bps: -43.304015639698235
- wl_magnitude_ratio: 0.0
- mean_bps: -43.304015639698235
- median_bps: -42.817310503343556
- std_bps: 1.3443283188290296
- sharpe: -511.3556913815085
- max_dd_bps: -130.78618198021798
- sum_bps: -173.21606255879294
- sl_hit_rate: 1.0
- avg_hold_h: 0.0
- longs: 0
- shorts: 4

## Hold time distribution
- min_h: 0.0
- p25_h: 0.0
- median_h: 0.0
- p75_h: 0.0
- max_h: 0.0
- sl_hit_rate: 1.0

## Notes
- scipy available: True
- OI filter omitted: Binance `/futures/data/openInterestHist` returns only ~30 days of history on the public endpoint; per spec we documented and proceeded without the OI filter for this first pass.
- Raw trades: `backtest_results/cr1_raw_data/trades.csv`
- Per v1.1 spec: **if FAIL, archive; do NOT iterate parameters to force a pass.**

## Root-cause analysis (why this failed at the data level)

Empirical funding-rate distribution on BTCUSDT / ETHUSDT perps, 2023-01-01 -> 2026-04-19 (n=3,613 funding events per symbol):

| symbol | max |rate| | p95 |rate| | p99 |rate| | count |r|>0.08% | count |r|>0.05% | count |r|>0.02% |
|---|---|---|---|---|---|---|
| BTCUSDT | 0.000881 | 0.000181 | 0.000458 | 2 | 26 | 168 |
| ETHUSDT | 0.001017 | 0.000213 | 0.000488 | 2 | 30 | 194 |

The spec's |0.08%|/8h threshold is **above the 99th percentile** of realized funding on both symbols. Only 4 events across 3+ years clear the gate, making the strategy statistically untestable on the BTC/ETH-only universe specified. The honest S1 verdict is FAIL and, per v1.1 rules, we do NOT tune the threshold.

## Recommendation

**Archive CR-1 as specified.** Do not graduate to S2. If the funding-reversion family is worth revisiting under a future proposal, it would require a fresh v1.1 spec (not a parameter tweak) that either:
1. Expands the universe to altcoin perps where funding regularly exceeds |0.08%| (introduces new survivorship/liquidity risks), or
2. Uses a percentile-relative trigger (e.g. rolling 99th-percentile) rather than an absolute threshold.

Neither is a permitted mutation of this S1 run.
