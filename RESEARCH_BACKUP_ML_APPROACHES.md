# Alternative Machine Learning Approaches for Trading
## Research Document - Backup Options Beyond Supervised Learning

**Date:** February 15, 2026  
**Purpose:** Research alternative ML paradigms as backup options when standard supervised learning underperforms

---

## Executive Summary

When traditional supervised learning (predicting price direction with classification/regression) fails, these alternative approaches offer fundamentally different ways to model market behavior:

| Approach | Best For | Complexity | Risk Level | Implementation Time |
|----------|----------|------------|------------|---------------------|
| **Reinforcement Learning** | Sequential decision making | High | High | 2-4 weeks |
| **Hidden Markov Models** | Regime detection | Medium | Medium | 1-2 weeks |
| **Ensemble Methods** | Robust predictions | Low-Medium | Low | 1 week |
| **Online Learning** | Adapting to market changes | Medium | Medium | 1-2 weeks |
| **Genetic Algorithms** | Strategy optimization | Medium | Medium | 2-3 weeks |
| **Transformers** | Long-range dependencies | High | High | 3-4 weeks |

**Recommended First Backup:** Start with **Ensemble Methods (XGBoost/LightGBM)** combined with **HMM for regime detection** - they offer the best risk/reward ratio for implementation effort.

---

## 1. Reinforcement Learning for Trading

### Overview

Reinforcement Learning (RL) treats trading as a sequential decision-making problem where an agent learns to maximize cumulative rewards through trial and error. Unlike supervised learning, RL doesn't need labeled targets - it learns from rewards (profits/losses).

### Key Algorithms

#### 1.1 Deep Q-Network (DQN)

**When it works best:**
- Discrete action spaces (Buy/Hold/Sell)
- Need for experience replay to stabilize learning
- Medium-frequency trading (daily to hourly)

**Implementation:**

```python
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random

class DQNTradingNetwork(nn.Module):
    """
    Deep Q-Network for trading decisions.
    Input: Market state features
    Output: Q-values for each action (Buy, Hold, Sell)
    """
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super(DQNTradingNetwork, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, action_dim)
        )
    
    def forward(self, x):
        return self.network(x)

class DQNTradingAgent:
    """
    DQN Agent for portfolio management.
    
    Research shows DQN achieved 11.24% ROI on TQQQ with proper training:
    - Learning rate: 0.0003
    - Discount factor: 0.99
    - Epsilon decay: 1.0 -> 0.01
    - Batch size: 64
    - Replay buffer: 100,000 transitions
    """
    def __init__(self, state_dim, action_dim, learning_rate=0.0003):
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Q-Networks (main and target)
        self.q_network = DQNTradingNetwork(state_dim, action_dim)
        self.target_network = DQNTradingNetwork(state_dim, action_dim)
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        self.replay_buffer = deque(maxlen=100000)
        
        self.gamma = 0.99  # Discount factor
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.batch_size = 64
        self.update_target_every = 1000
        self.step_count = 0
        
    def select_action(self, state, evaluate=False):
        """Epsilon-greedy action selection"""
        if not evaluate and random.random() < self.epsilon:
            return random.randrange(self.action_dim)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            q_values = self.q_network(state_tensor)
            return q_values.argmax().item()
    
    def store_transition(self, state, action, reward, next_state, done):
        """Store experience in replay buffer"""
        self.replay_buffer.append((state, action, reward, next_state, done))
    
    def train(self):
        """Train the Q-network using experience replay"""
        if len(self.replay_buffer) < self.batch_size:
            return
        
        # Sample mini-batch
        batch = random.sample(self.replay_buffer, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        dones = torch.FloatTensor(dones)
        
        # Current Q-values
        current_q = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Double DQN: use main network to select action, target to evaluate
        with torch.no_grad():
            next_actions = self.q_network(next_states).argmax(1)
            next_q = self.target_network(next_states).gather(1, next_actions.unsqueeze(1))
            target_q = rewards.unsqueeze(1) + (1 - dones.unsqueeze(1)) * self.gamma * next_q
        
        # Compute loss and update
        loss = nn.MSELoss()(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        # Update target network
        self.step_count += 1
        if self.step_count % self.update_target_every == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        
        return loss.item()

# Reward function for trading
def calculate_trading_reward(portfolio_value, previous_value, risk_free_rate=0.02/252):
    """
    Calculate risk-adjusted reward for trading.
    Uses Sharpe-like metric: return / volatility
    """
    returns = (portfolio_value - previous_value) / previous_value
    excess_return = returns - risk_free_rate
    
    # Penalize high volatility
    volatility_penalty = abs(returns) * 0.1  # Risk aversion
    
    return excess_return - volatility_penalty
```

#### 1.2 Proximal Policy Optimization (PPO)

**When it works best:**
- Continuous action spaces (position sizing)
- Need for stable training
- High-frequency trading scenarios

**Implementation:**

