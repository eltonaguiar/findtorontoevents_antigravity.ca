# Edge Detection Report - 2026-05-16

## Statistical Edge per Asset Class and Strategy
Edge Score Formula: `(Sharpe * WinRate) / MaxDD` (higher is better)

### FOREX
| asset_class   | strategy            |   n |   win_rate |   mean_pnl |   sharpe |   max_dd |   edge_score |   ci_low |   ci_high |
|:--------------|:--------------------|----:|-----------:|-----------:|---------:|---------:|-------------:|---------:|----------:|
| FOREX         | signal_validation   |  22 |       31.8 |     0.7541 |     9.41 |   0.01   |     29944    |   0.2226 |    1.2856 |
| FOREX         | alpha_engine_fast   |  13 |       53.8 |     0.1534 |     2.8  |   2.4581 |        61.43 |  -0.3187 |    0.6256 |
| FOREX         | kimi_riseoftheclaw  |  46 |       41.3 |     0.0294 |     0.49 |   7.0845 |         2.83 |  -0.2483 |    0.3071 |
| FOREX         | multi_asset_scanner |  11 |        0   |    -0.0185 |    -4.79 |   0.2037 |        -0    |  -0.0548 |    0.0178 |

### CRYPTO
| asset_class   | strategy                 |   n |   win_rate |   mean_pnl |   sharpe |   max_dd |   edge_score |   ci_low |   ci_high |
|:--------------|:-------------------------|----:|-----------:|-----------:|---------:|---------:|-------------:|---------:|----------:|
| CRYPTO        | signal_validation        |  30 |       60   |     1.056  |     7.51 |   7.53   |        59.84 |   0.2572 |    1.8548 |
| CRYPTO        | alpha_engine_fast        |   6 |       50   |     1.6888 |     5.26 |   7.4036 |        35.53 |  -2.3881 |    5.7657 |
| CRYPTO        | mega_mutation            |  94 |       60.6 |     1.7009 |     6.84 |  21.873  |        18.96 |   0.9028 |    2.4989 |
| CRYPTO        | baby_strats_forward      | 532 |       52.6 |     0.1678 |     3.08 |  11.4318 |        14.16 |   0.0942 |    0.2413 |
| CRYPTO        | claude_gainer_st         | 106 |       58.5 |     0.2638 |     3.34 |  14.18   |        13.79 |   0.0252 |    0.5023 |
| CRYPTO        | aggregated_picks         |  51 |       51   |     0.766  |     4.13 |  15.3272 |        13.72 |  -0.0428 |    1.5748 |
| CRYPTO        | dna_winner_picks         | 109 |       52.3 |     0.6133 |     4.49 |  18.57   |        12.63 |   0.2059 |    1.0207 |
| CRYPTO        | ml_bg_system_f           |  11 |       54.5 |     1.2861 |     3.22 |  15.8349 |        11.1  |  -2.4576 |    5.0299 |
| CRYPTO        | kimi_riseoftheclaw       |  92 |       62   |     1.455  |     4.33 |  30.267  |         8.86 |   0.3651 |    2.5448 |
| CRYPTO        | mercury2                 | 171 |       41.5 |     0.418  |     2    |  39.7716 |         2.09 |  -0.0794 |    0.9155 |
| CRYPTO        | signal_engine_mutations  |  92 |       38   |     0.1257 |     1.01 |  21.7    |         1.77 |  -0.2775 |    0.5288 |
| CRYPTO        | quan_engine              | 334 |       34.4 |     0.2457 |     1.86 |  42.02   |         1.52 |   0.0204 |    0.471  |
| CRYPTO        | dna_rapid_fire_mutations |  17 |       41.2 |     0.03   |     0.23 |   8.28   |         1.13 |  -0.9643 |    1.0243 |
| CRYPTO        | regime_terminal          |  70 |       34.3 |     0.0429 |     0.32 |  18      |         0.6  |  -0.4611 |    0.5469 |
| CRYPTO        | alpha_engine             | 374 |       44.9 |     0.0541 |     0.29 |  43.0826 |         0.3  |  -0.2435 |    0.3516 |
| CRYPTO        | luxalgo_filters          | 775 |       44.8 |     0.0727 |     0.41 | 203.216  |         0.09 |  -0.1238 |    0.2691 |
| CRYPTO        | ml_crypto_pred           |   7 |        0   |    -1.5714 |   -46.67 |   9      |        -0    |  -1.9674 |   -1.1754 |
| CRYPTO        | mutation_lab             |  15 |       20   |    -0.7227 |    -6.37 |  18.78   |        -6.78 |  -1.6346 |    0.1893 |
| CRYPTO        | battleground             |  72 |       41.7 |    -0.2245 |    -4.01 |  21.6018 |        -7.74 |  -0.4297 |   -0.0193 |

### EQUITY
| asset_class   | strategy           |   n |   win_rate |   mean_pnl |   sharpe |   max_dd |   edge_score |   ci_low |   ci_high |
|:--------------|:-------------------|----:|-----------:|-----------:|---------:|---------:|-------------:|---------:|----------:|
| EQUITY        | alpha_engine_fast  |  11 |       72.7 |     0.203  |     2.38 |   3.5965 |        48.18 |  -0.5963 |    1.0024 |
| EQUITY        | ml_bg_system_f     |   8 |       50   |     0.6184 |     1.59 |  10.2371 |         7.74 |  -3.6723 |    4.9091 |
| EQUITY        | kimi_riseoftheclaw | 210 |       56.7 |     1.6237 |     4.61 |  60.1681 |         4.34 |   0.8679 |    2.3794 |
| EQUITY        | stocksunify2       |  11 |        0   |     0      |     0    |   0.01   |         0    |   0      |    0      |
| EQUITY        | goldmine_stocks    |   5 |       60   |    -0.0618 |    -0.81 |   2.0166 |       -24.18 |  -1.1197 |    0.9962 |

### COMMODITY
| asset_class   | strategy               |   n |   win_rate |   mean_pnl |   sharpe |   max_dd |   edge_score |   ci_low |   ci_high |
|:--------------|:-----------------------|----:|-----------:|-----------:|---------:|---------:|-------------:|---------:|----------:|
| COMMODITY     | multi_asset_copytrader |  33 |       54.5 |     1.6741 |     6.39 |  27.8986 |        12.49 |   0.2551 |    3.093  |
| COMMODITY     | multi_asset_cot        |  30 |       60   |     1.1269 |     4    |  34.9213 |         6.87 |  -0.4735 |    2.7274 |

### ETF
| asset_class   | strategy           |   n |   win_rate |   mean_pnl |   sharpe |   max_dd |   edge_score |   ci_low |   ci_high |
|:--------------|:-------------------|----:|-----------:|-----------:|---------:|---------:|-------------:|---------:|----------:|
| ETF           | kimi_riseoftheclaw |  99 |       56.6 |     0.4134 |     2.17 |  40.3993 |         3.04 |  -0.1815 |    1.0083 |

### BOND
| asset_class   | strategy           |   n |   win_rate |   mean_pnl |   sharpe |   max_dd |   edge_score |   ci_low |   ci_high |
|:--------------|:-------------------|----:|-----------:|-----------:|---------:|---------:|-------------:|---------:|----------:|
| BOND          | kimi_riseoftheclaw |   9 |       44.4 |    -0.2332 |    -4.42 |   3.0629 |       -64.07 |  -0.7809 |    0.3145 |

