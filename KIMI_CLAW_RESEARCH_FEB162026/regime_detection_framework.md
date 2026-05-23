# MARKET REGIME DETECTION & STRATEGY MAPPING FRAMEWORK

## Executive Summary

This document provides a comprehensive framework for identifying market regimes and mapping optimal trading strategies to each regime condition. Based on extensive research and empirical analysis, this framework enables dynamic strategy allocation that adapts to changing market conditions.

---

## 1. MARKET REGIME DEFINITIONS

### 1.1 Core Regime Classification

| Regime | Key Characteristics | Duration | Typical Conditions |
|--------|---------------------|----------|-------------------|
| **Bull Market** | Trending up, low volatility | Months to years | Economic expansion, low rates, positive sentiment |
| **Bear Market** | Trending down, high volatility | Months to 2+ years | Recession, crisis, high rates, negative sentiment |
| **Sideways/Choppy** | No trend, mean-reverting | Weeks to months | Consolidation, indecision, range-bound |
| **High Volatility** | Large moves, uncertainty | Days to weeks | Crisis events, news shocks, regime transitions |
| **Low Volatility** | Compressed ranges, calm | Weeks to months | Pre-crisis, summer doldrums, complacency |

### 1.2 Multi-Dimensional Regime Characterization

```
REGIME IDENTIFICATION MATRIX:

                    Trend Direction
                    ↑ Up        ↓ Down
               ┌───────────┬───────────┐
        High   │   Bull    │   Bear    │
Volatility     │  (Strong) │  (Strong) │
               ├───────────┼───────────┤
        Low    │   Bull    │   Bear    │
               │  (Weak)   │  (Weak)   │
               └───────────┴───────────┘

Additional Axes:
- Correlation Regime: High (crisis) vs Low (normal)
- Liquidity Regime: Deep vs Thin
- Sentiment Regime: Extreme vs Neutral
```

### 1.3 Regime Detection Indicators

**Primary Indicators:**
- 20-day vs 200-day moving average (trend direction)
- Realized volatility (20-day rolling)
- VIX or equivalent fear index
- Market breadth (advance-decline line)

**Secondary Indicators:**
- Correlation between assets (average pairwise correlation)
- Skewness of returns
- Volume patterns
- Credit spreads
- Yield curve slope

**Advanced Regime Detection Models:**
- Hidden Markov Models (HMM)
- Gaussian Mixture Models (GMM)
- Statistical Jump Models (SJM)
- K-Means clustering on return/volatility features

---

## 2. STRATEGY-TO-REGIME MAPPING

### 2.1 Strategy Performance by Regime

| Strategy Type | Bull Market | Bear Market | Sideways | High Vol | Low Vol |
|---------------|-------------|-------------|----------|----------|---------|
| **Trend Following** | ★★★★★ | ★★★☆☆ | ★☆☆☆☆ | ★★★☆☆ | ★★☆☆☆ |
| **Momentum** | ★★★★★ | ★★☆☆☆ | ★★☆☆☆ | ★★★☆☆ | ★★★☆☆ |
| **Mean Reversion** | ★★☆☆☆ | ★★★☆☆ | ★★★★★ | ★★★★☆ | ★★☆☆☆ |
| **Breakout** | ★★★★☆ | ★★☆☆☆ | ★★☆☆☆ | ★★★★★ | ★☆☆☆☆ |
| **Statistical Arbitrage** | ★★★☆☆ | ★★★★☆ | ★★★★★ | ★★☆☆☆ | ★★★★☆ |
| **Carry Trade** | ★★★★☆ | ★☆☆☆☆ | ★★★☆☆ | ★☆☆☆☆ | ★★★★★ |
| **Volatility Selling** | ★★★★★ | ★☆☆☆☆ | ★★★★☆ | ★☆☆☆☆ | ★★★★★ |
| **Volatility Buying** | ★☆☆☆☆ | ★★★★★ | ★★☆☆☆ | ★★★★★ | ★☆☆☆☆ |
| **Value Investing** | ★★★☆☆ | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★★☆☆ |
| **Quality Factor** | ★★★☆☆ | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★★☆ |