```python
class PPOTradingAgent:
    """
    PPO Agent for continuous trading actions.
    Better for position sizing: outputs continuous position [-1, 1]
    """
    def __init__(self, state_dim, action_dim=1, lr=3e-4):
        self.actor = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, action_dim),
            nn.Tanh()  # Output in [-1, 1] for position sizing
        )
        
        self.critic = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, 1)
        )
        
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)
        
        self.clip_epsilon = 0.2
        self.value_coef = 0.5
        self.entropy_coef = 0.01
        
    def select_action(self, state, evaluate=False):
        state_tensor = torch.FloatTensor(state)
        action_mean = self.actor(state_tensor)
        
        if evaluate:
            return action_mean.item(), None
        
        # Add exploration noise
        dist = torch.distributions.Normal(action_mean, 0.1)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        
        return action.item(), log_prob.item()
    
    def compute_gae(self, rewards, values, dones, gamma=0.99, lambda_=0.95):
        """Generalized Advantage Estimation"""
        advantages = []
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0
            else:
                next_value = values[t + 1]
            
            delta = rewards[t] + gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + gamma * lambda_ * (1 - dones[t]) * gae
            advantages.insert(0, gae)
        
        return torch.FloatTensor(advantages)
    
    def update(self, states, actions, old_log_probs, rewards, dones):
        """PPO update with clipped objective"""
        states = torch.FloatTensor(states)
        actions = torch.FloatTensor(actions)
        old_log_probs = torch.FloatTensor(old_log_probs)
        
        # Compute advantages
        with torch.no_grad():
            values = self.critic(states).squeeze()
        advantages = self.compute_gae(rewards, values, dones)
        returns = advantages + values
        
        # Multiple epochs of updates
        for _ in range(10):
            # Compute new log probs and values
            action_means = self.actor(states)
            dist = torch.distributions.Normal(action_means, 0.1)
            new_log_probs = dist.log_prob(actions)
            entropy = dist.entropy().mean()
            
            # Compute ratios and clipped objective
            ratio = torch.exp(new_log_probs - old_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages
            actor_loss = -torch.min(surr1, surr2).mean() - self.entropy_coef * entropy
            
            # Update actor
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), 0.5)
            self.actor_optimizer.step()
            
            # Update critic
            current_values = self.critic(states).squeeze()
            critic_loss = nn.MSELoss()(current_values, returns)
            
            self.critic_optimizer.zero_grad()
            critic_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.critic.parameters(), 0.5)
            self.critic_optimizer.step()
```

#### 1.3 Actor-Critic (A2C/A3C)

**When it works best:**
- Real-time learning requirements
- Parallel training across multiple environments
- Balancing exploration and exploitation

### Comparison to Supervised Learning

| Aspect | Supervised Learning | Reinforcement Learning |
|--------|---------------------|------------------------|
| **Labels** | Needs price direction labels | Learns from profit/loss rewards |
| **Optimization** | Predict next price | Maximize cumulative return |
| **Time Horizon** | Single-step prediction | Multi-step sequential decisions |
| **Risk Management** | Manual position sizing | Built into reward function |
| **Market Adaptation** | Retrain periodically | Continuous online learning |
| **Data Efficiency** | High (needs labeled data) | Low (needs many simulations) |

### When to Use RL

**Use RL when:**
- Supervised models consistently mispredict during regime changes
- You need dynamic position sizing, not just direction
- Transaction costs and market impact matter significantly
- You can simulate realistic market environments

**Avoid RL when:**
- Limited compute resources (RL needs GPU + time)
- Can't realistically simulate slippage/spread
- Need explainable decisions (RL is a black box)

---

## 2. Unsupervised Learning for Trading

### 2.1 Hidden Markov Models (HMM) for Regime Detection

**Overview:**
HMMs identify hidden market regimes (bull/bear/sideways) that are not directly observable but manifest through price/volume patterns. Research shows HMMs can accurately predict regimes and improve Sharpe ratios by 20-30%.

**When it works best:**
- Markets exhibit clear regime clustering (volatility clustering)
- Different strategies work better in different regimes
- Need probabilistic regime assignment (not hard labels)

**Implementation:**

