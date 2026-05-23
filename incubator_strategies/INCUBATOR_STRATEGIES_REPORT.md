# INCUBATOR STRATEGIES REPORT

## Monte Carlo Bootstrap Analysis Appendix

Performed 1000 bootstrap resamples (with replacement) of trade PnLs for RSI Momentum strategy across symbols/timeframes with >30 trades.

Metrics:
- **Median Sharpe**: Median annualized Sharpe ratio across simulations (annualized using trades per year).
- **Sharpe 5th/95th**: 5th/95th percentile of Sharpe ratios.
- **Total Return 5th/95th**: 5th/95th percentile of final equity return over the trade sequence.
- **95th Max DD**: 95th percentile (worst 5%) maximum drawdown.
- **Prob Ruin**: Probability of ruin, defined as max DD >10% or final return <0%.

### Results Table

| Config          | Trades | Years | Median Sharpe | Sharpe 5-95%     | Ret 5-95%       | 95th DD | Ruin Prob |
|-----------------|--------|-------|---------------|------------------|-----------------|---------|-----------|
| RSI BTCUSDT_1h | 177    | 0.2   | -12.05       | -18.67 to -7.08 | -57.6% to -37.5% | 57.6%  | 100%     |
| RSI BTCUSDT_4h | 172    | 0.9   | -3.92        | -6.10 to -1.90  | -58.3% to -29.5% | 59.0%  | 100%     |
| RSI BTCUSDT_1d | 130    | 4.6   | 0.27         | -0.53 to 0.96   | -52.8% to 233.9%| 63.1%  | 100%     |
| RSI ETHUSDT_1h | 165    | 0.2   | -4.28        | -9.84 to -0.42  | -48.6% to -6.4% | 49.6%  | 100%     |
| RSI ETHUSDT_4h | 165    | 0.9   | -0.10        | -1.90 to 1.61   | -48.8% to 84.2% | 56.0%  | 100%     |
| RSI ETHUSDT_1d | 143    | 4.5   | -0.08        | -1.06 to 0.67   | -80.1% to 142.6%| 83.6%  | 100%     |
| RSI SOLUSDT_1h | 173    | 0.2   | -6.69        | -12.35 to -2.66 | -56.4% to -25.3%| 57.7%  | 100%     |
| RSI SOLUSDT_4h | 153    | 0.9   | -0.12        | -1.99 to 1.55   | -47.8% to 71.4% | 55.3%  | 100%     |
| RSI SOLUSDT_1d | 118    | 4.5   | 0.57         | -0.18 to 1.14   | -60.8% to 1590% | 81.7%  | 100%     |

**Key Insights**:
- RSI SOLUSDT_1d shows strongest robustness (positive median Sharpe 0.57).
- BTCUSDT_1d marginally positive (0.27).
- Higher timeframes (1d) perform better than intraday.
- All configs show high ruin probability due to frequent >10% drawdowns in bootstraps, indicating high path dependency/volatility.
- Full results: [`incubator_strategies/monte_carlo_results.json`](incubator_strategies/monte_carlo_results.json)

Data from AsterDEX futures klines. Analysis script: [`monte_carlo_analysis.py`](monte_carlo_analysis.py)