"""
RL Market-Making Agent with Deep Q-Learning
=============================================
A DQN agent that learns optimal spread placement and inventory control
for market-making. Profits from bid-ask spreads rather than directional
price prediction.

State: [mid_price_return, spread_bps, inventory_level, volatility, order_imbalance, pnl]
Actions: 5 discrete spread strategies (tight/normal/wide/skew-bid/skew-ask)
Reward: realized PnL from spread capture - inventory penalty

Dependencies: numpy only. Runs on GitHub Actions Python 3.11.

This is a PROTOTYPE for experimentation. Not connected to live trading.
"""

import numpy as np
import json
import logging
import os
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
DATA_DIR = Path(__file__).parent / "data"
MM_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class MarketMakingEnv:
    """
    Market-making environment that simulates placing bid/ask quotes.

    The agent chooses a spread strategy each bar. Orders fill probabilistically
    based on spread width and price movement. Inventory accumulates and the
    agent must manage risk via spread skewing.
    """

    # Actions
    TIGHT = 0       # 2 bps spread — aggressive, high fill rate
    NORMAL = 1      # 5 bps spread — balanced
    WIDE = 2        # 10 bps spread — conservative
    SKEW_BID = 3    # shift spread to attract buys (reduce long inventory)
    SKEW_ASK = 4    # shift spread to attract sells (reduce short inventory)

    ACTION_NAMES = ["tight", "normal", "wide", "skew_bid", "skew_ask"]
    SPREAD_BPS = {0: 2, 1: 5, 2: 10, 3: 5, 4: 5}

    def __init__(
        self,
        prices: np.ndarray,
        initial_balance: float = 10000.0,
        max_inventory: float = 5.0,
        inventory_penalty_coeff: float = 0.001,
        fill_probability_base: float = 0.6,
    ):
        """
        Args:
            prices: 1D array of mid prices
            initial_balance: starting cash
            max_inventory: max absolute inventory units before forced flatten
            inventory_penalty_coeff: lambda for inventory risk penalty
            fill_probability_base: base probability that a quote gets filled
        """
        self.prices = np.asarray(prices, dtype=float)
        self.initial_balance = initial_balance
        self.max_inventory = max_inventory
        self.inventory_penalty_coeff = inventory_penalty_coeff
        self.fill_probability_base = fill_probability_base

        # Precompute returns
        self.returns = np.zeros(len(prices))
        self.returns[1:] = np.diff(prices) / prices[:-1]

        self.n_steps = len(prices)
        self.observation_dim = 6
        self.n_actions = 5

        self.reset()

    def reset(self) -> np.ndarray:
        """Reset environment to initial state."""
        self.step_idx = 20  # need history for volatility
        self.balance = self.initial_balance
        self.inventory = 0.0  # units of asset held (positive = long, negative = short)
        self.total_spread_captured = 0.0
        self.n_fills = 0
        self.peak_equity = self.initial_balance
        self.equity_history = [self.initial_balance]
        self.pnl_history = []
        self.done = False
        return self._get_obs()

    def _get_obs(self) -> np.ndarray:
        """Build observation vector."""
        i = self.step_idx

        # Mid-price return (1-bar)
        mid_return = self.returns[i] if i > 0 else 0.0

        # Current spread in bps (starts at 5 bps default)
        spread_bps = 5.0 / 10000.0  # normalized

        # Inventory level (normalized by max)
        inv_level = self.inventory / self.max_inventory if self.max_inventory > 0 else 0.0

        # Rolling volatility (20-bar)
        vol_window = self.returns[max(0, i - 20):i]
        volatility = vol_window.std() if len(vol_window) > 1 else 0.01

        # Order imbalance proxy: sign of recent returns
        recent = self.returns[max(0, i - 5):i]
        order_imbalance = recent.mean() / (volatility + 1e-8)

        # PnL normalized
        equity = self._get_equity()
        pnl = (equity - self.initial_balance) / self.initial_balance

        return np.array([
            mid_return,
            spread_bps,
            inv_level,
            volatility,
            np.clip(order_imbalance, -3, 3),
            pnl,
        ], dtype=np.float32)

    def _get_equity(self) -> float:
        """Current equity = cash + mark-to-market inventory value."""
        mark = self.inventory * self.prices[self.step_idx]
        return self.balance + mark

    def _fill_probability(self, spread_bps: float, is_skewed: bool) -> float:
        """Probability that a quote gets filled. Tighter spread = higher fill."""
        # Base fill prob inversely related to spread
        if spread_bps <= 2:
            p = self.fill_probability_base * 1.3
        elif spread_bps <= 5:
            p = self.fill_probability_base
        else:
            p = self.fill_probability_base * 0.7

        # Skewed quotes have slightly higher fill on the attractive side
        if is_skewed:
            p *= 1.1

        return min(p, 0.95)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        """Execute one bar of market-making."""
        if self.done:
            return self._get_obs(), 0.0, True, {}

        prev_equity = self._get_equity()
        mid_price = self.prices[self.step_idx]

        # Determine spread and skew from action
        spread_bps = self.SPREAD_BPS[action]
        half_spread = mid_price * spread_bps / 10000.0

        bid_skew = 0.0
        ask_skew = 0.0
        if action == self.SKEW_BID:
            # Tighten bid to attract buys (sell to reduce long inventory)
            bid_skew = -half_spread * 0.3
            ask_skew = half_spread * 0.3
        elif action == self.SKEW_ASK:
            # Tighten ask to attract sells (buy to reduce short inventory)
            bid_skew = half_spread * 0.3
            ask_skew = -half_spread * 0.3

        bid_price = mid_price - half_spread + bid_skew
        ask_price = mid_price + half_spread + ask_skew

        # Advance to next bar
        self.step_idx += 1
        if self.step_idx >= self.n_steps - 1:
            self.done = True

        next_price = self.prices[self.step_idx]
        bar_return = (next_price - mid_price) / mid_price

        # Simulate fills based on price movement
        realized_pnl = 0.0
        is_skewed = action in (self.SKEW_BID, self.SKEW_ASK)
        fill_prob = self._fill_probability(spread_bps, is_skewed)

        # Bid fill: price dropped to or below our bid
        bid_filled = (next_price <= bid_price) or (np.random.random() < fill_prob * 0.5)
        # Ask fill: price rose to or above our ask
        ask_filled = (next_price >= ask_price) or (np.random.random() < fill_prob * 0.5)

        if bid_filled and abs(self.inventory) < self.max_inventory:
            # We bought at bid_price
            self.inventory += 1.0
            self.balance -= bid_price
            self.n_fills += 1

        if ask_filled and abs(self.inventory) < self.max_inventory:
            # We sold at ask_price
            self.inventory -= 1.0
            self.balance += ask_price
            self.n_fills += 1

        # If both sides filled, we captured the full spread
        if bid_filled and ask_filled:
            spread_capture = ask_price - bid_price
            self.total_spread_captured += spread_capture

        # Force flatten if inventory exceeds max
        if abs(self.inventory) >= self.max_inventory:
            flatten_price = self.prices[self.step_idx]
            self.balance += self.inventory * flatten_price
            self.inventory = 0.0

        # Compute reward
        current_equity = self._get_equity()
        step_pnl = (current_equity - prev_equity) / self.initial_balance

        # Inventory penalty: penalize holding large positions
        inv_penalty = self.inventory_penalty_coeff * (self.inventory ** 2)

        reward = step_pnl - inv_penalty

        # Track
        self.pnl_history.append(step_pnl)
        self.peak_equity = max(self.peak_equity, current_equity)
        self.equity_history.append(current_equity)

        # Flatten at episode end
        if self.done and self.inventory != 0:
            self.balance += self.inventory * self.prices[self.step_idx]
            self.inventory = 0.0

        info = {
            "equity": current_equity,
            "inventory": self.inventory,
            "spread_bps": spread_bps,
            "bid_filled": bid_filled,
            "ask_filled": ask_filled,
            "step_pnl": step_pnl,
        }

        return self._get_obs(), reward, self.done, info

    def get_episode_stats(self) -> dict:
        """Summary statistics for completed episode."""
        equity = np.array(self.equity_history)
        pnls = np.array(self.pnl_history) if self.pnl_history else np.array([0.0])

        total_return = (equity[-1] - self.initial_balance) / self.initial_balance

        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / (peak + 1e-10)
        max_dd = abs(dd.min())

        sharpe = 0.0
        if pnls.std() > 0:
            sharpe = pnls.mean() / pnls.std() * np.sqrt(365 * 24)

        return {
            "total_return": float(total_return),
            "sharpe": float(sharpe),
            "max_drawdown": float(max_dd),
            "total_spread_captured": float(self.total_spread_captured),
            "n_fills": self.n_fills,
            "final_equity": float(equity[-1]),
        }