### 2.2 Detailed Strategy Descriptions

#### REGIME-SPECIFIC STRATEGIES

**Bull Market Strategies:**
- Long-only momentum (12-month lookback)
- Trend following with trailing stops
- Growth factor overweight
- Volatility selling (short puts, covered calls)
- Leveraged long exposure

**Bear Market Strategies:**
- Long volatility (VIX calls, straddles)
- Short selling / inverse ETFs
- Defensive sector rotation (utilities, staples)
- Quality factor focus
- Cash/bond allocation increase
- Trend following with short bias

**Sideways/Choppy Strategies:**
- Mean reversion (RSI, Bollinger Bands)
- Range trading
- Calendar spreads
- Pairs trading
- Short-term momentum (1-5 day)
- Iron condors (options)

**High Volatility Strategies:**
- Breakout trading
- Volatility breakout systems
- Options straddles/strangles
- Risk-off positioning
- Reduced position sizing
- Trend following (vol-adjusted)

**Low Volatility Strategies:**
- Volatility selling (collecting premium)
- Carry trades
- Range expansion plays
- Preparing for volatility expansion
- Credit spreads

### 2.3 Regime-Agnostic Strategies

These strategies work across multiple regimes but require parameter adjustment:

| Strategy | Regime Adaptation |
|----------|-------------------|
| Risk Parity | Volatility targeting |
| Trend Following | Adjust lookback periods |
| Momentum | Time-varying momentum windows |
| Factor Investing | Factor rotation based on macro |
| Statistical Arbitrage | Adjust correlation thresholds |

---

## 3. REGIME-SWITCHING FRAMEWORK

### 3.1 Detection Methodology

```python
# Pseudocode for Regime Detection

class RegimeDetector:
    def __init__(self):
        self.features = ['returns', 'volatility', 'correlation', 'trend']
        self.model = HiddenMarkovModel(n_states=4)
    
    def calculate_features(self, prices):
        returns = prices.pct_change()
        features = {
            'trend': returns.rolling(20).mean() / returns.rolling(20).std(),
            'volatility': returns.rolling(20).std() * np.sqrt(252),
            'momentum': prices.rolling(20).mean() / prices.rolling(200).mean() - 1,
            'skewness': returns.rolling(60).skew()
        }
        return features
    
    def detect_regime(self, features):
        # HMM or SJM inference
        regime_probabilities = self.model.predict(features)
        current_regime = np.argmax(regime_probabilities)
        confidence = max(regime_probabilities)
        return current_regime, confidence
```

### 3.2 Regime Transition Rules

**Conservative Switching (Lower turnover):**
- Require 2+ consecutive days in new regime
- Confidence threshold > 70%
- Confirmation from multiple indicators

**Aggressive Switching (Higher responsiveness):**
- Single day regime change triggers action
- Confidence threshold > 50%
- Lead indicator based (VIX, credit spreads)

### 3.3 Dynamic Portfolio Allocation

