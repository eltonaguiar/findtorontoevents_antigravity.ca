# Research: Kelly Criterion from ML Outputs + Realistic Crypto Slippage

**Date:** 2026-03-13
**Status:** Comprehensive literature review with implementation recommendations
**Gaps Addressed:** 2 of 30 identified gaps in prior research files

---

## GAP 1: Kelly Criterion from ML Model Outputs in Real-Time

### 1.1 Converting ML Classification Probability to Kelly Parameters

The Kelly formula for asymmetric payoffs is:

```
f* = p/a - (1-p)/b
```

Where `p` = win probability, `a` = fraction lost on loss, `b` = fraction gained on win.

Equivalently (the more common trading form):

```
f* = (p * b - q) / b
```

Where `q = 1 - p`, `b = avg_win / avg_loss`.

**The ML-to-Kelly pipeline requires three steps:**

**Step 1: Calibrate the ML probability.**
Raw XGBoost `predict_proba()` outputs are NOT well-calibrated. XGBoost tends to
produce overconfident probabilities near 0 and 1 (sigmoid distortion).

Two calibration methods (from scikit-learn):
- **Platt Scaling** (`CalibratedClassifierCV(method='sigmoid')`): Fits a logistic
  regression on holdout predictions. Works well for <1000 samples. Assumes
  sigmoid-shaped miscalibration.
- **Isotonic Regression** (`CalibratedClassifierCV(method='isotonic')`): Non-parametric,
  more flexible. Requires >1000 calibration samples. Preferred for crypto signals
  where miscalibration is non-monotonic.

**Step 2: Estimate win/loss ratio (b) from historical trades.**
- Use a rolling window of the last N closed trades (N=50-200).
- `avg_win = mean(returns | return > 0)`
- `avg_loss = abs(mean(returns | return < 0))`
- `b = avg_win / avg_loss`
- CRITICAL: Use the SAME signal type's history, not aggregate stats.

**Step 3: Feed calibrated p and empirical b into Kelly.**
```python
p_calibrated = calibrator.predict_proba(features)[0, 1]  # P(price_up)
b = avg_win / avg_loss  # from rolling window
q = 1 - p_calibrated
f_star = (p_calibrated * b - q) / b
```

### 1.2 Continuous Kelly for Financial Returns (Gaussian Approximation)

For continuous returns (not binary win/lose), the Kelly fraction is:

```
f* = mu / sigma^2
```

Where `mu` = expected excess return, `sigma` = standard deviation of returns.

For multi-asset portfolios:

```
f* = Sigma^{-1} * (mu - r)
```

Where `Sigma` = covariance matrix, `mu` = expected return vector, `r` = risk-free rate.

**WARNING:** `Sigma^{-1}` is extremely unstable for correlated assets. Small changes
to covariance produce wildly different allocations. Use shrinkage estimators
(Ledoit-Wolf) or regularization.

### 1.3 Fat Tails: Why Standard Kelly Overestimates

Crypto returns exhibit fat tails (kurtosis 5-20x normal). Standard Kelly assumes
log-normal returns and WILL over-bet in fat-tailed regimes.

**Key research (Osorio 2008, SSRN 1271373):**
- For Student-t distributed returns, optimal Kelly leverage is LOWER than Gaussian Kelly.
- Fatter tails (lower degrees of freedom) => more aggressive shrinkage needed.
- A prospect-theory approach with power decision weights gives increased weights to
  low-probability extreme events, naturally reducing position size.

**Schulist (2016, PIMCO) "Fat Tailed Kelly":**
- Showed that for distributions with tail index alpha < 2 (crypto often has alpha ~1.5-2.5),
  the standard Kelly can recommend infinite leverage.
- Solution: Use the empirical return distribution directly (bootstrap Kelly) rather
  than parametric assumptions.

**Practical correction for crypto:**
```python
# Empirical kurtosis adjustment
excess_kurtosis = scipy.stats.kurtosis(returns)
kurtosis_penalty = 1.0 / (1.0 + excess_kurtosis / 6.0)
f_adjusted = f_kelly * kurtosis_penalty

# For BTC with kurtosis ~8: penalty = 1/(1 + 8/6) = 0.43
# => Kelly is reduced to 43% of the Gaussian estimate
```

