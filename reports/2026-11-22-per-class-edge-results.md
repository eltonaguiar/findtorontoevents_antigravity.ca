# Per-class edge sweep — results, 2026-11-22

Window **2012-01-02 → 2026-11-22** · 33 cells · n_trials declared **22** · expected-max daily Sharpe **0.03981** · **PBO(CSCV) 0.09**

Every cell was pre-registered in `reports/hypothesis_registry.json` (H-200…H-221) and `reports/preregistration_2026-11-22_per_class.json` **before** the first run. Costs are round-trip: EQUITY/ETF/BOND/INDEX/MF 10 bps, CRYPTO 20, FOREX 5, COMMODITY 15, FUTURES 10, PENNY 10 (understated by design).

| class | id | cell | n | PF | mean trade % | daily bps | CI-LB | CI-LB @2× | halves | excess vs bench | DSR | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EQUITY | H-200:NVDA | tsmom_12_1 [NVDA] | 13 | 81.8382 | 113.4864 | 16.014 | 8.727 | 8.673 | [14.667, 17.362] | 10.278 | 0.9235 | **INSUFFICIENT_N** |
| EQUITY | H-201 | xsmom_top3_6m | 179 | 2.7395 | 2.3546 | 11.521 | 7.246 | 7.002 | [9.991, 13.051] | 5.784 | 0.9797 | **PASSES_ALL_BACKTEST_GATES** |
| EQUITY | H-200:AMZN | tsmom_12_1 [AMZN] | 32 | 8.1148 | 15.1943 | 8.304 | 2.987 | 2.832 | [10.485, 6.122] | 2.567 | 0.6756 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:META | tsmom_12_1 [META] | 33 | 8.0905 | 13.5397 | 7.324 | 1.592 | 1.397 | [8.574, 6.074] | 1.527 | 0.4953 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:MSFT | tsmom_12_1 [MSFT] | 23 | 14.1081 | 21.3514 | 6.856 | 2.619 | 2.525 | [7.729, 5.983] | 1.119 | 0.666 | **INSUFFICIENT_N** |
| EQUITY | H-200 | tsmom_12_1_long_flat | 37 | 6.8908 | 6.8869 | 6.13 | 1.449 | 1.233 | [3.007, 9.253] | 0.393 | 0.4844 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:GOOGL | tsmom_12_1 [GOOGL] | 33 | 10.0959 | 6.0511 | 5.787 | 1.188 | 1.004 | [4.24, 7.335] | 0.05 | 0.4659 | **FAILS_MULTIPLICITY** |
| EQUITY | H-200:JPM | tsmom_12_1 [JPM] | 31 | 4.9455 | 7.2033 | 4.75 | 0.989 | 0.833 | [4.423, 5.077] | -0.987 | 0.3881 | **FAILS_BENCHMARK** |
| EQUITY | H-200:UNH | tsmom_12_1 [UNH] | 43 | 3.6859 | 7.8711 | 4.142 | -0.707 | -0.905 | [8.256, 0.028] | -1.595 | 0.2234 | **REFUTED_OR_WEAK** |
| EQUITY | H-200:JNJ | tsmom_12_1 [JNJ] | 43 | 2.1064 | 2.3031 | 2.178 | -0.844 | -1.074 | [2.551, 1.805] | -3.559 | 0.1397 | **REFUTED_OR_WEAK** |
| EQUITY | H-200:XOM | tsmom_12_1 [XOM] | 40 | 2.0158 | 2.0111 | 1.698 | -1.7 | -1.926 | [-1.77, 5.166] | -4.038 | 0.0648 | **REFUTED_OR_WEAK** |
| ETF | H-205 | xsmom_top3_6m | 179 | 1.8819 | 1.0328 | 5.053 | 2.007 | 1.73 | [3.577, 6.529] | -0.684 | 0.6804 | **FAILS_BENCHMARK** |
| FUTURES | H-218 | xsmom_top2_6m | 179 | 1.5074 | 0.5602 | 2.806 | 0.186 | -0.054 | [3.543, 2.069] | -2.282 | 0.2699 | **FAILS_2X_COST** |
| FUTURES | H-214 | tsmom_12_1 [ES=F] | 49 | 2.391 | 2.0766 | 2.544 | 0.039 | -0.225 | [3.005, 2.082] | -2.544 | 0.2374 | **FAILS_2X_COST** |
| INDEX | H-221 | xsmom_top2_6m | 179 | 1.845 | 0.9779 | 4.644 | 1.613 | 1.357 | [4.426, 4.862] | -0.905 | 0.6269 | **FAILS_BENCHMARK** |
| INDEX | H-217 | tsmom_12_1 [^GSPC] | 23 | 4.1184 | 4.6206 | 2.873 | 0.301 | 0.165 | [1.9, 3.847] | -2.863 | 0.2936 | **INSUFFICIENT_N** |
| BOND | H-213 | xsmom_top2_6m | 179 | 1.2705 | 0.1608 | 0.776 | -0.453 | -0.659 | [1.378, 0.174] | -4.961 | 0.0909 | **REFUTED_OR_WEAK** |
| BOND | H-212 | tsmom_12_1 [TLT] | 51 | 0.8993 | -0.1198 | -0.079 | -1.916 | -2.197 | [0.629, -0.786] | -5.815 | 0.006 | **REFUTED_OR_WEAK** |
| COMMODITY | H-211 | xsmom_top2_6m | 179 | 1.1599 | 0.4168 | 2.377 | -3.757 | -4.148 | [-2.828, 7.579] | 1.173 | 0.0481 | **REFUTED_OR_WEAK** |
| COMMODITY | H-210 | tsmom_12_1 [GC=F] | 48 | 2.7205 | 1.8992 | 1.904 | -0.724 | -1.132 | [-1.527, 5.335] | 0.692 | 0.148 | **REFUTED_OR_WEAK** |
| FOREX | H-208:USDJPY=X | tsmom_ls [USDJPY=X] | 121 | 1.7686 | 0.4267 | 1.211 | -0.52 | -0.827 | [1.762, 0.66] | -0.11 | 0.131 | **REFUTED_OR_WEAK** |
| FOREX | H-208:AUDUSD=X | tsmom_ls [AUDUSD=X] | 86 | 1.1277 | 0.0814 | 0.133 | -1.658 | -1.879 | [0.443, -0.177] | -1.195 | 0.0096 | **REFUTED_OR_WEAK** |
| FOREX | H-208 | tsmom_ls_portfolio | 926 | 0.8403 | -0.0447 | 0.103 | -0.858 | -0.858 | [0.443, -0.237] | -1.217 | 0.0113 | **REFUTED_OR_WEAK** |
| FOREX | H-209 | xsmom_top2_3m | 179 | 1.0244 | 0.0166 | 0.076 | -1.171 | -1.329 | [-0.594, 0.745] | -1.244 | 0.0091 | **REFUTED_OR_WEAK** |
| FOREX | H-208:USDCAD=X | tsmom_ls [USDCAD=X] | 150 | 0.9923 | -0.0039 | -0.074 | -1.379 | -1.746 | [0.499, -0.647] | -1.403 | 0.0048 | **REFUTED_OR_WEAK** |
| FOREX | H-208:EURUSD=X | tsmom_ls [EURUSD=X] | 102 | 0.9123 | -0.0563 | -0.153 | -1.622 | -1.874 | [-0.012, -0.295] | -1.482 | 0.0037 | **REFUTED_OR_WEAK** |
| FOREX | H-208:GBPUSD=X | tsmom_ls [GBPUSD=X] | 113 | 0.7428 | -0.1871 | -0.537 | -2.311 | -2.618 | [-0.451, -0.623] | -1.857 | 0.001 | **REFUTED_OR_WEAK** |
| MUTUAL_FUND | H-216 | tsmom_12_1 [VFIAX] | 28 | 8.5327 | 5.3326 | 3.875 | 1.286 | 1.132 | [3.003, 4.747] | -1.861 | 0.5285 | **INSUFFICIENT_N** |
| MUTUAL_FUND | H-220 | xsmom_top2_6m | 179 | 1.6984 | 0.7767 | 3.805 | 0.997 | 0.727 | [4.844, 2.766] | -1.932 | 0.5236 | **FAILS_BENCHMARK** |
| PENNY_STOCK | H-215 | tsmom_12_1 [PLUG] | 26 | 4.3496 | 24.0678 | 8.691 | -3.254 | -3.397 | [6.967, 10.415] | 3.985 | 0.1597 | **INSUFFICIENT_N** |
| PENNY_STOCK | H-219 | xsmom_top2_6m | 179 | 1.1845 | 1.1347 | 4.565 | -8.636 | -8.898 | [2.967, 6.162] | -0.141 | 0.0355 | **REFUTED_OR_WEAK** |
| CRYPTO | H-206 | tsmom_6m_long_flat | 60 | 9.4234 | 25.8342 | 15.911 | 8.452 | 7.913 | [22.172, 9.65] | -1.021 | 0.8917 | **FAILS_BENCHMARK** |
| CRYPTO | H-207 | xsmom_top3_3m | 147 | 1.7661 | 4.6083 | 12.47 | 0.714 | 0.417 | [7.505, 17.435] | -4.463 | 0.3136 | **FAILS_BENCHMARK** |

