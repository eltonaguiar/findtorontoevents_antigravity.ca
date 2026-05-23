# Edge diagnosis by asset class — 2026-04-22

**Source:** `audit_dashboard/data/dashboard_data.json` (`picks.recent_closed`, 3,500 rows).
**Method:** last-N window stats + strategy/symbol/direction/confidence-bucket drill-downs.
**Edge definition:** WR ≥ 45% AND PF ≥ 1.10 on n ≥ 30.
**Drag definition:** WR ≤ 25% AND PF ≤ 0.6 on n ≥ 30 (candidates to kill/invert).


## Overall (system-wide)

```json
{
  "total": {
    "n": 3500,
    "wins": 1645,
    "losses": 1812,
    "flat": 43,
    "wr": 0.47,
    "wr_excl_flat": 0.4758,
    "pf": 1.4016,
    "mean_pnl_pct": 0.3648,
    "total_pnl_pct": 1276.7529
  },
  "last_20_overall": {
    "n": 20,
    "wins": 2,
    "losses": 18,
    "flat": 0,
    "wr": 0.1,
    "wr_excl_flat": 0.1,
    "pf": 0.1879,
    "mean_pnl_pct": -1.1045,
    "total_pnl_pct": -22.09
  },
  "last_50_overall": {
    "n": 50,
    "wins": 16,
    "losses": 32,
    "flat": 2,
    "wr": 0.32,
    "wr_excl_flat": 0.3333,
    "pf": 0.7079,
    "mean_pnl_pct": -0.2994,
    "total_pnl_pct": -14.9702
  },
  "last_100_overall": {
    "n": 100,
    "wins": 26,
    "losses": 72,
    "flat": 2,
    "wr": 0.26,
    "wr_excl_flat": 0.2653,
    "pf": 0.5185,
    "mean_pnl_pct": -0.572,
    "total_pnl_pct": -57.1963
  },
  "last_200_overall": {
    "n": 200,
    "wins": 70,
    "losses": 128,
    "flat": 2,
    "wr": 0.35,
    "wr_excl_flat": 0.3535,
    "pf": 0.8204,
    "mean_pnl_pct": -0.1797,
    "total_pnl_pct": -35.939
  }
}
```


## Claim verification (status-based vs pnl-based WR)

| asset_class   |   window |   n_used |   strict_status_wr_pct |   status_wr_pct |   pnl_wr_pct |   profit_factor |   mean_pnl_pct |
|:--------------|---------:|---------:|-----------------------:|----------------:|-------------:|----------------:|---------------:|
| stocks        |       20 |       20 |                   10   |            10   |         10   |          0.3901 |        -0.9857 |
| stocks        |      100 |      100 |                   57   |            57   |         57   |          2.9329 |         2.2613 |
| stocks        |      200 |      200 |                   56.5 |            56.5 |         56.5 |          2.282  |         1.7404 |
| forex         |       20 |       20 |                   15   |            15   |         15   |          1.1175 |         0.0104 |
| forex         |      100 |       96 |                   36.5 |            36.5 |         36.5 |          2.0628 |         0.2295 |
| forex         |      200 |       96 |                   36.5 |            36.5 |         36.5 |          2.0628 |         0.2295 |
| commodities   |       20 |       20 |                    5   |             5   |          5   |          0.125  |        -2.9431 |
| commodities   |      100 |       67 |                   55.2 |            55.2 |         55.2 |          1.923  |         1.2899 |
| commodities   |      200 |       67 |                   55.2 |            55.2 |         55.2 |          1.923  |         1.2899 |
| bonds         |       20 |       12 |                   41.7 |            41.7 |         50   |          0.6623 |        -0.1277 |
| bonds         |      100 |       12 |                   41.7 |            41.7 |         50   |          0.6623 |        -0.1277 |
| bonds         |      200 |       12 |                   41.7 |            41.7 |         50   |          0.6623 |        -0.1277 |
| etfs          |       20 |       20 |                   65   |            65   |         65   |          1.304  |         0.3155 |
| etfs          |      100 |      100 |                   57   |            57   |         57   |          1.3675 |         0.3895 |
| etfs          |      200 |      105 |                   57.1 |            57.1 |         57.1 |          1.3199 |         0.3468 |