```python
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import pandas as pd
import numpy as np

class MarketRegimeDetector:
    """
    Hidden Markov Model for market regime detection.
    Identifies hidden states (regimes) based on observable features.
    
    Research shows 3-9 regimes work best for S&P 500:
    - Regime 1: Steady bull market (high return, low vol)
    - Regime 2: Volatile bear market (negative return, high vol)
    - Regime 0: Sideways/kangaroo market (neutral return, medium vol)
    """
    def __init__(self, n_regimes=3, use_pca=True, pca_variance=0.95):
        self.n_regimes = n_regimes
        self.use_pca = use_pca
        self.pca_variance = pca_variance
        self.scaler = StandardScaler()
        self.pca = None
        self.hmm = None
        self.regime_labels = {}
        
    def engineer_features(self, df):
        """
        Create regime-sensitive features.
        Based on research: returns + volatility + credit spreads + VIX
        """
        features = pd.DataFrame(index=df.index)
        
        # Returns at different horizons
        features['daily_return'] = df['close'].pct_change()
        features['return_21d'] = df['close'].pct_change(21)
        features['return_63d'] = df['close'].pct_change(63)
        
        # Volatility (realized)
        features['volatility_21d'] = features['daily_return'].rolling(21).std() * np.sqrt(252)
        features['volatility_63d'] = features['daily_return'].rolling(63).std() * np.sqrt(252)
        
        # Trend indicators
        features['above_50d_ma'] = (df['close'] > df['close'].rolling(50).mean()).astype(int)
        features['above_200d_ma'] = (df['close'] > df['close'].rolling(200).mean()).astype(int)
        
        # Drawdown
        rolling_max = df['close'].rolling(126, min_periods=1).max()
        features['drawdown_126d'] = df['close'] / rolling_max - 1
        
        # Volume features (if available)
        if 'volume' in df.columns:
            features['volume_ma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        return features.dropna()
    
    def fit(self, df):
        """Fit the HMM to market data"""
        # Engineer features
        features = self.engineer_features(df)
        
        # Scale features
        X = self.scaler.fit_transform(features)
        
        # Apply PCA for dimensionality reduction
        if self.use_pca:
            self.pca = PCA()
            X_pca = self.pca.fit_transform(X)
            
            # Select components explaining desired variance
            explained_variance = np.cumsum(self.pca.explained_variance_ratio_)
            n_components = np.argmax(explained_variance >= self.pca_variance) + 1
            X_final = X_pca[:, :n_components]
            print(f"Using {n_components} principal components")
        else:
            X_final = X
        
        # Fit HMM with multiple initializations for robustness
        best_bic = np.inf
        best_hmm = None
        
        for seed in range(5):
            hmm = GaussianHMM(
                n_components=self.n_regimes,
                covariance_type="diag",
                n_iter=1000,
                random_state=42 + seed
            )
            hmm.fit(X_final)
            
            # Calculate BIC for model selection
            bic = self._calculate_bic(hmm, X_final)
            if bic < best_bic:
                best_bic = bic
                best_hmm = hmm
        
        self.hmm = best_hmm
        
        # Decode regimes for training data
        regimes = self.hmm.predict(X_final)
        features['regime'] = regimes
        
        # Analyze and label regimes
        self._analyze_regimes(features)
        
        return features
    
    def _calculate_bic(self, hmm, X):
        """Bayesian Information Criterion for model selection"""
        n_samples = X.shape[0]
        n_features = X.shape[1]
        n_components = hmm.n_components
        
        # Number of parameters
        n_params = (n_components - 1) + n_components * (n_components - 1) + \
                   n_components * n_features + n_components * n_features
        
        log_likelihood = hmm.score(X)
        bic = -2 * log_likelihood + n_params * np.log(n_samples)
        
        return bic
    
    def _analyze_regimes(self, features):
        """Analyze and label each regime based on characteristics"""
        for regime in range(self.n_regimes):
            mask = features['regime'] == regime
            regime_data = features[mask]
            
            avg_return = regime_data['daily_return'].mean() * 252
            avg_vol = regime_data['volatility_21d'].mean()
            avg_drawdown = regime_data['drawdown_126d'].mean()
            
            # Classify regime
            if avg_return > 0.05 and avg_vol < 0.20:
                label = "BULL_STEADY"
            elif avg_return > 0.05:
                label = "BULL_VOLATILE"
            elif avg_return < -0.05:
                label = "BEAR"
            elif avg_vol > 0.25:
                label = "HIGH_VOL"
            else:
                label = "SIDEWAYS"
            
            self.regime_labels[regime] = label
            
            print(f"\nRegime {regime} ({label}):")
            print(f"  Annual Return: {avg_return:.2%}")
            print(f"  Volatility: {avg_vol:.2%}")
            print(f"  Avg Drawdown: {avg_drawdown:.2%}")
            print(f"  Days: {mask.sum()}")
    
    def predict_current_regime(self, df):
        """Predict current regime with probability distribution"""
        features = self.engineer_features(df)
        X = self.scaler.transform(features)
        
        if self.use_pca:
            X_pca = self.pca.transform(X)
            n_components = X_pca.shape[1]
            X_final = X_pca[:, :n_components]
        else:
            X_final = X
        
        # Get regime probabilities
        regime_probs = self.hmm.predict_proba(X_final)[-1]
        current_regime = self.hmm.predict(X_final)[-1]
        
        return {
            'current_regime': current_regime,
            'regime_label': self.regime_labels.get(current_regime, "UNKNOWN"),
            'probabilities': {
                self.regime_labels.get(i, f"Regime_{i}"): prob 
                for i, prob in enumerate(regime_probs)
            }
        }


# Usage example: Regime-based strategy switching
class RegimeBasedStrategy:
    """Switch strategies based on detected market regime"""
    def __init__(self):
        self.regime_detector = MarketRegimeDetector(n_regimes=3)
        
        # Different strategies for different regimes
        self.strategies = {
            "BULL_STEADY": TrendFollowingStrategy(),
            "BULL_VOLATILE": MomentumStrategy(),
            "BEAR": DefensiveStrategy(),
            "HIGH_VOL": MeanReversionStrategy(),
            "SIDEWAYS": RangeTradingStrategy()
        }
    
    def get_signal(self, data):
        regime_info = self.regime_detector.predict_current_regime(data)
        regime_label = regime_info['regime_label']
        
        # Select appropriate strategy
        strategy = self.strategies.get(regime_label, self.strategies["SIDEWAYS"])
        
        return strategy.generate_signal(data), regime_label
```

### 2.2 Clustering for Regime Detection

```python
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture

class ClusteringRegimeDetector:
    """
    Unsupervised clustering to identify market regimes.
    Alternative to HMM when you don't need temporal dynamics.
    """
    def __init__(self, method='gmm', n_clusters=4):
        self.method = method
        self.n_clusters = n_clusters
        
        if method == 'kmeans':
            self.model = KMeans(n_clusters=n_clusters, random_state=42)
        elif method == 'gmm':
            self.model = GaussianMixture(n_components=n_clusters, random_state=42)
        elif method == 'dbscan':
            self.model = DBSCAN(eps=0.5, min_samples=10)
    
    def fit(self, features):
        self.model.fit(features)
        if self.method in ['kmeans', 'gmm']:
            labels = self.model.predict(features)
        else:
            labels = self.model.labels_
        return labels
```

### 2.3 Autoencoders for Anomaly Detection

