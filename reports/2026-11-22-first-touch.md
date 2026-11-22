# Honest first-touch re-resolution (real Binance daily bars) — 2026-11-22

CRYPTO picks in ledger: 2070 · symbols attempted: 62 (ok 60) · resolved: 1717

Status: `{'NO_TIMES': 204, 'RESOLVED': 1717, 'NO_BARS': 104, 'NEITHER_HIT': 43, 'NO_WINDOW': 2}`

Rule: **SL wins a same-bar tie** (conservative). Ties seen: 689.

| measure | recorded (ledger) | honest (re-walked) |
|---|---|---|
| n | 1717 | 1717 |
| win rate | 45.5% | 43.4% |
| profit factor | 1.366780216554495 | 1.4789321855446973 |
| expectancy % | +0.6160 | +0.6050 |

Exits whose first-touch level differs from the recorded reason: **922/1717**.

## By strategy

| strategy | n | changed | PF recorded | PF honest | exp recorded % | exp honest % |
|---|---|---|---|---|---|---|
| luxalgo_confluence | 1210 | 746 | 1.0274601398685599 | 1.346291107105055 | +0.0445 | +0.3661 |
| strong consensus (alpha_engine, luxalgo_filters) | 70 | 38 | 1.5280686489994193 | 4.235401991410446 | +1.5078 | +3.2210 |
| mega_mutation_ema_momentum_m006 | 66 | 2 | 0.7670844269915623 | 0.6600561132705088 | -0.5326 | -0.8289 |
| momentum_breakout | 65 | 21 | 1.380251838149318 | 0.36604517949837445 | +1.2258 | -2.9844 |
| mega_mutation_macd_rsi_m048 | 57 | 4 | 5.108370422918449 | 5.00772003100395 | +5.9336 | +5.9054 |
| crypto_liquidity_wick_reversal_v1 | 31 | 13 | 1.144683588628572 | 1.5625 | +0.0573 | +0.4355 |
| alpha_engine | 26 | 21 | 8.271994179348816 | 0.0 | +1.3839 | -0.9980 |
| unknown | 24 | 9 | 0.8673987588092983 | 1.1952380952380952 | -0.5253 | +0.1708 |
| multi_period_rsi_confluence_eth | 22 | 14 | 0.7031861880601604 | 0.9523809523809523 | -0.1492 | -0.0455 |
| mega_mutation_macd_rsi_m017 | 20 | 1 | 2.675187923118824 | 2.1295676154831082 | +2.6910 | +2.0643 |
| drawdown_recovery_rsi_eth | 14 | 12 | 5.978383072071661 | 3.0 | +0.7781 | +1.0714 |
| regime_mild_bear | 11 | 0 | None | None | +5.0497 | +3.7947 |
| atr_percentile_gate | 11 | 3 | 0.12352871441394145 | 0.9523809523809523 | -0.4705 | -0.0455 |
| strong consensus (alpha_engine, quan_engine) | 10 | 4 | 43.45131929616757 | 32.89762245679464 | +27.2380 | +19.1584 |
| clone_hl_copy_PensionFund_24M | 8 | 7 | 236.183 | 0.5 | +2.9398 | -0.4375 |
| crash_reversal | 8 | 2 | 3.4812420963889283 | None | +3.0903 | +5.0006 |
| extreme_fear | 7 | 1 | 7.243966560750492 | 2.999589995899959 | +4.7162 | +2.8565 |
| drawdown_recovery_rsi_sol | 6 | 4 | 8.56816922224275 | 8.333333333333334 | +1.3655 | +1.8333 |
| high_trust_momentum | 5 | 1 | 1.8398610562223103 | 1.056970721911003 | +0.8076 | +0.0647 |
| claude_ml_moderate_mut | 5 | 2 | 3.4751325891035867 | 0.6395975733299176 | +2.6695 | -0.6190 |
| clone_hl_copy_lb_None | 5 | 4 | None | 0.4 | +2.5000 | -0.7500 |
| strong consensus (luxalgo_filters, quan_engine) | 4 | 3 | 0.6617485672478965 | 0.3796188601592556 | -0.3468 | -0.5201 |
| regime_strong_bear | 4 | 1 | None | 5.9572 | +5.2905 | +2.4786 |
| ema_momentum_volume | 4 | 0 | 0.0 | 0.0 | -2.1164 | -2.0843 |
| vwma_momentum_trend | 3 | 1 | 0.0 | 0.0 | -1.7311 | -1.6479 |
| connors_williams_hybrid | 3 | 1 | 0.0 | 0.0 | -2.9372 | -2.9915 |
| stochastic_momentum_index | 3 | 0 | 0.0 | 0.0 | -2.8405 | -2.8405 |
| tsmom_28d | 3 | 0 | 1.0748427303192427 | 0.0 | +0.1273 | -5.8677 |
| adx_momentum | 3 | 1 | 0.3161903281586974 | 0.0 | -1.1732 | -1.6979 |
| st_fear_greed_contrarian (Revival) | 3 | 3 | 3.3156926793115753 | 0.6666666666666666 | +5.6242 | -0.6667 |
| drawdown_recovery_rsi_xrp | 3 | 2 | 2.967630809229769 | 0.8333333333333334 | +1.0091 | -0.1667 |
| macd_divergence_scanner | 1 | 0 | 0.0 | 0.0 | -2.0000 | -2.0000 |
| strong consensus (alpha_engine, kol_consensus, luxalgo_filters) | 1 | 1 | 0.0 | 0.0 | -28.3334 | -0.8800 |
| williams_vix_fix | 1 | 0 | None | 0.0 | +11.7188 | -7.1877 |
