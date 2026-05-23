# Researcher Profile: Dr. Michael Zhang

## Persona
- **Title:** Alpha Research and Strategy Lifecycle Manager
- **Expertise:** Alpha decay modeling, strategy rotation, factor timing, signal half-life estimation
- **Years Experience:** 12
- **Background:** PhD Stanford Finance, former researcher at AQR, now leads alpha research at a crypto quant fund.

## Research Scope
**Primary Question:** How do top funds detect and manage alpha decay in crypto ML strategies, and how do they rotate to new signals?

**Target Systems/Areas:**
- Alpha decay curves (half-life of predictive power)
- Regime detection (bull/bear/neutral) for strategy selection
- Dynamic factor weighting
- Strategy diversification and correlation management
- Continuous retraining and feature refresh
- CUSUM/PELT integration with strategy rotation

---

## STATUS: COMPLETE

---

## Section 1: Alpha Decay Fundamentals

### 1.1 What Is Alpha Decay?

Alpha decay is the loss in predictive power of an alpha model over time. It represents a structural feature of modern markets -- not a bug but an inevitable consequence of information diffusion, crowding, and competition. Every trading signal has a "shelf life" called its **Information Half-Life**: the time it takes for a signal's predictive power to decay by 50%.

**Quantified Annual Costs (Di Mascio, Lines & Naik, Columbia/Inalytics):**
- US markets: 5.6% annualized return loss from alpha decay
- European markets: 9.9% annualized return loss from alpha decay
- Rate of increase: US +36 bps/year, Europe +16 bps/year
- Average peak-to-trough decay across managers: ~400 basis points

**Key insight:** Alpha decay is accelerating. Every year, the Sharpe decay of newly-published factors increases by approximately 5 percentage points (Falck, Rej & Thesmar, Quantitative Finance 2022).

### 1.2 Why Does Backtested Performance Not Persist?

Published anomalies evaluated out-of-sample deliver approximately **50% of in-sample performance** (Falck et al. 2022). The backtest-to-live gap is driven by:

| Factor | Impact | Explanation |
|--------|--------|-------------|
| **Overfitting** | 30-50% of apparent alpha | Strategies tuned to historical noise; R-squared of overfitting vulnerability = 0.30 |
| **Transaction costs** | Can eliminate >50% of gross returns | Monthly-decay signals lose >50% to costs; high-frequency signals even more |
| **Slippage & latency** | 5-20% of gross returns | Backtests assume perfect execution; reality has queue priority, partial fills |
| **Crowding** | Accelerates decay 2-5x | Popular signals get arbitraged faster; first movers capture most profit |
| **Look-ahead bias** | Inflates backtests 10-40% | Subtle data leakage (survivorship, point-in-time violations) |
| **Regime change** | Structural breaks invalidate assumptions | Strategy assumptions (e.g., mean-reversion) may not hold in new regime |

**The 95% rule:** Industry consensus estimates that ~95% of backtested strategies fail in live trading. This is primarily due to overfitting and the multiple-testing problem (testing hundreds of parameter combinations and selecting the best).

### 1.3 The Self-Fulfilling Prophecy Paradox

Technical analysis indicators (RSI, MACD, Bollinger Bands, Fibonacci levels) exhibit a unique decay pattern:

1. **Phase 1 -- Signal Discovery:** A small group finds edge in a pattern. Works well because few participants.
2. **Phase 2 -- Self-Fulfilling Amplification:** Signal becomes popular. Traders act on it simultaneously, temporarily increasing its apparent accuracy (e.g., support/resistance levels hold because everyone buys there).
3. **Phase 3 -- Crowding Decay:** Too many participants. Early movers capture profit, late arrivals get slippage. Smart money begins fading the crowd signal.
4. **Phase 4 -- Signal Inversion:** Extremely popular signals can actually reverse -- becoming contrarian indicators against the crowd.

**Most susceptible to self-fulfilling/crowding decay:**
- Pivot points, round numbers, widely-followed moving averages (200 DMA)
- RSI overbought/oversold at standard thresholds (30/70)
- Bollinger Band mean reversion at 2-sigma
- Fibonacci retracement levels (38.2%, 61.8%)

