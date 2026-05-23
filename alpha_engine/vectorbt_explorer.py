#!/usr/bin/env python3
"""
ALPHA ENGINE -- VectorBT Explorer
===================================
Ultra-fast parameter exploration using vectorbt's Numba-accelerated backtesting.

Purpose: Explore thousands of strategy parameter combinations in seconds
to find optimal settings before running detailed backtests.

Usage (from repo root):
    from alpha_engine.vectorbt_explorer import explore_ma_crossover

    # Fast parameter sweep
    results = explore_ma_crossover('BTC-USD', start='2y', fast_window=(5, 50), slow_window=(20, 200))
    
    # Feed best params to existing pipeline
    best_params = results['best_params']
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import vectorbt as vbt
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
import warnings

vbt.settings.set_theme("dark")
vbt.settings.plotting["layout"]["template"] = "plotly_dark"

# Optional: yfinance for data
try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


def fetch_ohlcv(symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV data from yfinance."""
    if not YF_AVAILABLE:
        raise ImportError("yfinance required: pip install yfinance")
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    
    if df.empty:
        raise ValueError(f"No data for {symbol}")
    
    return df


def run_ma_crossover(
    price: pd.Series,
    fast_window: int,
    slow_window: int,
    direction: str = "both"
) -> pd.Series:
    """Generate signals for MA crossover strategy."""
    fast_ma = price.vbt.rolling(fast_window).mean()
    slow_ma = price.vbt.rolling(slow_window).mean()
    
    if direction == "long":
        entries = fast_ma > slow_ma
        exits = fast_ma < slow_ma
    elif direction == "short":
        entries = fast_ma < slow_ma
        exits = fast_ma > slow_ma
    else:  # both
        entries = fast_ma > slow_ma
        exits = fast_ma < slow_ma
    
    return entries.vbt.signals.accumulate(exits=exits)


def explore_ma_crossover(
    symbol: str,
    period: str = "2y",
    fast_windows: Optional[List[int]] = None,
    slow_windows: Optional[List[int]] = None,
    direction: str = "both",
    tp_pct: float = 0.05,
    sl_pct: float = 0.02,
    init_cash: float = 10000,
    commission: float = 0.001
) -> Dict[str, Any]:
    """
    Explore MA crossover parameter space using vectorbt.
    
    Returns comprehensive results including best params, Sharpe heatmap, returns.
    """
    if fast_windows is None:
        fast_windows = list(range(5, 51, 5))
    if slow_windows is None:
        slow_windows = list(range(20, 201, 10))
    
    print(f"Fetching {symbol} data...")
    price = fetch_ohlcv(symbol, period=period)
    close = price['Close']
    
    print(f"Running {len(fast_windows) * len(slow_windows)} parameter combinations...")
    
    # Run parameter sweep
    pf = vbt.ParameterSpace(
        fast_window=fast_windows,
        slow_window=slow_windows
    ).run(
        run_ma_crossover,
        price=close,
        direction=direction,
        tp_pct=tp_pct,
        sl_pct=sl_pct,
        init_cash=init_cash,
        commission=commission
    )
    
    # Get results
    returns = pf.returns()
    sharpe = returns.vbt.sharpe_ratio()
    max_dd = returns.vbt.max_drawdown()
    win_rate = pf.trades.win_rate()
    
    # Find best by Sharpe
    best_idx = sharpe.vbt.argmax()
    best_fast = fast_windows[best_idx[0]]
    best_slow = slow_windows[best_idx[1]]
    best_sharpe = sharpe.iloc[best_idx]
    
    print(f"\nBest params: fast={best_fast}, slow={best_slow}, Sharpe={best_sharpe:.2f}")
    print(f"Max Drawdown: {max_dd.iloc[best_idx]:.2%}, Win Rate: {win_rate.iloc[best_idx]:.2%}")
    
    return {
        "symbol": symbol,
        "period": period,
        "fast_windows": fast_windows,
        "slow_windows": slow_windows,
        "sharpe": sharpe,
        "returns": returns,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "best_params": {"fast_window": best_fast, "slow_window": best_slow},
        "best_sharpe": best_sharpe,
        "portfolio": pf
    }


def explore_rsi_strategy(
    symbol: str,
    period: str = "2y",
    rsi_periods: Optional[List[int]] = None,
    oversold: Optional[List[int]] = None,
    overbought: Optional[List[int]] = None,
    init_cash: float = 10000,
    commission: float = 0.001
) -> Dict[str, Any]:
    """Explore RSI-based strategy parameter space."""
    if rsi_periods is None:
        rsi_periods = list(range(5, 31, 2))
    if oversold is None:
        oversold = list(range(20, 41, 5))
    if overbought is None:
        overbought = list(range(60, 81, 5))
    
    print(f"Fetching {symbol} data...")
    price = fetch_ohlcv(symbol, period=period)
    close = price['Close']
    
    # Calculate RSI
    rsi = vbt.RSI.run(close, window=rsi_periods, param_product=True)
    
    print(f"Running {len(rsi_periods) * len(oversold) * len(overbought)} combinations...")
    
    # Create signal matrix
    entries = (rsi.rsi < overbought) & (rsi.rsi > oversold)
    exits = rsi.rsi >= overbought
    
    # Run backtest
    pf = vbt.Portfolio.from_signals(
        close,
        entries=entries,
        exits=exits,
        init_cash=init_cash,
        commission=commission
    )
    
    returns = pf.returns()
    sharpe = returns.vbt.sharpe_ratio()
    
    return {
        "symbol": symbol,
        "rsi_periods": rsi_periods,
        "oversold": oversold,
        "overbought": overbought,
        "sharpe": sharpe,
        "returns": returns,
        "portfolio": pf,
        "best_sharpe": sharpe.max()
    }


