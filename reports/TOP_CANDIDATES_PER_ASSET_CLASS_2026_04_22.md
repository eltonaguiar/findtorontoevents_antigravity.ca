# Top real-edge candidates per asset class

**Source:** `alpha_engine/data/active_picks.json` (current state).

**Filter (relaxed):** exclude copy_trader_intel + clone_hl_*; need any of score/fwd_wr/n signal; drop BLACK/BANNED trust.

**Rank:** composite = 0.5·score + 0.3·fwd_wr + 0.2·log1p(n)·10

**`hc_strict` column:** True if pick passes the strict HC gate (n>=5 AND fwd_wr>=55 AND score>=50).

**Not trade orders.** These are ranked diagnostic candidates from the current ledger. Verify TP/SL, check the symbol's current price against `entry`, and apply position sizing + source-concentration cap before paper-placing.


## COMMODITY  (5 of 8 passing filter)

| symbol   | direction   |   score |   fwd_wr |   n | hc_strict   | trust   | strategy                    | source          |    entry |        tp |        sl |   risk_reward |   composite |
|:---------|:------------|--------:|---------:|----:|:------------|:--------|:----------------------------|:----------------|---------:|----------:|----------:|--------------:|------------:|
| SI=F     | LONG        |      52 |        0 |   0 | False       |         | cta_commodity_momentum_term | cta_replicator  |   77.845 |   85.1291 |   72.0177 |          1.25 |        26   |
| ZC=F     | SHORT       |      52 |        0 |   0 | False       |         | cta_commodity_momentum_term | cta_replicator  |  463.5   |  445.062  |  478.25   |          1.25 |        26   |
| ZW=F     | SHORT       |      51 |        0 |   0 | False       |         | cot_positioning             | multi_asset_cot |  608.25  |  577.321  |  631.446  |          1.33 |        25.5 |
| ZS=F     | SHORT       |      51 |        0 |   0 | False       |         | cot_positioning             | multi_asset_cot | 1181.75  | 1151.5    | 1204.44   |          1.33 |        25.5 |
| KC=F     | LONG        |      51 |        0 |   0 | False       |         | cot_positioning             | multi_asset_cot |  289.25  |  306.457  |  276.345  |          1.33 |        25.5 |


## CRYPTO  (5 of 15 passing filter)

| symbol   | direction   |   score |   fwd_wr |   n | hc_strict   | trust   | strategy                          | source                      |     entry |          tp |          sl |   risk_reward |   composite |
|:---------|:------------|--------:|---------:|----:|:------------|:--------|:----------------------------------|:----------------------------|----------:|------------:|------------:|--------------:|------------:|
| ZECUSDT  | LONG        |      69 |       50 |   0 | False       |         | cross_sectional_reversal          |                             |  318.62   |  335.607    |  310.127    |          2    |        49.5 |
| ETHUSDT  | LONG        |      57 |        0 |   0 | False       |         | prediction_market_consensus       | prediction_market_agents    | 2394.86   | 2454.73     | 2358.94     |          1.67 |        28.5 |
| ADAUSDT  | SELL        |      56 |        0 |   0 | False       |         | inverse_ml_enhanced_ADAUSDT_15m_D | ml_strategy_reviver_inverse |    0.2556 |    0.252661 |    0.257952 |          1.25 |        28   |
| LTCUSDT  | BUY         |      55 |        0 |   0 | False       |         | ml_enhanced_LTCUSDT_4h_A_xgboost  | ml_strategy_reviver         |   56.47   |   59.4742   |   55.1825   |          2.33 |        27.5 |
| BNBUSDT  | SHORT       |      55 |        0 |   0 | False       |         | prediction_market_consensus       | prediction_market_agents    |  644.7    |  628.582    |  654.37     |          1.67 |        27.5 |


## EQUITY  (5 of 7 passing filter)

