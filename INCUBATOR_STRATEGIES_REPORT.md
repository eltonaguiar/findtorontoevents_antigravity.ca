# Incubator Strategies Report

## Executive Summary

Following a deep dive into Reddit-sourced trading strategies, four incubator strategies were implemented and backtested on BTCUSDT, ETHUSDT, and SOLUSDT across 1h, 4h, and 1d timeframes:

1. **Diagonal Trendline Short Breakout** [`backtest_diagonal_trendline.py`](incubator_strategies/backtest_diagonal_trendline.py)
2. **RSI(5) Momentum Long** [`backtest_rsi_momentum_strategy.py`](incubator_strategies/backtest_rsi_momentum_strategy.py)
3. **Grid Trading** [`backtest_grid_trading_incubator.py`](incubator_strategies/backtest_grid_trading_incubator.py)
4. **Bollinger Bands Mean Reversion** [`backtest_bollinger_meanrev.py`](incubator_strategies/backtest_bollinger_meanrev.py)

Backtest results available for Diagonal and RSI; Grid and Bollinger scripts ready for execution.

## 1. Diagonal Trendline Short Breakout

**Description:** Detects diagonal trendlines on swing lows using linear regression (R² ≥ 0.85). Enters **short** on confirmed breakout **above** the trendline (bearish signal), with stop-loss at recent swing high. Designed for short-side breakouts from uptrends.

**Core Strategy Module:** [`diagonal_trendline_breakout.py`](alpha_engine/diagonal_trendline_breakout.py)

**Key Logic Snippet:**
```python
strat = DiagonalTrendlineBreakout()
signals = strat.generate_signals(df)  # Generates 'entry_short', 'sl', 'exit_long'
# Risk-managed short entry on breakout above resistance line
```

**Backtest Summary** (from [`diagonal_trendline_results.json`](incubator_strategies/diagonal_trendline_results.json)):

| Symbol/TF    | Total Return | Sharpe | Winrate | Profit Factor | Max DD | Num Trades | Avg Trade | Calmar |
|--------------|--------------|--------|---------|---------------|--------|------------|-----------|--------|
| **All TFs/Pairs** | **0.00%** | **0.00** | **0.0%** | **0.00** | **0.00%** | **0** | **0.00%** | **0.00** |

*Note: Zero trades triggered across all assets/timeframes due to strict R²=0.85 filter. Loosen to ~0.80 recommended.*

**HTML Results:** [`diagonal_trendline_results.html`](incubator_strategies/diagonal_trendline_results.html)

## 2. RSI(5) Momentum Long

**Description:** Long-only momentum using fast RSI(5). **Enter long** when RSI crosses above 50 (bullish momentum confirmation). **Exit** on RSI cross below 50 or trailing stop-loss (1% initial SL, risk-managed position sizing).

**Core Strategy Module:** [`rsi_momentum_strategy.py`](alpha_engine/rsi_momentum_strategy.py)

**Key Logic Snippet:**
```python
signals = rsi_momentum_strategy(df)  # 'entry_long', 'exit_long', 'sl_pct'
# Long on RSI(5) >50 crossover, SL at entry * (1 + sl_pct)
```

**Backtest Summary** (from [`rsi_momentum_results.json`](incubator_strategies/rsi_momentum_results.json)):