## BOND — Window table (last-N)

| window   |   n |   wins |   losses |   flat |   wr |   wr_excl_flat |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-----:|---------------:|-------:|---------------:|----------------:|
| last_20  |  12 |      6 |        5 |      1 |  0.5 |         0.5455 | 0.6623 |        -0.1277 |         -1.5322 |
| last_50  |  12 |      6 |        5 |      1 |  0.5 |         0.5455 | 0.6623 |        -0.1277 |         -1.5322 |
| last_100 |  12 |      6 |        5 |      1 |  0.5 |         0.5455 | 0.6623 |        -0.1277 |         -1.5322 |
| last_200 |  12 |      6 |        5 |      1 |  0.5 |         0.5455 | 0.6623 |        -0.1277 |         -1.5322 |
| all_12   |  12 |      6 |        5 |      1 |  0.5 |         0.5455 | 0.6623 |        -0.1277 |         -1.5322 |


## BOND — Top strategies (by WR, min n=10, top 10)

_empty_


## BOND — Top symbols (by WR, min n=10, top 10)

_empty_


## BOND — Direction split

| signal_type   |   n |   wins |   losses |   wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:--------------|----:|-------:|---------:|-----:|-------:|---------------:|----------------:|
| LONG          |  12 |      6 |        5 |  0.5 | 0.6623 |        -0.1277 |         -1.5322 |


## BOND — Confidence buckets

_empty_


## BOND — Edge candidates (WR≥0.45 AND PF≥1.10, n≥30)

_none found_


## BOND — Drag candidates (WR≤0.25 AND PF≤0.60, n≥30)

_none found_


## COMMODITY — Window table (last-N)

| window   |   n |   wins |   losses |   flat |     wr |   wr_excl_flat |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-------:|---------------:|-------:|---------------:|----------------:|
| last_20  |  20 |      1 |       19 |      0 | 0.05   |         0.05   | 0.125  |        -2.9431 |        -58.8622 |
| last_50  |  50 |     29 |       21 |      0 | 0.58   |         0.58   | 1.9363 |         1.3039 |         65.1948 |
| last_100 |  67 |     37 |       30 |      0 | 0.5522 |         0.5522 | 1.923  |         1.2899 |         86.424  |
| last_200 |  67 |     37 |       30 |      0 | 0.5522 |         0.5522 | 1.923  |         1.2899 |         86.424  |
| all_67   |  67 |     37 |       30 |      0 | 0.5522 |         0.5522 | 1.923  |         1.2899 |         86.424  |


## COMMODITY — Top strategies (by WR, min n=10, top 10)

| strategy                   |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------------------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| cot_positioning            |  32 |     19 |       13 | 0.5938 | 1.6553 |         1.0502 |         33.6077 |
| cftc_cot_commercial_signal |  32 |     18 |       14 | 0.5625 | 2.4108 |         1.7402 |         55.6865 |


## COMMODITY — Top symbols (by WR, min n=10, top 10)

| symbol   |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| CT=F     |  41 |     33 |        8 | 0.8049 | 5.7377 |         3.2802 |        134.487  |
| ZW=F     |  13 |      3 |       10 | 0.2308 | 0.4115 |        -1.8024 |        -23.4318 |


## COMMODITY — Direction split

| signal_type   |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:--------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| SHORT         |  62 |     36 |       26 | 0.5806 | 2.1015 |         1.5155 |          93.958 |
| LONG          |   5 |      1 |        4 | 0.2    | 0.096  |        -1.5068 |          -7.534 |


## COMMODITY — Confidence buckets

| bucket    |   n |   wins |   losses |   wr |     pf |   mean_pnl_pct |
|:----------|----:|-------:|---------:|-----:|-------:|---------------:|
| 0.50-0.60 |  15 |      6 |        9 | 0.4  | 0.6741 |        -0.8033 |
| 0.60-0.70 |  50 |     31 |       19 | 0.62 | 2.8607 |         2.0181 |


## COMMODITY — Edge candidates (WR≥0.45 AND PF≥1.10, n≥30)

