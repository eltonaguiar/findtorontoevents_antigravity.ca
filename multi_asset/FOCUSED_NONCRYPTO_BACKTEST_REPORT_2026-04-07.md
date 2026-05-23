# Focused Non-Crypto Backtest Report

Date: 2026-04-07
Source: `multi_asset/backtest_focused_noncrypto_strategies.py`
Output: `multi_asset/data/focused_noncrypto_backtest_results.json`

## Summary

The focused non-crypto basket materially outperformed the older mixed multi-asset run by removing generic low-edge systems and concentrating on asset-class-specific strategies.

- Total trades: 3,557
- Win rate: 50.3%
- Average PnL per trade: +0.1921%
- Total return (sum of trade PnL): +683.45%
- Profit factor: 1.20
- Sharpe: 4.30
- Max drawdown: -119.0%

This is not "institutional-ready" yet, but it is strong enough to separate real edges from dead branches.

## Best Edges

### 1. DXY Trend Filter (Forex)

Best strategy in the whole run.

- Total return: +272.06%
- Profit factor: 1.63
- Sharpe: 6.75
- Trades: 995

Best symbols:

- `USDCHF=X`: +51.30%, PF 2.26
- `EURUSD=X`: +45.24%, PF 1.85
- `AUDUSD=X`: +43.66%, PF 1.64
- `USDJPY=X`: +40.06%, PF 1.55
- `GBPUSD=X`: +36.28%, PF 1.57

Interpretation: macro dollar alignment is the real forex edge here. Generic reversal alone is not enough.

### 2. Blue-Chip Mean Reversion (Equity)

Most reliable equity strategy in the run.

- Total return: +166.99%
- Profit factor: 1.18
- Sharpe: 2.02
- Trades: 657

Best symbols:

- `META`: +76.95%, PF 1.59
- `JPM`: +39.86%, PF 1.34
- `V`: +35.12%, PF 1.49
- `MSFT`: +28.48%, PF 1.43
- `GOOGL`: +23.10%, PF 1.21

Interpretation: large-cap RSI mean reversion works when filtered by long-term trend and six-month momentum. This is much better than treating all stocks equally.

### 3. ETF Relative Strength

Clean ETF trend/pullback edge.

- Total return: +104.23%
- Profit factor: 1.55
- Sharpe: 2.57
- Trades: 178

Best symbols:

- `GLD`: +42.99%, PF 3.96
- `XLK`: +29.81%, PF 2.99
- `QQQ`: +16.66%, PF 2.23
- `XLF`: +11.68%, PF 2.15
- `XLV`: +10.81%, PF 1.95

Interpretation: trend leadership plus pullback entry is the cleanest ETF edge in the repo right now. `GLD` is especially strong.

### 4. Gold Safe Haven

Fear-regime commodity exposure is working.

- Total return: +90.87%
- Profit factor: 1.98
- Sharpe: 2.35
- Trades: 61

Best symbols:

- `GC=F`: +29.74%, PF 2.42
- `GLD`: +27.12%, PF 2.13
- `SI=F`: +34.00%, PF 1.71

Interpretation: risk-off precious-metals exposure is a real edge. It is sparse, which is fine.

### 5. Commodity Seasonality

Positive but uneven.

- Total return: +103.72%
- Profit factor: 1.20
- Sharpe: 1.33
- Trades: 283

Best symbols:

- `CL=F`: +45.34%, PF 1.63
- `CORN`: +45.32%, PF 2.51
- `NG=F`: +36.00%, PF 1.19

Interpretation: seasonality is real, but symbol selection matters. Corn and crude are the cleanest expressions.

## Weak Or Misleading Edges

### Connors RSI2 Forex

- Win rate: 61.75%
- Total return: -20.60%
- Profit factor: 0.68

This is a classic bad-strategy trap: high win rate, negative economics. It wins often but pays too much on losses.

### Crude Oil Mean Reversion

- Total return: -30.38%
- Profit factor: 0.94

`XLE` worked, but the raw commodity expressions did not. `NG=F` is especially toxic here.

### Equity Index Gap Reversion

- Win rate: 53.10%
- Total return: -55.43%
- Profit factor: 0.87

Another misleading setup. The hit rate looks acceptable, but the payoff shape is bad.

### Earnings Momentum PEAD

- Total return: +31.73%
- Profit factor: 1.43
- Trades: 50

Promising, but still sparse. Keep it in probation, not in core production.

## Asset-Class Readout

- `forex`: strongest aggregate book only because `dxy_trend_filter` dominates. Keep macro-aligned forex, cut generic forex reversal.
- `equity`: blue-chip mean reversion is the anchor. PEAD is promising but under-sampled.
- `etf`: strongest clean profile. `GLD`, `XLK`, `QQQ`, `XLF`, `XLV` deserve priority.
- `commodity`: positive overall, but should be narrowed to seasonality + safe-haven metals.
- `futures`: still negative. Do not scale the futures book yet.

## Recommendations

1. Promote `dxy_trend_filter`, `blue_chip_mean_reversion`, `etf_relative_strength`, and `gold_safe_haven` into the next validation layer.
2. Keep `earnings_momentum_pead` on probation until it clears at least 100 trades.
3. Remove or heavily down-rank `connors_rsi2_forex`, `crude_oil_mean_reversion`, and `equity_index_gap_reversion` from any capital-bearing flow.
4. Narrow commodity deployment to `GC=F`, `GLD`, `CORN`, and selective crude seasonality.
5. Treat futures as unresolved. The current daily gap-reversion expression is not good enough.

## Caveats

- Daily-bar backtest.
- Uses yfinance OHLCV.
- Entry is modeled from the signal bar's computed price, not intraday execution.
- No commissions/slippage model beyond the strategy's own TP/SL geometry.
- This is not a walk-forward split. It is a focused historical filter to locate edge candidates worth deeper validation.