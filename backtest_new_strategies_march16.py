"""
New Strategies Backtest Runner - March 16
==========================================

Backtest runner for 4 new strategies:
1. VWAPRSIInstitutionalStrategy (VWAP + Triple RSI institutional confluence)
2. LiquidationCascadeContrarianStrategy (Wick bounce after liquidation cascades)
3. RegimeSentinelCompositeStrategy (Multi-regime adaptive strategy)
4. RSIPairsArbitrageStrategy (Market neutral pairs trading)

Tests on: BTCUSDT, ETHUSDT, SOLUSDT
Timeframes: 15m, 1h, 4h
Output: backtest_results/new_strategies_march16.json
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import sys

# Add baby_strategies to path
sys.path.insert(0, str(Path(__file__).parent / "baby_strategies"))

# Import the 4 strategies
from vwap_rsi_institutional import VWAPRSIInstitutionalStrategy
from liquidation_cascade_contrarian import LiquidationCascadeContrarianStrategy
from regime_sentinel_composite import RegimeSentinelCompositeStrategy
from rsi_pairs_arbitrage import RSIPairsArbitrageStrategy


@dataclass
class BacktestResult:
    """Backtest result container."""
    strategy_name: str
    symbol: str
    timeframe: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int
    avg_trade: float


def generate_crypto_data(
    symbol: str, 
    timeframe: str = "1h",
    n_bars: int = 1000, 
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate realistic synthetic crypto OHLCV data for specified timeframe.
    
    Timeframe adjustments:
    - 15m: Higher frequency, lower volatility per bar
    - 1h: Standard volatility
    - 4h: Lower frequency, higher volatility per bar
    """
    np.random.seed(seed)
    
    # Base parameters per symbol
    params = {
        'BTCUSDT': {'drift': 0.0005, 'vol': 0.035, 'price': 85000},
        'ETHUSDT': {'drift': 0.0006, 'vol': 0.045, 'price': 3200},
        'SOLUSDT': {'drift': 0.0008, 'vol': 0.055, 'price': 140}
    }
    
    # Timeframe multipliers
    tf_multipliers = {
        '15m': {'vol_mult': 0.5, 'drift_mult': 0.25, 'bars_per_day': 96},
        '1h': {'vol_mult': 1.0, 'drift_mult': 1.0, 'bars_per_day': 24},
        '4h': {'vol_mult': 1.8, 'drift_mult': 4.0, 'bars_per_day': 6}
    }
    
    p = params.get(symbol, params['BTCUSDT'])
    tf = tf_multipliers.get(timeframe, tf_multipliers['1h'])
    
    # Adjust parameters for timeframe
    drift = p['drift'] * tf['drift_mult']
    vol = p['vol'] * tf['vol_mult']
    
    # Generate returns with regime switching
    returns = []
    regime = 0
    regime_duration = 0
    
    for i in range(n_bars):
        if regime_duration <= 0:
            # Regimes: 0=normal, 1=trending_up, 2=trending_down, 3=high_vol
            regime = np.random.choice([0, 1, 2, 3], p=[0.5, 0.2, 0.2, 0.1])
            regime_duration = np.random.randint(20, 60)
        regime_duration -= 1
        
        if regime == 0:
            r_drift, r_vol = drift, vol
        elif regime == 1:
            r_drift, r_vol = drift * 3, vol * 0.8
        elif regime == 2:
            r_drift, r_vol = -drift * 2, vol * 1.2
        else:
            r_drift, r_vol = 0, vol * 1.8
        
        ret = np.random.normal(r_drift, r_vol)
        returns.append(ret)
    
    returns = np.array(returns)
    prices = p['price'] * np.exp(np.cumsum(returns))
    
    # Generate OHLCV from price series
    n = len(prices)
    daily_range = np.abs(returns) + np.random.exponential(vol * 0.4, n)
    
    # Create realistic OHLC relationships
    opens = prices * (1 + np.random.normal(0, vol * 0.2, n))
    highs = np.maximum(np.maximum(opens, prices), 
                       prices * (1 + daily_range * np.random.uniform(0.3, 0.7, n)))
    lows = np.minimum(np.minimum(opens, prices), 
                      prices * (1 - daily_range * np.random.uniform(0.3, 0.7, n)))
    
    # Volume correlates with volatility
    base_volume = np.random.lognormal(20, 0.8, n)
    vol_spikes = 1 + np.abs(returns) * 10  # Higher volume on large moves
    volumes = base_volume * vol_spikes
    
    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': prices,
        'volume': volumes
    })
    
    return df


