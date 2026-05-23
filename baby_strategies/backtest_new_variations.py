"""
Backtest New Strategy Variations
=================================

Backtests the new strategy variations created based on the battleground strategies.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import sys

# Add baby_strategies to path
sys.path.insert(0, str(Path(__file__).parent))

# Import new strategy variations
from keltner_rsi_confluence import KeltnerRSIConfluenceStrategy
from connors_r4_mean_reversion import ConnorsR4MeanReversionStrategy
from supertrend_multi_timeframe import SuperTrendMultiTimeframeStrategy
from vol_scaled_keltner import VolScaledKeltnerStrategy


@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int
    avg_trade: float


def generate_crypto_data(symbol: str, n_bars: int = 800, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic crypto OHLCV data."""
    np.random.seed(seed)
    
    params = {
        'BTC': {'drift': 0.0005, 'vol': 0.035, 'price': 45000},
        'ETH': {'drift': 0.0006, 'vol': 0.045, 'price': 3000},
        'SOL': {'drift': 0.0008, 'vol': 0.055, 'price': 100}
    }
    
    p = params.get(symbol, params['BTC'])
    
    returns = []
    regime = 0
    regime_duration = 0
    
    for i in range(n_bars):
        if regime_duration <= 0:
            regime = np.random.choice([0, 1, 2, 3], p=[0.5, 0.2, 0.2, 0.1])
            regime_duration = np.random.randint(20, 60)
        regime_duration -= 1
        
        if regime == 0:
            drift, vol = p['drift'], p['vol']
        elif regime == 1:
            drift, vol = p['drift'] * 3, p['vol'] * 0.8
        elif regime == 2:
            drift, vol = -p['drift'] * 2, p['vol'] * 1.2
        else:
            drift, vol = 0, p['vol'] * 1.8
        
        ret = np.random.normal(drift, vol)
        returns.append(ret)
    
    returns = np.array(returns)
    prices = p['price'] * np.exp(np.cumsum(returns))
    
    n = len(prices)
    daily_range = np.abs(returns) + np.random.exponential(p['vol'] * 0.4, n)
    
    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, p['vol'] * 0.2, n)),
        'high': prices * (1 + daily_range * np.random.uniform(0.4, 0.8, n)),
        'low': prices * (1 - daily_range * np.random.uniform(0.4, 0.8, n)),
        'close': prices,
        'volume': np.random.lognormal(20, 0.8, n)
    })
    
    df['high'] = df[['high', 'open', 'close']].max(axis=1) * 1.001
    df['low'] = df[['low', 'open', 'close']].min(axis=1) * 0.999
    
    return df


def run_strategy_backtest(
    strategy,
    strategy_name: str,
    symbol: str,
    data: pd.DataFrame,
    initial_capital: float = 10000
) -> BacktestResult:
    """Run backtest for a single strategy."""
    capital = initial_capital
    position = 0.0
    entry_price = 0.0
    trades = []
    portfolio = [capital]

    signals = []
    for i in range(1, len(data)):
        window_data = data.iloc[:i+1].copy()
        
        try:
            new_signals = strategy.generate_signals(window_data, symbol)
        except Exception as e:
            new_signals = []
        
        if new_signals:
            signals.extend(new_signals)
        
        current_price = data['close'].iloc[i]
        
        # Execute signals
        for sig in new_signals:
            if sig.direction == "BUY" and position == 0:
                position = capital / current_price
                entry_price = current_price
            elif sig.direction == "SELL" and position > 0:
                capital = position * current_price
                position = 0
                trades.append({
                    'entry': entry_price,
                    'exit': current_price,
                    'profit': capital - initial_capital
                })
        
        # Update portfolio value
        if position > 0:
            portfolio_value = position * current_price
        else:
            portfolio_value = capital
        portfolio.append(portfolio_value)
    
    # Calculate performance metrics
    portfolio = np.array(portfolio)
    returns = np.diff(portfolio) / portfolio[:-1]
    
    total_return = (portfolio[-1] - initial_capital) / initial_capital * 100
    sharpe_ratio = np.sqrt(252) * np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
    max_drawdown = 0.0
    peak = initial_capital
    
    for value in portfolio:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    win_rate = 0.0
    profit_factor = 0.0
    
    if trades:
        winning_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] <= 0]
        win_rate = len(winning_trades) / len(trades) * 100
        
        total_winning = sum(t['profit'] for t in winning_trades)
        total_losing = abs(sum(t['profit'] for t in losing_trades))
        
        if total_losing > 0:
            profit_factor = total_winning / total_losing
        else:
            profit_factor = 1000
    
    avg_trade = np.mean([t['profit'] for t in trades]) if trades else 0
    
    return BacktestResult(
        strategy_name=strategy_name,
        symbol=symbol,
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown * 100,
        win_rate=win_rate,
        profit_factor=profit_factor,
        num_trades=len(trades),
        avg_trade=avg_trade
    )