**Most resistant:**
- Obscure oscillators and proprietary indicators (low adoption)
- Multi-factor composites that are hard to reverse-engineer
- On-chain metrics (require blockchain-specific infrastructure)
- Cross-asset signals (fewer participants trade cross-market)

---

## Section 2: Decay Rates by Signal Type

### 2.1 Comprehensive Decay Rate Table

| Signal Category | Half-Life | Optimal Hold | Annual Decay | Crowding Risk | Notes |
|----------------|-----------|-------------|--------------|---------------|-------|
| **HFT microstructure** | <0.02 seconds | Milliseconds | N/A | Extreme | Requires co-location; not relevant to our system |
| **Intraday momentum** | 30 min - 4 hours | 1-4 hours | 80-95% | Very High | Peak alpha ~4 hours post-signal (Best 2023) |
| **Technical indicators (RSI/MACD)** | 2-8 weeks | 1-5 days | 60-80% | High | Standard parameters most crowded |
| **Momentum factor** | 3-6 months | 3-10 months | 40-60% | High | Turns negative after ~11 months; 426% turnover |
| **Mean reversion (swing)** | 3-10 days | 1-5 days | 50-70% | Medium-High | 60% initial deterioration in stable equities |
| **Social sentiment** | 1-2 months | Hours to days | 70-90% | High | Twitter/Reddit signals decay within hours-days |
| **Funding rate carry** | 1-4 weeks | Days to weeks | 50-70% | Medium | Extreme rates are contrarian; normal rates crowd fast |
| **On-chain metrics (MVRV/NVT)** | 6-12 months | Weeks to months | 20-40% | Low | Requires infrastructure; fewer participants |
| **Value factor** | 24-36+ months | Months to years | 10-20% | Low | Longest half-life of all pure factors |
| **Quality factor** | 25.9 months (median) | 4-5 months optimal rebalance | 15-25% | Low | Second longest half-life |
| **Macro/liquidity signals** | 3-12 months | Weeks to months | 20-40% | Low | Hayes liquidity index, Fed balance sheet |
| **Event-driven (token unlocks)** | 1-7 days | Hours to 2 days | 80-95% | Medium | Front-running erodes edge quickly |
| **Whale accumulation** | 2-6 weeks | Days to weeks | 40-60% | Medium | Partially observable; harder to crowd |
| **Cross-sectional momentum** | 1-4 weeks | 7-14 days | 50-70% | Medium | Rebalance weekly for crypto (Liu et al. 2022) |

### 2.2 Crypto-Specific Decay: The 24/7 Factor

Cryptocurrency markets operate 24/7/365, which fundamentally changes signal dynamics:

1. **No overnight gap:** Signals cannot "rest" -- decay is continuous. A signal generating alpha at 2 AM UTC is immediately arbitraged by Asian/European traders.
2. **Weekend liquidity drain:** While crypto trades on weekends, liquidity drops 40-60%, causing false signals from thin orderbooks. Signals generated on weekends have lower persistence.
3. **Compressed timelines:** What takes weeks to decay in equities may take days in crypto. The 24/7 nature effectively compresses half-lives by an estimated 2-3x.
4. **Funding rate cycles:** 8-hour funding rate resets (Binance) create micro-cycles that do not exist in traditional markets. Carry signals must account for these resets.
5. **Bot density:** An estimated 60-80% of crypto volume is algorithmic, meaning crowding happens faster than in traditional markets where human decision-making introduces latency.
6. **Information propagation:** Crypto-native information (whale alerts, on-chain data) propagates via Telegram/Twitter in minutes, not hours. Social signal half-life may be as short as 15-60 minutes.

**Practical implication for our system:** Crypto signals should be revalidated at 2-3x the frequency of equivalent equity signals. A strategy retrained monthly in equities needs biweekly or weekly retraining in crypto.

---

## Section 3: Alpha Decay Measurement Methods

### 3.1 CUSUM / PELT Change-Point Detection

**Our current implementation** (`scripts/cusum_detector.py`) uses PELT with RBF kernel from the `ruptures` library. This is scientifically sound -- PELT (Pruned Exact Linear Time) is the gold standard for offline change-point detection (Killick et al. 2012).

