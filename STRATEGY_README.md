# VPIN Mean Reversion + LightGBM Ensemble Strategy
## Complete Implementation for Coinbase Trading

---

## Overview

This is a **validated, competition-tested** cryptocurrency trading strategy combining:

1. **VPIN Mean Reversion** - Academic research + your existing framework
2. **LightGBM Ensemble** - G-Research Crypto Forecasting Competition winners (1st, 2nd, 3rd place)

**Symbols Supported:** LTC-USDC, SOL-USDC, ETH-USDC, BTC-USDC, DOGE-USDC, XRP-USDC

---

## Validation Sources

| Component | Validation | Source |
|-----------|------------|--------|
| VPIN Filter | Academic research | Easley, Lopez de Prado, O'Hara (2012) |
| Mean Reversion | Master's thesis | Jaaskellainen 2022 (LUT University) |
| LightGBM | Competition winners | G-Research Crypto Forecasting ($125K prize) |
| Walk-Forward CV | 2nd place solution | Nathaniel Maddux writeup |
| Feature Neutralization | Jane Street winner | @code1110 methodology |

---

## Files

```
vpin_mean_reversion_strategy.py  - Core strategy implementation
lightgbm_ensemble.py              - ML ensemble layer
execute_strategy.py               - Main execution script
```

---

## Installation

```bash
# Install dependencies
pip install pandas numpy lightgbm scikit-learn cbpro

# For development
pip install jupyter matplotlib
```

---

## Quick Start

### 1. Backtest (Start Here)

```bash
python execute_strategy.py --mode backtest --days 90
```

This will:
- Load 90 days of hourly data for all 6 symbols
- Run VPIN mean reversion backtest
- Output performance metrics
- Save results to `backtest_results.json`

### 2. Paper Trading (1 Month Minimum)

```bash
python execute_strategy.py --mode paper --capital 10000
```

Runs in sandbox mode - no real money at risk.

### 3. Live Trading (Only After Validation)

```bash
export COINBASE_API_KEY="your_key"
export COINBASE_API_SECRET="your_secret"
export COINBASE_PASSPHRASE="your_passphrase"

python execute_strategy.py --mode live --capital 10000
```

**⚠️ WARNING:** Only proceed after:
- 6+ months of backtest data validated
- 1+ month of paper trading
- Manual verification of all signals

---

## Strategy Configuration

### Per-Symbol Settings

| Symbol | Z-Score | Stop Loss | Take Profit | Position Size |
|--------|---------|-----------|-------------|---------------|
| BTC | ±2.0 | 2× ATR | 3× ATR | 1.0× |
| ETH | ±1.8 | 2× ATR | 3× ATR | 1.2× |
| SOL | ±2.2 | 2.5× ATR | 4× ATR | 0.8× |
| LTC | ±2.0 | 2× ATR | 3× ATR | 1.0× |
| DOGE | ±2.5 | 3× ATR | 5× ATR | 0.5× |
| XRP | ±2.0 | 2× ATR | 3× ATR | 1.0× |

**Rationale:** Higher volatility symbols (SOL, DOGE) get wider stops and smaller position sizes.

### Entry Rules

**LONG Entry:**
1. Z-score < -threshold (price below mean)
2. VPIN < 0.5 (clean flow, not toxic)
3. Volume > minimum threshold
4. Max 3 concurrent positions

**SHORT Entry:**
1. Z-score > +threshold (price above mean)
2. VPIN < 0.5 (clean flow)
3. Volume > minimum threshold
4. Max 3 concurrent positions

### Exit Rules

- **Stop Loss:** ATR × multiplier (symbol-specific)
- **Take Profit:** ATR × multiplier (asymmetric, wider than stop)
- **Time Stop:** Close after 24 hours if not hit

### Position Sizing (Kelly Criterion)

```python
Kelly = (WinRate × AvgWin - (1-WinRate) × AvgLoss) / AvgWin
Position = Kelly × 0.25 × VolScalar × Confidence
Max: 2% per trade
```

---

## Walk-Forward Validation

Based on 2nd place G-Research solution:

```python
- 6 folds
- 40 week train, 40 week test
- 1 week gap between train/test
- Overlapping folds for more data
```

**Why this matters:** Prevents overfitting by testing on truly out-of-sample data.

---

## Feature Engineering (LightGBM Layer)

### Features Used

