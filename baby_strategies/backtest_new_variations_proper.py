"""
Backtest New Strategy Variations Using Proper Framework
=======================================================

Backtests the new strategy variations created based on the battleground strategies
using the existing comprehensive backtest framework.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import backtest framework
from backtest_framework import (
    Strategy, Signal as BTSignal, PositionSide, Trade, Position,
    BacktestConfig, BacktestResult, BacktestEngine,
    DataLoader, BatchBacktester
)

# Import new strategy variations
from keltner_rsi_confluence import KeltnerRSIConfluenceStrategy
from connors_r4_mean_reversion import ConnorsR4MeanReversionStrategy
from supertrend_multi_timeframe import SuperTrendMultiTimeframeStrategy
from vol_scaled_keltner import VolScaledKeltnerStrategy


def convert_to_framework_signals(baby_signals, current_time):
    """Convert baby strategy signals to backtest framework signals."""
    framework_signals = []
    for sig in baby_signals:
        direction = BTSignal.BUY if sig.direction == "BUY" else BTSignal.SELL
        framework_signals.append({
            'signal': direction,
            'confidence': sig.confidence,
            'entry_price': sig.entry_price,
            'take_profit': sig.take_profit,
            'stop_loss': sig.stop_loss,
            'reason': sig.reason,
            'timestamp': current_time
        })
    return framework_signals


class BabyStrategyWrapper:
    """Wraps baby strategy to work with backtest framework."""
    
    def __init__(self, strategy_instance, strategy_name):
        self.strategy = strategy_instance
        self.strategy_name = strategy_name
    
    def generate_signals(self, data, position):
        """Generate signals using baby strategy."""
        if isinstance(data, pd.DataFrame) and len(data) > 0:
            baby_signals = self.strategy.generate_signals(data, "BTCUSDT")
            framework_signals = convert_to_framework_signals(baby_signals, data.index[-1])
            return framework_signals
        return []


def generate_crypto_data(n_bars: int = 800, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic crypto OHLCV data with proper timestamps."""
    np.random.seed(seed)
    
    params = {
        'drift': 0.0005,
        'vol': 0.035,
        'price': 45000
    }
    
    returns = []
    regime = 0
    regime_duration = 0
    
    for i in range(n_bars):
        if regime_duration <= 0:
            regime = np.random.choice([0, 1, 2, 3], p=[0.5, 0.2, 0.2, 0.1])
            regime_duration = np.random.randint(20, 60)
        regime_duration -= 1
        
        if regime == 0:
            drift, vol = params['drift'], params['vol']
        elif regime == 1:
            drift, vol = params['drift'] * 3, params['vol'] * 0.8
        elif regime == 2:
            drift, vol = -params['drift'] * 2, params['vol'] * 1.2
        else:
            drift, vol = 0, params['vol'] * 1.8
        
        ret = np.random.normal(drift, vol)
        returns.append(ret)
    
    returns = np.array(returns)
    prices = params['price'] * np.exp(np.cumsum(returns))
    
    n = len(prices)
    daily_range = np.abs(returns) + np.random.exponential(params['vol'] * 0.4, n)
    
    dates = pd.date_range(start='2026-01-01', periods=n, freq='h')
    
    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, params['vol'] * 0.2, n)),
        'high': prices * (1 + daily_range * np.random.uniform(0.4, 0.8, n)),
        'low': prices * (1 - daily_range * np.random.uniform(0.4, 0.8, n)),
        'close': prices,
        'volume': np.random.lognormal(20, 0.8, n)
    }, index=dates)
    
    df['high'] = df[['high', 'open', 'close']].max(axis=1) * 1.001
    df['low'] = df[['low', 'open', 'close']].min(axis=1) * 0.999
    
    return df


def run_backtest(strategy, strategy_name, data):
    """Run backtest using the framework."""
    config = BacktestConfig(
        initial_capital=10000,
        commission=0.001,
        slippage=0.001,
        max_hold_period='168h',
        risk_per_trade=0.02
    )
    
    engine = BacktestEngine(
        strategy=strategy,
        config=config,
        data=data
    )
    
    result = engine.run()
    return result


def print_result(result, strategy_name):
    """Print backtest results."""
    print(f"\n=== {strategy_name} ===")
    print(f"Total Return: {result.total_return:.1f}%")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {result.max_drawdown:.1f}%")
    print(f"Win Rate: {result.win_rate:.1f}%")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    print(f"Number of Trades: {result.num_trades}")
    print(f"Average Trade Duration: {result.avg_trade_duration:.1f} hours")


def main():
    """Main backtesting function."""
    print("Running backtests on new strategy variations using proper framework...")
    
    # Generate test data
    data = generate_crypto_data(n_bars=800)
    
    # Initialize strategies
    strategies = [
        (BabyStrategyWrapper(KeltnerRSIConfluenceStrategy(), "KeltnerRSIConfluence"), "KeltnerRSIConfluence"),
        (BabyStrategyWrapper(ConnorsR4MeanReversionStrategy(), "ConnorsR4MeanReversion"), "ConnorsR4MeanReversion"),
        (BabyStrategyWrapper(SuperTrendMultiTimeframeStrategy(), "SuperTrendMultiTimeframe"), "SuperTrendMultiTimeframe"),
        (BabyStrategyWrapper(VolScaledKeltnerStrategy(), "VolScaledKeltner"), "VolScaledKeltner")
    ]
    
    results = []
    
    for strategy, strategy_name in strategies:
        print(f"\nTesting strategy: {strategy_name}")
        
        try:
            result = run_backtest(strategy, strategy_name, data)
            results.append((strategy_name, result))
            print_result(result, strategy_name)
        except Exception as e:
            print(f"Error testing {strategy_name}: {e}")
            import traceback
            print(traceback.format_exc())
    
    # Save results
    results_data = []
    for strategy_name, result in results:
        results_data.append({
            'strategy': strategy_name,
            'total_return': result.total_return,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'num_trades': result.num_trades,
            'avg_trade_duration': result.avg_trade_duration
        })
    
    # Save to JSON
    with open('new_strategy_variations_framework_results.json', 'w') as f:
        json.dump(results_data, f, indent=2, default=str)
    print("\nResults saved to 'new_strategy_variations_framework_results.json'")
    
    # Save to CSV
    results_df = pd.DataFrame(results_data)
    results_df.to_csv('new_strategy_variations_framework_results.csv', index=False)
    print("Results saved to 'new_strategy_variations_framework_results.csv'")
    
    return results


if __name__ == "__main__":
    main()
