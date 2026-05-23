# Pairs Trading System - Comprehensive Guide

## Table of Contents
1. [Mathematical Foundation](#mathematical-foundation)
2. [Parameter Selection Guidelines](#parameter-selection-guidelines)
3. [Risk Management Framework](#risk-management-framework)
4. [Implementation Examples](#implementation-examples)
5. [Performance Optimization](#performance-optimization)

---

## Mathematical Foundation

### Cointegration Theory

Two time series $Y_t$ and $X_t$ are **cointegrated** if:
1. Both series are I(1) - integrated of order 1 (non-stationary in levels but stationary in first differences)
2. There exists a linear combination $Z_t = Y_t - \beta X_t - \alpha$ that is I(0) - stationary

### Engle-Granger Two-Step Method

**Step 1:** Estimate the long-run equilibrium relationship via OLS:

$$Y_t = \alpha + \beta X_t + \varepsilon_t$$

The residuals $\varepsilon_t$ represent the deviation from equilibrium (spread).

**Step 2:** Test residuals for stationarity using Augmented Dickey-Fuller:

$$\Delta\varepsilon_t = \gamma\varepsilon_{t-1} + \sum_{i=1}^{p}\delta_i \Delta\varepsilon_{t-i} + u_t$$

- $H_0: \gamma = 0$ (unit root exists, no cointegration)
- $H_1: \gamma < 0$ (stationary, cointegration exists)

### Johansen Test (Multiple Cointegrating Relationships)

The Johansen test is based on the Vector Error Correction Model (VECM):

$$\Delta Y_t = \Pi Y_{t-1} + \sum_{i=1}^{p-1}\Gamma_i \Delta Y_{t-i} + \Psi D_t + \varepsilon_t$$

Where:
- $Y_t$ is a vector of n time series
- $\Pi = \alpha\beta'$ contains information about long-run relationships
- $\alpha$ is the adjustment coefficient matrix
- $\beta$ is the cointegrating vector matrix
- $r = \text{rank}(\Pi)$ = number of cointegrating relationships

**Test Statistics:**
- Trace statistic: $\lambda_{trace} = -T \sum_{i=r+1}^{n}\ln(1-\lambda_i)$
- Max eigenvalue: $\lambda_{max} = -T \ln(1-\lambda_{r+1})$

### Z-Score Calculation

$$Z_t = \frac{\text{Spread}_t - \mu_{\text{Spread}}}{\sigma_{\text{Spread}}}$$

**Spread Types:**
- **Price spread:** $S_t = P_{1,t} - \beta P_{2,t}$
- **Log spread:** $S_t = \ln(P_{1,t}) - \beta \ln(P_{2,t})$ (recommended for crypto)
- **Ratio:** $S_t = P_{1,t} / P_{2,t}$

### Half-Life of Mean Reversion

From the Ornstein-Uhlenbeck process:

$$dS = -\theta(S-\mu)dt + \sigma dW$$

**Half-life:** $t_{1/2} = \frac{\ln(2)}{\theta}$

Where $\theta$ is estimated from:
$$\Delta\varepsilon_t = \alpha + \rho\varepsilon_{t-1} + u_t$$
$$\theta = -\rho$$

---

## Parameter Selection Guidelines

### Lookback Period

| Asset Class | Recommended Range | Rationale |
|-------------|-------------------|-----------|
| Crypto (BTC/ETH) | 30-90 days | High volatility, faster regime changes |
| Large Cap Equities | 60-120 days | Moderate volatility, stable relationships |
| Sector ETFs | 90-180 days | Lower volatility, longer cycles |
| Commodities | 60-252 days | Seasonal patterns, varying volatility |

**Selection Criteria:**
- Half-life of mean reversion × 2-3
- Minimum: 30 periods for statistical significance
- Maximum: 252 periods (1 year) to avoid stale relationships

### Z-Score Thresholds

| Market Regime | Entry | Exit | Stop Loss | Rationale |
|---------------|-------|------|-----------|-----------|
| Normal | ±2.0 | ±0.5 | ±3.5 | Balanced opportunity/risk |
| High Volatility | ±2.5 | ±0.5 | ±4.0 | Wider entry to avoid noise |
| Low Volatility | ±1.5 | ±0.0 | ±3.0 | Tighter entry for more signals |
| Bear Market | ±2.0 | ±0.0 | ±3.0 | Faster exits, no profit target |

**Guidelines:**
- Entry should be 2-4 standard deviations
- Exit should be 0-1 standard deviations (mean reversion)
- Stop loss should be 1-1.5 standard deviations beyond entry
- Exit < Entry (always)

### Position Sizing Methods

#### 1. Dollar-Neutral
```
Long $X of Asset1, Short $X of Asset2
Position sizes: Q1 = X/P1, Q2 = X/P2
```
**Best for:** Market-neutral portfolios, equal risk assumption

#### 2. Beta-Neutral
```
Portfolio beta = w1×β1 + w2×β2 = 0
With hedge ratio: w1 = hedge_ratio × w2
Adjusted position: Q2 = Q1 × (β1/β2)
```
**Best for:** Hedging market exposure, multi-asset portfolios

#### 3. Volatility Parity
```
Position sizes inversely proportional to volatility
Q1 = (Capital/2)/P1 × (σ_avg/σ1)
Q2 = (Capital/2)/P2 × (σ_avg/σ2)
```
**Best for:** Equal risk contribution, risk budgeting

### Transaction Cost Considerations

| Asset Class | Typical Cost | Impact on Thresholds |
|-------------|--------------|---------------------|
| Crypto (Binance) | 0.1% | Increase entry by 0.1-0.2 |
| Crypto (institutional) | 0.02-0.05% | Minimal adjustment |
| US Equities | 0.01-0.05% | Minimal adjustment |
| ETFs | 0.01-0.03% | Minimal adjustment |

**Rule of Thumb:**
- Entry threshold ≥ 2× round-trip cost in standard deviations
- For 0.1% cost, add 0.1-0.2 to entry threshold

---

## Risk Management Framework

### Position-Level Risk Controls

#### 1. Stop Loss Rules
```python
# Z-score stop loss
if abs(current_zscore) > stop_loss_threshold:
    exit_position()

# PnL-based stop loss
unrealized_pnl_pct = current_pnl / position_value
if unrealized_pnl_pct < -0.05:  # 5% max loss
    exit_position()
```

#### 2. Time-Based Exits
```python
# Maximum holding period
if holding_periods > max_holding:
    exit_position(reason="time_stop")

# Half-life based exit
max_holding = int(half_life * 3)  # 3× half-life
```

#### 3. Divergence Continuation
```python
# If z-score moves further away after entry
if position_direction == LONG and zscore < entry_zscore - 0.5:
    exit_position(reason="divergence_continuation")
```

### Portfolio-Level Risk Controls

#### 1. Correlation Risk
```python
# Maximum correlation between pairs
if pair_correlation > 0.8:
    reduce_position_size()

# Portfolio concentration limit
max_pair_exposure = 0.20  # 20% of capital per pair
```

#### 2. Drawdown Controls
```python
# Circuit breakers
if portfolio_drawdown > -0.10:  # 10% drawdown
    reduce_all_positions(0.5)
    
if portfolio_drawdown > -0.15:  # 15% drawdown
    close_all_positions()
    pause_trading(days=5)
```

#### 3. Volatility Regime Detection
```python
# VIX-based or realized volatility regime
if current_volatility > vol_percentile_90:
    widen_entry_thresholds(1.5)
    reduce_position_sizes(0.7)
```

### Value at Risk (VaR) Calculation

```python
# Historical VaR (95% confidence)
var_95 = -np.percentile(returns, 5) * portfolio_value

# Parametric VaR
var_95 = -(mu - 1.645 * sigma) * portfolio_value

# Monte Carlo VaR
simulated_returns = np.random.normal(mu, sigma, 100000)
var_95 = -np.percentile(simulated_returns, 5) * portfolio_value
```

---

## Implementation Examples

### Example 1: BTC/ETH Pair

```python
from pairs_trading_system import *

# Configuration for crypto pair
config = PairConfig(
    asset1="BTC",
    asset2="ETH",
    lookback_period=60,        # 60 days for crypto
    entry_zscore=2.0,
    exit_zscore=0.5,
    stop_loss_zscore=3.5,
    max_holding_periods=20,    # ~3 weeks max
    position_size_method="dollar_neutral"
)

# Initialize strategy
strategy = PairsTradingStrategy(config, use_log_prices=True)

# Test for cointegration
result = PairsTradingStrategy.engle_granger_test(btc_prices, eth_prices)
print(f"Cointegrated: {result.is_cointegrated}, p-value: {result.p_value:.4f}")

# Run backtest
backtester = PairsBacktester(strategy, initial_capital=100000)
results = backtester.run_backtest(btc_prices, eth_prices)

# Get metrics
metrics = backtester.get_performance_metrics()
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Win Rate: {metrics['win_rate']:.2%}")
```

### Example 2: Sector ETF Pair (XLB/XLP)

```python
# Configuration for sector ETFs
config = PairConfig(
    asset1="XLB",  # Materials
    asset2="XLP",  # Consumer Staples
    lookback_period=90,        # Longer for ETFs
    entry_zscore=2.0,
    exit_zscore=0.0,           # Exit at mean
    stop_loss_zscore=3.0,
    max_holding_periods=30,
    position_size_method="beta_neutral"
)

strategy = PairsTradingStrategy(config, use_log_prices=False)
```

### Example 3: Finding Cointegrated Pairs

```python
# Universe of assets
price_df = pd.DataFrame({
    'BTC': btc_prices,
    'ETH': eth_prices,
    'SOL': sol_prices,
    'DOT': dot_prices,
    'SPY': spy_prices,
    'QQQ': qqq_prices
})

# Find all cointegrated pairs
coint_pairs = PairsTradingStrategy.find_cointegrated_pairs(
    price_df,
    significance=0.05,
    min_half_life=5,
    max_half_life=100
)

print(coint_pairs.head(10))
```

### Example 4: Parameter Optimization

```python
# Grid search for optimal parameters
opt_results = ParameterOptimizer.optimize_zscore_thresholds(
    price1, price2,
    entry_range=np.arange(1.5, 3.5, 0.25),
    exit_range=np.arange(0.0, 1.5, 0.25),
    lookback_range=[30, 60, 90],
    metric="sharpe"
)

# Best parameters
best = opt_results.iloc[0]
print(f"Best Entry: {best['entry']}, Exit: {best['exit']}, Lookback: {best['lookback']}")

# Walk-forward optimization (avoids overfitting)
wf_results = ParameterOptimizer.walk_forward_optimization(
    price1, price2,
    train_size=252,    # 1 year training
    test_size=63       # 3 months testing
)

print(f"Out-of-sample Sharpe: {wf_results['sharpe_ratio'].mean():.2f}")
```

---

## Performance Optimization

### Computational Efficiency

#### 1. Vectorized Operations
```python
# Fast rolling calculations
spread = price1 - hedge_ratio * price2
zscore = (spread - spread.rolling(window).mean()) / spread.rolling(window).std()
```

#### 2. Pre-computation
```python
# Calculate once, use many times
hedge_ratios = {}
for pair in pairs:
    hedge_ratios[pair] = calculate_hedge_ratio(pair)
```

#### 3. Parallel Processing
```python
from multiprocessing import Pool

def test_pair(pair):
    return PairsTradingStrategy.engle_granger_test(pair[0], pair[1])

with Pool() as pool:
    results = pool.map(test_pair, all_pairs)
```

### Memory Optimization

```python
# Use appropriate data types
prices = prices.astype('float32')  # Instead of float64

# Process in chunks
for chunk in pd.read_csv('prices.csv', chunksize=10000):
    process_chunk(chunk)
```

### Production Deployment

#### 1. Real-time Signal Generation
```python
class LivePairsTrader:
    def __init__(self, config):
        self.strategy = PairsTradingStrategy(config)
        self.position = None
        
    def on_price_update(self, price1, price2):
        spread = self.strategy.calculate_spread(price1, price2)
        zscore = self.strategy.calculate_zscore(spread)
        
        if self.position is None and abs(zscore) > config.entry_zscore:
            self.enter_position(zscore)
        elif self.position and self.should_exit(zscore):
            self.exit_position()
```

#### 2. Risk Monitoring
```python
def monitor_risk(positions, portfolio_value):
    # Calculate portfolio VaR
    var = calculate_portfolio_var(positions)
    
    # Check drawdown
    drawdown = calculate_drawdown(portfolio_value)
    
    # Alert if risk limits breached
    if var > var_limit or drawdown > drawdown_limit:
        send_alert("Risk limit breached")
        reduce_exposure()
```

---

## Best Practices

### 1. Pair Selection
- **Economic rationale:** Choose pairs with fundamental relationships
- **Statistical validation:** Require p-value < 0.05 for cointegration
- **Half-life filter:** Target 5-50 periods for tradable mean reversion
- **Liquidity:** Ensure both legs are liquid for execution

### 2. Signal Generation
- **Multiple confirmations:** Use Hurst exponent, correlation filters
- **Regime detection:** Adjust thresholds based on volatility
- **Avoid overfitting:** Use walk-forward optimization

### 3. Execution
- **Limit orders:** Use limit orders to reduce slippage
- **TWAP/VWAP:** Split large orders across time
- **Smart order routing:** Route to best available venue

### 4. Monitoring
- **Daily P&L attribution:** Track performance by pair
- **Signal decay:** Monitor if z-score patterns change
- **Correlation breakdown:** Alert if pair correlation shifts

---

## References

1. Engle, R.F. and Granger, C.W. (1987). "Co-integration and Error Correction: Representation, Estimation, and Testing." Econometrica.

2. Johansen, S. (1991). "Estimation and Hypothesis Testing of Cointegration Vectors in Gaussian Vector Autoregressive Models." Econometrica.

3. Gatev, E., Goetzmann, W.N., and Rouwenhorst, K.G. (2006). "Pairs Trading: Performance of a Relative-Value Arbitrage Rule." Review of Financial Studies.

4. Avellaneda, M. and Lee, J.H. (2010). "Statistical Arbitrage in the U.S. Equities Market." Quantitative Finance.

---

*Document Version: 1.0.0*
*Last Updated: 2024*