### 1.4 Parameter Uncertainty: The Baker-McHale Shrinkage

**Baker & McHale (2013), Decision Analysis 10(3):189-199:**
"Optimal Betting Under Parameter Uncertainty: Improving the Kelly Criterion"

Core finding: When win probability `p` is estimated (not known), the Kelly fraction
should be SHRUNK. The "back of envelope" correction:

```
f_shrunk = f_kelly * (1 - sigma_p^2 / (p * q))
```

Where `sigma_p` = standard error of the probability estimate.

For ML models with N calibration samples:
```python
# Standard error of a proportion
sigma_p = np.sqrt(p_hat * (1 - p_hat) / N_calibration_samples)

# Shrinkage factor
shrinkage = max(0, 1 - sigma_p**2 / (p_hat * (1 - p_hat)))
f_shrunk = f_kelly * shrinkage

# Example: p_hat=0.65, N=100
# sigma_p = sqrt(0.65*0.35/100) = 0.0477
# shrinkage = 1 - 0.0477^2 / (0.65*0.35) = 1 - 0.0023/0.2275 = 0.99
# => With 100 samples, barely shrinks. But with N=20:
# sigma_p = 0.1067, shrinkage = 1 - 0.0114/0.2275 = 0.95
```

### 1.5 Fractional Kelly: Simulation Results

**Matthew Downey (2024) simulation findings:**

| Uncertainty (sigma) | Full Kelly f* | Adjusted f* | Reduction |
|---------------------|---------------|-------------|-----------|
| 5% around p=0.70   | 0.40          | 0.38        | 5%        |
| 20% around p=0.70  | 0.40          | 0.36        | 10%       |
| 50% around p=0.70  | 0.40          | 0.26        | 35%       |

**Key finding:** Optimizing for the 10th percentile outcome (instead of median) reduces
optimal bet from 0.40 to **0.28** -- this IS fractional Kelly, emerging naturally from
downside risk optimization.

**Half-Kelly rule of thumb (widely validated):**
- Half Kelly returns 75% of Kelly-optimal growth with only 25% of the variance.
- Quarter Kelly returns ~56% of growth with ~6% of variance.

**Recommendation for crypto ML systems:**
- Use **quarter-Kelly** (0.25x) as baseline for any ML signal.
- Scale up to half-Kelly ONLY after >200 out-of-sample validated trades.
- NEVER use full Kelly in crypto (fat tails + model uncertainty = ruin).

### 1.6 Complete ML-to-Kelly Pipeline (Code-Level)

```python
from sklearn.calibration import CalibratedClassifierCV
import numpy as np

class MLKellySizer:
    """Convert ML model output to Kelly-optimal position size."""

    def __init__(self, model, kelly_fraction=0.25, min_edge=0.02,
                 min_trades=30, kurtosis_adjust=True):
        self.model = model
        self.kelly_fraction = kelly_fraction
        self.min_edge = min_edge
        self.min_trades = min_trades
        self.kurtosis_adjust = kurtosis_adjust
        self.calibrator = None
        self.trade_history = []  # (return, win_flag)

    def calibrate(self, X_cal, y_cal):
        """Fit probability calibrator on holdout data."""
        self.calibrator = CalibratedClassifierCV(
            self.model, method='isotonic', cv='prefit'
        )
        self.calibrator.fit(X_cal, y_cal)

    def get_kelly_fraction(self, features):
        """Compute position size from ML prediction."""
        # Step 1: Get calibrated probability
        if self.calibrator:
            p = self.calibrator.predict_proba(features.reshape(1, -1))[0, 1]
        else:
            p = self.model.predict_proba(features.reshape(1, -1))[0, 1]

        # Step 2: Get win/loss ratio from history
        if len(self.trade_history) < self.min_trades:
            return 0.0  # Not enough data

        returns = np.array([t[0] for t in self.trade_history])
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        if len(wins) < 5 or len(losses) < 5:
            return 0.0

        avg_win = np.mean(wins)
        avg_loss = abs(np.mean(losses))
        b = avg_win / avg_loss

        # Step 3: Kelly formula
        q = 1 - p
        f_kelly = (p * b - q) / b

        if f_kelly <= self.min_edge:
            return 0.0  # No edge

        # Step 4: Kurtosis adjustment for fat tails
        if self.kurtosis_adjust:
            kurt = max(scipy.stats.kurtosis(returns[-200:]), 0)
            kurtosis_penalty = 1.0 / (1.0 + kurt / 6.0)
            f_kelly *= kurtosis_penalty

        # Step 5: Parameter uncertainty shrinkage (Baker-McHale)
        n = len(self.trade_history)
        sigma_p = np.sqrt(p * q / n)
        shrinkage = max(0, 1 - sigma_p**2 / (p * q))
        f_kelly *= shrinkage

        # Step 6: Apply fractional Kelly
        f_final = f_kelly * self.kelly_fraction

        return max(0, min(f_final, 0.25))  # Cap at 25% of portfolio
```

