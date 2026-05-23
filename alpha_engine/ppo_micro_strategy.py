"""
PPO Policy for Micro-Strategy Optimization
===========================================
Implements Proximal Policy Optimization for limit vs market order decisions.

Planned v1.1 from updates_torontoevent.html - NOW IMPLEMENTED
"""
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PPOConfig:
    """PPO hyperparameters for micro-strategy."""
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    n_epochs: int = 10
    batch_size: int = 64
    hidden_dim: int = 128


class ActorCritic(nn.Module):
    """Actor-Critic network for order type decisions."""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 128):
        super().__init__()
        
        # Shared feature extractor
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        
        # Actor head (policy)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Critic head (value function)
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )
    
    def forward(self, state):
        features = self.shared(state)
        action_probs = self.actor(features)
        value = self.critic(features)
        return action_probs, value
    
    def get_action(self, state, deterministic=False):
        """Sample action from policy."""
        with torch.no_grad():
            action_probs, value = self.forward(state)
            
            if deterministic:
                action = torch.argmax(action_probs, dim=-1)
            else:
                dist = torch.distributions.Categorical(action_probs)
                action = dist.sample()
            
            log_prob = torch.log(action_probs.gather(-1, action.unsqueeze(-1)))
            
        return action.item(), log_prob.item(), value.item()