**Current classification thresholds:**
| Status | Sharpe | Win Rate | Weight |
|--------|--------|----------|--------|
| Strong | >1.5 | >55% | 1.0-1.5 |
| Healthy | >0.5 | >45% | 1.0 |
| Warning | >0 | Mean>0 | 0.6 |
| Decayed | >-0.5 | Any | 0.3 |
| Dead | <-0.5 | Any | 0.0 |

**What is missing from our CUSUM implementation:**

1. **No automated action:** Detector classifies but does not trigger retraining, weight reduction, or strategy rotation. Results are posted to API but nothing consumes them for allocation decisions.
2. **No online detection:** PELT is an offline algorithm -- it re-analyzes the entire series. For real-time detection, we need online CUSUM or FOCuS (Functional Online CuSUM) which runs in O(log n) per iteration.
3. **Static hyperparameters:** Penalty = 1.5 and min_size = 8 are hardcoded. Research shows CUSUM effectiveness depends heavily on hyperparameter tuning, and a single setup may not be universally suitable. Meta-learning approaches can optimize these dynamically.
4. **No concept drift detection:** CUSUM detects level shifts in PnL but not gradual drift in feature distributions. Need complementary drift detectors (ADWIN, DDM, EDDM).
5. **No false positive control:** Current system may flag normal drawdowns as decay. Need a Bayesian layer or minimum evidence threshold (e.g., 20+ trades in deteriorated segment).

### 3.2 Rolling Sharpe Ratio

The most widely used decay monitoring tool in institutional quant trading. Calculate on a rolling window (typically 60-90 trading periods for crypto):

```
Rolling_Sharpe(t) = mean(returns[t-W:t]) / std(returns[t-W:t]) * sqrt(annualization_factor)
```

**Thresholds for action (recommended):**
| Rolling Sharpe | Action |
|----------------|--------|
| > 1.5 | Increase allocation (strategy is hot) |
| 0.5 - 1.5 | Normal allocation |
| 0.0 - 0.5 | Yellow alert: reduce to 60% allocation |
| -0.5 - 0.0 | Red alert: reduce to 25% allocation |
| < -0.5 for 30+ periods | Pause strategy; investigate |

**Key insight from Robot Wealth:** "The right question is not 'Has my edge stopped working?' but 'Given recent evidence, how much do I trust it now?' The answer is always probabilistic, never definitive." Tests that need thousands of data points to reject the null at 95% confidence will never detect regime shifts in real time.

### 3.3 Information Coefficient (IC) Decay

Track the rank correlation between signal predictions and subsequent returns over a rolling window:

```
IC(t) = spearman_correlation(signal[t], forward_returns[t+h])
```

**Thresholds:**
- IC > 0.05: Signal has meaningful predictive power
- IC 0.02-0.05: Weak but potentially usable in ensemble
- IC < 0.02 for 60 days: Retire signal/feature (from Two Sigma research)

### 3.4 Signal Half-Life Estimation

Model signal autocorrelation as AR(1) process:

```python
# AR(1) model: signal[t] = phi * signal[t-1] + epsilon
# Half-life = -ln(2) / ln(phi)
import numpy as np
from statsmodels.tsa.ar_model import AutoReg

def estimate_half_life(signal_series):
    """Estimate signal half-life using AR(1) coefficient."""
    model = AutoReg(signal_series, lags=1).fit()
    phi = model.params[1]  # AR(1) coefficient
    if phi <= 0 or phi >= 1:
        return float('inf')  # Non-stationary or negative correlation
    half_life = -np.log(2) / np.log(phi)
    return half_life  # In units of observation frequency
```

**Critical rule:** Your forecast horizon must roughly equal the persistence of your inputs. If inputs have a half-life of minutes, you must be a scalper. If inputs have a half-life of months, you must be a position trader. A mismatch guarantees failure.

### 3.5 Concept Drift Detection

Complementary to CUSUM, these detect gradual distribution shifts:

| Method | Type | Best For | Speed |
|--------|------|----------|-------|
| **ADWIN** (Adaptive Windowing) | Online | Gradual + sudden drift | Fast |
| **DDM** (Drift Detection Method) | Online | Sudden drift | Very fast |
| **EDDM** (Early Drift Detection) | Online | Gradual drift | Fast |
| **ADDM** (Autoregressive Drift Detection) | Online | Regime shifts | Medium |
| **KS Test** (Kolmogorov-Smirnov) | Batch | Distribution shifts | Slow |
| **Wasserstein Distance** | Batch | Magnitude of shift | Medium |
| **PSI** (Population Stability Index) | Batch | Feature drift | Fast |

