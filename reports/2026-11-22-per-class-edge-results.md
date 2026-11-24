# Per-class edge sweep — results, 2026-11-22

Window **2012-01-02 → 2026-11-22** · 40 cells · n_trials declared **29** · expected-max daily Sharpe **0.04695** · **PBO(CSCV) 0.345**

Every cell was pre-registered in `reports/hypothesis_registry.json` (H-200…H-225) and `reports/preregistration_2026-11-22_per_class.json` **before** the first run. Costs are round-trip: EQUITY/ETF/BOND/INDEX/MF 10 bps, CRYPTO 20, FOREX 5, COMMODITY 15, FUTURES 10, PENNY 10 (understated by design).

| class | id | cell | n | PF | mean trade % | daily bps | CI-LB | CI-LB @2× | halves | excess vs bench | DSR | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EQUITY | H-200:NVDA | tsmom_12_1 [NVDA] | 13 | 81.8382 | 113.4864 | 16.014 | 8.727 | 8.673 | [14.667, 17.362] | 10.278 | 0.8377 | **INSUFFICIENT_N** |
| EQUITY | H-201 | xsmom_top3_6m | 179 | 2.7395 | 2.3546 | 11.521 | 7.246 | 7.002 | [9.991, 13.051] | 5.784 | 0.9469 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:AMZN | tsmom_12_1 [AMZN] | 32 | 8.1148 | 15.1943 | 8.304 | 2.987 | 2.832 | [10.485, 6.122] | 2.567 | 0.5063 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:META | tsmom_12_1 [META] | 33 | 8.0905 | 13.5397 | 7.324 | 1.592 | 1.397 | [8.574, 6.074] | 1.527 | 0.331 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:MSFT | tsmom_12_1 [MSFT] | 23 | 14.1081 | 21.3514 | 6.856 | 2.619 | 2.525 | [7.729, 5.983] | 1.119 | 0.498 | **INSUFFICIENT_N** |
| EQUITY | H-200 | tsmom_12_1_long_flat | 37 | 6.8908 | 6.8869 | 6.13 | 1.449 | 1.233 | [3.007, 9.253] | 0.393 | 0.317 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:GOOGL | tsmom_12_1 [GOOGL] | 33 | 10.0959 | 6.0511 | 5.787 | 1.188 | 1.004 | [4.24, 7.335] | 0.05 | 0.3008 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:JPM | tsmom_12_1 [JPM] | 31 | 4.9455 | 7.2033 | 4.75 | 0.989 | 0.833 | [4.423, 5.077] | -0.987 | 0.2358 | **FAILS_BENCHMARK** |
| EQUITY | H-200:UNH | tsmom_12_1 [UNH] | 43 | 3.6859 | 7.8711 | 4.142 | -0.707 | -0.905 | [8.256, 0.028] | -1.595 | 0.1174 | **REFUTED_OR_WEAK** |
| EQUITY | H-200:JNJ | tsmom_12_1 [JNJ] | 43 | 2.1064 | 2.3031 | 2.178 | -0.844 | -1.074 | [2.551, 1.805] | -3.559 | 0.0647 | **REFUTED_OR_WEAK** |
| EQUITY | H-226 | xsmom_ls_top3_bottom3_6m | 179 | 1.3194 | 0.368 | 1.79 | -0.75 | -1.006 | [1.567, 2.013] | -3.947 | 0.0618 | **REFUTED_OR_WEAK** |
| EQUITY | H-200:XOM | tsmom_12_1 [XOM] | 40 | 2.0158 | 2.0111 | 1.698 | -1.7 | -1.926 | [-1.77, 5.166] | -4.038 | 0.0255 | **REFUTED_OR_WEAK** |
| EQUITY | H-222 | pead_sue12_20d | 13 | 0.9807 | -0.0579 | -579.448 | -37641.2 | -39641.2 | [-26080.655, 21278.729] | -32760.131 | 0.4248 | **INSUFFICIENT_N** |
| ETF | H-205 | xsmom_top3_6m | 179 | 1.8819 | 1.0328 | 5.053 | 2.007 | 1.73 | [3.577, 6.529] | -0.684 | 0.5152 | **FAILS_BENCHMARK** |
| ETF | H-225 | dual_momentum_top2_12m | 179 | 1.6761 | 0.7706 | 3.8 | 0.826 | 0.622 | [3.333, 4.267] | -1.936 | 0.3005 | **FAILS_BENCHMARK** |
| FUTURES | H-218 | xsmom_top2_6m | 179 | 1.5074 | 0.5602 | 2.806 | 0.186 | -0.054 | [3.543, 2.069] | -2.282 | 0.1474 | **FAILS_2X_COST** |
| FUTURES | H-214 | tsmom_12_1 [ES=F] | 49 | 2.391 | 2.0766 | 2.544 | 0.039 | -0.225 | [3.005, 2.082] | -2.544 | 0.1257 | **FAILS_2X_COST** |
| INDEX | H-221 | xsmom_top2_6m | 179 | 1.845 | 0.9779 | 4.644 | 1.613 | 1.357 | [4.426, 4.862] | -0.905 | 0.4553 | **FAILS_BENCHMARK** |
| INDEX | H-217 | tsmom_12_1 [^GSPC] | 23 | 4.1184 | 4.6206 | 2.873 | 0.301 | 0.165 | [1.9, 3.847] | -2.863 | 0.1647 | **INSUFFICIENT_N** |
| BOND | H-213 | xsmom_top2_6m | 179 | 1.2705 | 0.1608 | 0.776 | -0.453 | -0.659 | [1.378, 0.174] | -4.961 | 0.0382 | **REFUTED_OR_WEAK** |
| BOND | H-212 | tsmom_12_1 [TLT] | 51 | 0.8993 | -0.1198 | -0.079 | -1.916 | -2.197 | [0.629, -0.786] | -5.815 | 0.0016 | **REFUTED_OR_WEAK** |
| COMMODITY | H-211 | xsmom_top2_6m | 179 | 1.1599 | 0.4168 | 2.377 | -3.757 | -4.148 | [-2.828, 7.579] | 1.173 | 0.0179 | **DATA_INTEGRITY_FAIL** |
| COMMODITY | H-210 | tsmom_12_1 [GC=F] | 48 | 2.7205 | 1.8992 | 1.904 | -0.724 | -1.132 | [-1.527, 5.335] | 0.692 | 0.0697 | **DATA_INTEGRITY_FAIL** |
| COMMODITY | H-224 | xsmom_top3_6m_etf | 179 | 1.1062 | 0.2057 | 1.114 | -2.785 | -3.146 | [-4.632, 6.859] | -0.07 | 0.0094 | **REFUTED_OR_WEAK** |
| COMMODITY | H-223 | tsmom_12_1_etf_basket | 179 | 1.0922 | 0.0751 | 0.361 | -1.324 | -1.624 | [-1.65, 2.372] | -0.822 | 0.0066 | **REFUTED_OR_WEAK** |
| FOREX | H-208:USDJPY=X | tsmom_ls [USDJPY=X] | 121 | 1.7686 | 0.4267 | 1.211 | -0.52 | -0.827 | [1.762, 0.66] | -0.11 | 0.0587 | **REFUTED_OR_WEAK** |
| FOREX | H-208:AUDUSD=X | tsmom_ls [AUDUSD=X] | 86 | 1.1277 | 0.0814 | 0.133 | -1.658 | -1.879 | [0.443, -0.177] | -1.195 | 0.0027 | **REFUTED_OR_WEAK** |
| FOREX | H-208 | tsmom_ls_portfolio | 926 | 0.8403 | -0.0447 | 0.103 | -0.858 | -0.858 | [0.443, -0.237] | -1.217 | 0.0032 | **REFUTED_OR_WEAK** |
| FOREX | H-209 | xsmom_top2_3m | 179 | 1.0244 | 0.0166 | 0.076 | -1.171 | -1.329 | [-0.594, 0.745] | -1.244 | 0.0025 | **REFUTED_OR_WEAK** |
| FOREX | H-208:USDCAD=X | tsmom_ls [USDCAD=X] | 150 | 0.9923 | -0.0039 | -0.074 | -1.379 | -1.746 | [0.499, -0.647] | -1.403 | 0.0012 | **REFUTED_OR_WEAK** |
| FOREX | H-208:EURUSD=X | tsmom_ls [EURUSD=X] | 102 | 0.9123 | -0.0563 | -0.153 | -1.622 | -1.874 | [-0.012, -0.295] | -1.482 | 0.0009 | **REFUTED_OR_WEAK** |
| FOREX | H-208:GBPUSD=X | tsmom_ls [GBPUSD=X] | 113 | 0.7428 | -0.1871 | -0.537 | -2.311 | -2.618 | [-0.451, -0.623] | -1.857 | 0.0002 | **REFUTED_OR_WEAK** |
| MUTUAL_FUND | H-216 | tsmom_12_1 [VFIAX] | 28 | 8.5327 | 5.3326 | 3.875 | 1.286 | 1.132 | [3.003, 4.747] | -1.861 | 0.3598 | **INSUFFICIENT_N** |
| MUTUAL_FUND | H-220 | xsmom_top2_6m | 179 | 1.6984 | 0.7767 | 3.805 | 0.997 | 0.727 | [4.844, 2.766] | -1.932 | 0.3549 | **FAILS_BENCHMARK** |
| PENNY_STOCK | H-215 | tsmom_12_1 [PLUG] | 26 | 4.3496 | 24.0678 | 8.691 | -3.254 | -3.397 | [6.967, 10.415] | 3.985 | 0.0744 | **INSUFFICIENT_N** |
| PENNY_STOCK | H-219 | xsmom_top2_6m | 179 | 1.1845 | 1.1347 | 4.565 | -8.636 | -8.898 | [2.967, 6.162] | -0.141 | 0.0123 | **REFUTED_OR_WEAK** |
| CRYPTO | H-206 | tsmom_6m_long_flat | 60 | 9.4234 | 25.8342 | 15.911 | 8.452 | 7.913 | [22.172, 9.65] | -1.021 | 0.7752 | **FAILS_BENCHMARK** |
| CRYPTO | H-207 | xsmom_top3_3m | 147 | 1.7661 | 4.6083 | 12.47 | 0.714 | 0.417 | [7.505, 17.435] | -4.463 | 0.1678 | **FAILS_BENCHMARK** |
| CRYPTO | H-228 | funding_carry_delta_neutral | 71 | 2.0702 | 0.2953 | 0.925 | 0.143 | -0.857 | [1.504, 0.346] | -6.812 | 0.8276 | **FAILS_2X_COST** |
| CRYPTO | H-227 | xsmom_ls_top2_bottom2_3m | 147 | 0.9205 | -0.2566 | -1.269 | -5.9 | -6.401 | [-2.182, -0.355] | -18.201 | 0.0001 | **REFUTED_OR_WEAK** |

