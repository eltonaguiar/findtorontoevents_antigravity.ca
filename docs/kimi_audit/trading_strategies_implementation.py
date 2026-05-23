"""
Proven Trading Strategies - Python Implementation Guide
======================================================

This module provides working code examples for backtesting
the top strategies from the research report.

Requirements:
    pip install pandas numpy matplotlib backtrader ta

Author: AI Research Assistant
Date: March 16, 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class TradingStrategy:
    """Base class for trading strategies"""

    def __init__(self, df):
        """
        Initialize with OHLCV dataframe

        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()
        self.signals = pd.DataFrame(index=df.index)

    def calculate_indicators(self):
        """Calculate required indicators - override in subclass"""
        pass

    def generate_signals(self):
        """Generate buy/sell signals - override in subclass"""
        pass

    def backtest(self, initial_capital=10000, risk_per_trade=0.02):
        """
        Run backtest simulation

        Args:
            initial_capital: Starting capital
            risk_per_trade: Risk per trade (0.02 = 2%)

        Returns:
            Dictionary with performance metrics
        """
        self.calculate_indicators()
        self.generate_signals()

        capital = initial_capital
        position = 0
        trades = []
        equity_curve = [capital]

        for i in range(1, len(self.df)):
            # Check for entry signals
            if self.signals['buy'].iloc[i] == 1 and position == 0:
                entry_price = self.df['close'].iloc[i]
                position_size = (capital * risk_per_trade) / (entry_price * 0.02)  # 2% stop
                position = position_size
                entry_time = self.df.index[i]

            # Check for exit signals
            elif self.signals['sell'].iloc[i] == 1 and position > 0:
                exit_price = self.df['close'].iloc[i]
                pnl = (exit_price - entry_price) * position
                capital += pnl
                position = 0

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': self.df.index[i],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return_pct': (exit_price - entry_price) / entry_price * 100
                })

            equity_curve.append(capital + (position * self.df['close'].iloc[i] if position > 0 else 0))

        # Calculate metrics
        trades_df = pd.DataFrame(trades)

        if len(trades_df) == 0:
            return {"error": "No trades generated"}

        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] <= 0]

        metrics = {
            'total_trades': len(trades_df),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades_df) * 100,
            'total_return': (capital - initial_capital) / initial_capital * 100,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 else float('inf'),
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'max_drawdown': self._calculate_max_drawdown(equity_curve),
            'trades': trades_df
        }

        return metrics

    def _calculate_max_drawdown(self, equity_curve):
        """Calculate maximum drawdown"""
        peak = equity_curve[0]
        max_dd = 0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        return max_dd * 100


class HoffmanStrategy(TradingStrategy):
    """
    Hoffman Trading Method Implementation

    Uses multiple EMA alignment with pullback signals
    """

    def __init__(self, df, ema_fast=3, ema_medium=5, ema_slow=18):
        super().__init__(df)
        self.ema_fast = ema_fast
        self.ema_medium = ema_medium
        self.ema_slow = ema_slow

    def calculate_indicators(self):
        """Calculate EMAs"""
        self.df['ema_fast'] = self.df['close'].ewm(span=self.ema_fast).mean()
        self.df['ema_medium'] = self.df['close'].ewm(span=self.ema_medium).mean()
        self.df['ema_slow'] = self.df['close'].ewm(span=self.ema_slow).mean()

        # Calculate pullback (simplified IRB)
        self.df['pullback'] = (
            (self.df['close'] < self.df['open']) & 
            (self.df['close'].shift(1) > self.df['open'].shift(1))
        ).astype(int)

    def generate_signals(self):
        """Generate buy/sell signals based on Hoffman Method"""
        # Bullish alignment: fast > medium > slow
        bullish = (
            (self.df['ema_fast'] > self.df['ema_medium']) & 
            (self.df['ema_medium'] > self.df['ema_slow'])
        )

        # Bearish alignment: fast < medium < slow
        bearish = (
            (self.df['ema_fast'] < self.df['ema_medium']) & 
            (self.df['ema_medium'] < self.df['ema_slow'])
        )

        # Buy signal: bullish alignment + price above fast EMA + pullback
        self.signals['buy'] = (
            bullish & 
            (self.df['close'] > self.df['ema_fast']) & 
            (self.df['pullback'] == 1)
        ).astype(int)

        # Sell signal: bearish alignment + price below fast EMA + pullback
        self.signals['sell'] = (
            bearish & 
            (self.df['close'] < self.df['ema_fast']) & 
            (self.df['pullback'] == 1)
        ).astype(int)