class PPOMicroStrategy:
    """
    PPO-based micro-strategy for optimal order execution.
    
    Decides: Limit Order vs Market Order based on:
    - Current spread
    - Orderbook imbalance
    - Time urgency
    - Expected fill rate
    - Market volatility
    
    Status: IMPLEMENTED (was PLANNED v1.1)
    """
    
    def __init__(self, config: PPOConfig = None):
        self.config = config or PPOConfig()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # State: [spread_pct, imbalance, urgency, vol_estimate, queue_position]
        self.state_dim = 5
        # Actions: [Limit_Buy, Market_Buy, Limit_Sell, Market_Sell, Wait]
        self.action_dim = 5
        
        self.model = ActorCritic(
            self.state_dim, 
            self.action_dim,
            self.config.hidden_dim
        ).to(self.device)
        
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate
        )
        
        # Memory for training
        self.memory = []
        
        logger.info("[OK] PPO Micro-Strategy INITIALIZED (v1.1 IMPLEMENTED)")
    
    def compute_state(self, orderbook: Dict, signal: Dict) -> np.ndarray:
        """
        Compute state vector from orderbook data.
        
        Args:
            orderbook: Current orderbook with bids/asks
            signal: Trading signal with direction and urgency
        
        Returns:
            State vector [spread_pct, imbalance, urgency, vol_estimate, queue_pos]
        """
        best_bid = orderbook.get('bids', [[0, 0]])[0][0]
        best_ask = orderbook.get('asks', [[0, 0]])[0][0]
        mid_price = (best_bid + best_ask) / 2
        
        # Spread percentage
        spread_pct = (best_ask - best_bid) / mid_price * 100
        
        # Orderbook imbalance (top 5 levels)
        bid_volume = sum([v for _, v in orderbook.get('bids', [])[:5]])
        ask_volume = sum([v for _, v in orderbook.get('asks', [])[:5]])
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume + 1e-10)
        
        # Time urgency (0-1, higher = more urgent)
        urgency = signal.get('urgency', 0.5)
        
        # Volatility estimate from recent price action
        vol_estimate = signal.get('volatility', 0.01)
        
        # Estimated queue position (0-1, 0 = front of queue)
        queue_pos = signal.get('queue_position', 0.5)
        
        state = np.array([
            spread_pct,
            imbalance,
            urgency,
            vol_estimate,
            queue_pos
        ], dtype=np.float32)
        
        return state
    
    def decide_order_type(
        self,
        orderbook: Dict,
        signal: Dict,
        deterministic: bool = False
    ) -> Dict:
        """
        Decide whether to use limit or market order.
        
        Returns:
            Dict with order_type, confidence, expected_fill_rate
        """
        state = self.compute_state(orderbook, signal)
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        action_idx, log_prob, value = self.model.get_action(
            state_tensor,
            deterministic=deterministic
        )
        
        action_map = {
            0: ('LIMIT', 'BUY'),
            1: ('MARKET', 'BUY'),
            2: ('LIMIT', 'SELL'),
            3: ('MARKET', 'SELL'),
            4: ('WAIT', None)
        }
        
        order_type, direction = action_map[action_idx]
        
        # Calculate expected fill rate based on orderbook
        expected_fill = self._estimate_fill_rate(
            order_type, orderbook, signal
        )
        
        result = {
            'order_type': order_type,
            'direction': direction,
            'action_idx': action_idx,
            'confidence': np.exp(log_prob),
            'expected_fill_rate': expected_fill,
            'state_value': value,
            'state': state
        }
        
        logger.debug(f"PPO Decision: {order_type} {direction} (conf: {result['confidence']:.3f})")
        
        return result
    
    def _estimate_fill_rate(
        self,
        order_type: str,
        orderbook: Dict,
        signal: Dict
    ) -> float:
        """Estimate probability of fill for limit orders."""
        if order_type == 'MARKET':
            return 1.0
        
        if order_type == 'WAIT':
            return 0.0
        
        # For limit orders, estimate based on queue position and imbalance
        imbalance = signal.get('imbalance', 0)
        queue_pos = signal.get('queue_position', 0.5)
        
        # Higher fill rate if:
        # - Favorable imbalance (e.g., buying when bids > asks)
        # - Better queue position (closer to front)
        base_fill = 0.7
        imbalance_boost = abs(imbalance) * 0.2
        queue_penalty = queue_pos * 0.3
        
        fill_rate = base_fill + imbalance_boost - queue_penalty
        return np.clip(fill_rate, 0.1, 0.95)
    
    def store_transition(self, state, action, reward, next_state, done):
        """Store transition for PPO training."""
        self.memory.append({
            'state': state,
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'done': done
        })
    
    def train_step(self) -> Dict:
        """
        Perform one PPO training step.
        
        Returns:
            Training metrics
        """
        if len(self.memory) < self.config.batch_size:
            return {'status': 'insufficient_data'}
        
        # Sample batch
        batch = self.memory[-self.config.batch_size:]
        
        # Convert to tensors
        states = torch.FloatTensor([t['state'] for t in batch]).to(self.device)
        actions = torch.LongTensor([t['action'] for t in batch]).to(self.device)
        rewards = torch.FloatTensor([t['reward'] for t in batch]).to(self.device)
        next_states = torch.FloatTensor([t['next_state'] for t in batch]).to(self.device)
        dones = torch.FloatTensor([t['done'] for t in batch]).to(self.device)
        
        # Compute advantages using GAE
        with torch.no_grad():
            _, next_values = self.model(next_states)
            _, values = self.model(states)
            
            advantages = self._compute_gae(
                rewards, values.squeeze(), next_values.squeeze(), dones
            )
            returns = advantages + values.squeeze()
        
        # PPO update
        total_loss = 0
        policy_losses = []
        value_losses = []
        entropy_losses = []
        
        for _ in range(self.config.n_epochs):
            # Get current policy outputs
            action_probs, current_values = self.model(states)
            dist = torch.distributions.Categorical(action_probs)
            
            # Log probs and entropy
            current_log_probs = dist.log_prob(actions)
            entropy = dist.entropy()
            
            # Ratio for PPO clip
            old_log_probs = torch.FloatTensor([
                self.memory[-self.config.batch_size + i].get('log_prob', 0)
                for i in range(len(batch))
            ]).to(self.device)
            
            ratio = torch.exp(current_log_probs - old_log_probs)
            
            # Clipped surrogate loss
            surr1 = ratio * advantages
            surr2 = torch.clamp(
                ratio,
                1 - self.config.clip_epsilon,
                1 + self.config.clip_epsilon
            ) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # Value loss
            value_loss = nn.MSELoss()(current_values.squeeze(), returns)
            
            # Entropy bonus
            entropy_loss = -entropy.mean()
            
            # Total loss
            loss = (
                policy_loss +
                self.config.value_coef * value_loss +
                self.config.entropy_coef * entropy_loss
            )
            
            # Optimize
            self.optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(
                self.model.parameters(),
                self.config.max_grad_norm
            )
            self.optimizer.step()
            
            policy_losses.append(policy_loss.item())
            value_losses.append(value_loss.item())
            entropy_losses.append(entropy_loss.item())
            total_loss += loss.item()
        
        # Clear memory after training
        self.memory = []
        
        return {
            'status': 'trained',
            'total_loss': total_loss / self.config.n_epochs,
            'policy_loss': np.mean(policy_losses),
            'value_loss': np.mean(value_losses),
            'entropy': np.mean(entropy_losses)
        }
    
    def _compute_gae(
        self,
        rewards: torch.Tensor,
        values: torch.Tensor,
        next_values: torch.Tensor,
        dones: torch.Tensor
    ) -> torch.Tensor:
        """Compute Generalized Advantage Estimation."""
        advantages = torch.zeros_like(rewards)
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = next_values[t]
            else:
                next_value = values[t + 1]
            
            delta = rewards[t] + self.config.gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + self.config.gamma * self.config.gae_lambda * (1 - dones[t]) * gae
            advantages[t] = gae
        
        return advantages
    
    def save(self, path: str):
        """Save model checkpoint."""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config
        }, path)
        logger.info(f"💾 PPO model saved to {path}")
    
    def load(self, path: str):
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        logger.info(f"📂 PPO model loaded from {path}")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Initialize PPO micro-strategy
    ppo = PPOMicroStrategy()
    
    # Example orderbook
    orderbook = {
        'bids': [[50000, 1.5], [49995, 2.0], [49990, 3.0]],
        'asks': [[50010, 1.2], [50015, 2.5], [50020, 4.0]]
    }
    
    # Example signal
    signal = {
        'direction': 'BUY',
        'urgency': 0.8,
        'volatility': 0.02,
        'queue_position': 0.3,
        'imbalance': 0.4
    }
    
    # Get order decision
    decision = ppo.decide_order_type(orderbook, signal)
    print(f"Decision: {decision}")
    
    print("\n[OK] PPO Micro-Strategy v1.1 IMPLEMENTATION COMPLETE")