## Class verdicts

| class | cells | best cell | verdict | what it means |
|---|---|---|---|---|
| EQUITY | 13 | H-201 xsmom_top3_6m (CI-LB 7.246 bps, n=179, DSR 0.9469) | FAILS_MULTIPLICITY | survives cost/stability but not the trial-count-adjusted Sharpe bar |
| ETF | 2 | H-205 xsmom_top3_6m (CI-LB 2.007 bps, n=179, DSR 0.5152) | FAILS_BENCHMARK | beats cash but not buy-and-hold of its own universe |
| FUTURES | 2 | H-218 xsmom_top2_6m (CI-LB 0.186 bps, n=179, DSR 0.1474) | FAILS_2X_COST | signal exists, cannot pay for itself at 2× cost |
| INDEX | 2 | H-221 xsmom_top2_6m (CI-LB 1.613 bps, n=179, DSR 0.4553) | FAILS_BENCHMARK | beats cash but not buy-and-hold of its own universe |
| BOND | 2 | H-213 xsmom_top2_6m (CI-LB -0.453 bps, n=179, DSR 0.0382) | REFUTED_OR_WEAK | no usable signal at this resolution |
| COMMODITY | 4 | H-210 tsmom_12_1 [GC=F] (CI-LB -0.724 bps, n=48, DSR 0.0697) | REFUTED_OR_WEAK | no usable signal at this resolution |
| FOREX | 7 | H-208:USDJPY=X tsmom_ls [USDJPY=X] (CI-LB -0.52 bps, n=121, DSR 0.0587) | REFUTED_OR_WEAK | no usable signal at this resolution |
| MUTUAL_FUND | 2 | H-220 xsmom_top2_6m (CI-LB 0.997 bps, n=179, DSR 0.3549) | FAILS_BENCHMARK | beats cash but not buy-and-hold of its own universe |
| PENNY_STOCK | 2 | H-219 xsmom_top2_6m (CI-LB -8.636 bps, n=179, DSR 0.0123) | REFUTED_OR_WEAK | no usable signal at this resolution |
| CRYPTO | 4 | H-206 tsmom_6m_long_flat (CI-LB 8.452 bps, n=60, DSR 0.7752) | FAILS_BENCHMARK | beats cash but not buy-and-hold of its own universe |

