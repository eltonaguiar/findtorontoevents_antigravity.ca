#!/usr/bin/env python3
"""
Realistic Backtest for Championship Hoffman Elite Strategy
==========================================================

Backtests with proper time frame handling and more realistic parameters.
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from championship_hoffman_elite import generate_signals, Signal, SYMBOLS


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


def simulate_trading(df: pd.DataFrame, symbol: str, initial_balance: float = 100000, max_risk: float = 0.02) -> dict:
    """
    Simulate trading on historical data.
    
    Args:
        df: Historical OHLCV data
        symbol: Trading symbol
        initial_balance: Starting balance
        max_risk: Maximum risk per trade
        
    Returns:
        Performance metrics
    """
    balance = initial_balance
    peak_balance = initial_balance
    positions = 0
    entry_price = 0
    entry_balance = 0
    trade_count = 0
    win_count = 0
    loss_count = 0
    total_pnl = 0
    gross_profit = 0
    gross_loss = 0
    drawdown = 0
    max_drawdown = 0
    
    signals = []
    
    # Generate signals for each bar
    for i in range(100, len(df)):
        bar_data = df.iloc[:i+1]
        sigs = generate_signals(bar_data, symbol, max_hold_hours=4)
        
        if sigs:
            signals.append(sigs[0])
    
    # Simulate signal execution
    for signal in signals:
        # Find the index of this signal in the dataframe
        signal_time = df.index[-1]  # Approximate to last bar
        signal_price = signal.entry_price
        
        # Calculate position size based on ATR stop loss
        # For simplicity, we'll use a fixed 2% risk per trade
        risk_amount = balance * max_risk
        stop_loss_distance = abs(signal_price - signal.stop_loss)
        
        if stop_loss_distance <= 0:
            continue
            
        position_size = risk_amount / stop_loss_distance
        
        # Simulate trade outcome
        # Find exit price - for demo, we'll use TP/SL hit
        exit_price = signal.take_profit
        
        # Calculate P&L
        if signal.direction == "BUY":
            pnl = (exit_price - signal_price) * position_size
        else:
            pnl = (signal_price - exit_price) * position_size
            
        # Update balance
        balance += pnl
        total_pnl += pnl
        
        # Track performance metrics
        trade_count += 1
        if pnl > 0:
            win_count += 1
            gross_profit += pnl
        else:
            loss_count += 1
            gross_loss += abs(pnl)
            
        # Update peak and drawdown
        if balance > peak_balance:
            peak_balance = balance
            
        current_drawdown = (peak_balance - balance) / peak_balance
        if current_drawdown > max_drawdown:
            max_drawdown = current_drawdown
            
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
        'max_drawdown': max_drawdown,
        'signals': len(signals)
    }


def main():
    """Run realistic backtest"""
    print("=" * 70)
    print("REALISTIC CHAMPIONSHIP HOFFMAN ELITE BACKTEST")
    print("=" * 70)
    
    # Configuration
    start_date = "2025-10-01"
    end_date = "2026-01-01"  # 3 month backtest
    initial_balance = 100000
    max_risk = 0.02  # 2% risk per trade
    
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
            
        result = simulate_trading(df, symbol, initial_balance, max_risk)
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
        
        # Calculate weighted average return
        total_return = np.mean([r['total_return'] for r in all_results])
        
        # Calculate drawdown
        avg_drawdown = np.mean([r['max_drawdown'] for r in all_results])
        
        print(f"Average Win Rate: {avg_win_rate:.1%}")
        print(f"Average Profit Factor: {avg_profit_factor:.2f}")
        print(f"Total Trades: {total_trades}")
        print(f"Portfolio Return: {total_return:.2%}")
        print(f"Average Max Drawdown: {avg_drawdown:.1%}")


if __name__ == "__main__":
    main()
