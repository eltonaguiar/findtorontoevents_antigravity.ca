#!/usr/bin/env python3
"""
Backtest Optimized Strategy on Volatile Period
==============================================

Backtests the optimized strategy on a higher volatility period.
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from optimized_hoffman_strategy import generate_signals, Signal, SYMBOLS


def fetch_binance_data(symbol: str, start_date: str, end_date: str, interval: str = "15m") -> pd.DataFrame:
    """
    Fetch historical data from Binance API.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Timeframe (default: 15m)
        
    Returns:
        DataFrame with OHLCV data
    """
    try:
        def _date_to_timestamp(date_str: str) -> int:
            return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp() * 1000)
            
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={_date_to_timestamp(start_date)}&endTime={_date_to_timestamp(end_date)}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
            
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        df.set_index('open_time', inplace=True)
        df['symbol'] = symbol
        
        return df
        
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()


def simulate_trading(df: pd.DataFrame, symbol: str, initial_balance: float = 100000, max_risk: float = 0.02, max_hold: int = 96) -> dict:
    """
    Simulate trading with actual price movement.
    
    Args:
        df: Historical OHLCV data
        symbol: Trading symbol
        initial_balance: Starting balance
        max_risk: Maximum risk per trade
        max_hold: Maximum hold time in bars (15min * 96 = 24 hours)
        
    Returns:
        Performance metrics
    """
    balance = initial_balance
    peak_balance = initial_balance
    positions = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trade_count = 0
    win_count = 0
    loss_count = 0
    total_pnl = 0
    gross_profit = 0
    gross_loss = 0
    max_drawdown = 0
    
    # Iterate through each bar to find signals and execute trades
    i = 100
    while i < len(df):
        # Check for signals
        bar_data = df.iloc[:i+1]
        signals = generate_signals(bar_data, symbol, max_hold_hours=4)
        
        if signals and positions == 0:
            signal = signals[0]
            trade_count += 1
            
            # Calculate position size
            risk_amount = balance * max_risk
            stop_loss_distance = abs(signal.entry_price - signal.stop_loss)
            
            if stop_loss_distance > 0:
                position_size = risk_amount / stop_loss_distance
                
                # Enter trade
                positions = position_size
                entry_price = signal.entry_price
                stop_loss = signal.stop_loss
                take_profit = signal.take_profit
                
                # Move to next bar
                i += 1
                
                # Find exit
                exit_i = i
                exit_found = False
                max_exit_i = min(i + max_hold, len(df))
                
                while exit_i < max_exit_i:
                    current_high = df['high'].iloc[exit_i]
                    current_low = df['low'].iloc[exit_i]
                    current_close = df['close'].iloc[exit_i]
                    
                    if signal.direction == "BUY":
                        # Check if SL or TP hit
                        if current_low <= stop_loss:
                            exit_price = stop_loss
                            pnl = (exit_price - entry_price) * positions
                            exit_found = True
                        elif current_high >= take_profit:
                            exit_price = take_profit
                            pnl = (exit_price - entry_price) * positions
                            exit_found = True
                        elif exit_i == max_exit_i - 1:
                            # Time stop
                            exit_price = current_close
                            pnl = (exit_price - entry_price) * positions
                            exit_found = True
                    else:
                        # SHORT trade
                        if current_high >= stop_loss:
                            exit_price = stop_loss
                            pnl = (entry_price - exit_price) * positions
                            exit_found = True
                        elif current_low <= take_profit:
                            exit_price = take_profit
                            pnl = (entry_price - exit_price) * positions
                            exit_found = True
                        elif exit_i == max_exit_i - 1:
                            # Time stop
                            exit_price = current_close
                            pnl = (entry_price - exit_price) * positions
                            exit_found = True
                            
                    if exit_found:
                        # Exit trade
                        balance += pnl
                        total_pnl += pnl
                        
                        if pnl > 0:
                            win_count += 1
                            gross_profit += pnl
                        else:
                            loss_count += 1
                            gross_loss += abs(pnl)
                            
                        positions = 0
                        entry_price = 0
                        stop_loss = 0
                        take_profit = 0
                        
                        # Update peak and drawdown
                        if balance > peak_balance:
                            peak_balance = balance
                            
                        current_drawdown = (peak_balance - balance) / peak_balance
                        if current_drawdown > max_drawdown:
                            max_drawdown = current_drawdown
                            
                        i = exit_i  # Move to exit bar
                        break
                        
                    exit_i += 1
                    
            else:
                i += 1
        else:
            i += 1
            
    # Calculate performance metrics
    win_rate = win_count / trade_count if trade_count > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    total_return = (balance - initial_balance) / initial_balance
    average_win = gross_profit / win_count if win_count > 0 else 0
    average_loss = gross_loss / loss_count if loss_count > 0 else 0
    
    return {
        'symbol': symbol,
        'initial_balance': initial_balance,
        'final_balance': balance,
        'total_return': total_return,
        'total_pnl': total_pnl,
        'total_trades': trade_count,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'average_win': average_win,
        'average_loss': average_loss,
        'peak_balance': peak_balance,
        'max_drawdown': max_drawdown
    }


def main():
    """Run backtest on volatile period"""
    print("=" * 70)
    print("OPTIMIZED HOFFMAN STRATEGY - VOLATILE PERIOD")
    print("=" * 70)
    
    # Configuration - volatile period (Bitcoin ETF launch)
    start_date = "2024-10-01"
    end_date = "2024-12-31"
    initial_balance = 100000
    max_risk = 0.02
    max_hold_bars = 96
    
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    print(f"Risk per Trade: {max_risk:.0%}")
    print()
    
    # Run backtest for each symbol
    all_results = []
    
    for symbol in SYMBOLS:
        print(f"Testing {symbol}...")
        
        df = fetch_binance_data(symbol, start_date, end_date)
        if df.empty:
            print(f"Warning: No data available for {symbol}")
            continue
            
        result = simulate_trading(df, symbol, initial_balance, max_risk, max_hold_bars)
        all_results.append(result)
        
        print(f"Results for {symbol}:")
        print(f"  Total Return: {result['total_return']:.2%}")
        print(f"  Trades: {result['total_trades']}")
        print(f"  Wins/Losses: {result['win_count']}/{result['loss_count']}")
        print(f"  Win Rate: {result['win_rate']:.1%}")
        print(f"  Profit Factor: {result['profit_factor']:.2f}")
        print(f"  Max Drawdown: {result['max_drawdown']:.1%}")
        print()
    
    # Calculate portfolio performance (equal weight)
    if all_results:
        print("=" * 70)
        print("PORTFOLIO PERFORMANCE (EQUAL WEIGHT)")
        print("=" * 70)
        
        avg_win_rate = np.mean([r['win_rate'] for r in all_results])
        avg_profit_factor = np.mean([r['profit_factor'] for r in all_results])
        total_trades = np.sum([r['total_trades'] for r in all_results])
        
        total_return = np.mean([r['total_return'] for r in all_results])
        avg_drawdown = np.mean([r['max_drawdown'] for r in all_results])
        
        print(f"Average Win Rate: {avg_win_rate:.1%}")
        print(f"Average Profit Factor: {avg_profit_factor:.2f}")
        print(f"Total Trades: {total_trades}")
        print(f"Portfolio Return: {total_return:.2%}")
        print(f"Average Max Drawdown: {avg_drawdown:.1%}")


if __name__ == "__main__":
    main()
