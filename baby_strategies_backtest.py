"""
Baby Strategies Backtest Engine
===============================

Comprehensive backtesting for 10 new trading strategies on BTC, ETH, SOL.
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
sys.path.insert(0, str(Path(__file__).parent / "baby_strategies"))

# Import all strategies
from market_structure_volume import MarketStructureVolumeStrategy
from kalman_mean_reversion import KalmanMeanReversionStrategy
from liquidity_sweep_reversal import LiquiditySweepReversalStrategy
from adaptive_momentum import AdaptiveMomentumStrategy
from volume_profile_deviation import VolumeProfileDeviationStrategy
from range_expansion_breakout import RangeExpansionBreakoutStrategy
from order_block_retest import OrderBlockRetestStrategy
from multi_timeframe_confluence import MultiTimeframeConfluenceStrategy
from relative_strength_rotation import RelativeStrengthRotationStrategy
from volatility_regime_switch import VolatilityRegimeSwitchStrategy
from price_roc_mean_reversion_strategy import PriceRocMeanReversionStrategy


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
    data: pd.DataFrame,
    symbol: str,
    initial_capital: float = 10000,
    position_pct: float = 0.1,
    commission: float = 0.001,
    slippage: float = 0.0005
) -> BacktestResult:
    """Run backtest on a strategy."""
    equity = initial_capital
    trades = []
    
    position = None
    entry_bar = 0
    min_bars = 80
    
    for i in range(min_bars, len(data)):
        current_bar = data.iloc[i]
        
        # Check if position should be closed
        if position is not None:
            bars_held = i - entry_bar
            current_price = current_bar['close']
            
            if position['direction'] == 'BUY':
                pnl = (current_price - position['entry_price']) / position['entry_price']
                
                if current_price >= position['tp_price']:
                    exit_reason = 'TP'
                elif current_price <= position['sl_price']:
                    exit_reason = 'SL'
                elif bars_held >= 15:
                    exit_reason = 'TIME'
                else:
                    exit_reason = None
            else:
                pnl = (position['entry_price'] - current_price) / position['entry_price']
                
                if current_price <= position['tp_price']:
                    exit_reason = 'TP'
                elif current_price >= position['sl_price']:
                    exit_reason = 'SL'
                elif bars_held >= 15:
                    exit_reason = 'TIME'
                else:
                    exit_reason = None
            
            if exit_reason:
                pnl -= (commission * 2 + slippage * 2)
                trades.append({'pnl': pnl, 'reason': exit_reason})
                equity *= (1 + pnl * position_pct)
                position = None
        
        # Generate signals
        if position is None and i < len(data) - 1:
            signal_data = data.iloc[:i+1].copy()
            signals = strategy.generate_signals(signal_data, symbol)
            
            if signals:
                sig = signals[0]
                position = {
                    'direction': sig.direction,
                    'entry_price': sig.entry_price,
                    'tp_price': sig.take_profit,
                    'sl_price': sig.stop_loss
                }
                entry_bar = i
    
    # Calculate metrics
    if trades:
        pnls = [t['pnl'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_return = (equity - initial_capital) / initial_capital
        win_rate = len(wins) / len(pnls) if pnls else 0
        avg_return = np.mean(pnls) if pnls else 0
        std_return = np.std(pnls) if pnls else 0.001
        sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        peak = initial_capital
        max_dd = 0
        running_equity = initial_capital
        for t in trades:
            running_equity *= (1 + t['pnl'] * position_pct)
            if running_equity > peak:
                peak = running_equity
            dd = (peak - running_equity) / peak
            max_dd = max(max_dd, dd)
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return BacktestResult(
            strategy_name=strategy.__class__.__name__,
            symbol=symbol,
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
            num_trades=len(trades),
            avg_trade=np.mean(pnls)
        )
    else:
        return BacktestResult(
            strategy_name=strategy.__class__.__name__,
            symbol=symbol,
            total_return=0,
            sharpe_ratio=0,
            max_drawdown=0,
            win_rate=0,
            profit_factor=0,
            num_trades=0,
            avg_trade=0
        )


def get_all_strategies():
    """Return list of all strategy instances."""
    return [
        MarketStructureVolumeStrategy(),
        KalmanMeanReversionStrategy(),
        LiquiditySweepReversalStrategy(),
        AdaptiveMomentumStrategy(),
        VolumeProfileDeviationStrategy(),
        RangeExpansionBreakoutStrategy(),
        OrderBlockRetestStrategy(),
        MultiTimeframeConfluenceStrategy(),
        RelativeStrengthRotationStrategy(),
        VolatilityRegimeSwitchStrategy(),
        PriceRocMeanReversionStrategy()
    ]


def run_full_backtest_suite(symbols=None):
    """Run full backtest suite."""
    if symbols is None:
        symbols = ['BTC', 'ETH', 'SOL']
    
    strategies = get_all_strategies()
    all_results = []
    
    print("=" * 80)
    print("BABY STRATEGIES BACKTEST SUITE")
    print("=" * 80)
    print(f"\nTesting {len(strategies)} strategies on {len(symbols)} symbols")
    print(f"Symbols: {', '.join(symbols)}\n")
    
    for symbol in symbols:
        print(f"\n--- {symbol} ---")
        data = generate_crypto_data(symbol, n_bars=800, seed=hash(symbol) % 10000)
        
        for strategy in strategies:
            strategy_name = strategy.__class__.__name__.replace('Strategy', '')
            result = run_strategy_backtest(strategy, data, symbol)
            all_results.append(result)
            
            status = "*" if result.sharpe_ratio > 1.0 and result.win_rate > 0.45 else " "
            print(f"  [{status}] {strategy_name:30s} Trades: {result.num_trades:3d} | Return: {result.total_return:7.2%} | Sharpe: {result.sharpe_ratio:5.2f} | WR: {result.win_rate:5.1%}")
    
    results_df = pd.DataFrame([
        {
            'Strategy': r.strategy_name.replace('Strategy', ''),
            'Symbol': r.symbol,
            'Trades': r.num_trades,
            'Win Rate': r.win_rate,
            'Total Return': r.total_return,
            'Sharpe': r.sharpe_ratio,
            'Max DD': r.max_drawdown,
            'Profit Factor': r.profit_factor,
            'Avg Trade': r.avg_trade
        }
        for r in all_results
    ])
    
    results_df = results_df.sort_values('Sharpe', ascending=False).reset_index(drop=True)
    return results_df, all_results


def generate_report(results_df, all_results):
    """Generate comprehensive report."""
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 80)
    
    print("\n--- Overall Statistics ---")
    print(f"Total combinations tested: {len(results_df)}")
    print(f"Sharpe > 1.0: {(results_df['Sharpe'] > 1.0).sum()}")
    print(f"Win Rate > 45%: {(results_df['Win Rate'] > 0.45).sum()}")
    print(f"Max DD < 20%: {(results_df['Max DD'] < 0.2).sum()}")
    
    print("\n--- TOP 15 PERFORMERS ---")
    top15 = results_df.head(15)
    print(top15.to_string(index=False))
    
    print("\n--- BEST PER SYMBOL ---")
    for symbol in results_df['Symbol'].unique():
        symbol_df = results_df[results_df['Symbol'] == symbol]
        best = symbol_df.iloc[0]
        print(f"{symbol}: {best['Strategy']} (Sharpe: {best['Sharpe']:.2f}, Return: {best['Total Return']:.2%})")
    
    print("\n--- STRATEGY AVERAGES ---")
    strategy_avg = results_df.groupby('Strategy').agg({
        'Sharpe': 'mean',
        'Total Return': 'mean',
        'Win Rate': 'mean',
        'Max DD': 'mean',
        'Trades': 'mean'
    }).sort_values('Sharpe', ascending=False)
    print(strategy_avg.to_string())
    
    print("\n--- PASSING ALL CRITERIA ---")
    passing = results_df[
        (results_df['Sharpe'] > 1.0) & 
        (results_df['Win Rate'] > 0.45) & 
        (results_df['Max DD'] < 0.25)
    ]
    if len(passing) > 0:
        print(passing.to_string(index=False))
    else:
        print("No strategies passed all criteria (this is expected on synthetic data)")
    
    # Save results
    results_df.to_csv('baby_strategies_backtest_results.csv', index=False)
    print("\n[OK] Results saved to baby_strategies_backtest_results.csv")
    
    detailed = {
        'summary': {
            'total_combinations': len(results_df),
            'sharpe_above_1': int((results_df['Sharpe'] > 1.0).sum()),
            'win_rate_above_45': int((results_df['Win Rate'] > 0.45).sum()),
        },
        'results': results_df.to_dict('records'),
        'timestamp': datetime.now().isoformat()
    }
    
    with open('baby_strategies_backtest_results.json', 'w') as f:
        json.dump(detailed, f, indent=2, default=str)
    print("[OK] Results saved to baby_strategies_backtest_results.json")


if __name__ == "__main__":
    results_df, all_results = run_full_backtest_suite(symbols=['BTC', 'ETH', 'SOL'])
    generate_report(results_df, all_results)
    
    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)