```python
import torch.nn as nn

class LSTMAutoencoder(nn.Module):
    """
    LSTM Autoencoder for anomaly detection in price series.
    Anomalies (crashes, pumps) are detected by high reconstruction error.
    """
    def __init__(self, input_dim, hidden_dim=64, num_layers=2):
        super().__init__()
        
        self.encoder = nn.LSTM(
            input_dim, hidden_dim, num_layers,
            batch_first=True
        )
        self.decoder = nn.LSTM(
            hidden_dim, input_dim, num_layers,
            batch_first=True
        )
        
    def forward(self, x):
        # Encode
        _, (hidden, _) = self.encoder(x)
        
        # Decode - repeat hidden state for each timestep
        seq_len = x.size(1)
        decoded, _ = self.decoder(hidden[-1].unsqueeze(1).repeat(1, seq_len, 1))
        
        return decoded

# Anomaly detection
def detect_anomalies(model, data, threshold_percentile=95):
    model.eval()
    with torch.no_grad():
        reconstructed = model(data)
        reconstruction_error = torch.mean((data - reconstructed) ** 2, dim=(1, 2))
    
    threshold = np.percentile(reconstruction_error.numpy(), threshold_percentile)
    anomalies = reconstruction_error > threshold
    
    return anomalies, reconstruction_error
```

---

## 3. Ensemble Methods

### Overview

Ensemble methods combine multiple models to improve robustness. XGBoost and LightGBM are particularly effective for financial prediction due to their handling of tabular data and feature importance.

### 3.1 XGBoost for Trading

**When it works best:**
- Tabular market data (features are technical indicators)
- Need for feature importance analysis
- Medium-sized datasets (10K - 1M samples)

**Implementation:**

```python
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
import numpy as np

class XGBoostTradingModel:
    """
    XGBoost for directional prediction with proper time-series CV.
    """
    def __init__(self, params=None):
        self.default_params = {
            'objective': 'binary:logistic',
            'max_depth': 6,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'min_child_weight': 5,
            'scale_pos_weight': 1,
            'random_state': 42
        }
        self.params = params or self.default_params
        self.model = None
        self.feature_importance = None
        
    def create_features(self, df):
        """
        Create technical indicator features.
        Research shows these features are most predictive:
        - RSI, MACD, Bollinger Bands
        - Price momentum at multiple horizons
        - Volume indicators
        - Volatility measures
        """
        features = pd.DataFrame(index=df.index)
        
        # Returns
        features['returns_1d'] = df['close'].pct_change()
        features['returns_5d'] = df['close'].pct_change(5)
        features['returns_20d'] = df['close'].pct_change(20)
        
        # Volatility
        features['volatility_20d'] = features['returns_1d'].rolling(20).std()
        features['volatility_ratio'] = features['volatility_20d'] / features['volatility_20d'].rolling(60).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        features['macd'] = ema_12 - ema_26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_hist'] = features['macd'] - features['macd_signal']
        
        # Bollinger Bands
        sma_20 = df['close'].rolling(20).mean()
        std_20 = df['close'].rolling(20).std()
        features['bb_upper'] = (sma_20 + 2 * std_20) / df['close'] - 1
        features['bb_lower'] = (sma_20 - 2 * std_20) / df['close'] - 1
        features['bb_position'] = (df['close'] - sma_20) / (2 * std_20)
        
        # Volume features
        if 'volume' in df.columns:
            features['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
            features['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
        
        # Price position
        features['price_position'] = (df['close'] - df['close'].rolling(50).min()) / \
                                      (df['close'].rolling(50).max() - df['close'].rolling(50).min())
        
        return features.dropna()
    
    def fit(self, X, y, validation_split=0.2):
        """
        Train XGBoost with time-series aware validation.
        """
        # Time-series split for validation
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        self.model = xgb.XGBClassifier(**self.params)
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False
        )
        
        # Store feature importance
        self.feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return self
    
    def predict_proba(self, X):
        return self.model.predict_proba(X)[:, 1]
    
    def get_feature_importance(self, top_n=10):
        return self.feature_importance.head(top_n)


# Stacking ensemble
class StackingEnsemble:
    """
    Stacking: Combine XGBoost, LightGBM, and Random Forest
    with a meta-learner (logistic regression).
    """
    def __init__(self):
        self.xgb_model = xgb.XGBClassifier(**XGBoostTradingModel().default_params)
        self.lgb_model = None  # LightGBM
        self.rf_model = None   # Random Forest
        self.meta_learner = None
        
    def fit(self, X, y):
        # Time-series cross-validation for out-of-fold predictions
        tscv = TimeSeriesSplit(n_splits=5)
        
        oof_preds = np.zeros((len(X), 3))
        
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            # Train base models
            self.xgb_model.fit(X_train, y_train)
            
            # Get OOF predictions
            oof_preds[val_idx, 0] = self.xgb_model.predict_proba(X_val)[:, 1]
            # Add other models similarly
        
        # Train meta-learner on OOF predictions
        from sklearn.linear_model import LogisticRegression
        self.meta_learner = LogisticRegression()
        self.meta_learner.fit(oof_preds, y)
        
        # Retrain base models on full data
        self.xgb_model.fit(X, y)
        
    def predict_proba(self, X):
        preds_xgb = self.xgb_model.predict_proba(X)[:, 1]
        # preds_lgb = self.lgb_model.predict_proba(X)[:, 1]
        # preds_rf = self.rf_model.predict_proba(X)[:, 1]
        
        meta_features = np.column_stack([preds_xgb])  # Add others
        return self.meta_learner.predict_proba(meta_features)[:, 1]
```

### 3.2 LightGBM (Faster Alternative)

