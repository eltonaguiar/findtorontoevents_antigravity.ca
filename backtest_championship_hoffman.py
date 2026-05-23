#!/usr/bin/env python3
"""
Backtest Championship Hoffman Elite Strategy
============================================

Backtests the Championship Hoffman Elite strategy using Binance historical data.
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from championship_hoffman_elite import generate_signals, Signal, SYMBOLS
from backtest_framework import Strategy, BacktestEngine, BacktestConfig, PositionSide, Signal as BacktestSignal


class ChampionshipHoffmanStrategy(Strategy):
    """
    Championship Hoffman Elite strategy implementation for backtesting.
    """
    
    def __init__(self, name: str = "Championship Hoffman Elite"):
        super().__init__(name)
        self.symbol = None
        
    def initialize(self, data: pd.DataFrame):
        """Initialize strategy with data"""
        super().initialize(data)
        self.symbol = data['symbol'].iloc[0]
        
    def _calculate_indicators(self):
        """Calculate technical indicators"""
        pass
        
    def on_bar(self, idx: int, bar: pd.Series) -> Optional[BacktestSignal]:
        """
        Called on each bar.
        
        Args:
            idx: Current index
            bar: Current bar data
            
        Returns:
            Signal or None
        """
        # Generate signals using the championship strategy
        signals = generate_signals(self.data.iloc[:idx+1], self.symbol, max_hold_hours=4)
        
        if signals:
            signal = signals[0]
            if signal.direction == "BUY":
                return BacktestSignal.BUY
            elif signal.direction == "SELL":
                return BacktestSignal.SELL
                
        return BacktestSignal.HOLD


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


def _date_to_timestamp(date_str: str) -> int:
    """Convert date string to timestamp in milliseconds"""
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp() * 1000)


def main():
    """Run backtest on Championship Hoffman Elite strategy"""
    print("=" * 70)
    print("CHAMPIONSHIP HOFFMAN ELITE BACKTEST")
    print("=" * 70)
    
    # Configuration
    start_date = "2025-01-01"
    end_date = "2026-01-01"
    initial_capital = 100000
    
    # Initialize backtest engine
    config = BacktestConfig(
        initial_capital=initial_capital,
        commission_rate=0.001,  # 0.1% per trade
        slippage=0.0005,  # 0.05% slippage
        max_position_pct=1.0,
        allow_short=True,
        position_sizing="percent_risk",
        risk_per_trade=0.02
    )
    
    engine = BacktestEngine(config)
    
    # Run backtest for each symbol
    all_results = []
    
    for symbol in SYMBOLS:
        print(f"\nTesting {symbol}...")
        
        # Fetch historical data
        df = fetch_binance_data(symbol, start_date, end_date)
        if df.empty:
            print(f"Warning: No data available for {symbol}")
            continue
            
        # Initialize strategy
        strategy = ChampionshipHoffmanStrategy(name=f"Championship Hoffman {symbol}")
        
        # Run backtest
        engine.set_data(df)
        engine.set_strategy(strategy)
        result = engine.run()
        
        all_results.append({
            'symbol': symbol,
            'result': result
        })
        
        # Print symbol-specific results
        print(f"\n{symbol} Results:")
        print(f"Total Return: {result.total_return:.2%}")
        print(f"Annualized Return: {result.annualized_return:.2%}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {result.max_drawdown:.2%}")
        print(f"Win Rate: {result.win_rate:.2%}")
        print(f"Profit Factor: {result.profit_factor:.2f}")
        print(f"Number of Trades: {result.num_trades}")
        
        # Save detailed results
        result.to_json(f"prop_firm_reports/{symbol}_backtest.json")
    
    # Calculate portfolio performance
    if all_results:
        print("\n" + "=" * 70)
        print("PORTFOLIO PERFORMANCE")
        print("=" * 70)
        
        avg_win_rate = np.mean([r['result'].win_rate for r in all_results])
        avg_profit_factor = np.mean([r['result'].profit_factor for r in all_results])
        total_trades = np.sum([r['result'].num_trades for r in all_results])
        
        print(f"Average Win Rate: {avg_win_rate:.2%}")
        print(f"Average Profit Factor: {avg_profit_factor:.2f}")
        print(f"Total Trades: {total_trades}")
        
        # Calculate weighted performance (equal weight)
        total_return = np.mean([r['result'].total_return for r in all_results])
        annualized_return = np.mean([r['result'].annualized_return for r in all_results])
        avg_sharpe = np.mean([r['result'].sharpe_ratio for r in all_results])
        avg_drawdown = np.mean([r['result'].max_drawdown for r in all_results])
        
        print(f"Weighted Total Return: {total_return:.2%}")
        print(f"Weighted Annualized Return: {annualized_return:.2%}")
        print(f"Weighted Sharpe Ratio: {avg_sharpe:.2f}")
        print(f"Weighted Max Drawdown: {avg_drawdown:.2%}")


if __name__ == "__main__":
    main()