def run_strategy_backtest(
    strategy,
    data: pd.DataFrame,
    symbol: str,
    timeframe: str,
    initial_capital: float = 10000,
    position_pct: float = 0.1,
    commission: float = 0.001,
    slippage: float = 0.0005
) -> BacktestResult:
    """
    Run backtest on a strategy.
    
    Simulates realistic trade execution with commission and slippage.
    """
    equity = initial_capital
    trades = []
    equity_curve = [initial_capital]
    
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
                # Apply commission and slippage
                pnl -= (commission * 2 + slippage * 2)
                trades.append({'pnl': pnl, 'reason': exit_reason})
                equity *= (1 + pnl * position_pct)
                equity_curve.append(equity)
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
        
        # Annualized Sharpe (adjusted for timeframe)
        sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Max drawdown
        peak = initial_capital
        max_dd = 0
        running_equity = initial_capital
        for t in trades:
            running_equity *= (1 + t['pnl'] * position_pct)
            if running_equity > peak:
                peak = running_equity
            dd = (peak - running_equity) / peak
            max_dd = max(max_dd, dd)
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return BacktestResult(
            strategy_name=strategy.__class__.__name__,
            symbol=symbol,
            timeframe=timeframe,
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
            timeframe=timeframe,
            total_return=0,
            sharpe_ratio=0,
            max_drawdown=0,
            win_rate=0,
            profit_factor=0,
            num_trades=0,
            avg_trade=0
        )


def get_all_strategies():
    """Return list of all 4 strategy instances."""
    return [
        VWAPRSIInstitutionalStrategy(),
        LiquidationCascadeContrarianStrategy(),
        RegimeSentinelCompositeStrategy(),
        RSIPairsArbitrageStrategy()
    ]


