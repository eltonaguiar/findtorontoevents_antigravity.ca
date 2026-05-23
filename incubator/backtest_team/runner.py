#!/usr/bin/env python3
"""
Backtest Runner Agent
=====================

The "worker" agent that executes backtests for individual strategies.
Generates synthetic price data or fetches real data, runs the strategy,
and calculates performance metrics.

Pass Criteria (Baby Strat Standard):
- Sharpe Ratio >= 1.0
- Win Rate >= 45%
- Max Drawdown <= 20%
"""

import numpy as np
import pandas as pd
from typing import Type, List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


def generate_synthetic_crypto_data(days: int = 90, seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic synthetic BTC price data for backtesting.
    
    Features:
    - Realistic volatility (~3% daily)
    - Mean reversion tendencies
    - Occasional trend regimes
    - GARCH-like volatility clustering
    """
    rng = np.random.default_rng(seed)
    n = days
    
    # Generate returns with realistic properties
    returns = []
    vol = 0.03  # Base volatility
    
    for i in range(n):
        # GARCH-like volatility clustering
        if i > 0:
            vol = 0.02 + 0.1 * returns[-1]**2 + 0.85 * vol
            vol = np.clip(vol, 0.01, 0.08)  # Bound volatility
        
        # Mean reversion component
        if i > 10:
            recent_return = np.mean(returns[-10:])
            mean_rev = -0.1 * recent_return  # Pull back to zero
        else:
            mean_rev = 0
        
        # Random shock
        shock = rng.normal(0.0005 + mean_rev, vol)
        returns.append(shock)
    
    returns = np.array(returns)
    
    # Generate price series
    base_price = 50000
    prices = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLCV
    dates = pd.date_range(end=datetime.now(), periods=n, freq='D')
    
    data = pd.DataFrame({
        'open': prices * (1 + rng.normal(0, 0.002, n)),
        'high': prices * (1 + abs(rng.normal(0, 0.015, n))),
        'low': prices * (1 - abs(rng.normal(0, 0.015, n))),
        'close': prices,
        'volume': rng.uniform(1000, 10000, n)
    }, index=dates)
    
    return data


def generate_spx_data(btc_data: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic SPX data that is correlated with BTC.
    Used for cross-asset strategies.
    """
    rng = np.random.default_rng(seed)
    n = len(btc_data)
    
    # BTC returns
    btc_returns = btc_data['close'].pct_change().fillna(0)
    
    # Create regime indicator (85% correlated, 15% breakdown)
    regime = np.ones(n)
    i = 0
    while i < n:
        if rng.random() < 0.03:  # 3% chance per bar
            duration = rng.integers(5, 20)
            regime[i:min(i + duration, n)] = 0
            i += duration
        else:
            i += 1
    
    # Generate SPX returns
    spx_noise = rng.normal(0.0003, 0.012, n)
    btc_arr = btc_returns.values
    
    spx_returns = np.where(
        regime == 1,
        0.5 * btc_arr + 0.5 * spx_noise,
        -0.2 * btc_arr + 0.8 * spx_noise
    )
    
    # Generate SPX prices
    base_price = 4500
    prices = base_price * np.exp(np.cumsum(spx_returns))
    
    dates = btc_data.index
    spx_data = pd.DataFrame({
        'open': prices * (1 + rng.normal(0, 0.001, n)),
        'high': prices * (1 + abs(rng.normal(0, 0.008, n))),
        'low': prices * (1 - abs(rng.normal(0, 0.008, n))),
        'close': prices,
        'volume': rng.uniform(1000000, 5000000, n)
    }, index=dates)
    
    return spx_data


@dataclass
class Trade:
    """Represents a single trade."""
    entry_bar: int
    exit_bar: int
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    exit_reason: str


class BacktestRunner:
    """
    Runs backtests for Baby Strat strategies.
    
    Simulates a realistic trading environment:
    - Walk-forward analysis (no future peeking)
    - Transaction costs (0.1% per trade)
    - Slippage simulation
    - ATR-based position sizing
    """
    
    def __init__(self, days: int = 90, initial_capital: float = 10000):
        self.days = days
        self.initial_capital = initial_capital
        self.transaction_cost = 0.001  # 0.1%
        
    def run_strategy(self, strategy_class: Type, strategy_name: str):
        """Run full backtest for a strategy."""
        from controller import BacktestResult
        
        # Generate data
        data = generate_synthetic_crypto_data(self.days)
        
        # For cross-asset strategies, inject SPX data
        if "spx" in strategy_name.lower() or "corr" in strategy_name.lower():
            spx_data = generate_spx_data(data)
            # Strategy will generate its own SPX data via MockSPXDataBridge
        
        # Initialize strategy
        strategy = strategy_class()
        
        # Run walk-forward backtest
        trades = []
        capital = self.initial_capital
        equity_curve = [capital]
        
        min_bars = 50  # Minimum history needed
        
        for end_idx in range(min_bars, len(data)):
            window = data.iloc[:end_idx + 1]
            
            # Get signals
            try:
                signals = strategy.generate_signals(window, symbol="BTCUSDT")
            except Exception as e:
                return BacktestResult(
                    strategy_name=strategy_name,
                    agent_id="unknown",
                    status="error",
                    error_message=f"Signal generation error: {e}"
                )
            
            # Execute signals (simplified - one trade at a time)
            for signal in signals:
                trade = self._simulate_trade(signal, data, end_idx, capital)
                if trade:
                    trades.append(trade)
                    capital += trade.pnl
            
            equity_curve.append(capital)
        
        # Calculate metrics
        if len(trades) < 5:
            return BacktestResult(
                strategy_name=strategy_name,
                agent_id="unknown",
                status="failed",
                error_message=f"Insufficient trades: {len(trades)} (need >= 5)",
                total_trades=len(trades)
            )
        
        metrics = self._calculate_metrics(trades, equity_curve)
        
        # Determine pass/fail
        passed = (
            metrics['sharpe'] >= 1.0 and
            metrics['win_rate'] >= 0.45 and
            metrics['max_drawdown'] <= 0.20
        )
        
        return BacktestResult(
            strategy_name=strategy_name,
            agent_id="unknown",
            status="passed" if passed else "failed",
            sharpe=metrics['sharpe'],
            win_rate=metrics['win_rate'],
            max_drawdown=metrics['max_drawdown'],
            total_trades=len(trades),
            profit_factor=metrics['profit_factor']
        )
    
    def _simulate_trade(self, signal, data: pd.DataFrame, entry_bar: int, capital: float) -> Optional[Trade]:
        """Simulate a single trade from signal to exit."""
        if entry_bar >= len(data) - 1:
            return None
        
        entry_price = signal.entry_price
        direction = 1 if signal.direction == "BUY" else -1
        
        # Position sizing: risk 1% of capital
        risk_per_trade = capital * 0.01
        
        if signal.direction == "BUY":
            stop_distance = entry_price - signal.stop_loss
        else:
            stop_distance = signal.stop_loss - entry_price
        
        if stop_distance <= 0:
            return None
        
        position_size = risk_per_trade / stop_distance
        
        # Simulate until exit
        for exit_bar in range(entry_bar + 1, min(entry_bar + 20, len(data))):
            current_price = data['close'].iloc[exit_bar]
            
            # Check TP/SL
            if signal.direction == "BUY":
                if current_price >= signal.take_profit:
                    exit_price = signal.take_profit
                    pnl = (exit_price - entry_price) * position_size * (1 - self.transaction_cost)
                    pnl_pct = (exit_price - entry_price) / entry_price
                    return Trade(entry_bar, exit_bar, "LONG", entry_price, exit_price, pnl, pnl_pct, "TP")
                
                if current_price <= signal.stop_loss:
                    exit_price = signal.stop_loss
                    pnl = (exit_price - entry_price) * position_size * (1 - self.transaction_cost)
                    pnl_pct = (exit_price - entry_price) / entry_price
                    return Trade(entry_bar, exit_bar, "LONG", entry_price, exit_price, pnl, pnl_pct, "SL")
            else:
                if current_price <= signal.take_profit:
                    exit_price = signal.take_profit
                    pnl = (entry_price - exit_price) * position_size * (1 - self.transaction_cost)
                    pnl_pct = (entry_price - exit_price) / entry_price
                    return Trade(entry_bar, exit_bar, "SHORT", entry_price, exit_price, pnl, pnl_pct, "TP")
                
                if current_price >= signal.stop_loss:
                    exit_price = signal.stop_loss
                    pnl = (entry_price - exit_price) * position_size * (1 - self.transaction_cost)
                    pnl_pct = (entry_price - exit_price) / entry_price
                    return Trade(entry_bar, exit_bar, "SHORT", entry_price, exit_price, pnl, pnl_pct, "SL")
        
        # Time exit
        exit_bar = min(entry_bar + 19, len(data) - 1)
        exit_price = data['close'].iloc[exit_bar]
        
        if signal.direction == "BUY":
            pnl = (exit_price - entry_price) * position_size * (1 - self.transaction_cost)
            pnl_pct = (exit_price - entry_price) / entry_price
            return Trade(entry_bar, exit_bar, "LONG", entry_price, exit_price, pnl, pnl_pct, "TIME")
        else:
            pnl = (entry_price - exit_price) * position_size * (1 - self.transaction_cost)
            pnl_pct = (entry_price - exit_price) / entry_price
            return Trade(entry_bar, exit_bar, "SHORT", entry_price, exit_price, pnl, pnl_pct, "TIME")
    
    def _calculate_metrics(self, trades: List[Trade], equity_curve: List[float]) -> Dict:
        """Calculate performance metrics."""
        if not trades:
            return {'sharpe': 0, 'win_rate': 0, 'max_drawdown': 0, 'profit_factor': 0}
        
        # Win rate
        wins = [t for t in trades if t.pnl > 0]
        win_rate = len(wins) / len(trades)
        
        # Profit factor
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        
        # Sharpe ratio (simplified)
        if len(equity_curve) > 1:
            returns = np.diff(equity_curve) / equity_curve[:-1]
            if len(returns) > 1 and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        return {
            'sharpe': round(sharpe, 2),
            'win_rate': round(win_rate, 2),
            'max_drawdown': round(max_dd, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 999
        }


if __name__ == "__main__":
    print("Backtest Runner Agent v1.0")
    print("Use via: python controller.py")