# ---------------------------------------------------------------------------
# DQN Agent (numpy-only)
# ---------------------------------------------------------------------------

class DQNMarketMaker:
    """
    Deep Q-Network for market-making spread optimization.

    Architecture: 2-layer MLP (state_dim -> 64 -> 32 -> n_actions) with ReLU.
    Uses epsilon-greedy exploration, experience replay, and target network
    with soft updates. Implemented entirely in numpy.
    """

    def __init__(
        self,
        state_dim: int = 6,
        n_actions: int = 5,
        hidden1: int = 64,
        hidden2: int = 32,
        lr: float = 1e-3,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.995,
        buffer_size: int = 10000,
        batch_size: int = 64,
        tau: float = 0.01,
    ):
        self.state_dim = state_dim
        self.n_actions = n_actions
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.tau = tau

        # Experience replay buffer
        self.buffer = deque(maxlen=buffer_size)

        # Online network weights (Xavier init)
        s1 = np.sqrt(2.0 / (state_dim + hidden1))
        s2 = np.sqrt(2.0 / (hidden1 + hidden2))
        s3 = np.sqrt(2.0 / (hidden2 + n_actions))

        self.w1 = np.random.randn(state_dim, hidden1) * s1
        self.b1 = np.zeros(hidden1)
        self.w2 = np.random.randn(hidden1, hidden2) * s2
        self.b2 = np.zeros(hidden2)
        self.w3 = np.random.randn(hidden2, n_actions) * s3
        self.b3 = np.zeros(n_actions)

        # Target network (copy of online)
        self.tw1 = self.w1.copy()
        self.tb1 = self.b1.copy()
        self.tw2 = self.w2.copy()
        self.tb2 = self.b2.copy()
        self.tw3 = self.w3.copy()
        self.tb3 = self.b3.copy()

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _forward(self, state: np.ndarray) -> np.ndarray:
        """Forward pass through online network. Returns Q-values for all actions."""
        h1 = self._relu(state @ self.w1 + self.b1)
        h2 = self._relu(h1 @ self.w2 + self.b2)
        q_values = h2 @ self.w3 + self.b3
        return q_values

    def _forward_target(self, state: np.ndarray) -> np.ndarray:
        """Forward pass through target network."""
        h1 = self._relu(state @ self.tw1 + self.tb1)
        h2 = self._relu(h1 @ self.tw2 + self.tb2)
        q_values = h2 @ self.tw3 + self.tb3
        return q_values

    def act(self, state: np.ndarray) -> int:
        """Epsilon-greedy action selection."""
        if np.random.random() < self.epsilon:
            return np.random.randint(self.n_actions)
        q_values = self._forward(state)
        return int(np.argmax(q_values))

    def store_transition(self, state, action, reward, next_state, done):
        """Add transition to replay buffer."""
        self.buffer.append((state.copy(), action, reward, next_state.copy(), done))

    def train_step(self) -> float:
        """Sample batch from buffer and perform one gradient step. Returns loss."""
        if len(self.buffer) < self.batch_size:
            return 0.0

        # Sample random batch
        indices = np.random.choice(len(self.buffer), self.batch_size, replace=False)
        batch = [self.buffer[i] for i in indices]

        states = np.array([t[0] for t in batch])
        actions = np.array([t[1] for t in batch])
        rewards = np.array([t[2] for t in batch])
        next_states = np.array([t[3] for t in batch])
        dones = np.array([t[4] for t in batch], dtype=float)

        # Current Q-values
        q_current = self._forward(states)  # (batch, n_actions)

        # Target Q-values
        q_next = self._forward_target(next_states)  # (batch, n_actions)
        q_target = rewards + self.gamma * (1 - dones) * np.max(q_next, axis=1)

        # TD error for selected actions
        q_selected = q_current[np.arange(self.batch_size), actions]
        td_error = q_target - q_selected
        loss = float(np.mean(td_error ** 2))

        # Backprop through online network (manual gradient computation)
        # Forward pass with intermediate values
        z1 = states @ self.w1 + self.b1
        h1 = self._relu(z1)
        z2 = h1 @ self.w2 + self.b2
        h2 = self._relu(z2)

        # Gradient of loss w.r.t. Q output (only for selected actions)
        dq = np.zeros_like(q_current)
        dq[np.arange(self.batch_size), actions] = -2.0 * td_error / self.batch_size

        # Output layer gradients
        dw3 = h2.T @ dq
        db3 = dq.sum(axis=0)

        # Layer 2 gradients
        dh2 = dq @ self.w3.T
        dh2 *= (z2 > 0).astype(float)  # ReLU derivative
        dw2 = h1.T @ dh2
        db2 = dh2.sum(axis=0)

        # Layer 1 gradients
        dh1 = dh2 @ self.w2.T
        dh1 *= (z1 > 0).astype(float)  # ReLU derivative
        dw1 = states.T @ dh1
        db1 = dh1.sum(axis=0)

        # Gradient clipping
        max_grad = 1.0
        for g in [dw1, db1, dw2, db2, dw3, db3]:
            np.clip(g, -max_grad, max_grad, out=g)

        # Apply gradients
        self.w1 -= self.lr * dw1
        self.b1 -= self.lr * db1
        self.w2 -= self.lr * dw2
        self.b2 -= self.lr * db2
        self.w3 -= self.lr * dw3
        self.b3 -= self.lr * db3

        # Soft update target network
        self.tw1 = self.tau * self.w1 + (1 - self.tau) * self.tw1
        self.tb1 = self.tau * self.b1 + (1 - self.tau) * self.tb1
        self.tw2 = self.tau * self.w2 + (1 - self.tau) * self.tw2
        self.tb2 = self.tau * self.b2 + (1 - self.tau) * self.tb2
        self.tw3 = self.tau * self.w3 + (1 - self.tau) * self.tw3
        self.tb3 = self.tau * self.b3 + (1 - self.tau) * self.tb3

        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        return loss

    def save(self, path: str):
        """Save agent weights to .npz file."""
        np.savez(
            path,
            w1=self.w1, b1=self.b1,
            w2=self.w2, b2=self.b2,
            w3=self.w3, b3=self.b3,
            tw1=self.tw1, tb1=self.tb1,
            tw2=self.tw2, tb2=self.tb2,
            tw3=self.tw3, tb3=self.tb3,
            epsilon=np.array([self.epsilon]),
        )

    def load(self, path: str):
        """Load agent weights from .npz file."""
        if not path.endswith(".npz"):
            path = path + ".npz"
        data = np.load(path)
        self.w1, self.b1 = data["w1"], data["b1"]
        self.w2, self.b2 = data["w2"], data["b2"]
        self.w3, self.b3 = data["w3"], data["b3"]
        self.tw1, self.tb1 = data["tw1"], data["tb1"]
        self.tw2, self.tb2 = data["tw2"], data["tb2"]
        self.tw3, self.tb3 = data["tw3"], data["tb3"]
        if "epsilon" in data:
            self.epsilon = float(data["epsilon"][0])