## Volatility-matched comparison (G6b) — reported, not a promotion

G6 as written asks a cell to beat buy-and-hold of its own universe on raw daily return. No de-risking rule can pass that: holding cash part of the time must lower the mean. G6b scales each cell to the benchmark's ex-post volatility (capped at 4×) and compares there. It is a separate yardstick, applied to every cell alike, and **no cell is promoted on G6b alone** — it tells us which classes have a risk-adjusted edge worth a forward pod, nothing more.

| class | id | cell | vol | bench vol | lev | matched bps | matched CI-LB | halves | CAGR | bench CAGR | levered CAGR | MDD | bench MDD | G6b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EQUITY | H-201 | xsmom_top3_6m | 24.85% | 16.56% | 0.666× | 1.94 | -0.533 | [1.192, 2.688] | 29.6% | 13.97% | 19.68% | -36.94% | -33.72% | — |
| EQUITY | H-200:NVDA | tsmom_12_1 [NVDA] | 40.48% | 16.56% | 0.409× | 0.813 | -2.112 | [0.533, 1.093] | 38.02% | 13.97% | 16.34% | -57.77% | -33.72% | — |
| EQUITY | H-200:MSFT | tsmom_12_1 [MSFT] | 23.22% | 16.56% | 0.713× | -0.848 | -3.573 | [0.045, -1.742] | 15.69% | 13.97% | 11.57% | -29.14% | -33.72% | — |
| EQUITY | H-200:AMZN | tsmom_12_1 [AMZN] | 27.92% | 16.56% | 0.593× | -0.813 | -4.045 | [0.752, -2.378] | 18.57% | 13.97% | 11.67% | -37.84% | -33.72% | — |
| EQUITY | H-200 | tsmom_12_1_long_flat | 24.84% | 16.56% | 0.666× | -1.652 | -4.471 | [-3.462, 0.159] | 13.16% | 13.97% | 9.33% | -38.23% | -33.72% | — |
| EQUITY | H-200:GOOGL | tsmom_12_1 [GOOGL] | 23.92% | 16.56% | 0.692× | -1.731 | -4.616 | [-2.531, -0.931] | 12.43% | 13.97% | 9.11% | -34.9% | -33.72% | — |
| EQUITY | H-200:JPM | tsmom_12_1 [JPM] | 21.45% | 16.56% | 0.772× | -2.071 | -4.845 | [-2.053, -2.09] | 10.14% | 13.97% | 8.18% | -44.83% | -33.72% | — |
| EQUITY | H-200:META | tsmom_12_1 [META] | 29.35% | 16.68% | 0.568× | -1.635 | -5.238 | [-0.672, -2.599] | 15.14% | 14.12% | 9.51% | -51.69% | -33.72% | — |
| EQUITY | H-200:UNH | tsmom_12_1 [UNH] | 24.27% | 16.56% | 0.682× | -2.911 | -6.352 | [0.166, -5.989] | 7.72% | 13.97% | 5.9% | -59.16% | -33.72% | — |
| EQUITY | H-200:JNJ | tsmom_12_1 [JNJ] | 15.68% | 16.56% | 1.056× | -3.437 | -7.019 | [-2.772, -4.101] | 4.35% | 13.97% | 4.52% | -47.55% | -33.72% | — |
| EQUITY | H-200:XOM | tsmom_12_1 [XOM] | 17.98% | 16.56% | 0.921× | -4.173 | -8.021 | [-7.095, -1.25] | 2.7% | 13.97% | 2.6% | -46.46% | -33.72% | — |
| EQUITY | H-226 | xsmom_ls_top3_bottom3_6m | 13.08% | 16.56% | 1.266× | -3.472 | -8.293 | [-3.483, -3.461] | 3.72% | 13.97% | 4.43% | -42.15% | -33.72% | — |
| ETF | H-205 | xsmom_top3_6m | 16.86% | 16.56% | 0.982× | -0.774 | -2.884 | [-1.952, 0.404] | 11.97% | 13.97% | 11.77% | -25.5% | -33.72% | — |
| ETF | H-225 | dual_momentum_top2_12m | 15.74% | 16.56% | 1.052× | -1.74 | -4.083 | [-1.96, -1.52] | 8.69% | 13.97% | 9.08% | -29.61% | -33.72% | — |
| FUTURES | H-214 | tsmom_12_1 [ES=F] | 14.42% | 16.74% | 1.161× | -2.135 | -3.7 | [-1.243, -3.027] | 5.51% | 12.09% | 6.22% | -35.59% | -34.45% | — |
| FUTURES | H-218 | xsmom_top2_6m | 14.98% | 16.74% | 1.117× | -1.952 | -4.143 | [-0.772, -3.132] | 6.13% | 12.09% | 6.71% | -33.82% | -34.45% | — |
| INDEX | H-221 | xsmom_top2_6m | 16.34% | 16.28% | 0.996× | -0.921 | -2.568 | [-0.878, -0.965] | 10.91% | 13.49% | 10.88% | -29.56% | -33.72% | — |
| INDEX | H-217 | tsmom_12_1 [^GSPC] | 14.79% | 16.56% | 1.119× | -2.521 | -4.09 | [-3.339, -1.702] | 6.33% | 13.97% | 6.96% | -33.92% | -33.72% | — |
| BOND | H-213 | xsmom_top2_6m | 6.85% | 16.56% | 2.418× | -3.861 | -7.857 | [-2.135, -5.588] | 1.74% | 13.97% | 3.41% | -19.82% | -33.72% | — |
| BOND | H-212 | tsmom_12_1 [TLT] | 9.78% | 16.56% | 1.693× | -5.87 | -10.462 | [-4.401, -7.339] | -0.67% | 13.97% | -1.69% | -38.27% | -33.72% | — |
| COMMODITY | H-210 | tsmom_12_1 [GC=F] | 13.39% | 17.02% | 1.271× | 1.208 | -3.177 | [0.719, 1.697] | 3.98% | 1.61% | 4.75% | -27.9% | -63.31% | — |
| COMMODITY | H-224 | xsmom_top3_6m_etf | 20.8% | 17.03% | 0.819× | -0.272 | -3.223 | [-1.013, 0.469] | 0.64% | 1.54% | 0.85% | -67.81% | -63.71% | — |
| COMMODITY | H-223 | tsmom_12_1_etf_basket | 9.0% | 17.03% | 1.893× | -0.5 | -3.56 | [-0.343, -0.657] | 0.51% | 1.54% | 0.27% | -33.44% | -63.71% | — |
| COMMODITY | H-211 | xsmom_top2_6m | 29.91% | 17.01% | 0.569× | 0.148 | -3.697 | [1.04, -0.744] | 1.52% | 1.59% | 1.98% | -67.21% | -63.42% | — |
| FOREX | H-208:USDJPY=X | tsmom_ls [USDJPY=X] | 8.83% | 6.88% | 0.779× | -0.377 | -2.094 | [0.403, -1.157] | 2.7% | 3.14% | 2.16% | -26.4% | -14.24% | — |
| FOREX | H-208 | tsmom_ls_portfolio | 5.11% | 6.88% | 1.347× | -1.181 | -2.655 | [-0.387, -1.975] | 0.13% | 3.14% | 0.11% | -18.17% | -14.24% | — |
| FOREX | H-208:AUDUSD=X | tsmom_ls [AUDUSD=X] | 9.55% | 6.88% | 0.72× | -1.233 | -2.776 | [-0.681, -1.784] | -0.12% | 3.16% | 0.01% | -22.67% | -14.24% | — |
| FOREX | H-208:USDCAD=X | tsmom_ls [USDCAD=X] | 6.64% | 6.88% | 1.035× | -1.405 | -2.978 | [-0.484, -2.327] | -0.41% | 3.16% | -0.43% | -34.17% | -14.24% | — |
| FOREX | H-209 | xsmom_top2_3m | 6.38% | 6.88% | 1.077× | -1.238 | -3.063 | [-1.623, -0.853] | -0.01% | 3.14% | -0.03% | -23.37% | -14.24% | — |
| FOREX | H-208:EURUSD=X | tsmom_ls [EURUSD=X] | 7.4% | 6.88% | 0.93× | -1.472 | -3.128 | [-0.999, -1.945] | -0.66% | 3.16% | -0.59% | -29.29% | -14.24% | — |
| FOREX | H-208:GBPUSD=X | tsmom_ls [GBPUSD=X] | 8.4% | 6.88% | 0.818× | -1.759 | -3.392 | [-1.339, -2.179] | -1.69% | 3.14% | -1.33% | -33.84% | -14.24% | — |
| MUTUAL_FUND | H-220 | xsmom_top2_6m | 14.81% | 16.56% | 1.118× | -1.483 | -2.957 | [-0.05, -2.915] | 8.86% | 13.97% | 9.79% | -30.84% | -33.72% | — |
| MUTUAL_FUND | H-216 | tsmom_12_1 [VFIAX] | 15.01% | 16.56% | 1.103× | -1.461 | -2.974 | [-2.152, -0.77] | 9.02% | 13.97% | 9.85% | -33.83% | -33.72% | — |
| PENNY_STOCK | H-215 | tsmom_12_1 [PLUG] | 57.63% | 21.13% | 0.367× | -1.519 | -7.126 | [-2.279, -0.759] | 6.03% | 10.09% | 6.01% | -93.15% | -41.13% | — |
| PENNY_STOCK | H-219 | xsmom_top2_6m | 68.4% | 21.13% | 0.309× | -3.295 | -8.11 | [-3.917, -2.674] | -10.44% | 10.09% | 1.37% | -98.54% | -41.13% | — |
| CRYPTO | H-206 | tsmom_6m_long_flat | 43.39% | 54.72% | 1.261× | 3.136 | -3.277 | [5.851, 0.422] | 35.94% | 31.75% | 42.81% | -64.9% | -83.4% | — |
| CRYPTO | H-207 | xsmom_top3_3m | 60.85% | 54.72% | 0.899× | -5.718 | -14.765 | [-15.366, 3.929] | 13.63% | 31.75% | 14.12% | -89.76% | -83.4% | — |
| CRYPTO | H-228 | funding_carry_delta_neutral | 1.71% | 47.08% | 4.0× | -4.036 | -16.253 | [-3.059, -5.013] | 2.34% | 8.79% | 9.5% | -14.12% | -76.63% | — |
| CRYPTO | H-227 | xsmom_ls_top2_bottom2_3m | 24.39% | 54.72% | 2.244× | -19.78 | -34.643 | [-27.013, -12.547] | -5.96% | 31.75% | -19.77% | -71.25% | -83.4% | — |