---

## GAP 2: Realistic Slippage and Fee Modeling for Crypto Backtests

### 2.1 Actual Slippage on Binance by Order Size

Based on Amberdata (2024-2025), Talos TCA, and FinanceFeeds empirical data:

| Order Size | BTC/USDT Slippage | ETH/USDT Slippage | Altcoin Slippage | Notes |
|------------|-------------------|-------------------|------------------|-------|
| $1,000     | <1 bps (0.01%)    | <1 bps            | 1-3 bps          | Negligible on liquid pairs |
| $10,000    | 1-2 bps           | 2-3 bps           | 5-15 bps         | Still within spread |
| $100,000   | 3-8 bps           | 5-12 bps          | 20-50 bps        | Order book impact begins |
| $1,000,000 | 10-25 bps         | 15-40 bps         | 100-500 bps      | Significant market impact |

**Real-world example:** $100k ADA purchase on Binance during moderate volume: **37 bps
slippage** ($370 cost). Source: FinanceFeeds 2025.

**Retail vs Institutional gap:** Retail traders experience **0.4% more slippage** than
institutional traders on average (Binance Research, late 2024). Causes: suboptimal
timing, market orders instead of limit orders, no TWAP/VWAP execution.

### 2.2 Slippage Models: Linear vs Square Root vs Sigmoid

**Linear Model (simplest, usually wrong):**
```
slippage = k * order_size
```
Underpredicts for large orders, overpredicts for small ones.

**Square Root Model (Almgren-Chriss, industry standard):**
```
Impact = sigma * sqrt(Q / V) * pi
```
Where:
- `sigma` = daily price volatility (e.g., 0.03 for BTC)
- `Q` = order size in base currency
- `V` = average daily volume
- `pi` = market-specific constant (~0.1 for crypto, per HyperQuant)

Example: BTC order of $100k, daily volume $20B, daily vol 3%:
```
Impact = 0.03 * sqrt(100000 / 20000000000) * 0.1
       = 0.03 * sqrt(5e-6) * 0.1
       = 0.03 * 0.00224 * 0.1
       = 0.67 bps
```

**Sigmoid-Adjusted Square Root (Talos TMI Model, state-of-art):**
The Talos model adjusts the square root exponent using a sigmoid function based on
participation rate. Validated on 50,000+ parent orders across major crypto assets.
Key finding: pure square root **underestimates by ~4 bps** at very low participation
rates (<0.5%), which is where most institutional crypto orders fall.

**Recommended implementation:**
```python
def estimate_slippage_bps(order_size_usd, daily_volume_usd,
                          daily_volatility, is_buy=True):
    """
    Sigmoid-adjusted square root market impact model.
    Returns slippage in basis points.
    """
    if daily_volume_usd <= 0:
        return 100  # Illiquid, assume 1%

    participation = order_size_usd / daily_volume_usd

    # Square root base
    sqrt_impact = daily_volatility * np.sqrt(participation)

    # Sigmoid adjustment for low participation rates
    # At very low rates, actual impact > sqrt prediction
    sigmoid_adj = 1.0 + 0.5 / (1.0 + np.exp(-np.log10(participation) - 5))

    impact = sqrt_impact * sigmoid_adj * 10000  # Convert to bps

    # Add spread cost (half spread)
    spread_bps = 2.0  # ~2 bps half-spread for BTC/USDT on Binance

    # Add fixed component (minimum market impact)
    min_impact_bps = 0.5

    total_bps = max(impact + spread_bps, min_impact_bps)
    return total_bps
```