**Recommended for our system:** ADWIN for online monitoring (catches both gradual and sudden drift) plus PSI for feature-level drift detection on model inputs.

### 3.6 Turnover-Adjusted Alpha Decay

Raw alpha decay understates true decay because it ignores transaction costs. For a signal with monthly turnover:

```
Net_Alpha = Gross_Alpha - (Turnover * Cost_Per_Trade)
```

**Empirical finding:** For monthly-decay signals, realistic transaction costs can reduce gross performance by more than 50% (QuantStart). This means a signal with apparent 2% monthly alpha and 200% annual turnover at 0.1% cost per trade loses 0.2% per month to costs alone -- making the true net alpha 1.8% at best, decaying to zero faster than gross metrics suggest.

**For crypto specifically:**
- Spot trading costs: 0.04-0.10% per trade (maker/taker on major exchanges)
- Perp funding: -0.01% to +0.03% per 8-hour period
- Slippage on $10K+ orders: 0.05-0.50% depending on pair liquidity
- Total round-trip cost estimate: 0.15-0.40% for liquid pairs, 0.50-2.0% for small caps

---

## Section 4: Signals Most Resistant to Crowding/Decay

### 4.1 Decay Resistance Ranking

**Tier 1 -- Most Resistant (half-life > 6 months):**
1. **On-chain fundamental metrics (MVRV, NVT, SOPR):** Require blockchain infrastructure, data pipeline expertise, and domain knowledge. Low adoption among retail. Half-life 6-12 months.
2. **Macro liquidity signals (Hayes index, Fed balance sheet):** Driven by central bank policy, not market participants. Cannot be arbitraged away. Half-life 3-12 months.
3. **Value factor (traditional):** Longest empirical half-life at 24-36+ months (Alpha Architect). Slow because value requires patience.
4. **Quality factor:** Median half-life 25.9 months. Persistent because quality companies structurally outperform.

**Tier 2 -- Moderately Resistant (half-life 1-6 months):**
5. **Cross-asset signals:** Trading crypto based on equity VIX, DXY, yield curves. Fewer participants bridge markets. Half-life 3-6 months.
6. **Whale accumulation patterns:** Partially observable but require sophisticated tracking. Half-life 2-6 months.
7. **Funding rate extremes (contrarian):** Extreme readings are inherently self-correcting. Half-life 1-4 weeks for the extreme signal itself.
8. **Multi-factor composites:** Harder to reverse-engineer than single indicators. Half-life 2-4 months.

**Tier 3 -- Moderate Decay (half-life 2-8 weeks):**
9. **Cross-sectional momentum (top-N rotation):** Effective in crypto due to dispersion (Liu et al. 2022, Sharpe ~2.1). Requires weekly rebalancing.
10. **Volatility regime strategies:** ATR breakouts, Keltner channels. Edge persists in regime transitions.

**Tier 4 -- Fast Decay (half-life < 2 weeks):**
11. **Standard RSI/MACD at default parameters:** Heavily crowded. Only edge comes from non-standard parameters or conditional filtering.
12. **Social sentiment (Twitter/Reddit):** Half-life measured in hours. By the time you trade, the edge is gone.
13. **Event-driven (token unlocks, listings):** Front-run within hours of announcement.

### 4.2 What Makes a Signal Decay-Resistant?

| Property | Decay Resistance | Why |
|----------|-----------------|-----|
| **High infrastructure cost** | Very High | Barriers to entry limit crowding (on-chain analytics, alternative data) |
| **Long feedback loop** | High | Macro signals take months to play out; hard to arb quickly |
| **Multi-dimensional** | High | Composite signals harder to replicate than single indicators |
| **Non-stationary adaptation** | High | Signals that self-adjust (online learning) maintain relevance |
| **Low turnover** | Medium | Fewer transactions = lower cost drag on alpha |
| **Contrarian** | Medium | Fading crowd behavior has structural edge as crowds grow |
| **Simple, well-known** | Very Low | RSI(14) at 30/70 is the most crowded signal in existence |

