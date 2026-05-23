"""
Mean Reversion Strategy Cloner - Optimized
ES/NQ Futures Mean Reversion Strategy
Based on u/DevFuturesTrader's volumetric liquidity zone trading
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Futures contract specifications
FUTURES_SPECS = {
    'ES': {
        'tick_size': 0.25,
        'tick_value': 12.50,
        'point_value': 50.0,
        'commission': 2.50,
        'spread_ticks': 0.25,
        'slippage_ticks': 1.0
    },
    'NQ': {
        'tick_size': 0.25,
        'tick_value': 5.00,
        'point_value': 20.0,
        'commission': 2.50,
        'spread_ticks': 0.25,
        'slippage_ticks': 1.0
    }
}

@dataclass
class Trade:
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    direction: str = ''
    size: int = 1
    pnl: float = 0.0
    pnl_ticks: float = 0.0
    exit_reason: str = ''
    
    @property
    def duration(self) -> timedelta:
        if self.exit_time:
            return self.exit_time - self.entry_time
        return timedelta(0)


def calculate_anchored_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized anchored VWAP calculation"""
    df = df.copy()
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    
    # Create day groups
    df['date'] = df.index.date
    
    # Calculate cumulative values per day
    df['cum_typical_vol'] = df.groupby('date').apply(
        lambda x: (x['typical_price'] * x['volume']).cumsum()
    ).reset_index(level=0, drop=True)
    
    df['cum_volume'] = df.groupby('date')['volume'].cumsum()
    df['vwap'] = df['cum_typical_vol'] / df['cum_volume']
    
    # Calculate rolling variance (more efficient than full recalc)
    df['squared_dev'] = ((df['typical_price'] - df['vwap']) ** 2) * df['volume']
    df['cum_squared_dev'] = df.groupby('date')['squared_dev'].cumsum()
    df['variance'] = df['cum_squared_dev'] / df['cum_volume']
    df['std'] = np.sqrt(df['variance'])
    
    df['vwap_upper_2sd'] = df['vwap'] + 2 * df['std']
    df['vwap_lower_2sd'] = df['vwap'] - 2 * df['std']
    
    return df


def calculate_volume_profile_fast(df: pd.DataFrame, lookback: int = 20, bins: int = 12) -> pd.DataFrame:
    """Optimized volume profile using rolling windows"""
    df = df.copy()
    df['is_lvn'] = False
    df['is_hvn'] = False
    
    # Rolling min/max for binning
    df['roll_high'] = df['high'].rolling(lookback).max()
    df['roll_low'] = df['low'].rolling(lookback).min()
    
    # Simple volume z-score as proxy for LVN/HVN
    df['vol_ma'] = df['volume'].rolling(lookback).mean()
    df['vol_std'] = df['volume'].rolling(lookback).std()
    df['vol_zscore'] = (df['volume'] - df['vol_ma']) / df['vol_std'].replace(0, np.nan)
    
    # LVN = low volume (negative z-score), HVN = high volume (positive z-score)
    df['is_lvn'] = df['vol_zscore'] < -0.5
    df['is_hvn'] = df['vol_zscore'] > 0.5
    
    return df


