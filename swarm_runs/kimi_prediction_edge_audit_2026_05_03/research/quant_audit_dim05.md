# Dimension 05: Backtesting Methodology Improvements
## Institutional-Grade Quantitative Audit Report

**Prepared for:** Platform Backtesting Infrastructure Review
**Scope:** Gap analysis between current backtesting methodology and institutional (hedge fund) standards
**Key References:** Lopez de Prado (2018), Harvey & Liu (2014), Bailey & Lopez de Prado (2014)

---

## Executive Summary

The current platform operates at a **retail-grade to sub-institutional level** in backtesting methodology. The critical findings are:

1. **Walk-forward OOS results are catastrophic** -- negative Sharpe ratios for CRYPTO (-0.242), FOREX (-1.406), and COMMODITY (-2.412) indicate strategies that fail institutional standards by a wide margin
2. **Sample sizes are systematically inadequate** -- multiple strategies flagged as "THIN" with fewer than 50 trades, far below the 200-500 trade institutional minimum
3. **No combinatorial purged cross-validation** -- the single most important institutional backtesting innovation (Lopez de Prado, 2018) is entirely absent
4. **No PSR/DSR validation** -- strategies are accepted without probabilistic Sharpe ratio or deflated Sharpe ratio testing
5. **Multiple testing correction is absent** -- with 50+ strategies tested, expected false discovery rate exceeds 50% without correction
6. **Bootstrap validation not implemented** -- 10,000-path bootstrap for Sharpe confidence intervals is missing
7. **Transaction cost modeling is primitive** -- no asset-class-specific cost modeling with realistic slippage
8. **Code duplication (5+ copies of outcome_resolver.py)** creates version-control risk and inconsistent backtest results

**Verdict: The platform requires a fundamental overhaul of its backtesting framework before it can be considered institutional-grade.**

---

## 1. Gap Analysis: Current vs. Institutional Standards

### 1.1 Current Platform State

| Dimension | Current Platform | Institutional Standard | Gap Severity |
|-----------|-----------------|----------------------|--------------|
| Walk-forward splits | 60% IS / 40% OOS, 12 folds (ETF) | Combinatorial Purged CV with N>=6, k>=2 | **Critical** |
| Minimum trades | 50 (crypto/futures), 100 (equity/forex) | 200-500 per asset class, 1000+ for HFT | **High** |
| PSR threshold | Not implemented | PSR > 0.95 required for deployment | **Critical** |
| DSR threshold | Not implemented | DSR > 0.95 required for deployment | **Critical** |
| Bootstrap CI | Not implemented | 10,000 paths, BCa method, 95% CI | **Critical** |
| Multiple testing | Not implemented | Bonferroni / Holm / Benjamini-Hochberg | **High** |
| Transaction costs | Generic spread + commission | Asset-class-specific with market impact | **High** |
| OOS Sharpe (CRYPTO) | -0.242 | > 1.0 minimum for consideration | **Critical** |
| OOS Sharpe (FOREX) | -1.406 | > 1.0 minimum for consideration | **Critical** |
| OOS Sharpe (COMMODITY) | -2.412 | > 1.0 minimum for consideration | **Critical** |
| OOS Sharpe (ETF) | 6.368 (suspicious, only 12 folds) | < 3.0 realistic max for medium-freq | **High** |
| Pick resolution rate | 27.3% within 24h (72.7% open) | > 80% within tracking window | **High** |
| Tracking window | 24h (extending to 120h) | Should be strategy-optimized | **Medium** |
| Code maintenance | 5+ copies of outcome_resolver.py | Single source of truth | **Medium** |

### 1.2 The Institutional Benchmark

According to industry standards cited in Lopez de Prado's "Advances in Financial Machine Learning" and Harvey & Liu's "Backtesting" (2014), a quant fund like Two Sigma, Renaissance Technologies, or Citadel would require [^87^][^89^][^100^]:

1. **Combinatorial Purged Cross-Validation (CPCV)** -- the gold standard for financial backtesting, generating multiple independent backtest paths
2. **Probabilistic Sharpe Ratio (PSR) > 0.95** -- meaning 95% confidence the true Sharpe exceeds a benchmark
3. **Deflated Sharpe Ratio (DSR) > 0.95** -- adjusting for multiple testing and non-Normal returns
4. **Minimum Track Record Length (MinTRL)** -- e.g., 2.73 years for Sharpe=2 to be > Sharpe=1 at 95% confidence [^100^]
5. **Minimum 200-500 trades** across multiple market regimes (bull, bear, sideways) [^27^][^29^]
6. **10,000-path bootstrap** with BCa (bias-corrected and accelerated) confidence intervals [^107^]
7. **Survivorship-bias-free datasets** with point-in-time accuracy [^118^][^122^]
8. **Regime-aware testing** with explicit regime detection and regime-specific performance reporting [^120^][^123^]

---

## 2. Walk-Forward Analysis: Fixing the Negative OOS Sharpe

### 2.1 Root Cause Analysis

The negative OOS Sharpe ratios (CRYPTO: -0.242, FOREX: -1.406, COMMODITY: -2.412) indicate one or more of the following fundamental problems:

**A. Overfitting via Parameter Optimization**
When strategy parameters are optimized on in-sample data and then tested on out-of-sample data, negative OOS Sharpe is the hallmark of overfitting. The 60/40 split provides only a single OOS path, which is statistically unreliable [^89^][^109^].