---

## Section 5: Online Learning to Combat Decay

### 5.1 The Case for Online Learning

Traditional batch retraining (retrain monthly on all historical data) has critical weaknesses:
- Model uses stale parameters for up to 30 days between retrains
- Equal weight to old and new data; cannot adapt to regime changes
- Computational cost grows linearly with data history

Online learning updates the model incrementally as each new data point arrives, balancing **stability** (preserving past knowledge) with **plasticity** (adapting to new patterns).

### 5.2 Practical Online Learning Approaches

**Approach 1: Sliding Window Retraining**
- Retrain on most recent N observations only (e.g., last 90 days)
- Drop oldest data as new data arrives
- Simple to implement; works well for gradual drift
- **Recommended window for crypto:** 60-120 days (shorter than equity due to 24/7 compression)

**Approach 2: Exponential Decay Weighting**
- Weight recent observations more heavily: w(t) = exp(-lambda * age)
- Lambda controls forgetting rate; tune via cross-validation
- Better than sliding window for gradual regime changes
- **Implementation:** Use `sample_weight` parameter in scikit-learn estimators

**Approach 3: Online Gradient Descent (SGD)**
- Update model weights with each new batch of trades
- Learning rate controls adaptation speed
- Risk of catastrophic forgetting if learning rate too high
- **Best for:** Neural network / deep learning models

**Approach 4: Ensemble with Drift Detection**
- Maintain ensemble of models trained on different windows
- Use ADWIN or CUSUM to detect drift
- When drift detected: increase weight of recently-trained models, decrease weight of old models
- **This is the recommended approach for our system**

**Approach 5: Bayesian Online Changepoint Detection (BOCPD)**
- Adams & MacKay (2007) algorithm
- Maintains probability distribution over possible run lengths
- Naturally handles both gradual and sudden regime changes
- More principled than CUSUM but computationally heavier

### 5.3 Recommended Architecture for Our System

```
                    +------------------+
                    | CUSUM Detector   |  (already built)
                    | (cusum_detector) |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    | Decay Router     |  (NEW - needed)
                    | - Read CUSUM     |
                    | - Read Rolling   |
                    |   Sharpe         |
                    | - Read IC        |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
        +-----------+  +-----------+  +-----------+
        | STRONG    |  | WARNING   |  | DECAYED   |
        | Keep full |  | Reduce wt |  | Pause +   |
        | allocation|  | to 60%    |  | retrain   |
        | Monitor   |  | Retrain   |  | or rotate |
        +-----------+  | weekly    |  | out       |
                       +-----------+  +-----------+
```

---

## Section 6: Strategy Rotation Framework

### 6.1 The Alpha Life Cycle (IEEE 2018)

Every strategy follows a lifecycle:

```
Discovery --> Development --> Deployment --> Peak Alpha --> Decay --> Death
   |              |              |              |           |         |
   6-12 mo        3-6 mo         Varies         1-6 mo     2-12 mo   Retire
```

**Key finding:** The lifecycle is compressing. What once took years from discovery to death now takes months. In crypto, the full cycle can complete in weeks for simple signals.

### 6.2 Practical Rotation Protocol

**Step 1: Continuous Monitoring (Daily)**
```python
for strategy in active_strategies:
    rolling_sharpe = compute_rolling_sharpe(strategy, window=60)
    ic = compute_rolling_ic(strategy, window=30)
    cusum_status = cusum_detector.classify(strategy)

    strategy.health_score = weighted_average(
        rolling_sharpe_percentile * 0.4,
        ic_percentile * 0.3,
        cusum_weight * 0.3
    )
```

**Step 2: Tiered Response**

| Health Score | Action | Timeline |
|-------------|--------|----------|
| 80-100 | Increase allocation up to 1.5x | Immediate |
| 60-80 | Normal allocation (1.0x) | Maintain |
| 40-60 | Reduce to 0.6x; begin retraining | Within 1 week |
| 20-40 | Reduce to 0.3x; retrain with recent data only | Within 3 days |
| 0-20 | Pause strategy; rotate in challenger | Immediate |

**Step 3: Challenger Pool Management**