```python
import lightgbm as lgb

class LightGBMTradingModel:
    """
    LightGBM: Faster training than XGBoost with similar performance.
    Best for larger datasets (>100K samples).
    """
    def __init__(self, params=None):
        self.params = params or {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'min_child_samples': 20
        }
        self.model = None
    
    def fit(self, X, y, validation_split=0.2):
        split_idx = int(len(X) * (1 - validation_split))
        
        train_data = lgb.Dataset(X[:split_idx], label=y[:split_idx])
        valid_data = lgb.Dataset(X[split_idx:], label=y[split_idx:], reference=train_data)
        
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=200,
            valid_sets=[valid_data],
            callbacks=[lgb.early_stopping(20), lgb.log_evaluation(0)]
        )
        return self
    
    def predict_proba(self, X):
        return self.model.predict(X, num_iteration=self.model.best_iteration)
```

### Comparison to Supervised Learning

Standard supervised learning often uses a single model (e.g., one Random Forest). Ensemble methods improve upon this by:

| Method | Improvement Over Single Model | Best Use Case |
|--------|------------------------------|---------------|
| **XGBoost** | 5-10% accuracy gain | Tabular features < 1M samples |
| **LightGBM** | Similar to XGBoost but 3x faster | Large datasets > 100K samples |
| **Stacking** | 3-5% additional gain | When base models are diverse |
| **Random Forest** | Baseline ensemble | Quick prototyping |

---

## 4. Online Learning

### Overview

Online learning updates models incrementally as new data arrives, making it ideal for adapting to market regime changes without full retraining.

### 4.1 Incremental Learning with SGD

```python
from sklearn.linear_model import SGDClassifier, PassiveAggressiveClassifier
import numpy as np

class OnlineTradingModel:
    """
    Online learning model that updates with each new bar.
    Adapts quickly to market regime changes.
    """
    def __init__(self, model_type='sgd'):
        if model_type == 'sgd':
            self.model = SGDClassifier(
                loss='log_loss',
                learning_rate='adaptive',
                eta0=0.01,
                penalty='elasticnet',
                alpha=0.0001,
                l1_ratio=0.15,
                max_iter=1,  # One pass for online learning
                warm_start=True
            )
        else:  # passive_aggressive
            self.model = PassiveAggressiveClassifier(
                C=1.0,
                max_iter=1,
                warm_start=True
            )
        
        self.is_initialized = False
        self.feature_buffer = []
        self.label_buffer = []
        self.buffer_size = 100
        
    def partial_fit(self, X, y):
        """Update model with new batch of data"""
        if not self.is_initialized:
            # Initialize with first batch
            self.model.partial_fit(X, y, classes=[0, 1])
            self.is_initialized = True
        else:
            self.model.partial_fit(X, y)
    
    def predict_proba(self, X):
        if not self.is_initialized:
            return np.ones(len(X)) * 0.5
        return self.model.predict_proba(X)[:, 1]


# Usage in trading loop
class OnlineTradingSystem:
    def __init__(self):
        self.model = OnlineTradingModel()
        self.lookback = 50
        
    def run(self, data_stream):
        """Process streaming data"""
        predictions = []
        
        for i, new_bar in enumerate(data_stream):
            if i < self.lookback:
                continue
                
            # Create features from recent history
            recent_data = data_stream[max(0, i-self.lookback):i]
            X = self.create_features(recent_data)
            
            # Make prediction
            if self.model.is_initialized:
                pred = self.model.predict_proba(X.reshape(1, -1))[0]
                predictions.append(pred)
            else:
                predictions.append(0.5)
            
            # Update model with actual outcome (after bar closes)
            if i > 0:
                actual_return = new_bar['close'] / data_stream[i-1]['close'] - 1
                y = 1 if actual_return > 0 else 0
                self.model.partial_fit(X.reshape(1, -1), [y])
        
        return predictions
```

### 4.2 Concept Drift Detection

```python
from collections import deque

class ConceptDriftDetector:
    """
    Detect when market regime changes (concept drift)
    and trigger model retraining.
    """
    def __init__(self, window_size=100, drift_threshold=0.05):
        self.window_size = window_size
        self.drift_threshold = drift_threshold
        self.reference_window = deque(maxlen=window_size)
        self.current_window = deque(maxlen=window_size)
        self.error_history = deque(maxlen=window_size)
        
    def add_prediction(self, prediction, actual):
        """Add new prediction and check for drift"""
        error = abs(prediction - actual)
        self.current_window.append(error)
        
        if len(self.reference_window) == self.window_size and \
           len(self.current_window) == self.window_size:
            
            # Kolmogorov-Smirnov test approximation
            ref_mean = np.mean(self.reference_window)
            cur_mean = np.mean(self.current_window)
            ref_std = np.std(self.reference_window)
            cur_std = np.std(self.current_window)
            
            # Detect drift
            if abs(cur_mean - ref_mean) > self.drift_threshold * ref_std:
                # Drift detected - update reference window
                self.reference_window = deque(self.current_window, maxlen=self.window_size)
                return True
        
        # Build reference window
        if len(self.reference_window) < self.window_size:
            self.reference_window.append(error)
        
        return False
```

### Comparison to Batch Learning

| Aspect | Batch Learning | Online Learning |
|--------|---------------|-----------------|
| **Update Frequency** | Daily/Weekly | Per bar |
| **Memory Usage** | Stores all data | Fixed window |
| **Adaptation Speed** | Slow | Fast |
| **Compute Cost** | High (full retrain) | Low (incremental) |
| **Stability** | High | Lower |

---

## 5. Alternative Approaches

### 5.1 Genetic Algorithms for Strategy Optimization