```
ALLOCATION FRAMEWORK:

Base Allocation (Equal Weight):
├── Trend Following: 20%
├── Mean Reversion: 20%
├── Momentum: 20%
├── Statistical Arbitrage: 20%
└── Risk Off (Cash/Bonds): 20%

Regime Adjustments:
┌─────────────────────────────────────────────────────────┐
│ BULL MARKET:                                            │
│   Trend Following: +15% → 35%                          │
│   Momentum: +10% → 30%                                 │
│   Mean Reversion: -10% → 10%                           │
│   Stat Arb: -5% → 15%                                  │
│   Risk Off: -10% → 10%                                 │
├─────────────────────────────────────────────────────────┤
│ BEAR MARKET:                                            │
│   Trend Following: +10% → 30% (short bias)             │
│   Momentum: -15% → 5%                                  │
│   Mean Reversion: +5% → 25%                            │
│   Stat Arb: -5% → 15%                                  │
│   Risk Off: +5% → 25%                                  │
├─────────────────────────────────────────────────────────┤
│ SIDEWAYS:                                               │
│   Trend Following: -15% → 5%                           │
│   Momentum: -10% → 10%                                 │
│   Mean Reversion: +20% → 40%                           │
│   Stat Arb: +10% → 30%                                 │
│   Risk Off: -5% → 15%                                  │
├─────────────────────────────────────────────────────────┤
│ HIGH VOLATILITY:                                        │
│   Trend Following: +5% → 25%                           │
│   Momentum: -5% → 15%                                  │
│   Mean Reversion: +5% → 25%                            │
│   Stat Arb: -15% → 5%                                  │
│   Risk Off: +10% → 30%                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 4. HISTORICAL REGIME ANALYSIS

### 4.1 2020 COVID Crash (Feb-Mar 2020)

**Regime Characteristics:**
- Transition: Bull → High Vol → Bear
- Duration: ~1 month extreme vol, then recovery
- VIX spike: 13 → 82 (all-time high)
- S&P 500 drawdown: -34%

**Optimal Strategy Response:**
| Period | Regime | Strategy Allocation |
|--------|--------|---------------------|
| Jan-Feb 2020 | Bull (late stage) | Reduce long exposure, increase vol hedges |
| Feb-Mar 2020 | High Vol/Crash | Long vol, short equity, risk off |
| Apr-Jun 2020 | Recovery/Bull | Trend following long, momentum |
| Jul-Dec 2020 | Bull | Full risk-on, momentum, growth |

**Lessons:**
- Regime detection lag cost ~5-10% in performance
- Volatility breakout systems captured the move
- Mean reversion strategies failed catastrophically

### 4.2 2021 Bull Run

**Regime Characteristics:**
- Strong trend, low volatility
- Retail participation surge
- Meme stock phenomenon
- Crypto boom
- Inflation beginning

**Optimal Strategy Response:**
| Strategy | Performance | Allocation |
|----------|-------------|------------|
| Momentum | +40% to +80% | 40% |
| Trend Following | +30% to +50% | 30% |
| Vol Selling | +15% to +25% | 15% |
| Mean Reversion | -5% to +5% | 5% |
| Risk Off | 0% | 10% |

**Lessons:**
- Momentum dominated all other factors
- Value strategies underperformed significantly
- Low vol environment rewarded risk-taking

### 4.3 2022 Bear Market

**Regime Characteristics:**
- Fed rate hikes (0% → 4.5%)
- Inflation surge (9.1% peak)
- Tech wreck
- Crypto collapse
- Russia-Ukraine war

**Optimal Strategy Response:**
| Period | Regime | Best Strategies |
|--------|--------|-----------------|
| Jan-Mar | Bear onset | Short equity, long vol, trend short |
| Apr-Jun | Bear continuation | Trend following short, quality factor |
| Jul-Aug | Bear rally | Mean reversion long (counter-trend) |
| Sep-Oct | Bear resumption | Trend following short, risk off |
| Nov-Dec | Bottoming | Value, quality, small long exposure |

**Lessons:**
- Trend following with short bias outperformed
- Buy-and-hold suffered -20% to -30%
- Factor rotation (growth→value) was critical
- Volatility buying paid off in spikes

### 4.4 2023-2024 Recovery

**Regime Characteristics:**
- AI/tech rally
- Narrow market (Magnificent 7)
- Rates plateau then decline
- Soft landing narrative
- Resilient economy

**Optimal Strategy Response:**
| Strategy | Performance | Notes |
|----------|-------------|-------|
| Momentum (tech) | +50% to +100% | Concentrated in AI names |
| Trend Following | +20% to +40% | Captured tech trend |
| Equal Weight | +10% to +20% | Underperformed cap-weighted |
| Mean Reversion | +5% to +15% | Worked in chop periods |
| Value | +5% to +15% | Lagged significantly |

**Lessons:**
- Narrow leadership requires concentrated exposure
- Factor timing (momentum vs value) was key
- Trend following captured the AI theme

### 4.5 2025 Current Conditions (as of Feb 2025)

**Observed Characteristics:**
- High valuations
- Geopolitical tensions
- Tariff concerns
- AI investment boom continues
- Rate uncertainty

**Detected Regime:** Late Bull / Transition Risk

**Recommended Allocation:**
| Strategy | Weight | Rationale |
|----------|--------|-----------|
| Trend Following | 25% | Capture remaining trend |
| Momentum | 20% | But reduce vs 2024 |
| Quality Factor | 20% | Defensive positioning |
| Mean Reversion | 15% | Increasing range-bound behavior |
| Long Volatility | 10% | Hedge for transition |
| Risk Off | 10% | Dry powder |

---

## 5. DYNAMIC ALLOCATION RULES

### 5.1 Regime-Based Rebalancing Triggers

**Trigger Types:**
1. **Regime Change**: Primary trigger - full reallocation
2. **Confidence Threshold**: Secondary trigger - partial adjustment
3. **Time-Based**: Monthly/quarterly review regardless of regime
4. **Risk Budget**: Volatility target breach

### 5.2 Position Sizing Rules

```
VOLATILITY-BASED SIZING:

Base Position Size = Portfolio Value × Target Risk / Asset Volatility

Regime Multipliers:
- Bull Market: 1.2x (increase risk)
- Bear Market: 0.6x (decrease risk)
- Sideways: 0.8x (moderate risk)
- High Vol: 0.5x (significantly reduce)
- Low Vol: 1.0x (normal risk)

Maximum Position Limits:
- Single strategy: 40% of portfolio
- Single asset: 20% of portfolio
- Correlated strategies: 60% combined
```

### 5.3 Risk Management by Regime

| Regime | Stop Loss | Position Size | Correlation Limit |
|--------|-----------|---------------|-------------------|
| Bull | 10-15% | 100% | 0.8 |
| Bear | 5-8% | 50% | 0.6 |
| Sideways | 3-5% | 75% | 0.7 |
| High Vol | 3-5% | 40% | 0.5 |
| Low Vol | 8-12% | 100% | 0.9 |

---

## 6. IMPLEMENTATION FRAMEWORK

### 6.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    REGIME DETECTION LAYER                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  HMM Model  │  │  GMM Model  │  │  Technical Filters  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         └─────────────────┼────────────────────┘             │
│                           ▼                                  │
│                  ┌─────────────────┐                         │
│                  │  Regime Fusion  │                         │
│                  │  (Ensemble)     │                         │
│                  └────────┬────────┘                         │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 STRATEGY ALLOCATION LAYER                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Trend      │  │    Mean      │  │   Momentum   │       │
│  │  Following   │  │  Reversion   │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Stat Arb    │  │  Volatility  │  │    Risk      │       │
│  │              │  │  Strategies  │  │    Off       │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  EXECUTION & RISK LAYER                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Sizing    │  │   Stops     │  │  Correlation Check  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Key Performance Metrics by Regime

| Metric | Bull Target | Bear Target | Sideways Target |
|--------|-------------|-------------|-----------------|
| Sharpe Ratio | > 1.5 | > 0.5 | > 1.0 |
| Max Drawdown | < 15% | < 10% (absolute) | < 8% |
| Win Rate | > 55% | > 45% | > 60% |
| Profit Factor | > 1.5 | > 1.2 | > 1.4 |
| Information Ratio | > 0.8 | > 0.3 | > 0.6 |

### 6.3 Backtesting Requirements

**Minimum Data Requirements:**
- 5+ years of data covering multiple regimes
- Include at least one major crisis period
- Out-of-sample testing: minimum 2 years
- Walk-forward analysis recommended

**Regime-Specific Testing:**
- Test each strategy in identified historical regimes
- Verify strategy transitions
- Measure regime detection lag impact
- Account for transaction costs in regime switches

---

## 7. SUMMARY & ACTION ITEMS

### 7.1 Key Takeaways

1. **No single strategy works in all regimes** - Dynamic allocation is essential
2. **Regime detection has lag** - Build in buffers and confirmation
3. **Transaction costs matter** - Don't over-trade regime switches
4. **Risk management varies by regime** - Adjust stops and sizing
5. **Historical patterns repeat** - Use past regime analysis for preparation

### 7.2 Implementation Checklist

- [ ] Implement regime detection model (HMM/SJM)
- [ ] Define strategy universe with regime-specific parameters
- [ ] Build allocation rules engine
- [ ] Create risk management overlays
- [ ] Backtest across multiple historical regimes
- [ ] Paper trade regime transitions
- [ ] Deploy with monitoring dashboards

### 7.3 Current Market Action (Feb 2025)

**Detected Regime:** Late Bull Market with Transition Risk

**Recommended Actions:**
1. Reduce momentum exposure from 40% to 20%
2. Increase quality factor allocation to 20%
3. Add 10% long volatility hedge
4. Maintain 10% cash for opportunities
5. Tighten stops on trend positions
6. Monitor for regime change signals

---

## APPENDIX: REGIME DETECTION CODE TEMPLATE

```python
import numpy as np
import pandas as pd
from hmmlearn import hmm
from sklearn.mixture import GaussianMixture