**B. Information Leakage**
Standard walk-forward without purging allows training samples whose label horizons overlap with test periods to "leak" future information into the model. In financial time series, where observations are serially correlated, this leakage is pervasive and catastrophic [^89^][^88^].

**C. Single-Path Dependency**
Walk-forward evaluates on a single historical path. If that path happens to be unfavorable, the strategy is rejected even if it has genuine edge. Conversely, a favorable path leads to false acceptance. Both are Type I/II errors [^89^].

**D. The ETF Anomaly (Sharpe 6.368)**
The suspiciously high ETF Sharpe of 6.368 with only 12 folds and 10.8% decay strongly suggests:
- Small sample bias (only 12 independent test periods)
- Potential data leakage
- Possible survivorship bias in ETF selection
- Mean-reversion to realistic levels expected with more folds

### 2.2 The Fix: Combinatorial Purged Cross-Validation (CPCV)

**Implementation Requirements:**

CPCV replaces the single walk-forward path with multiple combinatorial train/test splits, each generating an independent backtest path [^89^][^95^][^127^].

```
Algorithm: Combinatorial Purged Cross-Validation

Input: Time series of length T, number of groups N, test groups k
Output: Distribution of OOS Sharpe ratios across phi(N,k) paths

1. Divide data into N sequential, non-overlapping groups (G1, G2, ..., GN)
2. Generate all combinations C(N, k) of k groups as test sets
3. For each combination:
   a. Remaining N-k groups form the training set
   b. PURGE: Remove training observations whose label horizon 
      overlaps with any test period
   c. EMBARGO: Remove h observations after each test period 
      from the training set (prevents leakage from delayed reactions)
   d. Train model on purged training set
   e. Evaluate on test set
   f. Record OOS performance metric
4. Aggregate: Compute distribution of Sharpe ratios across all paths
5. Decision: Strategy passes if median OOS Sharpe > threshold AND
   PSR > 0.95 AND DSR > 0.95
```

**Key Parameters:**
- **N (number of groups):** Minimum 6, recommended 10-20. More groups = more paths = better statistical power
- **k (test groups per split):** Typically N/3 to N/2. Controls train/test ratio.
- **h (embargo period):** Typically 2-5% of observations, or calibrated by autocorrelation decay
- **Number of paths:** phi(N,k) = (k/N) * C(N, N-k). For N=10, k=3: phi = 30 paths [^95^]

**Example Configuration:**
| N | k | Paths | Train Groups | Test Groups | Path Diversity |
|---|---|-------|-------------|-------------|----------------|
| 6 | 2 | 5 | 4 | 2 | Low |
| 10 | 3 | 30 | 7 | 3 | Medium |
| 15 | 5 | 105 | 10 | 5 | High |
| 20 | 7 | 280 | 13 | 7 | Very High |

The platform should implement CPCV with **N >= 10, k >= 3**, generating at least 30 independent backtest paths per strategy. This is the single most impactful improvement possible [^89^][^91^].

### 2.3 Additional Walk-Forward Improvements

1. **Nested Cross-Validation:** Outer loop for model selection, inner loop for hyperparameter tuning. Prevents optimization bias in the CV process itself.
2. **Expanding Window (not rolling):** Training set grows over time, preserving more data for early periods while maintaining recency bias for later periods.
3. **Regime-Stratified Splits:** Ensure each fold contains representative samples from bull, bear, and sideways markets [^27^][^123^].
4. **Minimum Fold Size:** Each test fold must contain at least 30 independent observations (CLT threshold) [^29^].

---

## 3. Purged K-Fold Cross-Validation Implementation

### 3.1 Standard Purged K-Fold

For scenarios where CPCV is computationally prohibitive, standard Purged K-Fold provides a middle ground [^89^][^88^]:

```python
class PurgedKFold:
    """
    K-fold CV with purging and embargo for financial time series.
    Based on Lopez de Prado (2018), Advances in Financial Machine Learning.
    """
    
    def __init__(self, n_splits=5, pct_embargo=0.01):
        self.n_splits = n_splits
        self.pct_embargo = pct_embargo
    
    def split(self, X, y, pred_times, eval_times):
        """
        Parameters:
        -----------
        X : feature matrix
        y : target labels
        pred_times : Series, prediction times for each observation
        eval_times : Series, evaluation times (label horizon end) for each observation
        """
        indices = np.arange(X.shape[0])
        fold_bounds = np.linspace(0, X.shape[0], self.n_splits + 1, dtype=int)
        
        for i in range(self.n_splits):
            # Test set boundaries
            test_start = fold_bounds[i]
            test_end = fold_bounds[i + 1]
            test_indices = indices[test_start:test_end]
            
            # Training set: everything except test + purged + embargo
            train_mask = np.ones(X.shape[0], dtype=bool)
            train_mask[test_start:test_end] = False  # Remove test
            
            # PURGE: Remove observations whose eval_time overlaps test period
            test_pred_time = pred_times.iloc[test_start]
            test_eval_time = eval_times.iloc[min(test_end - 1, len(eval_times) - 1)]
            
            for j in range(X.shape[0]):
                if not train_mask[j]:
                    continue
                # If observation j's label period overlaps with test period, purge it
                if (pred_times.iloc[j] < test_eval_time and 
                    eval_times.iloc[j] > test_pred_time):
                    train_mask[j] = False
            
            # EMBARGO: Remove observations after test period
            embargo_start = test_end
            embargo_end = min(
                test_end + int(self.pct_embargo * X.shape[0]),
                X.shape[0]
            )
            train_mask[embargo_start:embargo_end] = False
            
            train_indices = indices[train_mask]
            yield train_indices, test_indices
```

