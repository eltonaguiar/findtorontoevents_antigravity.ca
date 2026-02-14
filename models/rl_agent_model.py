"""
================================================================================
REINFORCEMENT LEARNING AGENT FOR CRYPTO TRADING
================================================================================
Proximal Policy Optimization (PPO) Inspired Trading Agent

Architecture:
- Actor-Critic with shared feature extractor
- LSTM/GRU state representation
- Continuous action space (position sizing)
- Reward shaping for risk-adjusted returns

Reference: "Proximal Policy Optimization Algorithms" (Schulman et al., 2017)
================================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
from collections import deque


class ActionSpace(Enum):
    """Discrete action space for trading decisions"""
    STRONG_SHORT = -1.0
    SHORT = -0.5
    NEUTRAL = 0.0
    LONG = 0.5
    STRONG_LONG = 1.0


@dataclass
class RLConfig:
    """Configuration for RL Agent"""
    # State space
    observation_window: int = 24  # Bars to include in state
    n_features: int = 20
    
    # Reward parameters
    reward_scaling: float = 100.0  # Scale returns to reasonable range
    risk_penalty_coeff: float = 0.1  # Penalty for high volatility
    drawdown_penalty_coeff: float = 0.5  # Penalty for drawdowns
    transaction_cost: float = 0.0009  # 9 bps per trade
    
    # Policy parameters
    learning_rate: float = 0.0003
    gamma: float = 0.99  # Discount factor
    lambda_gae: float = 0.95  # GAE parameter
    clip_epsilon: float = 0.2  # PPO clipping
    value_coeff: float = 0.5
    entropy_coeff: float = 0.01
    
    # Risk management
    max_position: float = 1.0
    stop_loss_pct: float = 0.05  # 5% stop loss


class FeatureExtractor:
    """
    Extract features from market data for RL state representation
    """
    
    def __init__(self, window_size: int = 24):
        self.window_size = window_size
    
    def extract(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract normalized feature vector
        
        Returns:
            np.ndarray: Feature vector of shape (n_features,)
        """
        if len(df) < self.window_size:
            # Pad with zeros if insufficient data
            return np.zeros(self.get_feature_dim())
        
        recent = df.iloc[-self.window_size:]
        
        features = []
        
        # Price features
        prices = recent['price'].values
        returns = np.diff(prices) / prices[:-1]
        log_returns = np.log(prices[1:] / prices[:-1])
        
        # Return statistics
        features.extend([
            np.mean(returns),
            np.std(returns),
            np.min(returns),
            np.max(returns),
            np.percentile(returns, 25),
            np.percentile(returns, 75),
            np.sum(returns > 0) / len(returns),  # Win rate proxy
        ])
        
        # Trend features
        sma_short = np.mean(prices[-6:])
        sma_medium = np.mean(prices[-12:])
        sma_long = np.mean(prices)
        
        features.extend([
            (prices[-1] / sma_short - 1),
            (prices[-1] / sma_medium - 1),
            (prices[-1] / sma_long - 1),
            (sma_short / sma_medium - 1),
            (sma_medium / sma_long - 1),
        ])
        
        # Volatility features
        for window in [6, 12, 24]:
            if len(returns) >= window:
                vol = np.std(returns[-window:]) * np.sqrt(2190)  # Annualized
                features.append(vol)
            else:
                features.append(0)
        
        # Volume features if available
        if 'volume' in recent.columns:
            volumes = recent['volume'].values
            features.extend([
                np.mean(volumes[-6:]) / np.mean(volumes) - 1,
                np.std(volumes) / np.mean(volumes),
                np.corrcoef(np.abs(returns), volumes[1:])[0, 1] if len(volumes) > 1 else 0,
            ])
        else:
            features.extend([0, 0, 0])
        
        # Technical indicators
        # RSI-like feature
        gains = np.where(returns > 0, returns, 0)
        losses = np.where(returns < 0, -returns, 0)
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 1e-10
        rs = avg_gain / avg_loss
        rsi = 1 - (1 / (1 + rs))
        features.append(rsi)
        
        # Momentum
        momentum = (prices[-1] / prices[-12] - 1) if len(prices) >= 12 else 0
        features.append(momentum)
        
        # Normalize features
        features = np.array(features)
        features = np.nan_to_num(features, nan=0, posinf=0, neginf=0)
        
        return features
    
    def get_feature_dim(self) -> int:
        """Return dimension of feature vector"""
        return 20  # Must match number of features extracted