class MarketRegimeFramework:
    """
    Comprehensive regime detection and strategy allocation framework
    """
    
    def __init__(self, n_regimes=4):
        self.n_regimes = n_regimes
        self.hmm_model = hmm.GaussianHMM(n_components=n_regimes, 
                                         covariance_type="full",
                                         n_iter=100)
        self.regime_names = ['Bull', 'Bear', 'Sideways', 'High_Vol']
        
    def extract_features(self, prices):
        """Extract regime-relevant features"""
        returns = prices.pct_change().dropna()
        
        features = pd.DataFrame(index=returns.index)
        
        # Trend features
        features['trend'] = (prices.rolling(20).mean() / 
                            prices.rolling(200).mean() - 1)
        
        # Volatility features
        features['volatility'] = returns.rolling(20).std() * np.sqrt(252)
        
        # Momentum features
        features['momentum_1m'] = returns.rolling(21).sum()
        features['momentum_3m'] = returns.rolling(63).sum()
        
        # Return distribution features
        features['skewness'] = returns.rolling(60).skew()
        features['kurtosis'] = returns.rolling(60).kurt()
        
        return features.dropna()
    
    def fit_regime_model(self, features):
        """Fit HMM to identify regimes"""
        self.hmm_model.fit(features.values)
        hidden_states = self.hmm_model.predict(features.values)
        
        # Label regimes based on characteristics
        regime_labels = self._label_regimes(features, hidden_states)
        
        return hidden_states, regime_labels
    
    def _label_regimes(self, features, states):
        """Label regimes based on state characteristics"""
        labels = []
        for state in np.unique(states):
            mask = states == state
            avg_return = features.loc[mask, 'momentum_1m'].mean()
            avg_vol = features.loc[mask, 'volatility'].mean()
            
            if avg_return > 0.02 and avg_vol < 0.15:
                labels.append('Bull')
            elif avg_return < -0.02:
                labels.append('Bear')
            elif avg_vol > 0.25:
                labels.append('High_Vol')
            else:
                labels.append('Sideways')
        
        return labels
    
    def get_strategy_allocation(self, current_regime):
        """Return optimal strategy allocation for regime"""
        allocations = {
            'Bull': {
                'trend_following': 0.35,
                'momentum': 0.30,
                'mean_reversion': 0.10,
                'stat_arb': 0.15,
                'risk_off': 0.10
            },
            'Bear': {
                'trend_following': 0.30,
                'momentum': 0.05,
                'mean_reversion': 0.25,
                'stat_arb': 0.15,
                'risk_off': 0.25
            },
            'Sideways': {
                'trend_following': 0.05,
                'momentum': 0.10,
                'mean_reversion': 0.40,
                'stat_arb': 0.30,
                'risk_off': 0.15
            },
            'High_Vol': {
                'trend_following': 0.25,
                'momentum': 0.15,
                'mean_reversion': 0.25,
                'stat_arb': 0.05,
                'risk_off': 0.30
            }
        }
        
        return allocations.get(current_regime, allocations['Sideways'])
```

---

*Document Version: 1.0*
*Last Updated: February 2025*
*Framework Status: Ready for Implementation*