### 2.3 Fee Schedule: Major Crypto Exchanges (2025-2026)

**Binance Spot:**

| VIP Level | 30d Volume     | Maker Fee | Taker Fee |
|-----------|----------------|-----------|-----------|
| Regular   | < $1M          | 0.100%    | 0.100%    |
| VIP 1     | >= $1M         | 0.090%    | 0.100%    |
| VIP 2     | >= $5M         | 0.080%    | 0.100%    |
| VIP 3     | >= $20M        | 0.042%    | 0.060%    |
| VIP 9     | >= $4B         | 0.011%    | 0.023%    |

**Binance Futures (USD-M):**

| VIP Level | Maker Fee | Taker Fee |
|-----------|-----------|-----------|
| Regular   | 0.020%    | 0.050%    |
| VIP 1     | 0.016%    | 0.040%    |
| VIP 3     | 0.008%    | 0.032%    |
| VIP 9     | 0.000%    | 0.017%    |

**BNB discount:** 25% off when paying fees with BNB.

**Other exchanges (retail tier):**

| Exchange  | Maker   | Taker   |
|-----------|---------|---------|
| Coinbase  | 0.40%   | 0.60%   |
| Kraken    | 0.16%   | 0.26%   |
| Bybit     | 0.10%   | 0.10%   |
| OKX       | 0.08%   | 0.10%   |

**Funding rates (perpetual futures):** ~0.01% per 8-hour period = ~0.03%/day = ~11%/year.

### 2.4 Time-of-Day Liquidity Variation

**Amberdata (2024-2025) empirical findings on BTC/FDUSD, Binance:**

| Time Window (UTC) | Avg Depth (10bps) | Relative Slippage |
|--------------------|--------------------|--------------------|
| 09:00-14:00        | $3.86M             | 1.00x (baseline)   |
| 00:00-08:00 (Asia) | $3.58M             | 1.08x              |
| 16:00-24:00 (US)   | $3.32M             | 1.16x              |
| 21:00 (worst)      | $2.71M             | 1.42x              |

**Day-of-week effect:**
- Maximum depth: Saturday 17:00 UTC ($4.43M)
- Minimum depth: Monday 21:00 UTC ($2.36M)
- **87% variation** between best and worst hours

**Practical rule:** A trade costing 3 bps at 11:00 UTC costs ~5 bps at 21:00 UTC.
For a $1M order, this is a $200 difference just from timing.

**Recommendation for backtests:**
```python
def time_of_day_slippage_multiplier(hour_utc):
    """Empirical liquidity multiplier by hour (Amberdata 2024)."""
    # Peak liquidity at 11 UTC, trough at 21 UTC
    multipliers = {
        0: 1.08, 1: 1.08, 2: 1.08, 3: 1.10, 4: 1.10,
        5: 1.08, 6: 1.05, 7: 1.03, 8: 1.00, 9: 0.95,
        10: 0.93, 11: 0.90, 12: 0.93, 13: 0.95, 14: 0.98,
        15: 1.00, 16: 1.05, 17: 1.08, 18: 1.12, 19: 1.15,
        20: 1.20, 21: 1.42, 22: 1.35, 23: 1.20,
    }
    return multipliers.get(hour_utc, 1.10)
```

### 2.5 Impact of Ignoring Slippage on Backtest Sharpe

**Empirical findings from multiple sources:**

| Scenario | Backtest Sharpe | Live Sharpe | Degradation |
|----------|-----------------|-------------|-------------|
| High-frequency (100+ trades/day) | 3.0+ | Often negative | 100%+ |
| Medium-frequency (1-10/day) | 2.0 | 1.0-1.5 | 25-50% |
| Low-frequency (1-5/week) | 1.5 | 1.2-1.4 | 7-20% |
| Swing trading (1-2/month) | 1.2 | 1.0-1.15 | 5-15% |

**Gross-to-net return degradation:** Transaction costs reduce gross returns by
**10-30%** for typical crypto strategies. For high-turnover strategies, the degradation
is **20-50%** of gross returns (HyperQuant Research).