Maintain a pool of 5-10 "challenger" strategies that are paper-traded but not yet allocated real capital:
- Challengers are evaluated on rolling 30-day paper performance
- When a live strategy drops to "decayed" (0-20 health), the top challenger is promoted
- Promoted challenger starts at 0.3x allocation, graduating to 1.0x over 2 weeks if healthy
- Demoted strategy moves to observation for 60 days before permanent retirement

**Step 4: Quarterly Feature Refresh**
- Every 90 days, evaluate all features/inputs for IC decay
- Any feature with IC < 0.02 for 60+ consecutive days is replaced
- Source new features from on-chain data, alternative data, or academic research
- Retrain all models with refreshed feature set

### 6.3 Correlation-Aware Rotation

Do not just rotate based on individual performance -- maintain portfolio-level diversification:

```python
def select_strategies(candidates, n_select=5, max_correlation=0.6):
    """Select top-N strategies with correlation constraint."""
    selected = [candidates[0]]  # Best performer first

    for candidate in candidates[1:]:
        if len(selected) >= n_select:
            break
        # Check correlation with all selected strategies
        max_corr = max(
            abs(correlation(candidate.returns, s.returns))
            for s in selected
        )
        if max_corr < max_correlation:
            selected.append(candidate)

    return selected
```

**Target portfolio:** 3-5 uncorrelated strategies with average pairwise correlation < 0.3. Rotate monthly.

### 6.4 Regime-Adaptive Allocation

Use a regime detector (HMM or simpler) to shift weights:

| Regime | Detection | Momentum Weight | Mean-Reversion Weight | Carry Weight | Cash/Hedge |
|--------|-----------|-----------------|----------------------|--------------|------------|
| **Trending Bull** | BTC > 200d SMA, rising | 60% | 10% | 20% | 10% |
| **Trending Bear** | BTC < 200d SMA, falling | 10% (short) | 20% | 10% | 60% |
| **Mean-Reverting** | Low ADX, range-bound | 15% | 55% | 20% | 10% |
| **High Volatility** | VIX/DVOL > 80th %ile | 10% | 10% | 10% | 70% |
| **Capitulation** | F&G < 15, VIX spike | 20% (contrarian) | 30% | 10% | 40% |

**Performance improvement:** Regime-adaptive allocation improves Sharpe by 0.5-1.0 over static allocation (multiple academic studies).

---

## Section 7: Actionable Recommendations for Our System

### 7.1 Immediate Actions (This Week)

- [x] CUSUM detector exists and classifies strategy health
- [ ] **Wire CUSUM output to allocation engine:** The `recommended_weight` field from `classify_decay()` must actually be consumed by the strategy runner to adjust position sizing
- [ ] **Add Rolling Sharpe monitoring:** Compute 60-period rolling Sharpe for each strategy alongside CUSUM. Two independent decay signals are better than one
- [ ] **Set up paper-trade challenger pool:** Maintain 5+ strategies in paper-trade mode, ready to promote when live strategies decay

### 7.2 Short-Term (Next 2 Weeks)

- [ ] **Implement online CUSUM:** Replace offline PELT with FOCuS (Functional Online CuSUM) for real-time detection with O(log n) per iteration
- [ ] **Add ADWIN drift detector:** Complement CUSUM (detects level shifts) with ADWIN (detects gradual distribution drift). Library: `river` Python package
- [ ] **Feature IC tracking:** Compute rolling 30-day IC for each feature/signal. Auto-flag features below IC 0.02 threshold
- [ ] **Signal half-life estimation:** Implement AR(1) half-life estimator for each strategy's signal; alert when half-life drops below hold period

### 7.3 Medium-Term (Next Month)

- [ ] **Sliding window retraining:** Switch from "train once on all history" to sliding 90-day window for crypto ML models
- [ ] **Exponential decay weighting:** For models that support sample weights, weight recent observations exponentially higher
- [ ] **Correlation-aware portfolio construction:** Ensure active strategies maintain average pairwise correlation < 0.3
- [ ] **Regime classifier:** Implement simple regime detection (BTC vs 200d SMA + ADX + VIX equivalent) and adjust strategy weights accordingly

### 7.4 Long-Term (Next Quarter)

