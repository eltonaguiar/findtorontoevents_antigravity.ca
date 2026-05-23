# CryptoFusion Predictor Performance Report

**Report Date:** 2026-02-22

## Backtest Results (Last 500 Days, 1D Timeframe)

| Pair | Total Return | Number of Trades |
|------|--------------|------------------|
| BTC/USDT | 9.93% | 44 |
| ETH/USDT | 6.79% | 45 |
| SOL/USDT | 19.70% | 54 |
| BNB/USDT | 10.55% | 50 |
| XRP/USDT | 14.49% | 46 |
| DOGE/USDT | 15.02% | 51 |
| ADA/USDT | 12.10% | 53 |
| AVAX/USDT | 11.06% | 53 |
| TRX/USDT | 16.95% | 47 |
| DOT/USDT | 2.83% | 50 |

**Average Return:** 11.94%
**Total Trades:** 493

## Model Architecture

- **Algorithm:** XGBoost Regressor with HMM Regime Detection
- **Features:** RSI, MACD, Bollinger Bands, ATR, Volume Ratios, Momentum, On-chain Proxy
- **Timeframe:** Daily predictions
- **Pairs Covered:** 30 major crypto pairs

## Current Predictions

**Last Updated:** 2026-02-22T07:24:12.510499

| Pair | Current Price | Predicted Price | Change % |
|------|---------------|-----------------|-----------|
| BTC/USDT | $68042.26 | $68648.04 | 0.89% |
| ETH/USDT | $1974.48 | $2097.80 | 6.25% |
| SOL/USDT | $84.93 | $93.41 | 9.99% |
| BNB/USDT | $622.14 | $603.16 | -3.05% |
| XRP/USDT | $1.41 | $1.41 | 0.03% |
| DOGE/USDT | $0.10 | $0.10 | 2.84% |
| ADA/USDT | $0.27 | $0.27 | -3.03% |
| AVAX/USDT | $8.95 | $9.16 | 2.34% |
| TRX/USDT | $0.29 | $0.29 | 0.23% |
| DOT/USDT | $1.32 | $1.37 | 3.77% |

*Full predictions available in crypto_predictions.json*