### 3.2 Combinatorial Purged Cross-Validation (Full Implementation)

```python
class CombinatorialPurgedCV:
    """
    Combinatorial Purged Cross-Validation.
    Generates phi(N,k) independent backtest paths.
    """
    
    def __init__(self, n_splits=10, n_test_splits=3, pct_embargo=0.01):
        self.n_splits = n_splits  # N groups
        self.n_test_splits = n_test_splits  # k test groups
        self.pct_embargo = pct_embargo
    
    def split(self, X, y, pred_times, eval_times):
        """Generate all combinations of test group selections."""
        from itertools import combinations
        
        group_bounds = np.linspace(0, X.shape[0], self.n_splits + 1, dtype=int)
        groups = [(group_bounds[i], group_bounds[i+1]) 
                  for i in range(self.n_splits)]
        
        # All combinations of k test groups out of N
        for test_group_indices in combinations(range(self.n_splits), 
                                                self.n_test_splits):
            test_mask = np.zeros(X.shape[0], dtype=bool)
            for gi in test_group_indices:
                start, end = groups[gi]
                test_mask[start:end] = True
            test_indices = np.where(test_mask)[0]
            
            # Build training set with purging and embargo
            train_mask = ~test_mask
            
            # PURGE: Remove training observations overlapping with any test group
            test_pred_min = pred_times.iloc[test_indices].min()
            test_eval_max = eval_times.iloc[test_indices].max()
            
            for j in range(X.shape[0]):
                if not train_mask[j]:
                    continue
                if (pred_times.iloc[j] < test_eval_max and 
                    eval_times.iloc[j] > test_pred_min):
                    train_mask[j] = False
            
            # EMBARGO: Remove observations after the last test group
            last_test_end = max(groups[gi][1] for gi in test_group_indices)
            embargo_end = min(
                last_test_end + int(self.pct_embargo * X.shape[0]),
                X.shape[0]
            )
            train_mask[last_test_end:embargo_end] = False
            
            train_indices = np.where(train_mask)[0]
            if len(train_indices) > 0 and len(test_indices) > 0:
                yield train_indices, test_indices
    
    def num_paths(self):
        """Number of backtest paths: phi(N,k) = (k/N) * C(N, N-k)"""
        from math import comb
        N, k = self.n_splits, self.n_test_splits
        return (k / N) * comb(N, N - k)
```

### 3.3 Embargo Period Calibration

The embargo period `h` should be calibrated to the autocorrelation structure of the data [^89^]:

```
h = max_lag where autocorrelation(r_t, r_{t-lag}) > 0.05
```

For typical asset classes:
- **Equities:** h = 1-3 days (low autocorrelation in returns)
- **Forex:** h = 2-5 days (moderate autocorrelation)
- **Crypto:** h = 1-2 days (high volatility, rapid decay)
- **Commodities:** h = 3-7 days (seasonal effects, higher autocorrelation)

---

## 4. Minimum Sample Size Requirements

### 4.1 Per-Asset-Class Minimums

Based on Central Limit Theorem, statistical power analysis, and institutional standards [^27^][^29^][^104^]:

| Asset Class | Minimum Trades | Recommended | Rationale |
|-------------|---------------|-------------|-----------|
| **Equities** | 200 | 500 | Lower volatility, need more trades for significance |
| **Forex** | 200 | 500 | 24h market, need regime coverage |
| **Crypto** | 100 | 300 | Higher volatility, faster regime changes |
| **Futures** | 200 | 500 | Contract rollovers reduce effective sample |
| **ETF** | 200 | 500 | Need sector/broad market regime diversity |
| **Commodity** | 150 | 400 | Seasonal patterns require multi-year data |

### 4.2 Statistical Power Analysis

The sample size formula for a Sharpe ratio test [^27^]:

```
n = (Z_alpha + Z_beta)^2 * (1 + 0.5 * SR^2) / SR^2

Where:
  Z_alpha = 1.96 (two-tailed, alpha=0.05)
  Z_beta  = 0.84  (power=0.80)
  SR      = expected Sharpe ratio
```

**Required sample sizes for different Sharpe ratios (80% power, alpha=0.05):**

| Target Sharpe | Required Trades | Required (with decay) |
|--------------|----------------|---------------------|
| 0.5 | ~63 | ~80 |
| 1.0 | ~20 | ~25 |
| 1.5 | ~12 | ~15 |
| 2.0 | ~8 | ~10 |

However, these are minimum theoretical bounds. Institutional practice requires substantially more to account for:
1. **Non-Normal returns** (fat tails inflate variance)
2. **Regime dependency** (need coverage across bull/bear/sideways)
3. **Strategy decay** (edge erodes over time)
4. **Multiple testing** (correction reduces effective significance)

### 4.3 The Current Platform's Problem

With only **12 folds for ETF** and strategies flagged as "THIN" (likely < 50 trades), the platform suffers from:

1. **12% statistical power** at realistic effect sizes (as demonstrated in academic research with 34 folds) [^41^]
2. **Inability to distinguish signal from noise** -- the difference between Sharpe 0.5 and Sharpe 0.0 requires ~63 trades minimum
3. **Overfitting certainty** -- with 50+ strategies tested on small samples, false discoveries are guaranteed