## Class verdicts

| class | cells | best cell | verdict | what it means |
|---|---|---|---|---|
| EQUITY | 11 | H-201 xsmom_top3_6m (CI-LB 7.246 bps, n=179, DSR 0.9797) | PASSES_ALL_BACKTEST_GATES | backtest candidate — still needs a forward pod (G8), not money |
| ETF | 1 | H-205 xsmom_top3_6m (CI-LB 2.007 bps, n=179, DSR 0.6804) | FAILS_BENCHMARK | beats cash but not buy-and-hold of its own universe |
| FUTURES | 2 | H-218 xsmom_top2_6m (CI-LB 0.186 bps, n=179, DSR 0.2699) | FAILS_2X_COST | signal exists, cannot pay for itself at 2× cost |
| INDEX | 2 | H-221 xsmom_top2_6m (CI-LB 1.613 bps, n=179, DSR 0.6269) | FAILS_BENCHMARK | beats cash but not buy-and-hold of its own universe |
| BOND | 2 | H-213 xsmom_top2_6m (CI-LB -0.453 bps, n=179, DSR 0.0909) | REFUTED_OR_WEAK | no usable signal at this resolution |
| COMMODITY | 2 | H-210 tsmom_12_1 [GC=F] (CI-LB -0.724 bps, n=48, DSR 0.148) | REFUTED_OR_WEAK | no usable signal at this resolution |
| FOREX | 7 | H-208:USDJPY=X tsmom_ls [USDJPY=X] (CI-LB -0.52 bps, n=121, DSR 0.131) | REFUTED_OR_WEAK | no usable signal at this resolution |
| MUTUAL_FUND | 2 | H-220 xsmom_top2_6m (CI-LB 0.997 bps, n=179, DSR 0.5236) | FAILS_BENCHMARK | beats cash but not buy-and-hold of its own universe |
| PENNY_STOCK | 2 | H-219 xsmom_top2_6m (CI-LB -8.636 bps, n=179, DSR 0.0355) | REFUTED_OR_WEAK | no usable signal at this resolution |
| CRYPTO | 2 | H-206 tsmom_6m_long_flat (CI-LB 8.452 bps, n=60, DSR 0.8917) | FAILS_BENCHMARK | beats cash but not buy-and-hold of its own universe |

**Cells clearing every backtest gate: 1** — H-201 EQUITY xsmom_top3_6m

## Reading this honestly

- A `PASSES_ALL_BACKTEST_GATES` cell is a **backtest** result. It has not been forward-tested, so it is not an edge yet (G8 = n ≥ 100 closed forward trades).
- `excess vs bench` is the beta check: a cell can be profitable and still be worthless if it just tracks its own universe.
- `CI-LB @2×` is the cost stress; `FAILS_2X_COST` cells are the gross-looking strategies this desk has over-trusted before.
- PENNY_STOCK costs are understated (no market impact), so even a passing cell there needs a liquidity haircut first.
- MUTUAL_FUND cells trade at daily NAV with next-day execution; they can support a fund-selection rule, not a trading edge.

Reproduce: `python3 tools/per_class_edge_harness.py --out reports/per_class_edge_2026-11-22.json --md reports/per_class_edge_2026-11-22.md --n-trials 22` then `python3 tools/build_per_class_report.py`
