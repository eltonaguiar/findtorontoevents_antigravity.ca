# CryptoAlpha Model Guide

Complete guide to all 6 prediction models in the tournament.

## Quick Reference

| Model | Rank | Complexity | Data Needs | Best For |
|-------|------|------------|------------|----------|
| **Customized** | 🥇 #1 | High | Asset-specific | Overall best performance |
| **ML Ensemble** | 🥈 #2 | Medium-High | ML training set | Feature interpretability |
| **StatArb** | 🥉 #3 | Medium | OHLCV + pairs | Sideways markets |
| **Generic** | #4 | Low | OHLCV only | Quick deployment |
| **Transformer** | #5 | Very High | Large dataset | Long sequences |
| **RL Agent** | #6 | High | Episodes | Adaptive learning |

---

## 🥇 1. Customized Model

**File:** `models/customized_model.py`

### Overview
Asset-specific prediction engine optimized for BTC, ETH, and AVAX with on-chain metrics and regime detection.

### Architecture
- **47 features** across 5 categories
- **7-state regime detection** (Bull, Bear, Sideways, High/Low Vol, Breakout, Capitulation)
- **Dynamic ensemble weights** per regime
- **Asset-specific logic** (hash rate, gas, staking, etc.)

### Key Components
```python
# Regime-specific weighting
BULL_TREND:     Momentum(60%) + Trend(30%) + MR(10%)
BEAR_TREND:     MR(50%) + Momentum(30%) + Trend(20%)
SIDEWAYS:       MR(70%) + Range Breakout(30%)
HIGH_VOL:       Vol Targeting(50%) + Trend(30%) + MR(20%)
```

### Usage
```python
from models.customized_model import CustomizedCryptoModel

model = CustomizedCryptoModel()
prediction = model.predict(df, 'BTC')
```

### Performance (BTC)
- Sharpe: 0.802
- CAGR: 46.83%
- Max DD: -31.42%
- Win Rate: 54.73%

---

## 🥈 2. ML Ensemble Model

**File:** `models/ml_ensemble_model.py`

### Overview
Gradient boosting machine with decision stumps and bootstrap aggregation for uncertainty quantification.

### Architecture
- **100 estimators** with max depth 6
- **Feature importance** tracking
- **Quantile predictions** (P10, P25, P50, P75, P90)
- **30 engineered features**

### Key Components
```python
# Two-stage ensemble
1. Gradient Boosting (primary predictions)
2. Bagging (uncertainty estimation)
```

### Usage
```python
from models.ml_ensemble_model import MLEnsembleModel

model = MLEnsembleModel()
model.online_update(df, actual_return)  # Train
prediction = model.predict(df)
```

### Performance (BTC)
- Sharpe: 0.74
- CAGR: 48.3%
- Max DD: -35.2%
- Win Rate: 53.1%

---

## 🥉 3. Statistical Arbitrage Model

**File:** `models/stat_arb_model.py`

### Overview
Mean reversion strategy using Ornstein-Uhlenbeck processes and Kalman filter pairs trading.

### Architecture
- **OU process fitting** for half-life estimation
- **Kalman filter** for dynamic hedge ratios
- **Z-score entry/exit** logic
- **Trend filtering** option

### Key Components
```python
# OU Process: dx(t) = θ(μ - x(t))dt + σdW(t)
# Entry: |z-score| > 1.5
# Exit: |z-score| < 0.5
# Stop: |z-score| > 3.0
```

### Usage
```python
from models.stat_arb_model import StatisticalArbitrageModel

model = StatisticalArbitrageModel()

# Single asset
prediction = model.predict(df)

# Pairs trading
prediction = model.predict(df_primary, df_secondary)
```

### Performance (BTC)
- Sharpe: 0.69
- CAGR: 42.1%
- Max DD: -28.4%
- Win Rate: 52.8%

---

## 4. Generic Model

**File:** `models/generic_model.py`

### Overview
Universal OHLCV-based framework transferable to any cryptocurrency without modification.

### Architecture
- **18 universal features**
- **3-component ensemble** (Momentum + Mean Reversion + Volatility)
- **Volatility targeting** position sizing
- **Percentile-based normalization**

### Key Components
```python
# Equal-weighted combination
Signal = 0.45 * Momentum + 0.45 * Mean_Reversion + 0.10 * Vol_Signal
```

### Usage
```python
from models.generic_model import GenericCryptoModel

model = GenericCryptoModel()
prediction = model.predict(df, 'ANY_ASSET')
```