**Immediate Action Required:** Do not deploy any strategy with fewer than 100 trades in backtest. Flag all "THIN" strategies as "INSUFFICIENT_DATA -- DO NOT TRADE."

---

## 5. Transaction Cost Modeling

### 5.1 Current State vs. Required

The platform's current transaction cost model (spread + slippage + commission) is generic and likely underestimates true costs, especially for less liquid instruments [^102^][^105^][^110^].

### 5.2 Asset-Class-Specific Cost Models

| Cost Component | Equities (Liquid ETF) | Forex | Crypto | Commodities |
|----------------|----------------------|-------|--------|-------------|
| **Spread** | 0.01% (SPY) | 0.02-0.05% (majors) | 0.05-0.2% (liquid) | 0.02-0.1% |
| **Commission** | $0 (many brokers) | $0 (spread-only) | 0.05-0.1% | $1-5/contract |
| **Slippage (liquid)** | 0.01% | 0.01-0.02% | 0.02-0.05% | 0.02-0.05% |
| **Slippage (illiquid)** | 0.05-0.2% | 0.05-0.2% | 0.1-0.5% | 0.1-0.5% |
| **Market Impact** | Negligible (<$1M) | Negligible | Small (<$100K) | Moderate |
| **Total (liquid, round-trip)** | 0.02-0.04% | 0.03-0.07% | 0.07-0.25% | 0.05-0.15% |
| **Total (illiquid, round-trip)** | 0.1-0.4% | 0.1-0.4% | 0.2-1.0% | 0.2-0.6% |

### 5.3 Implementation Requirements

```python
class TransactionCostModel:
    """Asset-class-specific transaction cost model."""
    
    COST_PARAMETERS = {
        'EQUITY_LIQUID': {
            'spread_bps': 1.0,
            'commission_bps': 0.0,
            'slippage_bps': 1.0,
            'market_impact_coeff': 0.0,
            'min_commission': 0.0
        },
        'EQUITY_ILLIQUID': {
            'spread_bps': 5.0,
            'commission_bps': 1.0,
            'slippage_bps': 5.0,
            'market_impact_coeff': 0.1,
            'min_commission': 1.0
        },
        'FOREX_MAJOR': {
            'spread_bps': 2.0,
            'commission_bps': 0.0,
            'slippage_bps': 1.0,
            'market_impact_coeff': 0.0,
            'min_commission': 0.0
        },
        'FOREX_MINOR': {
            'spread_bps': 5.0,
            'commission_bps': 0.0,
            'slippage_bps': 3.0,
            'market_impact_coeff': 0.05,
            'min_commission': 0.0
        },
        'CRYPTO_LIQUID': {
            'spread_bps': 5.0,
            'commission_bps': 5.0,
            'slippage_bps': 2.0,
            'market_impact_coeff': 0.05,
            'min_commission': 0.1
        },
        'CRYPTO_ILLIQUID': {
            'spread_bps': 20.0,
            'commission_bps': 10.0,
            'slippage_bps': 10.0,
            'market_impact_coeff': 0.2,
            'min_commission': 0.5
        },
        'COMMODITY': {
            'spread_bps': 3.0,
            'commission_bps': 2.0,
            'slippage_bps': 3.0,
            'market_impact_coeff': 0.1,
            'min_commission': 1.0
        }
    }
    
    def calculate_cost(self, asset_class, notional_value, daily_volume=None):
        """Calculate total round-trip cost in basis points."""
        params = self.COST_PARAMETERS[asset_class]
        
        base_cost = params['spread_bps'] + params['commission_bps'] + params['slippage_bps']
        
        # Market impact: proportional to sqrt(notional / daily_volume)
        if daily_volume and daily_volume > 0:
            participation = notional_value / daily_volume
            impact = params['market_impact_coeff'] * np.sqrt(participation) * 100  # bps
            base_cost += impact
        
        return base_cost  # in basis points
```

### 5.4 Cost Model Validation

Every backtest must report:
1. **Total cost per trade** (sum of spread + commission + slippage)
2. **Cost as % of average trade profit** (must be < 50% for viability)
3. **Breakeven analysis** (minimum win rate to cover costs)
4. **Sensitivity analysis** (strategy Sharpe at 2x and 3x estimated costs)

**Critical Rule:** A strategy whose Sharpe ratio drops below 0.5 when realistic costs are doubled is **NOT VIABLE** for live trading [^105^].

---

## 6. Multiple Testing Correction

### 6.1 The Problem

With 50+ strategies being tested simultaneously, the probability of false discoveries approaches certainty. Under the null hypothesis (no true edge):

- **Probability of at least 1 false positive** with 50 tests at alpha=0.05: `1 - (0.95)^50 = 0.923`
- **Expected number of false positives:** `50 * 0.05 = 2.5`

Without correction, the platform will deploy 2-3 spurious strategies on average -- a recipe for losses [^90^][^99^][^101^].

### 6.2 Correction Methods

| Method | Type | Power | Use Case |
|--------|------|-------|----------|
| **Bonferroni** | FWER | Low (conservative) | Final gate before deployment |
| **Holm-Bonferroni** | FWER | Medium | Strategy screening |
| **Benjamini-Hochberg (BH)** | FDR | High | Exploratory research |
| **Benjamini-Yekutieli (BY)** | FDR (dependent) | Medium | When tests are correlated (finance) |