- [ ] **Full strategy lifecycle management:** Track each strategy from discovery through death with automated promotion/demotion
- [ ] **Bayesian Online Changepoint Detection:** Upgrade from CUSUM to BOCPD for more principled regime detection
- [ ] **Automated feature refresh pipeline:** Quarterly scan for new features; auto-retire features with sustained low IC
- [ ] **Meta-learning for CUSUM hyperparameters:** Auto-tune penalty and min_size parameters based on strategy characteristics

### 7.5 Specific Improvements to `cusum_detector.py`

**Current gaps and fixes:**

1. **Gap: No action taken on results.** Fix: Create a `decay_router.py` that reads CUSUM output and adjusts strategy weights in the live scanner.

2. **Gap: Offline-only PELT algorithm.** Fix: Add an online CUSUM mode using the `river` library's `drift.ADWIN` or implement FOCuS for O(log n) per-step online detection.

3. **Gap: Hardcoded hyperparameters (penalty=1.5, min_size=8).** Fix: Tune per-strategy using historical data. High-frequency strategies need lower min_size (4-6); low-frequency need higher (12-20).

4. **Gap: No feature-level drift detection.** Fix: Add PSI (Population Stability Index) computation for each model input feature. When PSI > 0.2, flag feature as drifted.

5. **Gap: No false-positive filtering.** Fix: Add a minimum-evidence threshold -- require at least 20 trades in the deteriorated segment before classifying as "decayed". Current threshold of 15 trades for confidence penalty is too permissive.

6. **Gap: Single detection method.** Fix: Ensemble CUSUM + Rolling Sharpe + IC into a composite health score. Require 2/3 methods to agree before triggering rotation.

---

## Section 8: Key Formulas and Code Snippets

### 8.1 Signal Half-Life Estimator

```python
import numpy as np
from statsmodels.tsa.ar_model import AutoReg

def signal_half_life(returns_series, max_lag=1):
    """
    Estimate half-life of mean-reversion in a return series.
    Returns half-life in units of the observation frequency.
    """
    series = np.array(returns_series, dtype=float)
    series = series[~np.isnan(series)]

    if len(series) < 20:
        return float('inf')

    model = AutoReg(series, lags=max_lag).fit()
    phi = model.params[1]

    if phi <= 0 or phi >= 1:
        return float('inf')

    half_life = -np.log(2) / np.log(abs(phi))
    return round(half_life, 2)
```

### 8.2 Composite Health Score

```python
def composite_health_score(strategy_stats):
    """
    Combine multiple decay indicators into single health score [0-100].

    Inputs:
        strategy_stats: dict with keys:
            - rolling_sharpe: float (60-period)
            - rolling_ic: float (30-period)
            - cusum_status: str ('strong'|'healthy'|'warning'|'decayed'|'dead')
            - recent_win_rate: float
            - n_trades: int
    """
    cusum_scores = {
        'strong': 100, 'healthy': 75, 'warning': 50,
        'decayed': 25, 'dead': 0, 'unknown': 50
    }

    # Sharpe component (0-100)
    sharpe = strategy_stats.get('rolling_sharpe', 0)
    sharpe_score = min(100, max(0, (sharpe + 1) * 33.3))  # Maps [-1, 2] to [0, 100]

    # IC component (0-100)
    ic = strategy_stats.get('rolling_ic', 0)
    ic_score = min(100, max(0, ic * 1000))  # Maps [0, 0.1] to [0, 100]

    # CUSUM component (0-100)
    cusum_score = cusum_scores.get(
        strategy_stats.get('cusum_status', 'unknown'), 50
    )

    # Win rate component (0-100)
    wr = strategy_stats.get('recent_win_rate', 0.5)
    wr_score = min(100, max(0, (wr - 0.3) * 250))  # Maps [0.3, 0.7] to [0, 100]

    # Confidence adjustment
    n_trades = strategy_stats.get('n_trades', 0)
    confidence = min(1.0, n_trades / 50)  # Full confidence at 50+ trades

    # Weighted composite
    raw_score = (
        sharpe_score * 0.35 +
        ic_score * 0.25 +
        cusum_score * 0.25 +
        wr_score * 0.15
    )

    # Blend toward 50 (uncertain) when low confidence
    final_score = raw_score * confidence + 50 * (1 - confidence)

    return round(final_score, 1)
```

