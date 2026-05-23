"""
Crypto Trading Environment for Reinforcement Learning
========================================================
OpenAI Gym-compatible environment for training RL trading agents.

State: [returns_5, returns_20, vol_20, rsi_14, position, pnl]
Actions: 0=HOLD, 1=BUY, 2=SELL
Reward: PnL with Sharpe penalty — r = pnl - lambda * drawdown

This is a PROTOTYPE for experimentation. Not connected to live trading.
"""

import numpy as np
from typing import Optional, Tuple


class CryptoTradingEnv:
    """
    Simple crypto trading environment.

    Designed for 1-hour bars. Agent observes price features and
    chooses to hold, buy, or sell each bar.
    """

    HOLD = 0
    BUY = 1
    SELL = 2

    def __init__(
        self,
        prices: np.ndarray,
        initial_balance: float = 10000.0,
        transaction_cost: float = 0.001,
        sharpe_penalty: float = 0.1,
        max_position: float = 1.0,
    ):
        """
        Args:
            prices: 1D array of close prices
            initial_balance: starting cash
            transaction_cost: cost per trade as fraction (0.001 = 0.1%)
            sharpe_penalty: lambda for drawdown penalty in reward
            max_position: max fraction of portfolio in position
        """
        self.prices = np.asarray(prices, dtype=float)
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        self.sharpe_penalty = sharpe_penalty
        self.max_position = max_position

        # Precompute features
        self.returns = np.zeros(len(prices))
        self.returns[1:] = np.diff(prices) / prices[:-1]

        self.n_steps = len(prices)
        self.observation_dim = 6
        self.n_actions = 3

        self.reset()

    def reset(self) -> np.ndarray:
        """Reset environment to initial state."""
        self.step_idx = 20  # start after enough history for features
        self.balance = self.initial_balance
        self.position = 0.0  # fraction of portfolio in crypto (-1 to 1)
        self.entry_price = 0.0
        self.peak_equity = self.initial_balance
        self.equity_history = [self.initial_balance]
        self.trade_returns = []
        self.done = False
        return self._get_obs()

    def _get_obs(self) -> np.ndarray:
        """Get current observation vector."""
        i = self.step_idx

        # 5-bar return
        ret_5 = self.returns[max(0, i-5):i].sum() if i >= 5 else 0.0

        # 20-bar return
        ret_20 = self.returns[max(0, i-20):i].sum() if i >= 20 else 0.0

        # 20-bar volatility
        vol_20 = self.returns[max(0, i-20):i].std() if i >= 20 else 0.01

        # RSI-14
        gains = self.returns[max(0, i-14):i].clip(min=0)
        losses = (-self.returns[max(0, i-14):i]).clip(min=0)
        avg_gain = gains.mean() if len(gains) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0.001
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - 100 / (1 + rs)

        # Current position
        pos = self.position

        # Current PnL
        current_equity = self._get_equity()
        pnl = (current_equity - self.initial_balance) / self.initial_balance

        return np.array([ret_5, ret_20, vol_20, rsi / 100, pos, pnl], dtype=np.float32)

    def _get_equity(self) -> float:
        """Calculate current portfolio equity."""
        if self.position != 0 and self.entry_price > 0:
            price_change = (self.prices[self.step_idx] - self.entry_price) / self.entry_price
            position_pnl = self.position * price_change * self.balance
            return self.balance + position_pnl
        return self.balance

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        """
        Execute one step.

        Returns: (observation, reward, done, info)
        """
        if self.done:
            return self._get_obs(), 0.0, True, {}

        prev_equity = self._get_equity()

        # Execute action
        cost = 0.0
        if action == self.BUY and self.position <= 0:
            # Close short (if any) and go long
            if self.position < 0:
                cost += abs(self.position) * self.transaction_cost * self.balance
            self.position = self.max_position
            self.entry_price = self.prices[self.step_idx]
            cost += self.max_position * self.transaction_cost * self.balance

        elif action == self.SELL and self.position >= 0:
            # Close long (if any) and go short
            if self.position > 0:
                cost += self.position * self.transaction_cost * self.balance
            self.position = -self.max_position
            self.entry_price = self.prices[self.step_idx]
            cost += self.max_position * self.transaction_cost * self.balance

        self.balance -= cost

        # Advance to next bar
        self.step_idx += 1

        if self.step_idx >= self.n_steps - 1:
            self.done = True
            # Close position at end
            if self.position != 0:
                self.balance = self._get_equity()
                self.position = 0.0

        # Compute reward
        current_equity = self._get_equity()
        pnl = (current_equity - prev_equity) / prev_equity if prev_equity > 0 else 0

        # Track for Sharpe
        self.trade_returns.append(pnl)

        # Update peak equity and drawdown
        self.peak_equity = max(self.peak_equity, current_equity)
        drawdown = (self.peak_equity - current_equity) / self.peak_equity

        # Reward = PnL - lambda * drawdown
        reward = pnl - self.sharpe_penalty * drawdown

        self.equity_history.append(current_equity)

        info = {
            "equity": current_equity,
            "position": self.position,
            "drawdown": drawdown,
            "pnl": pnl,
        }

        return self._get_obs(), reward, self.done, info

    def get_episode_stats(self) -> dict:
        """Get summary statistics for the completed episode."""
        returns = np.array(self.trade_returns)
        equity = np.array(self.equity_history)

        total_return = (equity[-1] - self.initial_balance) / self.initial_balance

        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / peak
        max_dd = abs(dd.min())

        sharpe = 0.0
        if returns.std() > 0:
            sharpe = returns.mean() / returns.std() * np.sqrt(365 * 24)  # hourly bars

        return {
            "total_return": float(total_return),
            "sharpe": float(sharpe),
            "max_drawdown": float(max_dd),
            "n_steps": len(returns),
            "final_equity": float(equity[-1]),
        }