# ---------------------------------------------------------------------------
# Top-level functions
# ---------------------------------------------------------------------------

def fetch_real_prices(symbol: str, limit: int = 500) -> np.ndarray:
    """Fetch real 1h kline close prices from Binance."""
    try:
        import requests
        url = "https://api.binance.com/api/v3/klines"
        resp = requests.get(url, params={
            "symbol": symbol, "interval": "1h", "limit": limit
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        prices = np.array([float(k[4]) for k in data])
        logger.info("Fetched %d real prices for %s", len(prices), symbol)
        return prices
    except Exception as exc:
        logger.warning("Failed to fetch real prices for %s: %s — using synthetic", symbol, exc)
        return generate_synthetic_prices(limit)


def generate_synthetic_prices(n: int = 500, base: float = 50000.0) -> np.ndarray:
    """Generate synthetic GBM price series for testing."""
    returns = np.random.normal(0.0001, 0.015, n)
    prices = base * np.exp(np.cumsum(returns))
    return prices


def train_market_maker(
    prices: np.ndarray,
    episodes: int = 50,
    inventory_penalty: float = 0.001,
) -> tuple:
    """
    Train a DQN market-making agent on price data.

    Returns: (agent, summary_dict)
    """
    env = MarketMakingEnv(
        prices,
        inventory_penalty_coeff=inventory_penalty,
    )
    agent = DQNMarketMaker(
        state_dim=env.observation_dim,
        n_actions=env.n_actions,
    )

    best_return = -np.inf
    history = []

    for episode in range(episodes):
        obs = env.reset()
        total_reward = 0.0
        total_loss = 0.0
        n_steps = 0

        while not env.done:
            action = agent.act(obs)
            next_obs, reward, done, info = env.step(action)

            agent.store_transition(obs, action, reward, next_obs, done)
            loss = agent.train_step()

            total_reward += reward
            total_loss += loss
            n_steps += 1
            obs = next_obs

        stats = env.get_episode_stats()
        stats["avg_loss"] = total_loss / max(n_steps, 1)
        stats["epsilon"] = agent.epsilon
        history.append(stats)

        if stats["total_return"] > best_return:
            best_return = stats["total_return"]

        if (episode + 1) % 10 == 0:
            logger.info(
                "Episode %d/%d: return=%.4f%%, sharpe=%.2f, fills=%d, "
                "spread_captured=%.2f, eps=%.3f",
                episode + 1, episodes,
                stats["total_return"] * 100,
                stats["sharpe"],
                stats["n_fills"],
                stats["total_spread_captured"],
                agent.epsilon,
            )

    summary = {
        "n_episodes": episodes,
        "best_return": float(best_return),
        "final_return": float(history[-1]["total_return"]),
        "final_sharpe": float(history[-1]["sharpe"]),
        "total_fills": int(history[-1]["n_fills"]),
        "history": history,
    }
    return agent, summary


def predict_spread(symbol: str, agent: DQNMarketMaker) -> dict:
    """
    Use trained agent to generate a spread recommendation.

    Returns a pick dict with recommended spread, skew, and confidence.
    """
    prices = fetch_real_prices(symbol, limit=100)
    if len(prices) < 25:
        return {}

    env = MarketMakingEnv(prices)
    obs = env.reset()

    # Walk through to the last bar
    while env.step_idx < len(prices) - 2 and not env.done:
        action = agent.act(obs)
        obs, _, _, _ = env.step(action)

    # Get final recommendation (greedy — no exploration)
    old_eps = agent.epsilon
    agent.epsilon = 0.0
    action = agent.act(obs)
    q_values = agent._forward(obs)
    agent.epsilon = old_eps

    # Derive confidence from Q-value advantage
    q_max = q_values.max()
    q_range = q_values.max() - q_values.min()
    confidence = float(np.clip(0.5 + 0.3 * (q_range / (abs(q_max) + 1e-8)), 0.3, 0.85))

    # Map action to spread recommendation
    spread_bps = MarketMakingEnv.SPREAD_BPS[action]
    action_name = MarketMakingEnv.ACTION_NAMES[action]

    if action == MarketMakingEnv.SKEW_BID:
        inventory_skew = "bid_heavy"
    elif action == MarketMakingEnv.SKEW_ASK:
        inventory_skew = "ask_heavy"
    else:
        inventory_skew = "neutral"

    # Estimate daily yield from recent spread captures
    # Rough: spread_bps * estimated_fills_per_day
    estimated_fills_per_hour = 0.6 if spread_bps <= 5 else 0.4
    estimated_daily_yield_bps = spread_bps * estimated_fills_per_hour * 24 * 0.5

    return {
        "symbol": symbol,
        "direction": "NEUTRAL",
        "strategy": "rl_market_maker",
        "source": "rl_agent",
        "confidence": round(confidence, 3),
        "recommended_spread_bps": spread_bps,
        "action": action_name,
        "inventory_skew": inventory_skew,
        "estimated_daily_yield_bps": round(estimated_daily_yield_bps, 1),
        "q_values": {MarketMakingEnv.ACTION_NAMES[i]: round(float(q_values[i]), 4) for i in range(5)},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_train_all():
    """Train market-maker models for BTC, ETH, SOL and save."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for symbol in MM_PAIRS:
        logger.info("Training DQN market-maker for %s...", symbol)
        prices = fetch_real_prices(symbol, limit=500)
        agent, summary = train_market_maker(prices, episodes=50)
        model_path = str(MODELS_DIR / f"{symbol}_mm_dqn")
        agent.save(model_path)
        logger.info("Saved market-maker model to %s.npz", model_path)
        results[symbol] = {
            "best_return": summary["best_return"],
            "final_return": summary["final_return"],
            "final_sharpe": summary["final_sharpe"],
        }

    summary_path = DATA_DIR / "mm_training_summary.json"
    summary_path.write_text(json.dumps({
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "agent_type": "DQN_MarketMaker",
        "pairs": results,
    }, indent=2))
    logger.info("Market-maker training complete for all pairs")


def run_predict_all():
    """Load trained market-maker models and generate spread recommendations."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    picks = []
    for symbol in MM_PAIRS:
        model_path = MODELS_DIR / f"{symbol}_mm_dqn.npz"
        if not model_path.exists():
            logger.warning("No market-maker model for %s, skipping", symbol)
            continue

        agent = DQNMarketMaker()
        agent.load(str(model_path))

        pick = predict_spread(symbol, agent)
        if pick:
            picks.append(pick)
            logger.info(
                "MM Signal: %s spread=%d bps, skew=%s (conf=%.3f)",
                symbol, pick["recommended_spread_bps"],
                pick["inventory_skew"], pick["confidence"],
            )

    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda picks, label="": picks
    picks = sanitize_active_picks(picks, "rl_market_maker")
    picks_path = DATA_DIR / "mm_active_picks.json"
    picks_path.write_text(json.dumps(picks, indent=2, default=str))
    logger.info("Wrote %d market-maker picks to %s", len(picks), picks_path)
    return picks


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DQN Market-Maker Agent")
    parser.add_argument("--mode", choices=["train", "predict", "both"], default="both")
    parser.add_argument("--episodes", type=int, default=50)
    args = parser.parse_args()

    if args.mode in ("train", "both"):
        run_train_all()
    if args.mode in ("predict", "both"):
        run_predict_all()