```python
import random
from typing import List, Dict, Callable

class TradingStrategyChromosome:
    """
    Represents a trading strategy as a chromosome for genetic algorithm.
    Genes are strategy parameters (thresholds, lookback periods, etc.)
    """
    def __init__(self, genes: Dict = None):
        # Default gene structure
        self.genes = genes or {
            'rsi_period': random.randint(5, 30),
            'rsi_overbought': random.randint(60, 85),
            'rsi_oversold': random.randint(15, 40),
            'ma_fast': random.randint(5, 20),
            'ma_slow': random.randint(20, 100),
            'stop_loss': random.uniform(0.01, 0.10),
            'take_profit': random.uniform(0.02, 0.20),
            'position_size': random.uniform(0.1, 1.0)
        }
        self.fitness = None
    
    def mutate(self, mutation_rate=0.1):
        """Randomly mutate genes"""
        for key in self.genes:
            if random.random() < mutation_rate:
                if isinstance(self.genes[key], int):
                    self.genes[key] += random.randint(-3, 3)
                    self.genes[key] = max(1, self.genes[key])
                else:
                    self.genes[key] *= random.uniform(0.9, 1.1)
    
    def crossover(self, other):
        """Single-point crossover with another chromosome"""
        child_genes = {}
        for key in self.genes:
            child_genes[key] = self.genes[key] if random.random() < 0.5 else other.genes[key]
        return TradingStrategyChromosome(child_genes)


class GeneticStrategyOptimizer:
    """
    Optimize trading strategy parameters using genetic algorithm.
    Better than grid search for high-dimensional parameter spaces.
    """
    def __init__(self, 
                 population_size=100,
                 generations=50,
                 mutation_rate=0.1,
                 elite_ratio=0.1):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_ratio = elite_ratio
        self.population = []
        
    def initialize_population(self):
        """Create random initial population"""
        self.population = [TradingStrategyChromosome() 
                          for _ in range(self.population_size)]
    
    def evaluate_fitness(self, chromosome: TradingStrategyChromosome, 
                        backtest_func: Callable) -> float:
        """
        Evaluate strategy fitness using backtest.
        Returns Sharpe ratio as fitness score.
        """
        results = backtest_func(chromosome.genes)
        sharpe = results.get('sharpe_ratio', 0)
        returns = results.get('total_return', 0)
        max_dd = results.get('max_drawdown', 1)
        
        # Multi-objective fitness
        fitness = sharpe * 0.5 + returns * 0.3 - max_dd * 0.2
        chromosome.fitness = fitness
        return fitness
    
    def select_parent(self) -> TradingStrategyChromosome:
        """Tournament selection"""
        tournament_size = 5
        tournament = random.sample(self.population, tournament_size)
        return max(tournament, key=lambda x: x.fitness or -999)
    
    def evolve(self, backtest_func: Callable):
        """Run genetic algorithm optimization"""
        self.initialize_population()
        
        for generation in range(self.generations):
            # Evaluate fitness
            for chrom in self.population:
                if chrom.fitness is None:
                    self.evaluate_fitness(chrom, backtest_func)
            
            # Sort by fitness
            self.population.sort(key=lambda x: x.fitness or -999, reverse=True)
            
            # Print best
            best = self.population[0]
            print(f"Gen {generation}: Best Fitness = {best.fitness:.4f}")
            
            # Create next generation
            new_population = []
            
            # Elitism - keep best performers
            elite_count = int(self.population_size * self.elite_ratio)
            new_population.extend(self.population[:elite_count])
            
            # Generate offspring
            while len(new_population) < self.population_size:
                parent1 = self.select_parent()
                parent2 = self.select_parent()
                
                child = parent1.crossover(parent2)
                child.mutate(self.mutation_rate)
                new_population.append(child)
            
            self.population = new_population
        
        # Return best strategy
        self.population.sort(key=lambda x: x.fitness or -999, reverse=True)
        return self.population[0]


# Example usage
def simple_backtest(genes):
    """Simple backtest function for demonstration"""
    # Implement your backtest logic here
    # Return dict with 'sharpe_ratio', 'total_return', 'max_drawdown'
    return {
        'sharpe_ratio': random.uniform(0.5, 2.0),
        'total_return': random.uniform(0.1, 0.5),
        'max_drawdown': random.uniform(0.05, 0.3)
    }

# optimizer = GeneticStrategyOptimizer()
# best_strategy = optimizer.evolve(simple_backtest)
```

### 5.2 Bayesian Optimization

```python
try:
    from bayes_opt import BayesianOptimization
except ImportError:
    print("Install: pip install bayesian-optimization")

class BayesianStrategyOptimizer:
    """
    Bayesian optimization for hyperparameter tuning.
    More efficient than grid/random search for expensive evaluations.
    """
    def __init__(self, backtest_func):
        self.backtest_func = backtest_func
        
    def objective(self, rsi_period, rsi_overbought, rsi_oversold, 
                  ma_fast, ma_slow, stop_loss, take_profit):
        """Objective function for bayesian optimization"""
        params = {
            'rsi_period': int(rsi_period),
            'rsi_overbought': int(rsi_overbought),
            'rsi_oversold': int(rsi_oversold),
            'ma_fast': int(ma_fast),
            'ma_slow': int(ma_slow),
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        
        results = self.backtest_func(params)
        
        # Return value to maximize
        return results['sharpe_ratio']
    
    def optimize(self, init_points=10, n_iter=50):
        """Run bayesian optimization"""
        pbounds = {
            'rsi_period': (5, 30),
            'rsi_overbought': (60, 85),
            'rsi_oversold': (15, 40),
            'ma_fast': (5, 20),
            'ma_slow': (20, 100),
            'stop_loss': (0.01, 0.10),
            'take_profit': (0.02, 0.20)
        }
        
        optimizer = BayesianOptimization(
            f=self.objective,
            pbounds=pbounds,
            random_state=42
        )
        
        optimizer.maximize(init_points=init_points, n_iter=n_iter)
        
        return optimizer.max
```