**Drawdown expansion:** Live max drawdown is typically **1.5-2.0x** the backtested max
drawdown. A 15% backtest drawdown => prepare for 25-30% in live trading.

**Rule of thumb for crypto strategies:**
```
Realistic_Sharpe = Backtest_Sharpe * 0.5 to 0.7  (medium frequency)
Realistic_Sharpe = Backtest_Sharpe * 0.3 to 0.5  (high frequency)
```

**Three-tier cost assumptions for crypto backtests (HyperQuant):**
- Conservative: 0.50% round trip (taker+taker + 2% annual funding)
- Moderate: 0.30% round trip (maker+taker + 1% annual funding)
- Optimistic: 0.15% round trip (maker+maker, minimal funding)

### 2.6 Complete Crypto Cost Model (Code-Level)

```python
@dataclass
class CryptoCostModel:
    """Realistic crypto transaction cost model with all components."""

    # Fee tier (Binance regular by default)
    maker_fee_pct: float = 0.10    # 10 bps
    taker_fee_pct: float = 0.10    # 10 bps
    bnb_discount: float = 0.25     # 25% off with BNB

    # Funding (for perpetual futures)
    funding_rate_8h: float = 0.01  # 0.01% per 8h = 1 bps
    funding_intervals_per_day: int = 3

    # Slippage model parameters
    slippage_model: str = "sqrt"  # "fixed", "linear", "sqrt"
    fixed_slippage_bps: float = 5.0

    def compute_slippage_bps(self, order_size_usd, daily_volume_usd,
                              daily_volatility=0.03, hour_utc=12):
        if self.slippage_model == "fixed":
            return self.fixed_slippage_bps

        if self.slippage_model == "linear":
            participation = order_size_usd / max(daily_volume_usd, 1)
            return participation * 10000 * 0.1  # 10% of participation rate

        # Square root model (default)
        participation = order_size_usd / max(daily_volume_usd, 1)
        base_impact = daily_volatility * np.sqrt(participation) * 10000

        # Time-of-day adjustment
        tod_mult = time_of_day_slippage_multiplier(hour_utc)
        # Volatility regime adjustment (high vol = more slippage)
        vol_mult = max(1.0, daily_volatility / 0.02)  # Normalize to 2% base

        return max(base_impact * tod_mult * vol_mult + 1.0, 0.5)

    def total_cost_bps(self, order_size_usd, daily_volume_usd,
                       is_maker=False, holding_days=0,
                       daily_volatility=0.03, hour_utc=12):
        # Trading fee
        fee = self.maker_fee_pct if is_maker else self.taker_fee_pct
        if self.bnb_discount > 0:
            fee *= (1 - self.bnb_discount)
        fee_bps = fee * 100  # Convert % to bps

        # Slippage (entry)
        slip = self.compute_slippage_bps(
            order_size_usd, daily_volume_usd, daily_volatility, hour_utc)

        # Funding cost (futures only)
        funding_bps = (self.funding_rate_8h *
                       self.funding_intervals_per_day *
                       holding_days)

        # Round trip = 2x fee + 2x slippage + funding
        total = 2 * fee_bps + 2 * slip + funding_bps
        return total
```

---

## Key Sources

### Kelly Criterion + ML
- Baker & McHale (2013), "Optimal Betting Under Parameter Uncertainty", Decision Analysis 10(3):189-199
- Osorio (2008), "A Prospect-Theory Approach to the Kelly Criterion for Fat-Tail Portfolios", SSRN 1271373
- Schulist (2016), "Fat Tailed Kelly", PIMCO/UCI
- Rising & Wyner, fractional Kelly = shrinkage to risk-free rate
- Frontiers in Applied Math (2020), "Practical Implementation of the Kelly Criterion"
- scikit-learn probability calibration documentation

### Slippage + Costs
- Talos TMI Model (2024), sigmoid-adjusted square root, 50k+ orders validated
- Amberdata (2024-2025), temporal liquidity patterns on Binance BTC/FDUSD
- Almgren & Chriss (1999), "Optimal Execution of Portfolio Transactions"
- HyperQuant Research, "Realistic Backtesting Methodology"
- Binance fee schedules (2025)
- hftbacktest (GitHub), order-book level backtesting with latency modeling