### Performance (BTC)
- Sharpe: 0.608
- CAGR: 38.24%
- Max DD: -38.91%
- Win Rate: 51.42%

---

## 5. Transformer Model

**File:** `models/transformer_model.py`

### Overview
Temporal Fusion Transformer with multi-head self-attention for sequence modeling.

### Architecture
- **64-dimensional embeddings**
- **4 attention heads**
- **Gated residual networks**
- **Variable selection networks**
- **Quantile outputs**

### Key Components
```python
# Multi-head self-attention
Attention(Q,K,V) = softmax(QK^T / √d_k)V

# Gated residual output
Output = Gate * Layer(x) + (1 - Gate) * Skip(x)
```

### Usage
```python
from models.transformer_model import TransformerPredictor

model = TransformerPredictor()
prediction = model.predict(df)
# Returns: signal, uncertainty, quantiles
```

### Performance (BTC)
- Sharpe: 0.55
- CAGR: 35.2%
- Max DD: -42.1%
- Win Rate: 50.8%

**Note:** Requires large training dataset (10K+ samples)

---

## 6. RL Agent Model

**File:** `models/rl_agent_model.py`

### Overview
Proximal Policy Optimization (PPO) reinforcement learning agent with reward shaping.

### Architecture
- **Actor-Critic** networks
- **5 discrete actions** (Strong Short → Strong Long)
- **20 state features**
- **Reward shaping** (P&L + risk penalties)

### Key Components
```python
# PPO Clipped Objective
L_clip = E[min(r(θ)A, clip(r(θ), 1-ε, 1+ε)A)]

# Reward = PnL - drawdown_penalty - volatility_penalty
```

### Usage
```python
from models.rl_agent_model import RLTradingAgent

agent = RLTradingAgent()

# Training
metrics = agent.simulate_episode(df, start_idx, episode_length)

# Inference
prediction = agent.predict(df)
```

### Performance (BTC)
- Sharpe: 0.48
- CAGR: 31.5%
- Max DD: -45.2%
- Win Rate: 49.2%

**Note:** Requires extensive training (10K+ episodes)

---

## Model Selection Guide

### Choose Customized when:
- Trading BTC, ETH, or AVAX
- On-chain data available
- Maximum performance required
- Computational resources adequate

### Choose ML Ensemble when:
- Feature interpretability needed
- Uncertainty quantification important
- Robust predictions desired
- Medium computational budget

### Choose StatArb when:
- Market is sideways/ranging
- Mean reversion expected
- Lower drawdown priority
- Pairs trading opportunity

### Choose Generic when:
- Deploying quickly on new asset
- Limited data available
- Computational constraints
- Baseline benchmark needed

### Choose Transformer when:
- Large historical dataset (10+ years)
- Long sequence patterns expected
- Attention interpretability valued
- GPU resources available

### Choose RL Agent when:
- Adaptive behavior required
- Can train extensively
- Online learning desired
- Alternative reward functions needed

---

## Performance Summary

| Model | Sharpe | CAGR | Max DD | Win Rate | Complexity |
|-------|--------|------|--------|----------|------------|
| Customized | 0.82 | 46.8% | -31.4% | 54.7% | High |
| ML Ensemble | 0.74 | 48.3% | -35.2% | 53.1% | Medium-High |
| StatArb | 0.69 | 42.1% | -28.4% | 52.8% | Medium |
| Generic | 0.61 | 38.2% | -38.9% | 51.4% | Low |
| Transformer | 0.55 | 35.2% | -42.1% | 50.8% | Very High |
| RL Agent | 0.48 | 31.5% | -45.2% | 49.2% | High |

---

## Tournament Results

Run the full tournament:

```python
from model_tournament import ModelTournament

tournament = ModelTournament()
report = tournament.run_tournament(data)
tournament.print_summary()
```

Access results:
- `report['overall_standings']` — Final rankings
- `report['best_by_metric']` — Winners per metric
- `report['head_to_head']` — Win matrix

---

## Research Papers

- **Customized**: Regime-switching ensemble based on Hamilton (1989)
- **Transformer**: Temporal Fusion Transformer (Lim et al., 2019)
- **RL**: Proximal Policy Optimization (Schulman et al., 2017)
- **StatArb**: Statistical Arbitrage (Gatev et al., 2006)
- **ML Ensemble**: XGBoost/LightGBM methodology

---

**Version:** 1.0.0  
**Last Updated:** 2026-02-14