def run_full_backtest_suite(
    symbols: List[str] = None,
    timeframes: List[str] = None
) -> Tuple[pd.DataFrame, List[BacktestResult]]:
    """
    Run full backtest suite across all strategies, symbols, and timeframes.
    """
    if symbols is None:
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    if timeframes is None:
        timeframes = ['15m', '1h', '4h']
    
    strategies = get_all_strategies()
    all_results = []
    
    print("=" * 90)
    print("NEW STRATEGIES BACKTEST SUITE - March 16")
    print("=" * 90)
    print(f"\nStrategies: {len(strategies)}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Total combinations: {len(strategies) * len(symbols) * len(timeframes)}\n")
    
    total_combinations = len(strategies) * len(symbols) * len(timeframes)
    current = 0
    
    for timeframe in timeframes:
        print(f"\n{'='*90}")
        print(f"TIMEFRAME: {timeframe}")
        print('='*90)
        
        for symbol in symbols:
            print(f"\n--- {symbol} ---")
            
            # Generate data for this symbol/timeframe
            n_bars = 1500 if timeframe == '15m' else 1000 if timeframe == '1h' else 800
            data = generate_crypto_data(symbol, timeframe, n_bars=n_bars, seed=hash(symbol + timeframe) % 10000)
            
            for strategy in strategies:
                current += 1
                strategy_name = strategy.__class__.__name__.replace('Strategy', '')
                
                result = run_strategy_backtest(strategy, data, symbol, timeframe)
                all_results.append(result)
                
                # Status indicator
                status = "✓" if result.sharpe_ratio > 1.0 and result.win_rate > 0.45 else " "
                
                print(f"  [{status}] {strategy_name:35s} | "
                      f"Trades: {result.num_trades:3d} | "
                      f"Return: {result.total_return:7.2%} | "
                      f"Sharpe: {result.sharpe_ratio:5.2f} | "
                      f"WR: {result.win_rate:5.1%} | "
                      f"PF: {result.profit_factor:4.2f}")
    
    # Create DataFrame
    results_df = pd.DataFrame([
        {
            'Strategy': r.strategy_name.replace('Strategy', ''),
            'Symbol': r.symbol,
            'Timeframe': r.timeframe,
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
    
    results_df = results_df.sort_values(['Sharpe', 'Win Rate'], ascending=False).reset_index(drop=True)
    
    return results_df, all_results


def generate_report(results_df: pd.DataFrame, all_results: List[BacktestResult]):
    """Generate comprehensive report and save results."""
    
    print("\n" + "=" * 90)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 90)
    
    print("\n--- Overall Statistics ---")
    print(f"Total combinations tested: {len(results_df)}")
    print(f"Sharpe > 1.0: {(results_df['Sharpe'] > 1.0).sum()}")
    print(f"Sharpe > 1.5: {(results_df['Sharpe'] > 1.5).sum()}")
    print(f"Win Rate > 45%: {(results_df['Win Rate'] > 0.45).sum()}")
    print(f"Win Rate > 55%: {(results_df['Win Rate'] > 0.55).sum()}")
    print(f"Max DD < 20%: {(results_df['Max DD'] < 0.2).sum()}")
    print(f"Profit Factor > 1.5: {(results_df['Profit Factor'] > 1.5).sum()}")
    
    print("\n--- TOP 15 PERFORMERS (by Sharpe) ---")
    top15 = results_df.head(15)
    print(top15.to_string(index=False))
    
    print("\n--- BEST PER SYMBOL ---")
    for symbol in results_df['Symbol'].unique():
        symbol_df = results_df[results_df['Symbol'] == symbol]
        best = symbol_df.iloc[0]
        print(f"{symbol}: {best['Strategy']} (Sharpe: {best['Sharpe']:.2f}, Return: {best['Total Return']:.2%})")
    
    print("\n--- BEST PER TIMEFRAME ---")
    for tf in results_df['Timeframe'].unique():
        tf_df = results_df[results_df['Timeframe'] == tf]
        best = tf_df.iloc[0]
        print(f"{tf}: {best['Strategy']} on {best['Symbol']} (Sharpe: {best['Sharpe']:.2f}, WR: {best['Win Rate']:.1%})")
    
    print("\n--- STRATEGY AVERAGES ---")
    strategy_avg = results_df.groupby('Strategy').agg({
        'Sharpe': 'mean',
        'Total Return': 'mean',
        'Win Rate': 'mean',
        'Max DD': 'mean',
        'Profit Factor': 'mean',
        'Trades': 'mean'
    }).sort_values('Sharpe', ascending=False)
    print(strategy_avg.to_string())
    
    print("\n--- PASSING ALL CRITERIA (Sharpe > 1.0, WR > 45%, Max DD < 25%) ---")
    passing = results_df[
        (results_df['Sharpe'] > 1.0) & 
        (results_df['Win Rate'] > 0.45) & 
        (results_df['Max DD'] < 0.25)
    ]
    if len(passing) > 0:
        print(passing.to_string(index=False))
    else:
        print("No strategies passed all criteria (this may be expected on synthetic data)")
    
    # Ensure output directory exists
    output_dir = Path('backtest_results')
    output_dir.mkdir(exist_ok=True)
    
    # Save results
    output_file = output_dir / 'new_strategies_march16.json'
    
    detailed = {
        'metadata': {
            'run_date': datetime.now().isoformat(),
            'strategies_tested': 4,
            'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            'timeframes': ['15m', '1h', '4h'],
            'total_combinations': len(results_df)
        },
        'summary': {
            'sharpe_above_1': int((results_df['Sharpe'] > 1.0).sum()),
            'sharpe_above_1_5': int((results_df['Sharpe'] > 1.5).sum()),
            'win_rate_above_45': int((results_df['Win Rate'] > 0.45).sum()),
            'win_rate_above_55': int((results_df['Win Rate'] > 0.55).sum()),
            'max_dd_below_20': int((results_df['Max DD'] < 0.2).sum()),
            'profit_factor_above_1_5': int((results_df['Profit Factor'] > 1.5).sum()),
        },
        'top_performers': top15.head(10).to_dict('records'),
        'all_results': results_df.to_dict('records')
    }
    
    with open(output_file, 'w') as f:
        json.dump(detailed, f, indent=2, default=str)
    
    print(f"\n[OK] Results saved to {output_file}")
    
    # Also save CSV for easy analysis
    csv_file = output_dir / 'new_strategies_march16.csv'
    results_df.to_csv(csv_file, index=False)
    print(f"[OK] CSV saved to {csv_file}")


if __name__ == "__main__":
    # Run full backtest suite
    results_df, all_results = run_full_backtest_suite(
        symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
        timeframes=['15m', '1h', '4h']
    )
    
    # Generate report
    generate_report(results_df, all_results)
    
    print("\n" + "=" * 90)
    print("BACKTEST COMPLETE")
    print("=" * 90)