| symbol   | direction   |   score |   fwd_wr |   n | hc_strict   | trust   | strategy                   | source                 |   entry |      tp |      sl |   risk_reward |   composite |
|:---------|:------------|--------:|---------:|----:|:------------|:--------|:---------------------------|:-----------------------|--------:|--------:|--------:|--------------:|------------:|
| CVX      | LONG        |      52 |       50 |   0 | False       |         | stocks_rsi2_pullback       |                        | 183.309 | 192.474 | 177.81  |          1.67 |        41   |
| JNJ      | LONG        |      52 |       50 |   0 | False       |         | stocks_rsi2_pullback       |                        | 230.69  | 240.217 | 223.769 |          1.38 |        41   |
| PEP      | LONG        |      52 |       50 |   0 | False       |         | stocks_rsi2_pullback       | forex_copy_trader      | 156.99  | 163.046 | 152.448 |          1.33 |        41   |
| GOOGL    | BUY         |      48 |       50 |   0 | False       |         | stocks_rsi2_pullback_tight | auto_dna_mutation      | 332.29  | 343.789 | 325.312 |          1.65 |        39   |
| MRK      | LONG        |      51 |        0 |   0 | False       |         | stocks_rsi2_pullback       | multi_asset_copytrader | 112.685 | 118.319 | 109.304 |          1.67 |        25.5 |


## FOREX  (5 of 9 passing filter)

| symbol   | direction   |   score |   fwd_wr |   n | hc_strict   | trust   | strategy                   | source                 |     entry |        tp |        sl |   risk_reward |   composite |
|:---------|:------------|--------:|---------:|----:|:------------|:--------|:---------------------------|:-----------------------|----------:|----------:|----------:|--------------:|------------:|
| USDCAD=X | LONG        |      51 |    66.67 |   0 | False       |         | myfxbook_retail_contrarian | forex_copy_trader      |   1.36431 |   1.37263 |   1.35749 |          1.2  |        45.5 |
| CADJPY=X | SHORT       |      53 |     0    |   0 | False       |         | myfxbook_retail_contrarian | multi_asset_copytrader | 116.722   | 115.977   | 117.343   |          1.2  |        26.5 |
| USDJPY=X | LONG        |      52 |     0    |   0 | False       |         | forex_carry_momentum       | multi_asset_copytrader | 159.446   | 165.027   | 155.46    |          1.34 |        26   |
| GBPJPY=X | SHORT       |      51 |     0    |   0 | False       |         | ig_contrarian_sentiment    | multi_asset_copytrader | 215.437   | 214.25    | 216.387   |          1.25 |        25.5 |
| AUDJPY=X | SHORT       |      51 |     0    |   0 | False       |         | ig_contrarian_sentiment    | multi_asset_copytrader | 114.189   | 113.286   | 114.76    |          1.58 |        25.5 |


## FUTURES  (2 of 2 passing filter)

| symbol   | direction   |   score |   fwd_wr |   n | hc_strict   | trust   | strategy         | source                 |    entry |         tp |         sl |   risk_reward |   composite |
|:---------|:------------|--------:|---------:|----:|:------------|:--------|:-----------------|:-----------------------|---------:|-----------:|-----------:|--------------:|------------:|
| HG=F     | LONG        |      53 |        0 |   0 | False       |         | futures_momentum | multi_asset_copytrader |    6.144 |    6.36337 |    6.01237 |          1.67 |        26.5 |
| PL=F     | LONG        |      53 |        0 |   0 | False       |         | futures_momentum | multi_asset_copytrader | 2093.7   | 2198.38    | 2030.89    |          1.67 |        26.5 |


## STOCKS  (3 of 3 passing filter)

| symbol   | direction   |   score |   fwd_wr |   n | hc_strict   | trust   | strategy           | source          |   entry |     tp |     sl |   risk_reward |   composite |
|:---------|:------------|--------:|---------:|----:|:------------|:--------|:-------------------|:----------------|--------:|-------:|-------:|--------------:|------------:|
| IONQ     | LONG        |      57 |       50 |   0 | False       |         | regime_mild_bull   | regime_terminal |   46.09 |  49.55 |  44.02 |          1.67 |        43.5 |
| MSFT     | LONG        |      56 |       50 |   0 | False       |         | regime_strong_bull | regime_terminal |  411.22 | 442.06 | 392.72 |          1.67 |        43   |
| SOFI     | LONG        |      56 |       50 |   0 | False       |         | regime_mild_bull   | regime_terminal |   18.79 |  20.2  |  17.94 |          1.66 |        43   |


## Summary of eligible pool by asset class

| asset_class   |   n |   mean_score |   mean_fwr |
|:--------------|----:|-------------:|-----------:|
| COMMODITY     |   8 |        51    |       0    |
| CRYPTO        |  15 |        48.69 |       3.33 |
| EQUITY        |   7 |        50.71 |      28.57 |
| FOREX         |   9 |        50.89 |       7.41 |
| FUTURES       |   2 |        53    |       0    |
| STOCKS        |   3 |        56.33 |      50    |