"""
PPO Agent for Crypto Trading
================================
Simple PPO implementation using only numpy (no PyTorch/TF dependency).

This is a PROTOTYPE for experimentation. Uses a simple policy network
(2-layer MLP with softmax output).

For production, replace with stable-baselines3 or cleanrl.
"""

import numpy as np
from typing import List, Tuple


class SimplePPOAgent:
    """
    Minimal PPO agent with numpy-only implementation.

    Architecture: 2-layer MLP with tanh activation.
    Policy: softmax over 3 actions (HOLD, BUY, SELL)
    Value: single output for state value estimation
    """

    def __init__(
        self,
        obs_dim: int = 6,
        n_actions: int = 3,
        hidden_dim: int = 32,
        lr: float = 3e-4,
        gamma: float = 0.99,
        clip_ratio: float = 0.2,
        value_coeff: float = 0.5,
        entropy_coeff: float = 0.01,
    ):
        self.obs_dim = obs_dim
        self.n_actions = n_actions
        self.hidden_dim = hidden_dim
        self.lr = lr
        self.gamma = gamma
        self.clip_ratio = clip_ratio
        self.value_coeff = value_coeff
        self.entropy_coeff = entropy_coeff

        # Initialize weights (Xavier init)
        scale1 = np.sqrt(2.0 / (obs_dim + hidden_dim))
        scale2 = np.sqrt(2.0 / (hidden_dim + hidden_dim))

        # Policy network
        self.w1 = np.random.randn(obs_dim, hidden_dim) * scale1
        self.b1 = np.zeros(hidden_dim)
        self.w2 = np.random.randn(hidden_dim, hidden_dim) * scale2
        self.b2 = np.zeros(hidden_dim)
        self.w_policy = np.random.randn(hidden_dim, n_actions) * 0.01
        self.b_policy = np.zeros(n_actions)

        # Value network (shares first layer)
        self.w_value = np.random.randn(hidden_dim, 1) * 0.01
        self.b_value = np.zeros(1)

    def _forward(self, obs: np.ndarray) -> Tuple[np.ndarray, float]:
        """Forward pass returning (action_probs, value)."""
        # Layer 1
        h1 = np.tanh(obs @ self.w1 + self.b1)
        # Layer 2
        h2 = np.tanh(h1 @ self.w2 + self.b2)

        # Policy head
        logits = h2 @ self.w_policy + self.b_policy
        logits = logits - logits.max()  # numerical stability
        probs = np.exp(logits) / np.exp(logits).sum()

        # Value head
        value = float((h2 @ self.w_value + self.b_value)[0])

        return probs, value

    def act(self, obs: np.ndarray) -> Tuple[int, float, float]:
        """Select action from policy.

        Returns: (action, log_prob, value)
        """
        probs, value = self._forward(obs)
        action = np.random.choice(self.n_actions, p=probs)
        log_prob = np.log(probs[action] + 1e-10)
        return action, log_prob, value

    def _compute_returns(self, rewards: List[float], values: List[float], dones: List[bool]) -> np.ndarray:
        """Compute GAE (Generalized Advantage Estimation) returns."""
        n = len(rewards)
        returns = np.zeros(n)
        gae = 0.0
        lam = 0.95  # GAE lambda

        for t in reversed(range(n)):
            if t == n - 1:
                next_value = 0.0
            else:
                next_value = values[t + 1]

            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * lam * (1 - dones[t]) * gae
            returns[t] = gae + values[t]

        return returns

    def update(
        self,
        observations: List[np.ndarray],
        actions: List[int],
        rewards: List[float],
        log_probs: List[float],
        values: List[float],
        dones: List[bool],
        n_epochs: int = 4,
    ):
        """PPO update step."""
        returns = self._compute_returns(rewards, values, dones)
        advantages = returns - np.array(values)
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        old_log_probs = np.array(log_probs)

        for _ in range(n_epochs):
            for i in range(len(observations)):
                obs = observations[i]
                action = actions[i]

                probs, value = self._forward(obs)
                new_log_prob = np.log(probs[action] + 1e-10)

                # PPO clipped objective
                ratio = np.exp(new_log_prob - old_log_probs[i])
                clipped = np.clip(ratio, 1 - self.clip_ratio, 1 + self.clip_ratio)
                policy_loss = -min(ratio * advantages[i], clipped * advantages[i])

                # Value loss
                value_loss = 0.5 * (returns[i] - value) ** 2

                # Entropy bonus
                entropy = -np.sum(probs * np.log(probs + 1e-10))

                # Total loss gradient approximation (numerical gradient)
                total_loss = policy_loss + self.value_coeff * value_loss - self.entropy_coeff * entropy

                # Simple gradient step on policy head
                # (Full backprop would need autograd — this is a simplified version)
                grad_direction = np.zeros(self.n_actions)
                grad_direction[action] = advantages[i] * (1 if ratio > 0 else -1)

                # Update policy weights
                h1 = np.tanh(obs @ self.w1 + self.b1)
                h2 = np.tanh(h1 @ self.w2 + self.b2)

                self.w_policy += self.lr * np.outer(h2, grad_direction)
                self.b_policy += self.lr * grad_direction

                # Update value weights
                value_grad = (returns[i] - value)
                self.w_value += self.lr * self.value_coeff * h2.reshape(-1, 1) * value_grad
                self.b_value += self.lr * self.value_coeff * value_grad

    def save(self, path: str):
        """Save agent weights."""
        np.savez(path,
                 w1=self.w1, b1=self.b1, w2=self.w2, b2=self.b2,
                 w_policy=self.w_policy, b_policy=self.b_policy,
                 w_value=self.w_value, b_value=self.b_value)

    def load(self, path: str):
        """Load agent weights."""
        data = np.load(path)
        self.w1, self.b1 = data["w1"], data["b1"]
        self.w2, self.b2 = data["w2"], data["b2"]
        self.w_policy, self.b_policy = data["w_policy"], data["b_policy"]
        self.w_value, self.b_value = data["w_value"], data["b_value"]
