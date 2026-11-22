# Edge screen — 20261122

Population: scrutiny filter, pnl in [-100,100]. Trials tested: **25** (min n 100). 

| verdict | source | class | n | WR | gross PF | net PF | net mean | CI-LB | h1 | h2 | top sym | top date | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ADVANCE | mega_mutation | CRYPTO | 339 | 0.6696 | 3.4958 | 3.33 | 2.5535 | 2.1291 | 2.2396 | 2.8656 | JUPUSDT 16% | 6% | - |
| ADVANCE | battleground_luxalgo | CRYPTO | 150 | 0.5533 | 2.9374 | 2.6091 | 0.9605 | 0.5143 | 1.0025 | 0.9184 | JUPUSDT 9% | 18% | - |
| ADVANCE | alpha_engine | COMMODITY | 150 | 0.4867 | 2.8328 | 2.515 | 1.3882 | 0.4096 | 1.8985 | 0.8779 | SI=F 27% | 4% | - |
| WATCH | prediction_market_agents | CRYPTO | 172 | 0.5407 | 14.4802 | 9.1466 | 1.1204 | 0.9091 | 1.6434 | 0.5974 | DOGEUSDT 38% | 30% | top symbol DOGEUSDT 38% |
| WATCH | kimi_signal_tracking | CRYPTO | 137 | 0.5766 | 2.102 | 2.0305 | 2.1044 | 0.4248 | 2.2278 | 1.9827 | BTC-USD 9% | 80% | top date 2026-04-10 80% |
| REJECT | alpha_engine | EQUITY | 313 | 0.6518 | 1.3931 | 1.3345 | 0.3263 | 0.0501 | -0.3614 | 1.0097 | AAPL 45% | 18% | split halves disagree; top symbol AAPL 45% |
| REJECT | cta_replicator | FOREX | 418 | 0.5742 | 1.9316 | 1.3044 | 0.0156 | 0.0017 | 0.0507 | -0.0194 | USDJPY=X 35% | 52% | split halves disagree; top symbol USDJPY=X 35%; top date 2026-06-05 52% |
| WATCH | ml_crypto_predictor | CRYPTO | 326 | 0.454 | 1.8317 | 1.7519 | 1.3728 | 0.0001 | 2.9527 | -0.2071 | DYDXUSDT 8% | 11% | split halves disagree |
| REJECT | multi_asset_copytrader | FOREX | 5879 | 0.3931 | 1.6314 | 1.0809 | 0.0044 | -0.0043 | -0.0195 | 0.0283 | AUDJPY=X 13% | 43% | net CI-LB <= 0; split halves disagree; top date 2026-06-05 43% |
| REJECT | alpha_engine | FOREX | 376 | 0.4894 | 1.3396 | 1.1679 | 0.0235 | -0.0106 | -0.0582 | 0.1053 | USDCHF=X 14% | 15% | net CI-LB <= 0; split halves disagree |
| REJECT | non_crypto_consensus | FOREX | 562 | 0.7278 | 2.1954 | 0.3797 | -0.0128 | -0.0157 | -0.0107 | -0.0148 | EURJPY=X 14% | 74% | net CI-LB <= 0; split halves disagree; top date 2026-06-05 74% |
| REJECT | forex_copy_trader | FOREX | 503 | 0.1909 | 0.9815 | 0.7768 | -0.0215 | -0.0468 | -0.0057 | -0.0371 | USDCAD=X 10% | 7% | net CI-LB <= 0; split halves disagree |
| WATCH | alpha_engine | CRYPTO | 2927 | 0.5012 | 1.1491 | 1.0889 | 0.1584 | -0.0649 | 0.0309 | 0.2858 | ETHUSDT 5% | 4% | net CI-LB <= 0 |
| REJECT | multi_asset_copytrader | EQUITY | 469 | 0.3006 | 1.2848 | 1.1751 | 0.096 | -0.0729 | -0.0283 | 0.2199 | INTC 9% | 72% | net CI-LB <= 0; split halves disagree; top date 2026-06-05 72% |
| REJECT | luxalgo_filters | CRYPTO | 4787 | 0.4295 | 1.0559 | 0.9807 | -0.0264 | -0.0968 | -0.0541 | 0.0013 | STXUSDT 7% | 1% | net CI-LB <= 0; split halves disagree |
| REJECT | alpha_engine_fast | CRYPTO | 399 | 0.1955 | 0.5984 | 0.5061 | -0.3517 | -0.5297 | -0.5794 | -0.125 | BTC-USD 5% | 39% | net CI-LB <= 0; split halves disagree; top date 2026-06-02 39% |
| REJECT | alpha_engine | UNCATEGORIZED | 135 | 0.5185 | 0.908 | 0.811 | -0.223 | -0.6685 | 0.0127 | -0.4553 | SPY 21% | 10% | net CI-LB <= 0; split halves disagree |
| REJECT | cta_replicator | COMMODITY | 236 | 0.2881 | 0.7779 | 0.6784 | -0.4041 | -0.7029 | 0.3151 | -1.1233 | CL=F 27% | 36% | net CI-LB <= 0; split halves disagree; top date 2026-05-31 36% |
| REJECT | multi_asset_copytrader | COMMODITY | 1004 | 0.26 | 0.3429 | 0.267 | -0.7025 | -0.8018 | -0.1505 | -1.2545 | HG=F 26% | 14% | net CI-LB <= 0; split halves disagree |
| REJECT | genome | CRYPTO | 163 | 0.3988 | 0.9786 | 0.9234 | -0.1363 | -0.9287 | -1.1918 | 0.9063 | PEPEUSDT 12% | 7% | net CI-LB <= 0; split halves disagree |
| REJECT | regime_terminal | EQUITY | 316 | 0.3386 | 0.5138 | 0.4908 | -0.7451 | -1.0308 | -0.713 | -0.7773 | AMD 12% | 43% | net CI-LB <= 0; split halves disagree; top date 2026-06-05 43% |
| REJECT | ml_bg_system_f | CRYPTO | 215 | 0.4 | 0.7903 | 0.7648 | -0.8023 | -1.4886 | -1.1254 | -0.4821 | ADA 17% | 98% | net CI-LB <= 0; split halves disagree; top date 2026-06-12 98% |
| REJECT | regime_terminal | CRYPTO | 282 | 0.3298 | 0.4979 | 0.4777 | -1.707 | -2.1998 | -1.2217 | -2.1922 | AVAXUSDT 19% | 7% | net CI-LB <= 0; split halves disagree |
| REJECT | copy_trader_intel | CRYPTO | 317 | 0.2871 | 0.6731 | 0.6615 | -2.2206 | -3.5653 | -4.419 | -0.0361 | INJUSDT 2% | 42% | net CI-LB <= 0; split halves disagree; top date 2026-04-18 42% |
| REJECT | battleground | CRYPTO | 137 | 0.5547 | 0.8046 | 0.7981 | -2.8069 | -8.2787 | -5.4908 | -0.1619 | BTCUSDT 46% | 100% | net CI-LB <= 0; split halves disagree; top symbol BTCUSDT 46%; top date 2026-04-10 100% |