class VWAPBounceStrategy(TradingStrategy):
    """
    VWAP Trend Continuation Bounce Strategy

    Buy when price returns to VWAP in uptrend with rejection
    """

    def calculate_indicators(self):
        """Calculate VWAP and std deviation bands"""
        # Calculate VWAP
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        self.df['vwap'] = (typical_price * self.df['volume']).cumsum() / self.df['volume'].cumsum()

        # Calculate standard deviation bands
        self.df['std'] = typical_price.rolling(20).std()
        self.df['upper_band'] = self.df['vwap'] + (self.df['std'] * 2)
        self.df['lower_band'] = self.df['vwap'] - (self.df['std'] * 2)

        # Trend detection (price above/below VWAP)
        self.df['trend'] = np.where(self.df['close'] > self.df['vwap'], 1, -1)

    def generate_signals(self):
        """Generate signals based on VWAP bounce"""
        # Buy: Price near VWAP in uptrend with rejection
        price_near_vwap = abs(self.df['close'] - self.df['vwap']) / self.df['vwap'] < 0.005

        self.signals['buy'] = (
            (self.df['trend'] == 1) & 
            price_near_vwap &
            (self.df['close'] > self.df['open'])  # Bullish candle
        ).astype(int)

        # Sell: Price near VWAP in downtrend with rejection
        self.signals['sell'] = (
            (self.df['trend'] == -1) & 
            price_near_vwap &
            (self.df['close'] < self.df['open'])  # Bearish candle
        ).astype(int)


class EMAPullbackStrategy(TradingStrategy):
    """
    EMA Pullback in Trend Strategy

    Enter on pullback to EMA in established trend
    """

    def __init__(self, df, ema_period=21, adx_period=14):
        super().__init__(df)
        self.ema_period = ema_period
        self.adx_period = adx_period

    def calculate_indicators(self):
        """Calculate EMA and ADX"""
        self.df['ema'] = self.df['close'].ewm(span=self.ema_period).mean()

        # Simplified ADX calculation
        plus_dm = self.df['high'].diff()
        minus_dm = self.df['low'].diff()

        tr1 = self.df['high'] - self.df['low']
        tr2 = abs(self.df['high'] - self.df['close'].shift(1))
        tr3 = abs(self.df['low'] - self.df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(self.adx_period).mean()

        plus_di = 100 * (plus_dm.rolling(self.adx_period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(self.adx_period).mean() / atr)

        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        self.df['adx'] = dx.rolling(self.adx_period).mean()

    def generate_signals(self):
        """Generate signals on EMA pullback"""
        # Price near EMA (within 0.5%)
        near_ema = abs(self.df['close'] - self.df['ema']) / self.df['ema'] < 0.005

        # Trend: ADX > 25 indicates strong trend
        strong_trend = self.df['adx'] > 25

        # Buy: Uptrend + pullback to EMA + bullish reversal
        self.signals['buy'] = (
            (self.df['close'] > self.df['ema']) & 
            near_ema & 
            strong_trend &
            (self.df['close'] > self.df['open'])
        ).astype(int)

        # Sell: Downtrend + pullback to EMA + bearish reversal
        self.signals['sell'] = (
            (self.df['close'] < self.df['ema']) & 
            near_ema & 
            strong_trend &
            (self.df['close'] < self.df['open'])
        ).astype(int)


def run_example_backtest():
    """
    Example usage with sample data

    In real usage, load your own OHLCV data:
    df = pd.read_csv('your_data.csv', parse_dates=['date'], index_col='date')
    """
    # Generate sample data (replace with real data)
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2024-01-01', freq='H')

    # Create trending price data
    trend = np.linspace(100, 150, len(dates))
    noise = np.random.randn(len(dates)) * 2
    prices = trend + noise

    df = pd.DataFrame({
        'open': prices + np.random.randn(len(dates)) * 0.5,
        'high': prices + abs(np.random.randn(len(dates))) * 1,
        'low': prices - abs(np.random.randn(len(dates))) * 1,
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)

    print("=" * 60)
    print("PROVEN TRADING STRATEGIES - BACKTEST EXAMPLE")
    print("=" * 60)

    # Test Hoffman Strategy
    print("\n🎯 Testing Hoffman Strategy...")
    hoffman = HoffmanStrategy(df)
    results = hoffman.backtest(initial_capital=10000, risk_per_trade=0.02)

    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.1f}%")
    print(f"Total Return: {results['total_return']:.1f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.1f}%")

    # Test VWAP Strategy
    print("\n🎯 Testing VWAP Bounce Strategy...")
    vwap = VWAPBounceStrategy(df)
    results = vwap.backtest(initial_capital=10000, risk_per_trade=0.02)

    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.1f}%")
    print(f"Total Return: {results['total_return']:.1f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.1f}%")

    # Test EMA Pullback Strategy
    print("\n🎯 Testing EMA Pullback Strategy...")
    ema = EMAPullbackStrategy(df)
    results = ema.backtest(initial_capital=10000, risk_per_trade=0.02)

    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.1f}%")
    print(f"Total Return: {results['total_return']:.1f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.1f}%")

    print("\n" + "=" * 60)
    print("✅ Backtest complete! Replace sample data with real OHLCV data.")
    print("=" * 60)


if __name__ == "__main__":
    run_example_backtest()