### 5.3 Transformer Models for Time Series

```python
import torch
import torch.nn as nn
import math

class PositionalEncoding(nn.Module):
    """Positional encoding for transformer"""
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x):
        return x + self.pe[:x.size(0)]

class TransformerTradingModel(nn.Module):
    """
    Transformer for financial time series prediction.
    Captures long-range dependencies better than LSTM.
    
    Research (FinCast) shows transformers can achieve:
    - 20% lower MSE than LSTM baselines
    - Better zero-shot performance
    """
    def __init__(self, 
                 input_dim,
                 d_model=128,
                 nhead=8,
                 num_layers=4,
                 dim_feedforward=512,
                 dropout=0.1,
                 num_classes=2):
        super().__init__()
        
        self.input_projection = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        encoder_layers = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        
        self.decoder = nn.Sequential(
            nn.Linear(d_model, dim_feedforward),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(dim_feedforward, num_classes)
        )
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        x = self.input_projection(x)
        x = self.pos_encoder(x)
        x = self.transformer_encoder(x)
        
        # Use last timestep for prediction
        x = x[:, -1, :]
        x = self.decoder(x)
        return x


# Simpler implementation using Time-Series Transformer
class TimeSeriesTransformer(nn.Module):
    """
    Time-Series Specific Transformer
    Uses patching and channel independence like PatchTST
    """
    def __init__(self, patch_size=16, d_model=128, nhead=8, num_layers=3):
        super().__init__()
        self.patch_size = patch_size
        self.patch_embedding = nn.Linear(patch_size, d_model)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, 
            dim_feedforward=512, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        
        self.head = nn.Linear(d_model, 1)
    
    def forward(self, x):
        # x: (batch, seq_len)
        batch_size = x.size(0)
        
        # Create patches
        x = x.unfold(dimension=1, size=self.patch_size, step=self.patch_size)
        # x: (batch, num_patches, patch_size)
        
        x = self.patch_embedding(x)
        x = self.encoder(x)
        
        # Global average pooling
        x = x.mean(dim=1)
        return self.head(x)
```

---

## 6. Python Libraries for Trading ML

### 6.1 Reinforcement Learning Environments

#### gym-trading-env
```python
# pip install gym-trading-env
import gym_trading_env
import gymnasium as gym

# Built-in environment
def create_trading_env():
    env = gym.make('TradingEnv-v1', 
                   name='BTCUSD',
                   df=df,  # Your price data
                   positions=[-1, 0, 1],  # Short, Hold, Long
                   trading_fees=0.01,  # 1%
                   borrow_interest_rate=0.0003)  # Per step
    return env
```

#### Custom Trading Environment
```python
import gymnasium as gym
from gymnasium import spaces
import numpy as np

class CustomTradingEnv(gym.Env):
    """
    Custom Gym environment for trading.
    Compatible with Stable-Baselines3 for RL training.
    """
    metadata = {'render_modes': ['human']}
    
    def __init__(self, df, initial_balance=10000, window_size=50):
        super().__init__()
        
        self.df = df
        self.initial_balance = initial_balance
        self.window_size = window_size
        
        # Action space: 0=HOLD, 1=BUY, 2=SELL
        self.action_space = spaces.Discrete(3)
        
        # Observation space: price history + technical indicators
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(window_size, 10),  # 10 features
            dtype=np.float32
        )
        
        self.reset()
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0  # 0 = no position, 1 = long
        self.entry_price = 0
        
        return self._get_observation(), {}
    
    def step(self, action):
        current_price = self.df['close'].iloc[self.current_step]
        
        # Execute action
        reward = 0
        if action == 1 and self.position == 0:  # BUY
            self.position = 1
            self.entry_price = current_price
        elif action == 2 and self.position == 1:  # SELL
            pnl = (current_price - self.entry_price) / self.entry_price
            reward = pnl
            self.balance *= (1 + pnl)
            self.position = 0
        
        # Holding position unrealized PnL
        if self.position == 1:
            unrealized_pnl = (current_price - self.entry_price) / self.entry_price
            reward += unrealized_pnl * 0.1  # Small reward for holding profit
        
        self.current_step += 1
        terminated = self.current_step >= len(self.df) - 1
        truncated = False
        
        obs = self._get_observation()
        info = {'balance': self.balance, 'position': self.position}
        
        return obs, reward, terminated, truncated, info
    
    def _get_observation(self):
        """Get window of recent data as observation"""
        start = max(0, self.current_step - self.window_size)
        end = self.current_step
        
        # Normalize features
        obs = self.df[['open', 'high', 'low', 'close', 'volume']].iloc[start:end]
        obs = (obs - obs.mean()) / obs.std()
        
        return obs.values.astype(np.float32)
```

### 6.2 Backtesting with ML

```python
# Using backtrader with ML
import backtrader as bt

class MLStrategy(bt.Strategy):
    """Backtrader strategy using ML predictions"""
    params = dict(model=None, threshold=0.6)
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.model = self.params.model
        self.order = None
        
    def next(self):
        if self.order:
            return
        
        # Create features from current bar
        features = self.create_features()
        
        # Get prediction
        prob_up = self.model.predict_proba(features)[0][1]
        
        if prob_up > self.params.threshold and not self.position:
            self.order = self.buy()
        elif prob_up < (1 - self.params.threshold) and self.position:
            self.order = self.sell()
    
    def create_features(self):
        # Implement feature creation
        pass

# Run backtest
def run_backtest(data, model):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MLStrategy, model=model)
    cerebro.adddata(data)
    cerebro.broker.setcash(10000.0)
    cerebro.run()
    return cerebro.broker.getvalue()
```