- `symbol=CT=F` — n=41, WR=0.8049, PF=5.7377, mean_pnl=3.2802
- `strategy=cftc_cot_commercial_signal & confidence_bucket=0.60-0.70` — n=30, WR=0.5667, PF=2.5228, mean_pnl=1.8345
- `strategy=cftc_cot_commercial_signal & direction=SHORT` — n=32, WR=0.5625, PF=2.4108, mean_pnl=1.7402


## COMMODITY — Drag candidates (WR≤0.25 AND PF≤0.60, n≥30)

_none found_


## CRYPTO — Window table (last-N)

| window   |    n |   wins |   losses |   flat |     wr |   wr_excl_flat |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|-----:|-------:|---------:|-------:|-------:|---------------:|-------:|---------------:|----------------:|
| last_20  |   20 |      2 |       18 |      0 | 0.1    |         0.1    | 0.1879 |        -1.1045 |        -22.09   |
| last_50  |   50 |     17 |       33 |      0 | 0.34   |         0.34   | 0.7181 |        -0.3059 |        -15.2953 |
| last_100 |  100 |     31 |       69 |      0 | 0.31   |         0.31   | 0.6234 |        -0.4017 |        -40.1749 |
| last_200 |  200 |     64 |      136 |      0 | 0.32   |         0.32   | 0.7485 |        -0.2398 |        -47.9628 |
| all_2966 | 2966 |   1369 |     1592 |      5 | 0.4616 |         0.4623 | 1.2987 |         0.2614 |        775.294  |


## CRYPTO — Top strategies (by WR, min n=10, top 10)

| strategy                                  |   n |   wins |   losses |     wr |       pf |   mean_pnl_pct |   total_pnl_pct |
|:------------------------------------------|----:|-------:|---------:|-------:|---------:|---------------:|----------------:|
| ml_enhanced_DYDXUSDT_15m_D_ensemble_stack |  13 |     13 |        0 | 1      | nan      |         2.4313 |         31.6067 |
| ema-ribbon-momentum-scout                 |  14 |     11 |        3 | 0.7857 |   4.091  |         2.6584 |         37.218  |
| ml_enhanced_STRKUSDT_15m_D_ensemble_stack |  12 |      9 |        3 | 0.75   |   1.571  |         0.4767 |          5.7209 |
| cci-crypto-reversal                       |  15 |     11 |        4 | 0.7333 |   2.7259 |         2.2271 |         33.407  |
| macd_rsi_m048                             |  45 |     32 |       13 | 0.7111 |   4.9492 |         3.4629 |        155.83   |
| atr_percentile_gate                       |  54 |     38 |       16 | 0.7037 |   1.7775 |         0.1486 |          8.0243 |
| vwap_deviation_reversion_xrp_v1           |  23 |     16 |        7 | 0.6957 |   4.1826 |         0.7694 |         17.6967 |
| multi_period_rsi_confluence_eth           |  27 |     18 |        9 | 0.6667 |   3.4551 |         0.4518 |         12.1998 |
| MomentumEMA                               |  30 |     18 |       12 | 0.6    |   2.7464 |         1.056  |         31.68   |
| incubator_gainer                          |  10 |      6 |        4 | 0.6    |   2.5271 |         1.269  |         12.69   |


## CRYPTO — Top symbols (by WR, min n=10, top 10)

| symbol   |   n |   wins |   losses |     wr |       pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|---------:|---------------:|----------------:|
| DYDXUSDT |  14 |     13 |        0 | 0.9286 | nan      |         2.2576 |         31.6067 |
| SEIUSDT  |  41 |     32 |        9 | 0.7805 |   7.1883 |         1.7146 |         70.2996 |
| STRKUSDT |  13 |     10 |        3 | 0.7692 |   1.8704 |         0.6708 |          8.7209 |
| POLUSDT  |  21 |     15 |        6 | 0.7143 |   9.1553 |         2.2996 |         48.2908 |
| DOT-USD  |  10 |      7 |        3 | 0.7    |   5.4196 |         1.9888 |         19.8883 |
| HBARUSDT |  15 |     10 |        5 | 0.6667 |   4.3034 |         0.9772 |         14.6587 |
| ADA-USD  |  15 |      9 |        6 | 0.6    |   2.0228 |         0.9306 |         13.9594 |
| WLDUSDT  |  12 |      7 |        5 | 0.5833 |   2.1    |         0.9167 |         11      |
| SOL-USD  |  19 |     11 |        8 | 0.5789 |   2.5366 |         1.1162 |         21.2084 |
| DOGE-USD |  18 |     10 |        8 | 0.5556 |   3.0729 |         1.6622 |         29.9194 |