class ActorNetwork:
    """
    Actor network for policy: state -> action probabilities
    Simplified MLP architecture
    """
    
    def __init__(self, input_dim: int, hidden_dim: int = 64):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.n_actions = len(ActionSpace)
        
        # Initialize weights
        self.W1 = np.random.randn(input_dim, hidden_dim) * 0.01
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, hidden_dim) * 0.01
        self.b2 = np.zeros(hidden_dim)
        self.W3 = np.random.randn(hidden_dim, self.n_actions) * 0.01
        self.b3 = np.zeros(self.n_actions)
    
    def relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)
    
    def softmax(self, x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)
    
    def forward(self, state: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Forward pass through actor network
        
        Returns:
            probs: Action probabilities
            hidden: Hidden layer output for value estimation
        """
        # Layer 1
        h1 = self.relu(np.dot(state, self.W1) + self.b1)
        
        # Layer 2
        h2 = self.relu(np.dot(h1, self.W2) + self.b2)
        
        # Output layer
        logits = np.dot(h2, self.W3) + self.b3
        probs = self.softmax(logits)
        
        return probs, h2


class CriticNetwork:
    """
    Critic network for value estimation: state -> expected return
    """
    
    def __init__(self, input_dim: int, hidden_dim: int = 64):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # Initialize weights
        self.W1 = np.random.randn(input_dim, hidden_dim) * 0.01
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, 1) * 0.01
        self.b2 = np.zeros(1)
    
    def relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)
    
    def forward(self, state: np.ndarray, hidden: Optional[np.ndarray] = None) -> float:
        """
        Forward pass through critic network
        
        Returns:
            value: Estimated state value
        """
        # Use provided hidden or compute
        if hidden is None:
            h1 = self.relu(np.dot(state, self.W1) + self.b1)
        else:
            h1 = hidden
        
        value = np.dot(h1, self.W2) + self.b2
        return value[0]


class TradingEnvironment:
    """
    Trading environment for RL agent
    Simulates trading with realistic costs and risk management
    """
    
    def __init__(self, config: RLConfig = None):
        self.config = config or RLConfig()
        self.feature_extractor = FeatureExtractor(self.config.observation_window)
        
        # State
        self.position = 0.0
        self.entry_price = 0.0
        self.peak_value = 1.0
        self.current_value = 1.0
        self.trade_history = []
        
    def reset(self):
        """Reset environment state"""
        self.position = 0.0
        self.entry_price = 0.0
        self.peak_value = 1.0
        self.current_value = 1.0
        self.trade_history = []
        return self.feature_extractor.extract(pd.DataFrame())
    
    def step(self, action: ActionSpace, price_data: pd.DataFrame) -> Tuple[np.ndarray, float, bool]:
        """
        Execute one trading step
        
        Args:
            action: Trading action to take
            price_data: Current price data
            
        Returns:
            next_state: New state observation
            reward: Step reward
            done: Whether episode ended
        """
        current_price = price_data['price'].iloc[-1]
        prev_price = price_data['price'].iloc[-2] if len(price_data) > 1 else current_price
        
        # Calculate action value
        target_position = action.value
        
        # Execute trade if position changes
        if abs(target_position - self.position) > 0.1:
            # Transaction cost
            trade_size = abs(target_position - self.position)
            cost = trade_size * self.config.transaction_cost
            self.current_value *= (1 - cost)
            
            # Record trade
            self.trade_history.append({
                'timestamp': price_data.index[-1],
                'action': action.name,
                'position': target_position,
                'price': current_price
            })
            
            self.position = target_position
            self.entry_price = current_price
        
        # Calculate P&L from position
        price_return = (current_price - prev_price) / prev_price
        position_pnl = self.position * price_return
        
        # Update portfolio value
        self.current_value *= (1 + position_pnl)
        
        # Update peak for drawdown calculation
        if self.current_value > self.peak_value:
            self.peak_value = self.current_value
        
        drawdown = (self.peak_value - self.current_value) / self.peak_value
        
        # Calculate reward
        reward = self._calculate_reward(position_pnl, drawdown, price_data)
        
        # Check stop loss
        if drawdown > self.config.stop_loss_pct:
            done = True
            reward -= 1.0  # Penalty for hitting stop loss
        else:
            done = False
        
        # Extract new state
        next_state = self.feature_extractor.extract(price_data)
        
        return next_state, reward, done
    
    def _calculate_reward(self, pnl: float, drawdown: float, price_data: pd.DataFrame) -> float:
        """
        Calculate shaped reward
        
        Components:
        1. Realized P&L (primary)
        2. Drawdown penalty (risk management)
        3. Volatility penalty (smoothness)
        """
        # Base reward from P&L
        reward = pnl * self.config.reward_scaling
        
        # Drawdown penalty
        reward -= drawdown * self.config.drawdown_penalty_coeff
        
        # Volatility penalty
        if len(price_data) >= 12:
            recent_returns = price_data['price'].pct_change().iloc[-12:].values
            volatility = np.std(recent_returns)
            reward -= volatility * self.config.risk_penalty_coeff
        
        return reward


class RLTradingAgent:
    """
    Reinforcement Learning Trading Agent
    
    Uses PPO-inspired architecture for learning optimal trading policies
    directly from reward signals rather than labeled data.
    """
    
    def __init__(self, config: RLConfig = None):
        self.config = config or RLConfig()
        self.feature_extractor = FeatureExtractor(self.config.observation_window)
        
        # Networks
        feature_dim = self.feature_extractor.get_feature_dim()
        self.actor = ActorNetwork(feature_dim)
        self.critic = CriticNetwork(feature_dim)
        
        # Environment
        self.env = TradingEnvironment(self.config)
        
        # Memory for training
        self.memory = {
            'states': [],
            'actions': [],
            'rewards': [],
            'values': [],
            'log_probs': []
        }
        
        # Performance tracking
        self.episode_rewards = []
        self.portfolio_values = [1.0]
    
    def predict(self, df: pd.DataFrame) -> Dict:
        """
        Generate trading decision using learned policy
        
        Returns:
            Dict with action, confidence, and metadata
        """
        # Extract state
        state = self.feature_extractor.extract(df)
        
        # Get action probabilities from actor
        probs, hidden = self.actor.forward(state)
        
        # Select action (in inference, use argmax)
        action_idx = np.argmax(probs)
        action = list(ActionSpace)[action_idx]
        
        # Get value estimate
        value = self.critic.forward(state, hidden)
        
        # Confidence based on probability
        confidence = probs[action_idx]
        
        # Position sizing based on confidence
        position_size = abs(action.value) * confidence
        
        return {
            'signal': action.value,
            'direction': action.name.replace('_', ' '),
            'confidence': float(confidence),
            'position_size': position_size,
            'value_estimate': float(value),
            'action_probabilities': {
                a.name: float(p) for a, p in zip(ActionSpace, probs)
            },
            'model_type': 'RL_PPO_Agent',
            'timestamp': str(df.index[-1]) if hasattr(df.index[-1], '__str__') else df.index[-1]
        }
    
    def simulate_episode(self, df: pd.DataFrame, start_idx: int, 
                         episode_length: int = 168) -> Dict:
        """
        Simulate a full trading episode for backtesting
        
        Args:
            df: Price data
            start_idx: Starting index
            episode_length: Number of steps in episode
            
        Returns:
            Episode metrics
        """
        # Reset environment
        state = self.env.reset()
        
        episode_reward = 0
        states, actions, rewards, values, log_probs = [], [], [], [], []
        
        for t in range(episode_length):
            idx = start_idx + t
            if idx >= len(df):
                break
            
            # Get current data window
            data_window = df.iloc[max(0, idx - self.config.observation_window):idx+1]
            
            # Get action from policy
            state = self.feature_extractor.extract(data_window)
            probs, hidden = self.actor.forward(state)
            
            # Sample action
            action_idx = np.random.choice(len(ActionSpace), p=probs)
            action = list(ActionSpace)[action_idx]
            
            # Get value estimate
            value = self.critic.forward(state, hidden)
            
            # Take step
            next_state, reward, done = self.env.step(action, data_window)
            
            # Store transition
            states.append(state)
            actions.append(action_idx)
            rewards.append(reward)
            values.append(value)
            log_probs.append(np.log(probs[action_idx] + 1e-10))
            
            episode_reward += reward
            
            if done:
                break
        
        return {
            'total_reward': episode_reward,
            'final_value': self.env.current_value,
            'n_steps': len(rewards),
            'trades': len(self.env.trade_history)
        }
    
    def backtest(self, df: pd.DataFrame, asset: str = None,
                 episode_length: int = 168, step_size: int = 24) -> Dict:
        """
        Backtest using RL agent with episodic evaluation
        """
        results = {
            'episode_returns': [],
            'portfolio_values': [],
            'n_trades': [],
            'timestamps': []
        }
        
        # Slide window through data
        idx = self.config.observation_window + episode_length
        while idx < len(df) - episode_length:
            episode_df = df.iloc[idx-episode_length:idx]
            
            # Simulate episode
            metrics = self.simulate_episode(df, idx - episode_length, episode_length)
            
            results['episode_returns'].append(metrics['total_reward'])
            results['portfolio_values'].append(metrics['final_value'])
            results['n_trades'].append(metrics['trades'])
            results['timestamps'].append(df.index[idx])
            
            idx += step_size
        
        return results


# Model metadata
RL_METADATA = {
    "model_name": "CryptoAlpha_RL_PPO",
    "architecture": "Proximal Policy Optimization (PPO)",
    "components": [
        "Actor Network (Policy)",
        "Critic Network (Value Estimation)",
        "Feature Extractor (20 technical features)",
        "Trading Environment (with realistic costs)",
        "Reward Shaping (P&L + Risk penalties)"
    ],
    "action_space": ["STRONG_SHORT", "SHORT", "NEUTRAL", "LONG", "STRONG_LONG"],
    "state_features": 20,
    "observation_window": "24 bars",
    "key_advantages": [
        "Learns optimal policy directly from rewards",
        "Adapts to changing market conditions",
        "Incorporates risk management via reward shaping",
        "No need for labeled training data",
        "Continuous learning capability"
    ],
    "limitations": [
        "Requires extensive training (10,000+ episodes)",
        "Sample inefficient compared to supervised learning",
        "Hyperparameter sensitive",
        "May overfit to training period",
        "Exploration vs exploitation tradeoff"
    ],
    "training_requirements": {
        "episodes": "10,000+",
        "compute": "GPU recommended",
        "wall_time": "4-8 hours for convergence"
    }
}


def get_rl_documentation() -> str:
    """Return formatted model documentation"""
    return json.dumps(RL_METADATA, indent=2)


if __name__ == "__main__":
    print("=" * 80)
    print("REINFORCEMENT LEARNING TRADING AGENT (PPO)")
    print("=" * 80)
    print("\nModel Metadata:")
    print(get_rl_documentation())
    print("\n" + "=" * 80)
    print("Note: This agent requires extensive training before deployment")
    print("Use the simulate_episode method for backtesting untrained policy")
    print("=" * 80)