Cells clearing G6b (matched-vol excess > 0, CI-LB > 0, both halves > 0): **0** — none

**Cells clearing every backtest gate: 0**

## Reading this honestly

- A `PASSES_ALL_BACKTEST_GATES` cell is a **backtest** result. It has not been forward-tested, so it is not an edge yet (G8 = n ≥ 100 closed forward trades).
- `excess vs bench` is the beta check: a cell can be profitable and still be worthless if it just tracks its own universe.
- `CI-LB @2×` is the cost stress; `FAILS_2X_COST` cells are the gross-looking strategies this desk has over-trusted before.
- PENNY_STOCK costs are understated (no market impact), so even a passing cell there needs a liquidity haircut first.
- MUTUAL_FUND cells trade at daily NAV with next-day execution; they can support a fund-selection rule, not a trading edge.

Reproduce: `python3 tools/per_class_edge_harness.py --out reports/per_class_edge_2026-11-22.json --md reports/per_class_edge_2026-11-22.md --n-trials 29` then `python3 tools/build_per_class_report.py`

## Data integrity (why COMMODITY is not merely 'weak')

| symbol | rows | negative prices | |ret|>8% | max |ret| | recurring month-day spikes | usable |
|---|---|---|---|---|---|---|
| GC=F | 3744 | 0 | 2 | 10.8% | — | True |
| CL=F | 3744 | 1 | 55 | 306.0% | {'03-06': [2020, 2026], '03-09': [2020, 2022], '03-10': [2020, 2026], '04-02': [2020, 2026], '04-17': [2020, 2026]} | False |
| SI=F | 3743 | 0 | 24 | 31.3% | — | True |
| NG=F | 3745 | 0 | 150 | 47.5% | {'06-14': [2012, 2022], '09-27': [2012, 2021, 2024], '10-31': [2012, 2022], '01-29': [2014, 2024, 2026], '01-30': [2014, 2018, 2023, 2024, 2025, 2026], '01-14': [2015, 2019, 2026], '01-20': [2015, 2026], '10-29': [2015, 2020], '12-21': [2015, 2016], '12-28': [2015, 2018, 2020, 2022], '10-28': [2016, 2022, 2024], '01-03': [2017, 2023, 2025], '02-21': [2017, 2023, 2024], '01-28': [2019, 2022], '11-29': [2019, 2021], '05-06': [2020, 2022], '05-18': [2020, 2023], '09-29': [2020, 2025], '02-01': [2021, 2023], '12-30': [2021, 2024, 2025], '01-27': [2022, 2025], '02-02': [2022, 2026], '02-03': [2022, 2025], '10-30': [2024, 2025]} | False |
| ZC=F | 3741 | 0 | 5 | 23.6% | {'07-15': [2013, 2021, 2022]} | False |
| HG=F | 3744 | 0 | 3 | 22.3% | — | True |

A series with roll-gap spikes on the same calendar day in multiple years, or a negative print, cannot confirm or refute a strategy. COMMODITY is reported as `DATA_INTEGRITY_FAIL` until rebuilt on roll-adjusted contracts.