### 8.3 Decay Router (Integration Point)

```python
def route_decay_action(health_score, strategy_name, current_weight):
    """
    Decide action based on composite health score.
    Returns: (new_weight, action_description)
    """
    if health_score >= 80:
        new_weight = min(1.5, current_weight * 1.1)
        action = "BOOST: Strategy performing strongly"
    elif health_score >= 60:
        new_weight = 1.0
        action = "HOLD: Normal performance"
    elif health_score >= 40:
        new_weight = 0.6
        action = "REDUCE: Showing signs of decay; schedule retrain"
    elif health_score >= 20:
        new_weight = 0.3
        action = "WARN: Significant decay detected; retrain with recent data"
    else:
        new_weight = 0.0
        action = "PAUSE: Strategy dead; rotate in challenger"

    return new_weight, action
```

---

## Section 9: References

### Academic Papers
1. Falck, Rej & Thesmar (2022). "When do systematic strategies decay?" *Quantitative Finance*, 22(11), 1955-1969. [Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/14697688.2022.2098810)
2. Di Mascio, Lines & Naik (2021). "Alpha Decay." *SSRN*. [PDF](https://www.top1000funds.com/wp-content/uploads/2021/05/SSRN-id2580551.pdf)
3. Killick, Fearnhead & Eckley (2012). "Optimal detection of changepoints with a linear computational cost." *JASA*, 107(500), 1590-1598.
4. Liu, Tsyvinski & Wu (2022). "Common Risk Factors in Cryptocurrency." *Journal of Finance*, 77(2), 1133-1177.
5. Adams & MacKay (2007). "Bayesian Online Changepoint Detection." *arXiv:0710.3742*.
6. Romano & Wolf (2005). "Stepwise Multiple Testing as Formalized Data Snooping." *Econometrica*, 73(4), 1237-1282.

### Industry Research
7. Maven Securities. "Alpha Decay: what does it look like?" [Link](https://www.mavensecurities.com/alpha-decay-what-does-it-look-like-and-what-does-it-mean-for-systematic-traders/)
8. Alpha Architect. "Information Decay: which factors have the longest half-lives?" [Link](https://alphaarchitect.com/information-decay/)
9. MicroAlphas. "Signal Decay Analysis: Understanding Alpha Lifecycles." [Link](https://microalphas.com/signal-decay-patterns/)
10. KX Systems. "Signal Decay: Why Alpha Half-Lives Are Shrinking." [Link](https://kx.com/resources/webinars/signal-decay-why-alpha-half-lives-are-shrinking-and-how-leading-funds-keep-up/)
11. Exegy. "How to Stop Alpha Decay with Infrastructure." [Link](https://www.exegy.com/alpha-decay/)
12. CFM (Capital Fund Management). "Why and how systematic strategies decay." [PDF](https://www.cfm.com/wp-content/uploads/2022/12/312-2021-05-Why-and-how-systematic-strategies-decay.pdf)
13. Robot Wealth. "Why You Can't Tell if Your Strategy Stopped Working." [Link](https://robotwealth.com/why-you-cant-tell-if-your-strategy-strategy-stopped-working-statistically-speaking/)
14. Best, Mark R. "Alpha Decay in Quantitative Trading." [Link](https://markrbest.github.io/alpha-decay/)
15. QuantStart. "Annualised Rolling Sharpe Ratio in QSTrader." [Link](https://www.quantstart.com/articles/annualised-rolling-sharpe-ratio-in-qstrader/)

### Concept Drift and Online Learning
16. QuantInsti. "Autoregressive Drift Detection Method (ADDM) in Trading." [Link](https://blog.quantinsti.com/autoregressive-drift-detection-method/)
17. MDPI Applied Sciences. "Concept Drift Adaptation Methods under the Deep Learning Framework." [Link](https://www.mdpi.com/2076-3417/13/11/6515)
18. JMLR. "Fast Online Changepoint Detection via Functional Pruning CUSUM Statistics." [Link](https://www.jmlr.org/papers/v24/21-1230/21-1230.pdf)

---

*Researcher ID: 010* | *Status: COMPLETE* | *Last Updated: 2026-02-24*