### 6.3 Stable Baselines3 for RL

```python
# pip install stable-baselines3[extra]
from stable_baselines3 import PPO, DQN, A2C
from stable_baselines3.common.vec_env import DummyVecEnv

def train_rl_agent(env, algorithm='PPO', total_timesteps=100000):
    """Train RL agent using Stable Baselines3"""
    
    # Vectorize environment
    vec_env = DummyVecEnv([lambda: env])
    
    # Select algorithm
    if algorithm == 'PPO':
        model = PPO('MlpPolicy', vec_env, verbose=1,
                   learning_rate=3e-4,
                   n_steps=2048,
                   batch_size=64,
                   n_epochs=10,
                   gamma=0.99)
    elif algorithm == 'DQN':
        model = DQN('MlpPolicy', vec_env, verbose=1,
                   learning_rate=1e-4,
                   buffer_size=100000,
                   learning_starts=1000,
                   batch_size=64,
                   gamma=0.99,
                   target_update_interval=1000)
    elif algorithm == 'A2C':
        model = A2C('MlpPolicy', vec_env, verbose=1,
                   learning_rate=7e-4,
                   n_steps=5,
                   gamma=0.99)
    
    # Train
    model.learn(total_timesteps=total_timesteps)
    
    return model
```

### 6.4 MLFinLab

```python
# pip install mlfinlab
try:
    import mlfinlab as mlf
    from mlfinlab.feature_importance import mdi_feature_importance
    from mlfinlab.cross_validation import PurgedKFold, embargo
    
    def mlfinlab_example():
        # Purged cross-validation (prevents data leakage)
        cv = PurgedKFold(n_splits=5, samples_info_sets=triple_barrier_events)
        
        # Feature importance with mean decrease impurity
        importance = mdi_feature_importance(
            model=rf_model,
            X=X_test,
            y=y_test
        )
        
        # Sample weights (address class imbalance)
        sample_weights = mlf.sample_weights.get_weights_by_return(
            triple_barrier_events.loc[X_train.index],
            X_train['close'],
            num_threads=1
        )
        
except ImportError:
    print("mlfinlab requires separate installation")
```

---

## 7. Recommendations: Which to Try First

### Immediate Implementation (Week 1-2)

**1. Ensemble Methods (XGBoost/LightGBM)**
```
WHY: Drop-in replacement for existing models
RISK: Low
EFFORT: 1 week
POTENTIAL IMPROVEMENT: 5-15% over single models
```

Action items:
- Replace current classifier with XGBoost
- Add feature importance analysis
- Implement time-series cross-validation

**2. HMM for Regime Detection**
```
WHY: Identifies when your current model is likely to fail
RISK: Low
EFFORT: 1 week
POTENTIAL IMPROVEMENT: 20-30% by switching strategies by regime
```

Action items:
- Train HMM on market data (returns + volatility)
- Identify 3 regimes (bull/bear/sideways)
- Build strategy switcher based on regime

### Medium-term Implementation (Week 3-4)

**3. Online Learning**
```
WHY: Adapts to market changes without retraining
RISK: Medium
EFFORT: 2 weeks
POTENTIAL IMPROVEMENT: Maintains performance during regime changes
```

**4. Genetic Algorithm for Strategy Optimization**
```
WHY: Optimizes parameters better than grid search
RISK: Medium
EFFORT: 2 weeks
POTENTIAL IMPROVEMENT: 10-20% from better parameters
```

### Advanced Implementation (Month 2+)

**5. Reinforcement Learning**
```
WHY: Learns optimal sequential decisions
RISK: High
EFFORT: 4+ weeks
POTENTIAL IMPROVEMENT: 30-50% if done correctly
```

**6. Transformers**
```
WHY: Captures long-range dependencies
RISK: High
EFFORT: 4+ weeks
POTENTIAL IMPROVEMENT: 10-20% for long-term predictions
```

---

## 8. Implementation Priority Matrix

| Approach | Impact | Effort | Risk | Priority |
|----------|--------|--------|------|----------|
| XGBoost Ensemble | High | Low | Low | **1 - Start Here** |
| HMM Regime Detection | High | Low | Low | **2** |
| Online Learning | Medium | Medium | Medium | **3** |
| Genetic Algorithms | Medium | Medium | Medium | **4** |
| Bayesian Optimization | Medium | Low | Low | **5** |
| Reinforcement Learning | Very High | High | High | **6** |
| Transformers | Medium | High | High | **7** |

---

## 9. Key Takeaways

1. **Start Simple:** XGBoost with HMM regime detection gives you 80% of the benefit with 20% of the effort

2. **Combine Approaches:** Use HMM to detect regime, then apply different models for each regime

3. **Risk Management:** All ML approaches will fail sometimes - position sizing and stop-losses are still critical

4. **Data Quality:** These methods amplify data quality issues - clean your data first

5. **Backtesting:** Use proper time-series CV and out-of-sample testing for all approaches

---

## References

1. Liu, X-Y. et al. (2020). "FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading"
2. Theate, T. & Ernst, D. (2021). "An Application of Deep Reinforcement Learning to Algorithmic Trading"
3. FinCast: Foundation Model for Financial Time-Series Forecasting (2025)
4. Borst, D. "Detecting Market Regimes with Hidden Markov Models"
5. Kim, D. et al. (2019). "Regime-Switching Factor Investing with Hidden Markov Models"
6. XGBoost/LightGBM Documentation and Financial Applications

---

*Document generated for findtorontoevents.ca trading systems research*