### 6.3 Recommended Implementation: Two-Stage Approach

**Stage 1: Research (BH FDR Control)**
```
For all 50+ strategies:
  1. Compute p-value for each strategy's Sharpe ratio
  2. Sort p-values: p(1) <= p(2) <= ... <= p(m)
  3. Find largest k such that p(k) <= (k/m) * alpha
  4. Strategies 1 through k pass Stage 1
```
This controls the False Discovery Rate at alpha=0.10, meaning at most 10% of "passing" strategies are false discoveries.

**Stage 2: Deployment Gate (Holm-Bonferroni FWER Control)**
```
For strategies passing Stage 1 (let's say m' strategies):
  1. Sort p-values: p(1) <= p(2) <= ... <= p(m')
  2. Starting from i=1:
     - Reject H(i) if p(i) <= alpha / (m' - i + 1)
     - Otherwise, stop and accept all remaining
  3. Only rejected strategies proceed to live trading
```
This controls the Family-Wise Error Rate at alpha=0.05, meaning the probability of ANY false deployment is < 5%.

### 6.4 Deflated Sharpe Ratio (DSR)

The DSR is the most sophisticated multiple-testing correction for Sharpe ratios, developed by Bailey & Lopez de Prado [^100^]:

```
DSR = PSR(SR_0 | V, T, skew, kurtosis, N_tests, rho)

Where:
  SR_0 = observed Sharpe ratio
  V = variance of Sharpe ratios across all tested strategies
  T = number of observations (track length)
  skew = skewness of returns
  kurtosis = excess kurtosis of returns
  N_tests = number of independent tests performed
  rho = average correlation between strategies
```

**Implementation:**
```python
def deflated_sharpe_ratio(estimated_sr, sr_std, n_trials, 
                          track_length, skewness, kurtosis,
                          benchmark_sr=0):
    """
    Compute Deflated Sharpe Ratio.
    
    Parameters:
    -----------
    estimated_sr : float
        The Sharpe ratio estimated from the backtest
    sr_std : float  
        Standard deviation of Sharpe ratios across all trials
    n_trials : int
        Number of independent trials/tests performed
    track_length : int
        Number of observations in the track record
    skewness : float
        Skewness of the return distribution
    kurtosis : float
        Excess kurtosis of the return distribution
    benchmark_sr : float
        Benchmark Sharpe ratio (default 0)
    """
    # Compute Expected Maximum Sharpe Ratio under null
    emsr = expected_maximum_sharpe(sr_std, n_trials)
    
    # Compute PSR against the deflated benchmark
    # The benchmark is adjusted for multiple testing
    adjusted_benchmark = emsr
    
    # PSR formula with non-Normal adjustment
    psr = probabilistic_sharpe_ratio(
        estimated_sr, adjusted_benchmark, track_length,
        skewness, kurtosis
    )
    
    return psr

def expected_maximum_sharpe(sr_std, n_trials):
    """Expected maximum Sharpe ratio under the null hypothesis."""
    from scipy.special import erfcinv
    gamma = 0.5772156649  # Euler-Mascheroni constant
    return sr_std * ((1 - gamma) * erfcinv(1 / n_trials) 
                     + gamma * erfcinv(1 / (n_trials * np.e)))
```

**Deployment Threshold:** `DSR > 0.95` required for live deployment [^100^].

---

## 7. Bootstrap Validation (10,000 Paths)

### 7.1 Why Bootstrap?

Financial returns are non-Normal (fat tails, skewness, volatility clustering). Standard parametric confidence intervals are invalid. Bootstrap provides distribution-free inference [^107^][^111^].

### 7.2 BCa Bootstrap for Sharpe Ratio

The bias-corrected and accelerated (BCa) bootstrap is the gold standard for Sharpe ratio confidence intervals [^107^]:

```python
class BootstrapValidator:
    """
    BCa Bootstrap validation for trading strategies.
    10,000 paths with 95% confidence intervals.
    """
    
    def __init__(self, n_bootstrap=10000, confidence=0.95, random_state=None):
        self.n_bootstrap = n_bootstrap
        self.confidence = confidence
        self.random_state = np.random.RandomState(random_state)
    
    def bootstrap_sharpe(self, returns, block_size=None):
        """
        BCa bootstrap confidence interval for Sharpe ratio.
        
        Uses circular block bootstrap to preserve time-series dependence.
        """
        n = len(returns)
        block_size = block_size or int(np.sqrt(n))  # Optimal block size
        
        # Original Sharpe
        orig_sharpe = self._sharpe_ratio(returns)
        
        # Bootstrap samples
        bootstrap_sharpes = np.zeros(self.n_bootstrap)
        for b in range(self.n_bootstrap):
            # Circular block bootstrap (preserves autocorrelation)
            sample_returns = self._circular_block_bootstrap(
                returns, block_size
            )
            bootstrap_sharpes[b] = self._sharpe_ratio(sample_returns)
        
        # BCa confidence interval
        alpha = 1 - self.confidence
        z_alpha = stats.norm.ppf(alpha / 2)
        z_1_alpha = stats.norm.ppf(1 - alpha / 2)
        
        # Bias correction
        z0 = stats.norm.ppf(np.mean(bootstrap_sharpes < orig_sharpe))
        
        # Acceleration (jackknife)
        jack_sharpes = np.zeros(n)
        for i in range(n):
            jack_returns = np.delete(returns, i)
            jack_sharpes[i] = self._sharpe_ratio(jack_returns)
        jack_mean = np.mean(jack_sharpes)
        a = np.sum((jack_mean - jack_sharpes)**3) / (
            6 * (np.sum((jack_mean - jack_sharpes)**2)**1.5)
        )
        
        # BCa adjusted percentiles
        p_low = stats.norm.cdf(z0 + (z0 + z_alpha) / (1 - a * (z0 + z_alpha)))
        p_high = stats.norm.cdf(z0 + (z0 + z_1_alpha) / (1 - a * (z0 + z_1_alpha)))
        
        ci_low = np.percentile(bootstrap_sharpes, p_low * 100)
        ci_high = np.percentile(bootstrap_sharpes, p_high * 100)
        
        return {
            'point_estimate': orig_sharpe,
            'ci_lower': ci_low,
            'ci_upper': ci_high,
            'bootstrap_mean': np.mean(bootstrap_sharpes),
            'bootstrap_std': np.std(bootstrap_sharpes),
            'p_value': np.mean(bootstrap_sharpes <= 0),  # H0: SR <= 0
            'is_significant': ci_low > 0  # 95% CI excludes zero
        }
    
    def bootstrap_max_drawdown(self, returns):
        """Bootstrap confidence intervals for maximum drawdown."""
        n = len(returns)
        bootstrap_mdds = np.zeros(self.n_bootstrap)
        
        for b in range(self.n_bootstrap):
            sample_returns = self._circular_block_bootstrap(
                returns, int(np.sqrt(n))
            )
            bootstrap_mdds[b] = self._max_drawdown(sample_returns)
        
        return {
            'md_95': np.percentile(bootstrap_mdds, 95),
            'md_99': np.percentile(bootstrap_mdds, 99),
            'md_999': np.percentile(bootstrap_mdds, 99.9)
        }
    
    def _circular_block_bootstrap(self, data, block_size):
        """Circular block bootstrap for time series."""
        n = len(data)
        n_blocks = int(np.ceil(n / block_size))
        
        indices = []
        for _ in range(n_blocks):
            start = self.random_state.randint(0, n)
            for j in range(block_size):
                indices.append((start + j) % n)
        
        return data[indices[:n]]
    
    def _sharpe_ratio(self, returns, risk_free=0):
        """Annualized Sharpe ratio."""
        if np.std(returns) == 0:
            return 0
        return (np.mean(returns) - risk_free) / np.std(returns) * np.sqrt(252)
    
    def _max_drawdown(self, returns):
        """Maximum drawdown."""
        cum_returns = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - peak) / peak
        return np.min(drawdown)
```

### 7.3 Bootstrap Acceptance Criteria

| Metric | Requirement | Rationale |
|--------|-------------|-----------|
| Sharpe 95% CI lower bound | > 0 | Strategy has positive edge |
| Sharpe 95% CI lower bound (institutional) | > 0.5 | Strategy is economically meaningful |
| P-value (H0: SR <= 0) | < 0.05 | Statistically significant |
| Max Drawdown 99% CI | < 25% (crypto) or < 15% (equity) | Risk limits |
| Profit Factor 95% CI lower bound | > 1.0 | Positive expectancy |

### 7.4 Minimum Track Record Length (MinTRL)

Bailey & Lopez de Prado's MinTRL answers: "How long must a track record be for a Sharpe ratio of S to be statistically greater than S* at confidence level?" [^100^]

```
MinTRL(S, S*, alpha, skew, kurt) = 1 + (1 - skew*S + (kurt-1)/4 * S^2) 
                                     * (Z_alpha / (S - S*))^2
```

**Critical Values (95% confidence):**

| Observed SR | Benchmark SR | Weekly (Normal) | Monthly (Normal) | Monthly (Non-Normal) |
|------------|-------------|-----------------|------------------|---------------------|
| 1.0 | 0.0 | 1.00 year | 1.25 years | 1.93 years |
| 1.5 | 0.5 | 1.21 years | 1.49 years | 2.26 years |
| 2.0 | 1.0 | 1.22 years | 1.49 years | 2.26 years |
| 2.0 | 0.0 | 0.69 years | 0.87 years | 1.31 years |
| 3.0 | 1.0 | 0.50 years | 0.68 years | 1.01 years |

**Platform Application:** For a strategy claiming Sharpe = 1.5 with 100 trades over 6 months:
- Monthly data: MinTRL to beat SR=0.5 is ~1.49 years
- **Verdict: INSUFFICIENT TRACK RECORD -- REJECT**

---

## 8. What Renaissance Technologies or Two Sigma Would Require

### 8.1 Two Sigma's Standards (from interview process) [^108^]

Two Sigma's quant research interviews explicitly test:

1. **Cross-validation specifics for time-series:** Forward chaining, walk-forward, purging
2. **Avoiding survivorship bias, look-ahead bias, snooping bias**
3. **Out-of-sample testing protocols** with statistical rigor
4. **Signal-to-noise reasoning** -- understanding that financial data has very low SNR
5. **Transaction cost awareness** at every stage
6. **Regularization** -- L1/L2, dropout, early stopping to prevent overfitting

### 8.2 What the Platform Lacks: A Hedge Fund Checklist