def explore_bollinger_bands(
    symbol: str,
    period: str = "2y",
    window_sizes: Optional[List[int]] = None,
    num_stds: Optional[List[float]] = None,
    init_cash: float = 10000,
    commission: float = 0.001
) -> Dict[str, Any]:
    """Explore Bollinger Bands mean reversion strategy."""
    if window_sizes is None:
        window_sizes = list(range(10, 51, 5))
    if num_stds is None:
        num_stds = [1.5, 2.0, 2.5, 3.0]
    
    print(f"Fetching {symbol} data...")
    price = fetch_ohlcv(symbol, period=period)
    close = price['Close']
    
    # Calculate Bollinger Bands
    bb = vbt.BollingerBands.run(close, window=window_sizes, num_std=num_stds, param_product=True)
    
    # Mean reversion: buy at lower band, sell at middle
    entries = close < bb.lower
    exits = close >= bb.middle
    
    print(f"Running {len(window_sizes) * len(num_stds)} combinations...")
    
    pf = vbt.Portfolio.from_signals(
        close,
        entries=entries,
        exits=exits,
        init_cash=init_cash,
        commission=commission
    )
    
    returns = pf.returns()
    sharpe = returns.vbt.sharpe_ratio()
    
    return {
        "symbol": symbol,
        "window_sizes": window_sizes,
        "num_stds": num_stds,
        "sharpe": sharpe,
        "returns": returns,
        "portfolio": pf,
        "best_sharpe": sharpe.max()
    }


def walk_forward_ma(
    symbol: str,
    train_days: int = 365,
    test_days: int = 90,
    fast_range: Tuple[int, int] = (5, 50),
    slow_range: Tuple[int, int] = (20, 200)
) -> pd.DataFrame:
    """
    Walk-forward optimization for MA crossover.
    
    Returns DataFrame with OOS performance per window.
    """
    price = fetch_ohlcv(symbol, period="5y")
    close = price['Close']
    
    results = []
    pos = 0
    
    while pos + train_days + test_days <= len(close):
        train_end = pos + train_days
        test_end = train_end + test_days
        
        train_data = close.iloc[pos:train_end]
        test_data = close.iloc[train_end:test_end]
        
        # Find best params on train
        best_sharpe = -999
        best_fast, best_slow = 10, 50
        
        for fast in range(fast_range[0], fast_range[1], 5):
            for slow in range(slow_range[0], slow_range[1], 10):
                if fast >= slow:
                    continue
                
                train_signals = run_ma_crossover(train_data, fast, slow)
                # Simple return approximation
                rets = train_data.pct_change() * train_signals.shift(1)
                sharpe = rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0
                
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_fast, best_slow = fast, slow
        
        # Test on OOS
        test_signals = run_ma_crossover(test_data, best_fast, best_slow)
        test_rets = test_data.pct_change() * test_signals.shift(1)
        oos_sharpe = test_rets.mean() / test_rets.std() * np.sqrt(252) if test_rets.std() > 0 else 0
        oos_return = test_rets.sum()
        
        results.append({
            "train_end": train_data.index[-1],
            "test_end": test_data.index[-1],
            "best_fast": best_fast,
            "best_slow": best_slow,
            "train_sharpe": best_sharpe,
            "oos_sharpe": oos_sharpe,
            "oos_return": oos_return
        })
        
        pos += test_days
        print(f"Window {len(results)}: train={best_fast}/{best_slow}, OOS Sharpe={oos_sharpe:.2f}")
    
    return pd.DataFrame(results)


def plot_heatmap(results: Dict[str, Any], metric: str = "sharpe"):
    """Plot parameter space heatmap."""
    if metric == "sharpe":
        data = results["sharpe"]
    elif metric == "returns":
        data = results["returns"]
    else:
        raise ValueError(f"Unknown metric: {metric}")
    
    data.vbt.plot()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="VectorBT Parameter Explorer")
    parser.add_argument("--symbol", default="BTC-USD", help="Symbol to explore")
    parser.add_argument("--strategy", default="ma", choices=["ma", "rsi", "bb"])
    parser.add_argument("--period", default="2y", help="Data period")
    
    args = parser.parse_args()
    
    if args.strategy == "ma":
        results = explore_ma_crossover(args.symbol, args.period)
    elif args.strategy == "rsi":
        results = explore_rsi_strategy(args.symbol, args.period)
    elif args.strategy == "bb":
        results = explore_bollinger_bands(args.symbol, args.period)
    
    print(f"\nBest Sharpe: {results['best_sharpe']:.3f}")
    print(f"Best Params: {results.get('best_params', 'N/A')}")