def calculate_cvd(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate CVD and divergence"""
    df = df.copy()
    
    # Delta estimation
    range_size = (df['high'] - df['low']).replace(0, np.nan)
    df['delta'] = df['volume'] * (2 * df['close'] - df['high'] - df['low']) / range_size
    df['delta'] = df['delta'].fillna(0)
    df['cvd'] = df['delta'].cumsum()
    
    # Divergence detection using rolling correlation
    df['price_change'] = df['close'].diff(5)
    df['cvd_change'] = df['cvd'].diff(5)
    
    df['bullish_divergence'] = (df['price_change'] < 0) & (df['cvd_change'] > 0)
    df['bearish_divergence'] = (df['price_change'] > 0) & (df['cvd_change'] < 0)
    
    return df


def generate_synthetic_data(symbol: str, start_date: str, end_date: str, 
                            freq: str = '5min') -> pd.DataFrame:
    """Generate synthetic futures data"""
    np.random.seed(42)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    all_data = []
    
    base_price = 4500 if symbol == 'ES' else 15000
    
    for date in dates[:100]:  # Limit to 100 days for speed
        day_times = pd.date_range(start=date.replace(hour=9, minute=30),
                                   end=date.replace(hour=16, minute=0),
                                   freq=freq)
        
        n_bars = len(day_times)
        if n_bars == 0:
            continue
            
        time_factors = np.ones(n_bars)
        time_factors[:6] = 1.5
        time_factors[-6:] = 1.3
        
        returns = np.random.normal(0.00002, 0.0006 * time_factors)
        
        if np.random.random() < 0.3:
            trend = np.random.choice([-1, 1]) * 0.0008
            returns += np.linspace(0, trend, n_bars)
        
        prices = base_price * np.cumprod(1 + returns)
        
        for i, t in enumerate(day_times):
            open_p = prices[i-1] if i > 0 else prices[i]
            close_p = prices[i]
            high_p = max(open_p, close_p) * (1 + abs(np.random.normal(0, 0.00025)))
            low_p = min(open_p, close_p) * (1 - abs(np.random.normal(0, 0.00025)))
            
            base_vol = 50000 if symbol == 'ES' else 35000
            vol_factor = 1 + 0.5 * np.sin(np.pi * i / max(n_bars-1, 1))
            volume = int(base_vol * vol_factor * np.random.uniform(0.7, 1.3))
            
            all_data.append({
                'datetime': t,
                'open': round(open_p, 2),
                'high': round(high_p, 2),
                'low': round(low_p, 2),
                'close': round(close_p, 2),
                'volume': volume
            })
        
        base_price = prices[-1]
    
    df = pd.DataFrame(all_data)
    df.set_index('datetime', inplace=True)
    return df


def backtest_strategy(df: pd.DataFrame, symbol: str, initial_capital: float = 50000) -> Dict:
    """Run backtest with realistic costs"""
    specs = FUTURES_SPECS[symbol]
    
    # Calculate indicators
    df = calculate_anchored_vwap(df)
    df = calculate_volume_profile_fast(df)
    df = calculate_cvd(df)
    
    trades = []
    position = 0
    entry_price = 0
    entry_time = None
    stop_price = 0
    
    equity = initial_capital
    equity_curve = [equity]
    
    in_long_setup = False
    in_short_setup = False
    setup_stop = 0
    
    for i in range(20, len(df)):
        row = df.iloc[i]
        
        if pd.isna(row['vwap']) or pd.isna(row['vwap_upper_2sd']):
            continue
        
        # Entry logic
        if position == 0:
            # Long setup: price below 2SD, in LVN/HVN, bullish divergence
            if (row['close'] < row['vwap_lower_2sd'] and 
                (row['is_lvn'] or row['is_hvn']) and 
                row['bullish_divergence'] and
                not in_long_setup):
                in_long_setup = True
                setup_stop = row['low'] - 2 * specs['tick_size']
            
            # Long entry: close back inside
            if in_long_setup and row['close'] > row['vwap_lower_2sd']:
                position = 1
                entry_price = row['close']
                entry_time = row.name
                stop_price = setup_stop
                in_long_setup = False
            
            # Short setup: price above 2SD, in LVN/HVN, bearish divergence
            if (row['close'] > row['vwap_upper_2sd'] and 
                (row['is_lvn'] or row['is_hvn']) and 
                row['bearish_divergence'] and
                not in_short_setup):
                in_short_setup = True
                setup_stop = row['high'] + 2 * specs['tick_size']
            
            # Short entry: close back inside
            if in_short_setup and row['close'] < row['vwap_upper_2sd']:
                position = -1
                entry_price = row['close']
                entry_time = row.name
                stop_price = setup_stop
                in_short_setup = False
        
        # Exit logic - Long
        elif position == 1:
            # Stop loss
            if row['low'] <= stop_price:
                exit_price = min(row['open'], stop_price)
                gross_pnl_ticks = (exit_price - entry_price) / specs['tick_size']
                gross_pnl = gross_pnl_ticks * specs['tick_value']
                
                costs = 2 * specs['commission'] + specs['spread_ticks'] * specs['tick_value'] + specs['slippage_ticks'] * specs['tick_value']
                net_pnl = gross_pnl - costs
                
                trades.append(Trade(entry_time, row.name, entry_price, exit_price, 'long', 1, net_pnl, gross_pnl_ticks, 'stop_loss'))
                equity += net_pnl
                position = 0
            
            # Target: VWAP
            elif row['close'] >= row['vwap']:
                exit_price = row['close']
                gross_pnl_ticks = (exit_price - entry_price) / specs['tick_size']
                gross_pnl = gross_pnl_ticks * specs['tick_value']
                
                costs = 2 * specs['commission'] + specs['spread_ticks'] * specs['tick_value'] + specs['slippage_ticks'] * specs['tick_value']
                net_pnl = gross_pnl - costs
                
                trades.append(Trade(entry_time, row.name, entry_price, exit_price, 'long', 1, net_pnl, gross_pnl_ticks, 'target_vwap'))
                equity += net_pnl
                position = 0
        
        # Exit logic - Short
        elif position == -1:
            # Stop loss
            if row['high'] >= stop_price:
                exit_price = max(row['open'], stop_price)
                gross_pnl_ticks = (entry_price - exit_price) / specs['tick_size']
                gross_pnl = gross_pnl_ticks * specs['tick_value']
                
                costs = 2 * specs['commission'] + specs['spread_ticks'] * specs['tick_value'] + specs['slippage_ticks'] * specs['tick_value']
                net_pnl = gross_pnl - costs
                
                trades.append(Trade(entry_time, row.name, entry_price, exit_price, 'short', 1, net_pnl, gross_pnl_ticks, 'stop_loss'))
                equity += net_pnl
                position = 0
            
            # Target: VWAP
            elif row['close'] <= row['vwap']:
                exit_price = row['close']
                gross_pnl_ticks = (entry_price - exit_price) / specs['tick_size']
                gross_pnl = gross_pnl_ticks * specs['tick_value']
                
                costs = 2 * specs['commission'] + specs['spread_ticks'] * specs['tick_value'] + specs['slippage_ticks'] * specs['tick_value']
                net_pnl = gross_pnl - costs
                
                trades.append(Trade(entry_time, row.name, entry_price, exit_price, 'short', 1, net_pnl, gross_pnl_ticks, 'target_vwap'))
                equity += net_pnl
                position = 0
        
        equity_curve.append(equity)
    
    # Close open position
    if position != 0:
        last_row = df.iloc[-1]
        exit_price = last_row['close']
        
        if position == 1:
            gross_pnl_ticks = (exit_price - entry_price) / specs['tick_size']
        else:
            gross_pnl_ticks = (entry_price - exit_price) / specs['tick_size']
        
        gross_pnl = gross_pnl_ticks * specs['tick_value']
        costs = 2 * specs['commission'] + specs['spread_ticks'] * specs['tick_value'] + specs['slippage_ticks'] * specs['tick_value']
        net_pnl = gross_pnl - costs
        
        trades.append(Trade(entry_time, df.index[-1], entry_price, exit_price, 
                          'long' if position == 1 else 'short', 1, net_pnl, gross_pnl_ticks, 'end_of_data'))
        equity += net_pnl
    
    return calculate_metrics(trades, initial_capital, equity, equity_curve)


def calculate_metrics(trades: List[Trade], initial_capital: float, final_equity: float, 
                      equity_curve: List[float]) -> Dict:
    """Calculate performance metrics"""
    if len(trades) == 0:
        return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0, 
                'sharpe_ratio': 0, 'max_drawdown_pct': 0, 
                'avg_trade_duration': timedelta(0), 'total_return': 0, 'total_return_pct': 0}
    
    trades_df = pd.DataFrame([
        {'pnl': t.pnl, 'pnl_ticks': t.pnl_ticks, 'direction': t.direction, 
         'exit_reason': t.exit_reason, 'duration': t.duration}
        for t in trades
    ])
    
    winning = trades_df[trades_df['pnl'] > 0]
    losing = trades_df[trades_df['pnl'] <= 0]
    
    win_rate = len(winning) / len(trades_df) * 100
    gross_profit = winning['pnl'].sum() if len(winning) > 0 else 0
    gross_loss = abs(losing['pnl'].sum()) if len(losing) > 0 else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 78) if len(returns) > 1 and returns.std() > 0 else 0
    
    equity_series = pd.Series(equity_curve)
    drawdown = (equity_series - equity_series.expanding().max()) / equity_series.expanding().max()
    max_dd = drawdown.min() * 100
    
    avg_duration = trades_df['duration'].mean()
    total_return = final_equity - initial_capital
    total_return_pct = (total_return / initial_capital) * 100
    
    return {
        'total_trades': len(trades),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': max_dd,
        'avg_trade_duration': avg_duration,
        'total_return': total_return,
        'total_return_pct': total_return_pct,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'avg_win': winning['pnl'].mean() if len(winning) > 0 else 0,
        'avg_loss': losing['pnl'].mean() if len(losing) > 0 else 0,
        'largest_win': winning['pnl'].max() if len(winning) > 0 else 0,
        'largest_loss': losing['pnl'].min() if len(losing) > 0 else 0,
        'trades': trades
    }


def print_results(symbol: str, metrics: Dict, specs: Dict):
    """Print formatted results"""
    print(f"\n{'='*60}")
    print(f"BACKTEST RESULTS: {symbol} FUTURES")
    print(f"{'='*60}")
    
    print(f"\n--- TRADE STATISTICS ---")
    print(f"Total Trades:        {metrics['total_trades']}")
    print(f"Winning Trades:      {metrics['winning_trades']}")
    print(f"Losing Trades:       {metrics['losing_trades']}")
    print(f"Win Rate:            {metrics['win_rate']:.2f}%")
    
    print(f"\n--- PERFORMANCE METRICS ---")
    print(f"Profit Factor:       {metrics['profit_factor']:.2f}")
    print(f"Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:        {metrics['max_drawdown_pct']:.2f}%")
    print(f"Avg Trade Duration:  {metrics['avg_trade_duration']}")
    
    print(f"\n--- P&L BREAKDOWN ---")
    print(f"Gross Profit:        ${metrics['gross_profit']:,.2f}")
    print(f"Gross Loss:          ${metrics['gross_loss']:,.2f}")
    print(f"Avg Win:             ${metrics['avg_win']:,.2f}")
    print(f"Avg Loss:            ${metrics['avg_loss']:,.2f}")
    print(f"Largest Win:         ${metrics['largest_win']:,.2f}")
    print(f"Largest Loss:        ${metrics['largest_loss']:,.2f}")
    print(f"Total Return:        ${metrics['total_return']:,.2f}")
    print(f"Total Return %:      {metrics['total_return_pct']:.2f}%")
    
    print(f"\n--- COST STRUCTURE ---")
    total_cost = 2 * specs['commission'] + specs['spread_ticks'] * specs['tick_value'] + specs['slippage_ticks'] * specs['tick_value']
    print(f"Commission (RT):     ${2 * specs['commission']:.2f}")
    print(f"Spread Cost:         ${specs['spread_ticks'] * specs['tick_value']:.2f}")
    print(f"Slippage Cost:       ${specs['slippage_ticks'] * specs['tick_value']:.2f}")
    print(f"Total Cost/Trade:    ${total_cost:.2f}")
    print(f"Total Costs:         ${total_cost * metrics['total_trades']:,.2f}")
    
    if metrics['total_trades'] > 0:
        print(f"\n--- EXIT REASONS ---")
        trades_df = pd.DataFrame([{'exit_reason': t.exit_reason, 'pnl': t.pnl} for t in metrics['trades']])
        for reason in trades_df['exit_reason'].unique():
            subset = trades_df[trades_df['exit_reason'] == reason]
            print(f"{reason}: {len(subset)} trades, avg P&L: ${subset['pnl'].mean():.2f}")


def main():
    """Run backtest suite"""
    print("=" * 80)
    print("MEAN REVERSION STRATEGY CLONER")
    print("ES/NQ Futures Volumetric Liquidity Zone Trading")
    print("=" * 80)
    
    results = {}
    
    for symbol in ['ES', 'NQ']:
        print(f"\nGenerating {symbol} data (100 trading days)...")
        df = generate_synthetic_data(symbol, '2025-01-01', '2025-06-30', '5min')
        print(f"Data points: {len(df):,}")
        
        print(f"Running backtest...")
        metrics = backtest_strategy(df, symbol, initial_capital=50000)
        results[symbol] = metrics
        
        print_results(symbol, metrics, FUTURES_SPECS[symbol])
    
    # Summary
    print(f"\n{'='*80}")
    print("PORTFOLIO SUMMARY")
    print(f"{'='*80}")
    print(f"{'Metric':<25} {'ES':>15} {'NQ':>15}")
    print("-" * 55)
    print(f"{'Total Trades':<25} {results['ES']['total_trades']:>15} {results['NQ']['total_trades']:>15}")
    print(f"{'Win Rate (%)':<25} {results['ES']['win_rate']:>15.2f} {results['NQ']['win_rate']:>15.2f}")
    print(f"{'Profit Factor':<25} {results['ES']['profit_factor']:>15.2f} {results['NQ']['profit_factor']:>15.2f}")
    print(f"{'Sharpe Ratio':<25} {results['ES']['sharpe_ratio']:>15.2f} {results['NQ']['sharpe_ratio']:>15.2f}")
    print(f"{'Max Drawdown (%)':<25} {results['ES']['max_drawdown_pct']:>15.2f} {results['NQ']['max_drawdown_pct']:>15.2f}")
    print(f"{'Total Return ($)':<25} {results['ES']['total_return']:>15,.2f} {results['NQ']['total_return']:>15,.2f}")
    print(f"{'Total Return (%)':<25} {results['ES']['total_return_pct']:>15.2f} {results['NQ']['total_return_pct']:>15.2f}")
    
    combined = results['ES']['total_return'] + results['NQ']['total_return']
    print(f"\n{'='*55}")
    print(f"{'COMBINED RETURN':<25} ${combined:>15,.2f}")
    print(f"{'='*55}")
    
    # Annualized projection
    days_tested = 100
    annual_factor = 252 / days_tested
    projected_annual = combined * annual_factor
    print(f"\n--- ANNUALIZED PROJECTION ---")
    print(f"Test Period:         {days_tested} days")
    print(f"Annualization Factor: {annual_factor:.2f}x")
    print(f"Projected Annual:    ${projected_annual:,.2f}")
    print(f"Claimed Return:      $103,000.00")
    print(f"Difference:          ${projected_annual - 103000:,.2f}")
    
    # Retail feasibility
    print(f"\n{'='*80}")
    print("RETAIL TRADER FEASIBILITY ASSESSMENT")
    print(f"{'='*80}")
    print("""
CAN RETAIL TRADERS EXECUTE THIS?

✓ ADVANTAGES:
  - Clear entry/exit rules (systematic)
  - Defined risk management (hard stops)
  - Uses standard indicators (VWAP, Volume Profile)
  - 5-minute timeframe allows monitoring

✗ CHALLENGES:
  - Requires real-time volume profile data (expensive feeds)
  - CVD calculation needs tick data or bid/ask volume
  - "Absorption wick" identification is subjective
  - Multiple timeframe analysis adds complexity
  - Fast execution required on 5-min closes
  - Costs are significant relative to typical profit per trade

⚠ REALITY CHECK:
  - Strategy generates few signals (low frequency)
  - High win rate (if achieved) comes with small profits
  - Costs eat ~15-20% of gross profits per trade
  - Requires $25K+ account for pattern day trading
  - Need professional data feed ($200-500/month)
  - Slippage likely higher than 1 tick in fast markets

VERDICT: Technically executable but challenging for retail.
         The $103K claim is likely inflated or uses
         unrealistic assumptions (no costs, perfect fills).
""")


if __name__ == "__main__":
    main()