def main():
    """Main backtesting function."""
    print("Running backtests on new strategy variations...\n")
    
    symbols = ['BTC', 'ETH', 'SOL']
    initial_capital = 10000
    
    # Initialize strategies
    strategies = [
        (KeltnerRSIConfluenceStrategy(), "KeltnerRSIConfluence"),
        (ConnorsR4MeanReversionStrategy(), "ConnorsR4MeanReversion"),
        (SuperTrendMultiTimeframeStrategy(), "SuperTrendMultiTimeframe"),
        (VolScaledKeltnerStrategy(), "VolScaledKeltner")
    ]
    
    all_results = []
    
    for strategy, strategy_name in strategies:
        print(f"Testing strategy: {strategy_name}")
        
        strategy_results = []
        
        for symbol in symbols:
            data = generate_crypto_data(symbol, n_bars=800)
            
            try:
                result = run_strategy_backtest(
                    strategy,
                    strategy_name,
                    symbol,
                    data,
                    initial_capital
                )
                strategy_results.append(result)
                all_results.append(result)
                
                print(f"  {symbol}: Total Return {result.total_return:.1f}%, "
                      f"Sharpe {result.sharpe_ratio:.2f}, "
                      f"WR {result.win_rate:.1f}%, "
                      f"PF {result.profit_factor:.2f}")
                
            except Exception as e:
                print(f"  {symbol}: Error - {e}")
        
        # Calculate average performance for strategy
        if strategy_results:
            avg_return = np.mean([r.total_return for r in strategy_results])
            avg_sharpe = np.mean([r.sharpe_ratio for r in strategy_results])
            avg_win_rate = np.mean([r.win_rate for r in strategy_results])
            avg_profit_factor = np.mean([r.profit_factor for r in strategy_results])
            
            print(f"\n  Average Performance:")
            print(f"  Total Return: {avg_return:.1f}%")
            print(f"  Sharpe Ratio: {avg_sharpe:.2f}")
            print(f"  Win Rate: {avg_win_rate:.1f}%")
            print(f"  Profit Factor: {avg_profit_factor:.2f}")
        
        print()
    
    # Save results to CSV
    results_df = pd.DataFrame([{
        'strategy': r.strategy_name,
        'symbol': r.symbol,
        'total_return': r.total_return,
        'sharpe_ratio': r.sharpe_ratio,
        'max_drawdown': r.max_drawdown,
        'win_rate': r.win_rate,
        'profit_factor': r.profit_factor,
        'num_trades': r.num_trades,
        'avg_trade': r.avg_trade
    } for r in all_results])
    
    results_df.to_csv('new_strategy_variations_backtest_results.csv', index=False)
    print("Results saved to 'new_strategy_variations_backtest_results.csv'")
    
    # Save results to JSON
    results_json = [{
        'strategy': r.strategy_name,
        'symbol': r.symbol,
        'total_return': r.total_return,
        'sharpe_ratio': r.sharpe_ratio,
        'max_drawdown': r.max_drawdown,
        'win_rate': r.win_rate,
        'profit_factor': r.profit_factor,
        'num_trades': r.num_trades,
        'avg_trade': r.avg_trade
    } for r in all_results]
    
    with open('new_strategy_variations_backtest_results.json', 'w') as f:
        json.dump(results_json, f, indent=2)
    
    print("Results saved to 'new_strategy_variations_backtest_results.json'")
    
    # Print summary
    print("\n=== Strategy Performance Summary ===")
    strategy_groups = results_df.groupby('strategy')
    
    for name, group in strategy_groups:
        avg_return = group['total_return'].mean()
        avg_sharpe = group['sharpe_ratio'].mean()
        avg_win_rate = group['win_rate'].mean()
        avg_profit_factor = group['profit_factor'].mean()
        
        print(f"\n{name}:")
        print(f"  Average Return: {avg_return:.1f}%")
        print(f"  Average Sharpe: {avg_sharpe:.2f}")
        print(f"  Average Win Rate: {avg_win_rate:.1f}%")
        print(f"  Average Profit Factor: {avg_profit_factor:.2f}")


if __name__ == "__main__":
    main()
