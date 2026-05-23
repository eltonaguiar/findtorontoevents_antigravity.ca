#!/usr/bin/env python3
"""
Backtest with Market Regime Filtering
=====================================

Backtests the strategy with market regime detection and filtering.
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from hoffman_elite_advanced import generate_signals, Signal, SYMBOLS
from market_regime_detector import backtest_with_regime_filter


def fetch_binance_data(symbol: str, start_date: str, end_date: str, interval: str = "15m") -> pd.DataFrame:
    """
    Fetch historical data from Binance API.
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


def run_backtest_period(start_date: str, end_date: str, name: str):
    """
    Run backtest for a specific time period.
    """
    print(f"\n{'='*70}")
    print(f"PERIOD: {name} ({start_date} to {end_date})")
    print(f"{'='*70}")
    
    initial_balance = 100000
    max_risk = 0.02
    max_hold_bars = 96
    
    all_results = []
    
    for symbol in SYMBOLS:
        print(f"\nTesting {symbol}...")
        
        df = fetch_binance_data(symbol, start_date, end_date)
        if df.empty:
            print(f"Warning: No data available for {symbol}")
            continue
            
        result = backtest_with_regime_filter(df, symbol, generate_signals, 
                                           initial_balance, max_risk, max_hold_bars)
        all_results.append(result)
        
        print(f"Results for {symbol}:")
        print(f"  Total Return: {result['total_return']:.2%}")
        print(f"  Trades: {result['total_trades']}")
        print(f"  Wins/Losses: {result['win_count']}/{result['loss_count']}")
        print(f"  Win Rate: {result['win_rate']:.1%}")
        print(f"  Profit Factor: {result['profit_factor']:.2f}")
        print(f"  Max Drawdown: {result['max_drawdown']:.1%}")
    
    if all_results:
        avg_win_rate = np.mean([r['win_rate'] for r in all_results])
        avg_profit_factor = np.mean([r['profit_factor'] for r in all_results])
        total_trades = np.sum([r['total_trades'] for r in all_results])
        
        total_return = np.mean([r['total_return'] for r in all_results])
        avg_drawdown = np.mean([r['max_drawdown'] for r in all_results])
        
        print(f"\n{'='*70}")
        print("PORTFOLIO PERFORMANCE (EQUAL WEIGHT)")
        print(f"{'='*70}")
        
        print(f"Average Win Rate: {avg_win_rate:.1%}")
        print(f"Average Profit Factor: {avg_profit_factor:.2f}")
        print(f"Total Trades: {total_trades}")
        print(f"Portfolio Return: {total_return:.2%}")
        print(f"Average Max Drawdown: {avg_drawdown:.1%}")
    
    return all_results


def main():
    """Run regime-filtered backtest across multiple time periods"""
    print("="*70)
    print("HOFFMAN ELITE ADVANCED - REGIME FILTERED BACKTEST")
    print("="*70)
    
    periods = [
        (
            "2024-06-01", 
            "2024-09-30", 
            "BEAR MARKET RECOVERY"
        ),
        (
            "2024-10-01", 
            "2024-12-31", 
            "BITCOIN ETF LAUNCH"
        ),
        (
            "2025-01-01", 
            "2025-03-31", 
            "POST-ETF CONSOLIDATION"
        ),
        (
            "2025-04-01", 
            "2025-06-30", 
            "SPRING RALLY"
        ),
        (
            "2025-07-01", 
            "2025-09-30", 
            "SUMMER CONSOLIDATION"
        ),
        (
            "2025-10-01", 
            "2025-12-31", 
            "FALL BREAKOUT"
        ),
        (
            "2024-06-01", 
            "2025-12-31", 
            "FULL 18-MONTH TREND"
        )
    ]
    
    all_period_results = []
    
    for start_date, end_date, name in periods:
        results = run_backtest_period(start_date, end_date, name)
        if results:
            avg_win_rate = np.mean([r['win_rate'] for r in results])
            avg_profit_factor = np.mean([r['profit_factor'] for r in results])
            total_trades = np.sum([r['total_trades'] for r in results])
            total_return = np.mean([r['total_return'] for r in results])
            avg_drawdown = np.mean([r['max_drawdown'] for r in results])
            
            all_period_results.append({
                'name': name,
                'start_date': start_date,
                'end_date': end_date,
                'avg_win_rate': avg_win_rate,
                'avg_profit_factor': avg_profit_factor,
                'total_trades': total_trades,
                'total_return': total_return,
                'avg_drawdown': avg_drawdown
            })
    
    print("\n" + "="*70)
    print("COMPREHENSIVE PERIOD SUMMARY")
    print("="*70)
    
    print(f"{'Period':<25} | {'Trades':<6} | {'Win Rate':<8} | {'Profit Factor':<12} | {'Return':<8} | {'Drawdown':<8}")
    print(f"{'-'*25} | {'-'*6} | {'-'*8} | {'-'*12} | {'-'*8} | {'-'*8}")
    
    for period in all_period_results:
        print(f"{period['name']:<25} | {period['total_trades']:<6} | {period['avg_win_rate']:.1%}    | {period['avg_profit_factor']:.2f}        | {period['total_return']:.1%}    | {period['avg_drawdown']:.1%}    ")
    
    overall_trades = sum(period['total_trades'] for period in all_period_results)
    weighted_win_rate = sum(period['avg_win_rate'] * period['total_trades'] for period in all_period_results) / overall_trades
    weighted_profit_factor = sum(period['avg_profit_factor'] * period['total_trades'] for period in all_period_results) / overall_trades
    overall_return = sum(period['total_return'] * period['total_trades'] for period in all_period_results) / overall_trades
    overall_drawdown = max(period['avg_drawdown'] for period in all_period_results)
    
    print(f"\n{'='*70}")
    print("OVERALL PERFORMANCE (18 MONTHS)")
    print("="*70)
    
    print(f"Total Trades: {overall_trades}")
    print(f"Average Win Rate: {weighted_win_rate:.1%}")
    print(f"Average Profit Factor: {weighted_profit_factor:.2f}")
    print(f"Total Return: {overall_return:.1%}")
    print(f"Max Drawdown: {overall_drawdown:.1%}")


if __name__ == "__main__":
    main()
