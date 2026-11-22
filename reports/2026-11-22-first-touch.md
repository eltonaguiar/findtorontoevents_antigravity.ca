# Honest first-touch re-resolution (real Binance daily bars) — 2026-11-22

CRYPTO picks in ledger: 1835 · symbols attempted: 65 (ok 65) · resolved: 1787

Status: `{'NO_WINDOW': 3, 'RESOLVED': 1787, 'NEITHER_HIT': 45}`

Rule: **SL wins a same-bar tie** (conservative). Ties seen: 789.

| measure | recorded (ledger) | honest (re-walked) |
|---|---|---|
| n | 1787 | 1787 |
| win rate | 35.8% | 37.0% |
| profit factor | 0.6195431348465582 | 0.9065406725010471 |
| expectancy % | -0.7803 | -0.1152 |

Exits whose first-touch level differs from the recorded reason: **974/1787**.

## By strategy

| strategy | n | changed | PF recorded | PF honest | exp recorded % | exp honest % |
|---|---|---|---|---|---|---|
| luxalgo_confluence | 1160 | 731 | 0.9840261829869056 | 1.1932282477056722 | -0.0234 | +0.1911 |
| extreme_fear | 68 | 15 | 0.12972658959693997 | 0.5739086238358199 | -4.2563 | -1.4412 |
| crypto-momentum-scout | 50 | 26 | 0.19477590463640354 | 1.0215031795630547 | -3.1897 | +0.0200 |
| crypto_signal_engine | 45 | 17 | 0.23753828920711087 | 2.6295911000986707 | -0.9802 | +1.1487 |
| crypto-bb-squeeze-scout | 44 | 24 | 0.38995145309660045 | 0.9523809523809523 | -1.9475 | -0.0455 |
| strong consensus (alpha_engine, luxalgo_filters) | 36 | 18 | 1.3220941672788251 | 0.6716406750478439 | +0.4738 | -0.4513 |
| rsi-divergence-scalp-scout | 31 | 11 | 0.2519104082619789 | 0.4861111111111111 | -3.7368 | -0.5968 |
| crypto_liquidity_wick_reversal_v1 | 31 | 13 | 1.144683588628572 | 1.5625 | +0.0573 | +0.4355 |
| cci-crypto-reversal | 27 | 8 | 0.04390460508057503 | 0.289854232306573 | -4.7848 | -0.9074 |
| strong consensus (kimi, luxalgo_filters) | 23 | 7 | 0.1582120421586001 | 0.21976801972040816 | -3.7445 | -3.0922 |
| momentum_breakout | 22 | 1 | 0.1590820615398249 | 0.0634929075340536 | -4.8308 | -5.3636 |
| multi_period_rsi_confluence_eth | 22 | 14 | 0.7031861880601604 | 0.9523809523809523 | -0.1492 | -0.0455 |
| clone_hl_copy_lb_None | 21 | 15 | 3.988931183889698 | 0.08692913385826771 | +0.8114 | -1.3805 |
| crypto-funding-confluence | 18 | 11 | 0.056432335915675494 | 0.8333333333333334 | -3.6404 | -0.1667 |
| crypto-rsi-divergence-scout | 17 | 10 | 0.3232983065159262 | 0.2222222222222222 | -2.0365 | -1.0294 |
| ema-ribbon-momentum-scout | 16 | 2 | 0.0 | 0.0 | -7.0749 | -1.5000 |
| drawdown_recovery_rsi_eth | 14 | 12 | 5.978383072071661 | 3.0 | +0.7781 | +1.0714 |
| funding-rate-reversal | 12 | 5 | 0.5632932215862763 | 0.3333333333333333 | -2.2896 | -0.8333 |
| atr_percentile_gate | 11 | 3 | 0.12352871441394145 | 0.9523809523809523 | -0.4705 | -0.0455 |
| macd_rsi_m048 | 10 | 2 | 2.6520143183255276 | 1.2810421038531947 | +3.0829 | +0.7553 |
| signal_engine_wide_net_mut | 9 | 0 | 0.0 | 0.0 | -2.0489 | -2.0494 |
| crash_reversal | 8 | 1 | 1.8805725225635885 | 3.749975 | +1.5696 | +2.7500 |
| claude_ml_moderate_mut | 7 | 0 | 0.0 | 0.0 | -2.0000 | -2.0000 |
| ema_momentum_m006 | 7 | 2 | 5.401969473165928 | 1.1851385640747047 | +3.1930 | +0.3992 |
| orderbook-imbalance | 6 | 3 | 0.0 | 0.8333333333333334 | -2.4600 | -0.1667 |
| drawdown_recovery_rsi_sol | 6 | 4 | 8.56816922224275 | 8.333333333333334 | +1.3655 | +1.8333 |
| btc-4h-rsi-macd-scout | 5 | 2 | 0.29604899123180384 | 0.4166666666666667 | -2.6462 | -0.7000 |
| price-accel-scout | 5 | 0 | 0.0 | 0.0 | -3.4083 | -1.5000 |
| clone_hl_copy_PensionFund_24M | 5 | 2 | 2.0917804064300882 | 0.0 | +0.7199 | -1.0000 |
| Crypto RSI Scout | 4 | 0 | 0.0 | 0.0 | -17.2525 | -2.0000 |
| B_flip_PriceRocMeanReversion | 4 | 3 | 5.441703143653004 | 0.0 | +2.2324 | -2.0000 |
| strong consensus (alpha_engine, quan_engine) | 4 | 1 | 0.0 | 0.0 | -1.6142 | -1.3942 |
| bb-squeeze-breakout-scout | 4 | 0 | 0.0 | 0.0 | -4.7311 | -1.5000 |
| clone_hl_bybit_copy_C_R_Y_P_T_O___K_I_N_ | 4 | 4 | None | 0.0 | +5.0000 | -3.0000 |
| moderate consensus (incubator_fwd, quan_engine) | 3 | 1 | 0.23065665375631966 | 0.354426918673206 | -1.7348 | -1.2592 |
| funding-rate-arb | 3 | 1 | 0.0 | 0.8333333333333334 | -4.5223 | -0.1667 |
| hs_ABC_41M | 3 | 0 | 0.035 | 0.035 | -0.6433 | -0.6433 |
| drawdown_recovery_rsi_xrp | 3 | 2 | 2.967630809229769 | 0.8333333333333334 | +1.0091 | -0.1667 |
| signal_engine_no_premium_mut | 2 | 0 | 0.0 | 0.0 | -2.0550 | -2.0523 |
| signal_engine_relaxed_mut | 2 | 0 | 0.0 | 0.0 | -2.0000 | -2.0000 |
| prediction_market_consensus | 2 | 1 | None | 1.6666666666666667 | +2.4512 | +0.5000 |
| macd_rsi_m017 | 2 | 1 | None | 1.4815409309791332 | +7.3315 | +1.0650 |
| unknown | 2 | 0 | 0.0 | 0.0 | -12.9348 | -1.5000 |
| pairs-trading | 2 | 0 | 0.0 | 0.0 | -7.8045 | -1.5000 |
| cal-effect-crypto-scout | 2 | 0 | 0.0 | 0.0 | -5.3078 | -1.5000 |
| GPM_Gen353_90539f | 1 | 0 | 0.0 | 0.0 | -1.5000 | -1.5000 |
| RSI Divergence Scalp | 1 | 0 | 0.0 | 0.0 | -17.8700 | -2.0000 |
| kimi_flash_crash_relaxed_mut | 1 | 0 | 0.0 | 0.0 | -2.0200 | -2.0231 |
| vwma_momentum_trend | 1 | 1 | None | 0.0 | +3.1809 | -2.0000 |
| bollinger-squeeze | 1 | 0 | 0.0 | 0.0 | -6.6736 | -1.5000 |