## CRYPTO — Direction split

| signal_type   |    n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:--------------|-----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| LONG          | 1956 |    973 |      979 | 0.4974 | 1.5869 |         0.4929 |         964.087 |
| SHORT         | 1010 |    396 |      613 | 0.3921 | 0.8019 |        -0.1869 |        -188.793 |


## CRYPTO — Confidence buckets

| bucket    |    n |   wins |   losses |     wr |     pf |   mean_pnl_pct |
|:----------|-----:|-------:|---------:|-------:|-------:|---------------:|
| <0.50     |  609 |    313 |      293 | 0.514  | 1.527  |         0.5433 |
| 0.50-0.60 |  904 |    428 |      474 | 0.4735 | 1.2882 |         0.1781 |
| 0.60-0.70 | 1127 |    517 |      610 | 0.4587 | 1.3478 |         0.3231 |
| 0.70-0.80 |  259 |     88 |      171 | 0.3398 | 0.71   |        -0.325  |
| 0.80-0.90 |   20 |      7 |       13 | 0.35   | 1.0552 |         0.0718 |
| 0.90-1.00 |   47 |     16 |       31 | 0.3404 | 1.0423 |         0.0415 |


## CRYPTO — Edge candidates (WR≥0.45 AND PF≥1.10, n≥30)

- `strategy=macd_rsi_m048 & direction=LONG` — n=32, WR=0.9375, PF=23.635, mean_pnl=5.3027
- `symbol=SEIUSDT` — n=41, WR=0.7805, PF=7.1883, mean_pnl=1.7146
- `strategy=macd_rsi_m048 & confidence_bucket=<0.50` — n=45, WR=0.7111, PF=4.9492, mean_pnl=3.4629
- `strategy=MomentumEMA & direction=LONG` — n=30, WR=0.6, PF=2.7464, mean_pnl=1.056
- `strategy=MomentumEMA & confidence_bucket=<0.50` — n=30, WR=0.6, PF=2.7464, mean_pnl=1.056
- `strategy=vwap_deviation_reversion_eth_v1 & direction=SHORT` — n=44, WR=0.5909, PF=2.4003, mean_pnl=0.3716
- `strategy=atr_percentile_gate & confidence_bucket=0.50-0.60` — n=36, WR=0.7222, PF=2.3955, mean_pnl=0.213
- `strategy=claude_ml_moderate_mut & direction=LONG` — n=87, WR=0.5862, PF=2.1817, mean_pnl=0.8418
- `strategy=claude_ml_moderate_mut & confidence_bucket=0.60-0.70` — n=87, WR=0.5862, PF=2.1817, mean_pnl=0.8418
- `strategy=vwap_deviation_reversion_eth_v1 & confidence_bucket=0.50-0.60` — n=65, WR=0.5846, PF=2.128, mean_pnl=0.3058
- `symbol=ONDOUSDT` — n=212, WR=0.4811, PF=2.0511, mean_pnl=0.8133
- `strategy=vwap_deviation_reversion_sol_v1 & direction=SHORT` — n=37, WR=0.5676, PF=1.9884, mean_pnl=0.3264
- `strategy=vwap_deviation_reversion_sol_v1 & confidence_bucket=0.50-0.60` — n=43, WR=0.5581, PF=1.8987, mean_pnl=0.304
- `symbol=WIFUSDT` — n=55, WR=0.5273, PF=1.8646, mean_pnl=1.3609
- `strategy=atr_percentile_gate & direction=LONG` — n=54, WR=0.7037, PF=1.7775, mean_pnl=0.1486


