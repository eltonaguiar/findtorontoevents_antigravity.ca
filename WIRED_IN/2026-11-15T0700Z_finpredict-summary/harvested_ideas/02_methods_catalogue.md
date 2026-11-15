# Methods Catalogue — Finpredict Project

## ML/Models
- Random forest, ARIMA/SARIMA, HMM, Kalman, Bayesian (framework only), PCA/SVM — detected in code/md.
- NOT found: XGBoost/LightGBM, Keras/TF LSTM, PyTorch Transformer, Prophet, GBM, k-means.

## Backtesting Frameworks
- walk-forward (60/40), train/test split, param sweep/grid search, rigorous_backtest_harness PBO.
- NOT found: vectorbt, zipline, backtrader, quantconnect.

## Risk Functions (active)
- var, max drawdown, sharpe, sortino (flagged), calmar, sterling, kelly, position sizing, TP/SL, ATR (SL), 10bp cost model. COMISSION/spread not in originals.

## Data Sources
- yfinance, Binance, CoinGecko (active). NOT found: ccxt, alpha vantage, polygon.

## Execution
- Paper trading (SQLite), live emission workflow (0 runs yet). Slippage/funding/tax NOT modelled.

## Code Patterns
- shift(1) lag, pct_change(), rolling(200), resample("W"), cumprod equity.