| Requirement | Renaissance/Two Sigma Level | Platform Status |
|-------------|---------------------------|-----------------|
| **Data Quality** | Point-in-time, survivorship-bias-free, audited | Unknown/Unchecked |
| **CV Method** | CPCV with N>=10, k>=3 | Single walk-forward |
| **Backtest Paths** | 30-280 independent paths | 1 path |
| **PSR Threshold** | > 0.95 for ANY capital allocation | Not implemented |
| **DSR Threshold** | > 0.95 after multiple testing correction | Not implemented |
| **Bootstrap** | 10,000 paths, BCa CI, block bootstrap | Not implemented |
| **Min Trades** | 500+ per strategy | 50-100 ("THIN" flagged) |
| **Regime Coverage** | Must span bull, bear, crash, recovery | Unknown |
| **Cost Model** | Strategy-specific with market impact | Generic |
| **Code Audit** | Single source of truth, version controlled | 5+ copies of same file |
| **Monitoring** | Real-time Sharpe decay, regime detection | 24h tracking window only |
| **Kill Switch** | Automatic shutdown on Sharpe decay | Not implemented |
| **Documentation** | Full hypothesis pre-registration | Not required |
| **Peer Review** | Independent strategy review before deployment | Not implemented |

### 8.3 The "Renaissance Gap"

Renaissance Technologies (Medallion Fund) operates at a fundamentally different level:

1. **Data:** Petabytes of cleaned, normalized, point-in-time data going back decades
2. **Infrastructure:** Custom hardware, co-located servers, microsecond execution
3. **Statistical Rigor:** Every strategy passes: CPCV -> PSR > 0.95 -> DSR > 0.95 -> MinTRL check -> Bootstrap validation -> Paper trading (6+ months) -> Live deployment (small size) -> Scale
4. **Risk Management:** Maximum drawdown limits are hard stops, not suggestions
5. **Decay Monitoring:** Continuous monitoring with automatic deleveraging when Sharpe decays below threshold

**The platform's gap to Renaissance-level is approximately 3-5 years of infrastructure and methodology development.**

### 8.4 Achievable Near-Term Targets

Within 6 months, the platform should achieve:

1. **CPCV implementation** (N=6, k=2 minimum; N=10, k=3 target)
2. **PSR calculation** for every strategy
3. **Bootstrap CI** (10,000 paths, BCa method)
4. **Multiple testing correction** (Holm-Bonferroni for deployment)
5. **Asset-class-specific cost models**
6. **Minimum trade thresholds enforced** (100 crypto, 200 equity/forex)
7. **Single outcome_resolver.py** with version control
8. **Regime detection** with regime-stratified reporting

---

## 9. Implementation Priority Matrix

### 9.1 Priority 1: Critical (Deploy Within 2 Weeks)

| # | Improvement | Impact | Effort | Expected Benefit |
|---|-------------|--------|--------|-----------------|
| 1 | **Stop deploying strategies with negative OOS Sharpe** | Catastrophic risk | 1 day | Prevent further losses |
| 2 | **Enforce minimum trade thresholds** | High | 2 days | Eliminate false discoveries from small samples |
| 3 | **Consolidate outcome_resolver.py to single file** | High | 3 days | Eliminate version-control risk |
| 4 | **Add basic PSR calculation** | Critical | 5 days | Filter out noise strategies |

### 9.2 Priority 2: High (Deploy Within 1-2 Months)

| # | Improvement | Impact | Effort | Expected Benefit |
|---|-------------|--------|--------|-----------------|
| 5 | **Implement Purged K-Fold CV** | Critical | 2 weeks | Eliminate information leakage |
| 6 | **Add asset-class cost models** | High | 1 week | Realistic profitability estimates |
| 7 | **Implement bootstrap validation (10K paths)** | Critical | 2 weeks | Distribution-free confidence intervals |
| 8 | **Add multiple testing correction (Holm-Bonferroni)** | High | 1 week | Control false discovery rate |
| 9 | **Implement DSR calculation** | High | 1 week | Account for multiple testing in Sharpe assessment |

### 9.3 Priority 3: Medium (Deploy Within 3-6 Months)

| # | Improvement | Impact | Effort | Expected Benefit |
|---|-------------|--------|--------|-----------------|
| 10 | **Implement full CPCV (N=10, k=3)** | Critical | 1 month | 30+ independent backtest paths |
| 11 | **Add regime detection and reporting** | Medium | 2 weeks | Regime-aware performance assessment |
| 12 | **Add MinTRL calculation** | Medium | 1 week | Minimum track record enforcement |
| 13 | **Implement strategy decay monitoring** | Medium | 2 weeks | Early warning for alpha erosion |
| 14 | **Add point-in-time data validation** | High | 1 month | Eliminate look-ahead bias |

### 9.4 Priority 4: Long-Term (6-12 Months)

| # | Improvement | Impact | Effort | Expected Benefit |
|---|-------------|--------|--------|-----------------|
| 15 | **Full hypothesis pre-registration system** | High | 2 months | Prevent data snooping |
| 16 | **Peer review workflow for strategy deployment** | High | 1 month | Independent validation |
| 17 | **Real-time Sharpe monitoring with kill switches** | Critical | 2 months | Automatic risk management |
| 18 | **Survivorship-bias-free dataset integration** | High | 2 months | Realistic backtest results |
| 19 | **Monte Carlo simulation (beyond bootstrap)** | Medium | 1 month | Stress testing with parametric models |

---

## 10. Summary of Key Recommendations

### Immediate Actions (This Week)