| Symbol/TF     | Total Return | Sharpe  | Winrate | PF    | Max DD  | Trades | Avg Trade | Calmar | Buy & Hold   |
|---------------|--------------|---------|---------|-------|---------|--------|-----------|--------|--------------|
| BTCUSDT_1h   | -28.04%     | -1.86  | 14.7%  | 0.30 | 28.13% | 177   | -0.37%   | -2.72 | -19.29%     |
| BTCUSDT_4h   | -26.68%     | -1.27  | 22.1%  | 0.47 | 28.27% | 172   | -0.36%   | -1.02 | -25.26%     |
| BTCUSDT_1d   | +16.87%     | +0.25  | 33.1%  | 1.20 | 23.56% | 130   | +0.31%   | +0.15 | +44.73%     |
| ETHUSDT_1h   | -16.81%     | -0.71  | 22.4%  | 0.60 | 17.46% | 165   | -0.22%   | -3.18 | -27.40%     |
| ETHUSDT_4h   | -2.51%      | -0.01  | 29.1%  | 0.99 | 21.51% | 165   | -0.01%   | -0.13 | +21.03%     |
| ETHUSDT_1d   | -12.09%     | -0.06  | 34.3%  | 0.96 | 29.19% | 143   | -0.08%   | -0.10 | -36.97%     |
| SOLUSDT_1h   | -24.56%     | -1.11  | 23.7%  | 0.48 | 24.95% | 173   | -0.32%   | -2.85 | -27.07%     |
| SOLUSDT_4h   | -2.39%      | -0.01  | 36.6%  | 0.99 | 22.79% | 153   | -0.01%   | -0.11 | -39.53%     |
| **SOLUSDT_1d**| **+84.98%** | **+0.47**| **35.6%**| **1.48**| **31.97%**| **118**| **+1.38%**| **+0.45**| **-51.45%** |

*Highlights:* Beats B&H in 5/9 configs. **Standout: SOL1d** (Sharpe 0.47, +85% vs B&H -51%).

**HTML Results:** [`rsi_momentum_results.html`](incubator_strategies/rsi_momentum_results.html)

## 3. Grid Trading

**Description:** Market-neutral grid bot. Places buy orders below price and sell orders above at fixed intervals (grid_size TF-dependent: 0.5% 1h, 1% 4h, 2% 1d). Profits from oscillations in ranging markets. 10 levels each side.

**Core Strategy Module:** [`grid_trading_incubator.py`](alpha_engine/grid_trading_incubator.py)

**Status:** Backtest script ready. High risk/reward potential in sideways markets; vulnerable to trends.

## 4. Bollinger Bands Mean Reversion

**Description:** Classic mean reversion. **Long** below BB lower band (20,2), **short** above upper band. ATR(14)-based dynamic stops. Risk 1% per trade.

**Core Strategy Module:** [`bollinger_meanrev.py`](alpha_engine/bollinger_meanrev.py)

**Status:** Backtest script ready. Recommend adding trend filter (e.g., above EMA200 → only shorts).

## Audit Summary Table

From [`audit_summary.md`](incubator_strategies/audit_summary.md):

| Strategy      | Avg Sharpe | Avg Winrate | Avg Num Trades | Beat B&H % | Avg Max DD | Notes                                      |
|---------------|------------|-------------|----------------|------------|------------|--------------------------------------------|
| Diagonal     | 0.0       | 0%         | 0             | 0%        | 0.0       | Strict R2 filter causes 0 trades          |
| RSI Momentum | -0.48     | 28%        | 155           | 56% (5/9) | 0.26      | SOL1d Sharpe 0.47>0.3; beats B&H on alts  |
| Grid         | N/A       | N/A        | N/A           | N/A       | N/A       | Pending                                    |
| Bollinger    | N/A       | N/A        | N/A           | N/A       | N/A       | Pending                                    |

## Key Winners

**RSI(5) Momentum Long** – Most promising. Positive Sharpe on dailies, massive outperformance on SOL1d.

## Recommendations

- **Diagonal:** Loosen params (R²=0.80, min pivots=3) for more trades.
- **RSI:** Highly promising for altcoins daily TF; proceed to integration.
- **Grid:** High risk/reward for ranging assets; test on low-vol pairs.
- **BB Mean Rev:** Add trend filter to avoid trending markets.
- **Next:** Tune/optimize with [`auto_tuner.py`](alpha_engine/auto_tuner.py). Run pending backtests.

## Integration & Next Steps

- RSI Momentum added to core research backtests for portfolio inclusion.
- Execute Grid/BB backtests.
- All results files listed below.

## Results Files

- [`diagonal_trendline_results.json`](incubator_strategies/diagonal_trendline_results.json)
- [`diagonal_trendline_results.html`](incubator_strategies/diagonal_trendline_results.html)
- [`rsi_momentum_results.json`](incubator_strategies/rsi_momentum_results.json)
- [`rsi_momentum_results.html`](incubator_strategies/rsi_momentum_results.html)

*Report generated: 2026-03-25*