## CRYPTO — Drag candidates (WR≤0.25 AND PF≤0.60, n≥30)

- `strategy=unknown & direction=SHORT` — n=117, WR=0.1368, PF=0.3816, mean_pnl=-0.6842
- `symbol=HYPEUSDT` — n=44, WR=0.2045, PF=0.5879, mean_pnl=-0.371


## EQUITY — Window table (last-N)

| window   |   n |   wins |   losses |   flat |     wr |   wr_excl_flat |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-------:|---------------:|-------:|---------------:|----------------:|
| last_20  |  20 |      2 |        8 |     10 | 0.1    |         0.2    | 0.3901 |        -0.9857 |         -19.714 |
| last_50  |  50 |     23 |       16 |     11 | 0.46   |         0.5897 | 3.0369 |         2.4289 |         121.443 |
| last_100 | 100 |     57 |       32 |     11 | 0.57   |         0.6404 | 2.9329 |         2.2613 |         226.126 |
| last_200 | 200 |    113 |       76 |     11 | 0.565  |         0.5979 | 2.282  |         1.7404 |         348.08  |
| all_252  | 252 |    136 |      104 |     12 | 0.5397 |         0.5667 | 1.9742 |         1.3541 |         341.223 |


## EQUITY — Top strategies (by WR, min n=10, top 10)

| strategy                |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:------------------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| donchian-stock-breakout |  14 |     11 |        3 | 0.7857 | 7.1335 |         6.2463 |         87.4482 |
| vol-contraction-scout   |  14 |     11 |        3 | 0.7857 | 6.409  |         3.645  |         51.0298 |
| rs-breakout-scout       |  22 |     16 |        6 | 0.7273 | 6.8605 |         2.932  |         64.5043 |
| quality-minus-junk      |  18 |     11 |        7 | 0.6111 | 1.4354 |         0.4836 |          8.7041 |
| price-accel-scout       |  14 |      8 |        6 | 0.5714 | 2.8654 |         2.3406 |         32.7681 |
| quality-momentum-scout  |  10 |      5 |        5 | 0.5    | 0.98   |        -0.0337 |         -0.337  |
| rsi-divergence-scout    |  10 |      5 |        5 | 0.5    | 2.5622 |         1.9905 |         19.9051 |
| macd-hidden-div-scout   |  10 |      3 |        7 | 0.3    | 0.3192 |        -1.7565 |        -17.565  |


## EQUITY — Top symbols (by WR, min n=10, top 10)

| symbol   |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| CVX      |  12 |      9 |        3 | 0.75   | 3.483  |         1.5846 |         19.0155 |
| AMD      |  21 |     14 |        6 | 0.6667 | 3.3628 |         3.8595 |         81.0497 |
| GOOGL    |  14 |      9 |        4 | 0.6429 | 2.823  |         1.4919 |         20.8863 |
| AMZN     |  18 |     11 |        6 | 0.6111 | 2.7058 |         1.3059 |         23.5063 |
| XOM      |  15 |      9 |        6 | 0.6    | 1.3307 |         0.4701 |          7.0514 |
| SOXX     |  17 |      9 |        8 | 0.5294 | 2.4854 |         1.6903 |         28.7345 |
| AAPL     |  18 |      9 |        9 | 0.5    | 1.077  |         0.0874 |          1.573  |
| COIN     |  12 |      6 |        5 | 0.5    | 1.6475 |         1.6928 |         20.3133 |
| META     |  10 |      5 |        5 | 0.5    | 2.1467 |         1.4084 |         14.0836 |
| JPM      |  13 |      6 |        7 | 0.4615 | 0.8557 |        -0.1912 |         -2.485  |


## EQUITY — Direction split

| signal_type   |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:--------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| LONG          | 249 |    136 |      102 | 0.5462 | 1.9948 |         1.3849 |        344.83   |
| SHORT         |   3 |      0 |        2 | 0      | 0      |        -1.2022 |         -3.6065 |


## EQUITY — Confidence buckets