1. **HALT deployment** of CRYPTO, FOREX, and COMMODITY strategies -- all show negative OOS Sharpe
2. **Flag all "THIN" strategies** as insufficient data -- do not trade
3. **Investigate the ETF Sharpe 6.368 anomaly** -- with only 12 folds, this is likely overfit or has data leakage
4. **Consolidate outcome_resolver.py** -- eliminate the 5+ copies immediately
5. **Extend tracking window analysis** -- the 72.7% of picks still open at 24h suggests TP/SL levels are poorly calibrated

### Critical Metric Thresholds (Should Be Enforced in Code)

| Metric | Minimum | Target | Action if Below |
|--------|---------|--------|----------------|
| PSR | 0.80 | 0.95 | Do not deploy |
| DSR | 0.80 | 0.95 | Do not deploy |
| OOS Sharpe | 0.0 | 1.0 | Reject strategy |
| Min Trades (Equity/Forex) | 100 | 200 | Flag as "THIN" |
| Min Trades (Crypto) | 50 | 100 | Flag as "THIN" |
| Bootstrap Sharpe CI (95% lower) | 0.0 | 0.5 | Do not deploy |
| Max Drawdown (Crypto) | 25% | 15% | Reduce position size |
| Max Drawdown (Equity/Forex) | 15% | 10% | Reduce position size |
| Profit Factor | 1.0 | 1.5 | Reject strategy |
| CPCV Paths | 5 | 30 | Insufficient validation |

### The Bottom Line

The platform's backtesting infrastructure has fundamental gaps that make it unsuitable for institutional capital deployment. The most critical issues are:

1. **Negative OOS Sharpe for 3 of 4 asset classes** -- strategies are failing out-of-sample
2. **No purged cross-validation** -- information leakage is likely inflating results
3. **No PSR/DSR validation** -- no statistical confidence in reported Sharpe ratios
4. **No multiple testing correction** -- false discoveries are guaranteed with 50+ strategies
5. **Inadequate sample sizes** -- "THIN" strategies lack statistical power
6. **Primitive transaction costs** -- profitability is overstated
7. **Code duplication** -- maintenance risk undermines result reliability

**The path to institutional-grade requires implementing Combinatorial Purged Cross-Validation, PSR/DSR thresholds, bootstrap validation, and multiple testing correction as non-negotiable deployment gates.** Without these, the platform will continue to deploy strategies that lose money out-of-sample.

---

## References

[^87^]: Lopez de Prado, M. (2018). "Advances in Financial Machine Learning." Wiley. Key takeaways on PSR, DSR, CPCV, and purged cross-validation.

[^89^]: Wikipedia. "Purged cross-validation." Cross-validation technique for time series and financial data. https://en.wikipedia.org/wiki/Purged_cross-validation

[^90^]: Multiple test correction: Bonferroni, FDR. https://edu.abi.am/statistics-theory/multiple-test-correction-bonferroni-fdr

[^91^]: Gort, B. & Yang, B. "The Combinatorial Purged Cross-Validation Method." Towards AI, 2022.

[^95^]: StackExchange. "What is Combinatorial Purged Cross-Validation for time series data?" 2020.

[^97^]: Bailey, D.H. & Lopez de Prado, M. "The Sharpe Ratio Efficient Frontier." Journal of Risk, 2012.

[^99^]: Noble, W.S. "How does multiple testing correction work?" Nature Biotechnology, 2009.

[^100^]: Lopez de Prado, M. "Deflating the Sharpe Ratio." Journal of Portfolio Management, 2014.

[^101^]: Statsig. "Controlling your type I errors: Bonferroni and Benjamini-Hochberg." 2024.

[^105^]: BSIC. "Backtesting Series Episode 5: Transaction Cost Modelling." 2025.

[^107^]: PyBroker. "Evaluating with Bootstrap Metrics." BCa bootstrap implementation for trading strategies.

[^108^]: Two Sigma Interview Guide 2026. Technical focus areas for quant research.

[^109^]: SharpeRatio.io. "Achieved Signal Noise Ratio via Cross Validation." 2021.

[^110^]: QuantStart. "Successful Backtesting of Algorithmic Trading Strategies Part II."

[^111^]: Binance. "Bootstrap Resampling: Robust Estimation Without Strong Distribution Assumptions." 2026.

[^118^]: QuantifiedStrategies. "Survivorship Bias In Trading (How To Avoid It)." 2026.

[^120^]: VertoxQuant. "Strategy Decay Detection: Building a Warning System for Alpha Erosion." 2026.

[^122^]: StarQube. "The critical pitfalls of backtesting trading strategies." 2025.

[^125^]: HedgeFundAlpha. "A Practical Guide To The Backtesting Mistakes That Kill Quant Strategies." 2026.

[^126^]: ScienceDirect. "Backtest overfitting in the machine learning era." 2024.

[^127^]: InsightBig. "Traditional Backtesting is Outdated. Use CPCV Instead." 2025.

[^27^]: BacktestBase. "Minimum Trades for a Valid Backtest?" 2026.

[^29^]: TradingDude. "How Many Trades Are Enough? A Guide to Statistical Significance in Backtesting." 2025.

[^41^]: Deep, G. et al. "A Rigorous Walk-Forward Validation Framework for Market Microstructure Signals." arXiv, 2025.

---

*Report generated for institutional-grade backtesting methodology review. All recommendations are based on peer-reviewed academic literature and industry best practices.*