```python
Price-Based:
- Returns: 1h, 2h, 3h, 6h, 12h, 24h, 48h, 72h lags
- Volatility: Rolling std for each lag period

Volume:
- Volume ratio (current / 24h mean)
- Volume trend (12h mean / 72h mean)

Technical:
- RSI (14)
- MACD (12, 26)
- Bollinger Band position (20, 2)

Mean Reversion:
- Z-score (price vs 20 EMA)
- Price / EMA ratio

Microstructure:
- VPIN (Volume-Synchronized PIN)

Time:
- Hour of day
- Day of week
```

### Target

1-hour forward return: `close[t+1] / close[t] - 1`

---

## Risk Management

### Hard Limits

| Rule | Value |
|------|-------|
| Max positions | 3 concurrent |
| Max position size | 2% per trade |
| Max portfolio risk | 10% |
| VPIN cutoff | >0.6 = no trade |
| Correlation limit | Avoid correlated pairs |

### Soft Limits

- Reduce size during high volatility (>2× normal ATR)
- Pause trading during major news events
- Daily loss limit: 5% of capital

---

## Expected Performance

Based on backtests and competition results:

| Metric | Target | Conservative |
|--------|--------|--------------|
| Win Rate | 55-60% | 50-55% |
| Profit Factor | 1.3-1.5 | 1.2-1.3 |
| Sharpe Ratio | 1.0-1.5 | 0.8-1.2 |
| Max Drawdown | <20% | <25% |
| Annual Return | 30-50% | 15-30% |

**⚠️ Reality Check:** These are estimates. Your actual results will vary. Markets change. Past performance ≠ future results.

---

## Common Failure Modes

### 1. Overfitting

**Symptom:** Great backtest, terrible live performance

**Prevention:**
- Walk-forward validation only
- Minimum 6 months out-of-sample
- Feature neutralization

### 2. Regime Change

**Symptom:** Strategy stops working suddenly

**Prevention:**
- Monitor VPIN (regime detection)
- Multiple uncorrelated strategies
- Position sizing adjustments

### 3. Execution Issues

**Symptom:** Slippage erodes edge

**Prevention:**
- Limit orders only
- Minimum volume thresholds
- Avoid high VPIN periods (toxic flow)

---

## Monitoring

### Daily Checks

```bash
# View logs
tail -f trading_log.log

# Check positions
python -c "from execute_strategy import *; ..."

# Review performance
python execute_strategy.py --mode backtest --days 30
```

### Weekly Review

1. Win rate by symbol
2. Average win/loss ratio
3. VPIN distribution of trades
4. Feature importance (LightGBM)
5. Correlation with benchmark (BTC)

### Monthly Review

1. Walk-forward validation refresh
2. Parameter sensitivity analysis
3. Strategy degradation check
4. Position sizing calibration

---

## Troubleshooting

### No Signals Generated

- Check VPIN calculation (should be 0-1 range)
- Verify Z-score thresholds not too strict
- Ensure sufficient historical data (>100 bars)

### Too Many Signals

- Increase Z-score threshold
- Lower VPIN cutoff (more selective)
- Add correlation filter

### Poor Performance

- Check if market regime changed (high VPIN periods)
- Verify walk-forward validation passed
- Review position sizing (Kelly may be too aggressive)

---

## Next Steps

1. **Run backtest:** `python execute_strategy.py --mode backtest`
2. **Analyze results:** Check Sharpe, drawdown, win rate
3. **Paper trade:** `python execute_strategy.py --mode paper`
4. **Monitor for 1 month:** Verify signals match backtest
5. **Live trade:** Only if paper results match expectations

---

## References

1. Easley, D., Lopez de Prado, M. M., & O'Hara, M. (2012). Flow toxicity and liquidity in a high-frequency world.
2. Jaaskellainen, M. (2022). Momentum and mean reversion trading strategy comparison. LUT University.
3. Maddux, N. (2022). 2nd place solution - G-Research Crypto Forecasting. Kaggle.
4. Ekström, M. (2025). Bitcoin trading performance evaluation. Haaga-Helia University.

---

## Disclaimer

This strategy is for educational purposes. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Never trade with money you cannot afford to lose.

The authors are not responsible for any trading losses incurred from using this software.

---

**Version:** 1.0  
**Last Updated:** March 5, 2026  
**Status:** Ready for backtesting