| bucket    |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |
|:----------|----:|-------:|---------:|-------:|-------:|---------------:|
| <0.50     | 153 |     96 |       57 | 0.6275 | 2.6211 |         2.1484 |
| 0.50-0.60 |  50 |     18 |       32 | 0.36   | 0.8269 |        -0.345  |
| 0.60-0.70 |  29 |     14 |       11 | 0.4828 | 1.9973 |         1.1672 |
| 0.70-0.80 |  11 |      6 |        2 | 0.5455 | 1.345  |         0.1817 |


## EQUITY — Edge candidates (WR≥0.45 AND PF≥1.10, n≥30)

_none found_


## EQUITY — Drag candidates (WR≤0.25 AND PF≤0.60, n≥30)

_none found_


## ETF — Window table (last-N)

| window   |   n |   wins |   losses |   flat |     wr |   wr_excl_flat |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-------:|---------------:|-------:|---------------:|----------------:|
| last_20  |  20 |     13 |        7 |      0 | 0.65   |         0.65   | 1.304  |         0.3155 |          6.3099 |
| last_50  |  50 |     36 |       14 |      0 | 0.72   |         0.72   | 2.6319 |         1.1136 |         55.681  |
| last_100 | 100 |     57 |       43 |      0 | 0.57   |         0.57   | 1.3675 |         0.3895 |         38.9485 |
| last_200 | 105 |     60 |       45 |      0 | 0.5714 |         0.5714 | 1.3199 |         0.3468 |         36.4189 |
| all_105  | 105 |     60 |       45 |      0 | 0.5714 |         0.5714 | 1.3199 |         0.3468 |         36.4189 |


## ETF — Top strategies (by WR, min n=10, top 10)

| strategy               |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:-----------------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| rs-breakout-scout      |  13 |     11 |        2 | 0.8462 | 2.5548 |         1.4777 |         19.2097 |
| adx-trend-scout        |  10 |      8 |        2 | 0.8    | 6.913  |         1.1485 |         11.4848 |
| intermarket-flow-scout |  19 |     12 |        7 | 0.6316 | 1.9567 |         0.7744 |         14.7128 |
| quality-minus-junk     |  12 |      6 |        6 | 0.5    | 1.0514 |         0.0734 |          0.881  |


## ETF — Top symbols (by WR, min n=10, top 10)

| symbol   |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| QQQ      |  19 |     15 |        4 | 0.7895 | 4.6098 |         1.2542 |         23.8299 |
| XLK      |  16 |     12 |        4 | 0.75   | 4.2569 |         1.8582 |         29.731  |
| SPY      |  15 |      9 |        6 | 0.6    | 1.9524 |         0.4957 |          7.4361 |
| XLE      |  15 |      8 |        7 | 0.5333 | 1.1532 |         0.234  |          3.51   |
| IWM      |  19 |      7 |       12 | 0.3684 | 0.4073 |        -0.7802 |        -14.8242 |
| GLD      |  11 |      4 |        7 | 0.3636 | 0.6462 |        -0.5663 |         -6.229  |


## ETF — Direction split

| signal_type   |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:--------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| LONG          | 105 |     60 |       45 | 0.5714 | 1.3199 |         0.3468 |         36.4189 |


## ETF — Confidence buckets

| bucket    |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |
|:----------|----:|-------:|---------:|-------:|-------:|---------------:|
| <0.50     |  48 |     28 |       20 | 0.5833 | 1.5478 |         0.6292 |
| 0.50-0.60 |  35 |     16 |       19 | 0.4571 | 0.811  |        -0.1871 |
| 0.60-0.70 |  12 |     10 |        2 | 0.8333 | 3.9629 |         1.5781 |


## ETF — Edge candidates (WR≥0.45 AND PF≥1.10, n≥30)

_none found_


## ETF — Drag candidates (WR≤0.25 AND PF≤0.60, n≥30)

_none found_


## FOREX — Window table (last-N)

