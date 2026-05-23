"""
Backtest Framework Runner Version 2
===================================

Backtests additional strategy variations using the backtest framework.
Includes 5 new strategies based on quantitative and technical algorithms.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import backtest framework
from backtest_framework import BacktestConfig, BacktestEngine, DataLoader

# Import strategy wrappers
from strategy_framework_wrappers import (
    KeltnerRSIConfluenceWrapper,
    ConnorsR4MeanReversionWrapper,
    SuperTrendMultiTimeframeWrapper,
    VolScaledKeltnerWrapper
)
from strategy_framework_wrappers_v2 import (
    AdaptiveBollingerMomentumWrapper,
    VolatilityRegimeBreakoutWrapper,
    KamaVolatilityAdaptiveWrapper,
    MultiTimeframeEMACloudWrapper,
    MovingAverageSlopeMomentumWrapper
)


def generate_crypto_data(n_bars: int = 1000, seed: int = 42) -> pd.DataFrame:
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
        commission_rate=0.001,
        slippage=0.001,
        max_position_pct=1.0,
        allow_short=True,
        position_sizing="fixed",
        risk_per_trade=0.02
    )
    
    engine = BacktestEngine(config)
    engine.set_data(data)
    engine.set_strategy(strategy)
    
    result = engine.run()
    return result


def print_result(result, strategy_name):
    """Print backtest results."""
    print(f"\n=== {strategy_name} ===")
    print(f"Total Return:        {result.total_return:.2%}")
    print(f"Annualized Return:   {result.annualized_return:.2%}")
    print(f"Sharpe Ratio:        {result.sharpe_ratio:.2f}")
    print(f"Sortino Ratio:       {result.sortino_ratio:.2f}")
    print(f"Max Drawdown:        {result.max_drawdown:.2%}")
    print(f"Calmar Ratio:        {result.calmar_ratio:.2f}")
    print(f"Win Rate:            {result.win_rate:.2%}")
    print(f"Profit Factor:       {result.profit_factor:.2f}")
    print(f"Number of Trades:    {result.num_trades}")
    print(f"Avg Trade Return:    {result.avg_trade_return:.2%}")
    print(f"Volatility:          {result.volatility:.2%}")


def main():
    """Main backtesting function."""
    print("Running backtests on additional strategy variations (v2)...")
    
    # Generate test data
    data = generate_crypto_data(n_bars=1000)
    
    # Initialize all strategies
    strategies = [
        # Initial 4 strategies
        (KeltnerRSIConfluenceWrapper(), "KeltnerRSIConfluence"),
        (ConnorsR4MeanReversionWrapper(), "ConnorsR4MeanReversion"),
        (SuperTrendMultiTimeframeWrapper(), "SuperTrendMultiTimeframe"),
        (VolScaledKeltnerWrapper(), "VolScaledKeltner"),
        # New 5 strategies
        (AdaptiveBollingerMomentumWrapper(), "AdaptiveBollingerMomentum"),
        (VolatilityRegimeBreakoutWrapper(), "VolatilityRegimeBreakout"),
        (KamaVolatilityAdaptiveWrapper(), "KamaVolatilityAdaptive"),
        (MultiTimeframeEMACloudWrapper(), "MultiTimeframeEMACloud"),
        (MovingAverageSlopeMomentumWrapper(), "MovingAverageSlopeMomentum")
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
            'annualized_return': result.annualized_return,
            'sharpe_ratio': result.sharpe_ratio,
            'sortino_ratio': result.sortino_ratio,
            'max_drawdown': result.max_drawdown,
            'calmar_ratio': result.calmar_ratio,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'num_trades': result.num_trades,
            'avg_trade_return': result.avg_trade_return,
            'volatility': result.volatility,
            'avg_win': result.avg_win,
            'avg_loss': result.avg_loss,
            'largest_win': result.largest_win,
            'largest_loss': result.largest_loss,
            'consecutive_wins': result.consecutive_wins,
            'consecutive_losses': result.consecutive_losses,
            'avg_trade_duration_days': result.avg_trade_duration.days if result.avg_trade_duration else 0
        })
    
    # Save to JSON
    with open('new_strategy_variations_framework_results_v2.json', 'w') as f:
        json.dump(results_data, f, indent=2, default=str)
    print("\nResults saved to 'new_strategy_variations_framework_results_v2.json'")
    
    # Save to CSV
    results_df = pd.DataFrame(results_data)
    results_df.to_csv('new_strategy_variations_framework_results_v2.csv', index=False)
    print("Results saved to 'new_strategy_variations_framework_results_v2.csv'")
    
    return results


if __name__ == "__main__":
    main()