| window   |   n |   wins |   losses |   flat |     wr |   wr_excl_flat |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-------:|---------------:|-------:|---------------:|----------------:|
| last_20  |  20 |      3 |        2 |     15 | 0.15   |          0.6   | 1.1175 |         0.0104 |          0.2081 |
| last_50  |  50 |     21 |       14 |     15 | 0.42   |          0.6   | 3.8893 |         0.4402 |         22.0082 |
| last_100 |  96 |     35 |       36 |     25 | 0.3646 |          0.493 | 2.0628 |         0.2295 |         22.0326 |
| last_200 |  96 |     35 |       36 |     25 | 0.3646 |          0.493 | 2.0628 |         0.2295 |         22.0326 |
| all_96   |  96 |     35 |       36 |     25 | 0.3646 |          0.493 | 2.0628 |         0.2295 |         22.0326 |


## FOREX — Top strategies (by WR, min n=10, top 10)

| strategy            |   n |   wins |   losses |     wr |       pf |   mean_pnl_pct |   total_pnl_pct |
|:--------------------|----:|-------:|---------:|-------:|---------:|---------------:|----------------:|
| forex-rsi-ema-scout |  22 |     12 |       10 | 0.5455 |   1.6761 |         0.1785 |          3.927  |
| unknown             |  21 |      7 |       14 | 0.3333 |   0.8564 |        -0.0603 |         -1.2667 |
| MeanReversionBB     |  22 |      7 |        0 | 0.3182 | nan      |         0.7541 |         16.59   |


## FOREX — Top symbols (by WR, min n=10, top 10)

| symbol   |   n |   wins |   losses |   wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-----:|-------:|---------------:|----------------:|
| USDJPY=X |  10 |      3 |        4 |  0.3 | 0.7631 |        -0.0662 |         -0.6624 |
| EURUSD=X |  10 |      2 |        6 |  0.2 | 0.5137 |        -0.1662 |         -1.6616 |


## FOREX — Direction split

| signal_type   |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:--------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| LONG          |  65 |     25 |       31 | 0.3846 | 1.1666 |         0.0463 |          3.0084 |
| SHORT         |  31 |     10 |        5 | 0.3226 | 8.106  |         0.6137 |         19.0242 |


## FOREX — Confidence buckets

| bucket    |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |
|:----------|----:|-------:|---------:|-------:|-------:|---------------:|
| <0.50     |  64 |     25 |       24 | 0.3906 | 2.2737 |         0.291  |
| 0.60-0.70 |  10 |      2 |        2 | 0.2    | 4.3661 |         0.1103 |


## FOREX — Edge candidates (WR≥0.45 AND PF≥1.10, n≥30)

_none found_


## FOREX — Drag candidates (WR≤0.25 AND PF≤0.60, n≥30)

_none found_


## FUTURES — Window table (last-N)

| window   |   n |   wins |   losses |   flat |   wr |   wr_excl_flat | pf   |   mean_pnl_pct |   total_pnl_pct |
|:---------|----:|-------:|---------:|-------:|-----:|---------------:|:-----|---------------:|----------------:|
| last_20  |   2 |      2 |        0 |      0 |    1 |              1 |      |         8.4462 |         16.8924 |
| last_50  |   2 |      2 |        0 |      0 |    1 |              1 |      |         8.4462 |         16.8924 |
| last_100 |   2 |      2 |        0 |      0 |    1 |              1 |      |         8.4462 |         16.8924 |
| last_200 |   2 |      2 |        0 |      0 |    1 |              1 |      |         8.4462 |         16.8924 |
| all_2    |   2 |      2 |        0 |      0 |    1 |              1 |      |         8.4462 |         16.8924 |


## FUTURES — Top strategies (by WR, min n=10, top 10)

_empty_


## FUTURES — Top symbols (by WR, min n=10, top 10)

_empty_


## FUTURES — Direction split

| signal_type   |   n |   wins |   losses |   wr | pf   |   mean_pnl_pct |   total_pnl_pct |
|:--------------|----:|-------:|---------:|-----:|:-----|---------------:|----------------:|
| SHORT         |   2 |      2 |        0 |    1 |      |         8.4462 |         16.8924 |


## FUTURES — Confidence buckets

_empty_


## FUTURES — Edge candidates (WR≥0.45 AND PF≥1.10, n≥30)

_none found_


## FUTURES — Drag candidates (WR≤0.25 AND PF≤0.60, n≥30)

_none found_
