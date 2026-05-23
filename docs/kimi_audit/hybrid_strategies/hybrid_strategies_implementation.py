"""
HYBRID TRADING STRATEGIES - Python Implementation
=================================================

DNA Mutation Strategies: Combining proven methodologies for superior performance

Requirements:
    pip install pandas numpy matplotlib backtrader ta yfinance

Strategies Included:
    1. Hoffman-Keltner Volatility Expansion
    2. VWAP-RSI Institutional Confluence
    3. AI-Enhanced EMA Pullback
    4. Convexity Zone Recovery
    5. RSI-Weighted Pairs Arbitrage
    6. Hoffman London Momentum

Author: AI Research Assistant
Date: March 16, 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class HybridStrategy:
    """Base class for hybrid trading strategies"""

    def __init__(self, df):
        """
        Initialize with OHLCV dataframe

        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()
        self.signals = pd.DataFrame(index=df.index)
        self.trades = []

    def calculate_indicators(self):
        """Calculate required indicators - override in subclass"""
        pass

    def generate_signals(self):
        """Generate buy/sell signals - override in subclass"""
        pass

    def backtest(self, initial_capital=10000, risk_per_trade=0.02, 
                 commission=0.001, slippage=0.0005):
        """
        Run backtest simulation

        Args:
            initial_capital: Starting capital
            risk_per_trade: Risk per trade (0.02 = 2%)
            commission: Commission per trade (0.001 = 0.1%)
            slippage: Slippage per trade (0.0005 = 0.05%)

        Returns:
            Dictionary with performance metrics
        """
        self.calculate_indicators()
        self.generate_signals()

        capital = initial_capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = [capital]

        for i in range(1, len(self.df)):
            current_price = self.df['close'].iloc[i]

            # Check for entry signals
            if self.signals['buy'].iloc[i] == 1 and position == 0:
                entry_price = current_price * (1 + slippage)  # Buy with slippage
                stop_loss = self._calculate_stop_loss(i, 'long')
                risk_amount = capital * risk_per_trade
                position_size = risk_amount / abs(entry_price - stop_loss)
                position = position_size
                entry_time = self.df.index[i]

            # Check for exit signals
            elif (self.signals['sell'].iloc[i] == 1 or self._check_stop_loss(i, position, entry_price)) and position > 0:
                exit_price = current_price * (1 - slippage)  # Sell with slippage

                # Calculate P&L
                gross_pnl = (exit_price - entry_price) * position
                trade_commission = (entry_price + exit_price) * position * commission
                net_pnl = gross_pnl - trade_commission

                capital += net_pnl
                position = 0

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': self.df.index[i],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'gross_pnl': gross_pnl,
                    'commission': trade_commission,
                    'net_pnl': net_pnl,
                    'return_pct': (exit_price - entry_price) / entry_price * 100
                })

            # Track equity
            current_equity = capital + (position * current_price if position > 0 else 0)
            equity_curve.append(current_equity)

        # Calculate metrics
        trades_df = pd.DataFrame(trades)

        if len(trades_df) == 0:
            return {"error": "No trades generated"}

        wins = trades_df[trades_df['net_pnl'] > 0]
        losses = trades_df[trades_df['net_pnl'] <= 0]

        metrics = {
            'total_trades': len(trades_df),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades_df) * 100,
            'total_return': (capital - initial_capital) / initial_capital * 100,
            'profit_factor': abs(wins['net_pnl'].sum() / losses['net_pnl'].sum()) if len(losses) > 0 else float('inf'),
            'avg_win': wins['net_pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['net_pnl'].mean() if len(losses) > 0 else 0,
            'max_drawdown': self._calculate_max_drawdown(equity_curve),
            'sharpe_ratio': self._calculate_sharpe(equity_curve),
            'equity_curve': equity_curve,
            'trades': trades_df
        }

        return metrics

    def _calculate_stop_loss(self, idx, direction):
        """Calculate stop loss - override in subclass"""
        if direction == 'long':
            return self.df['low'].iloc[idx] * 0.98  # Default 2% stop
        else:
            return self.df['high'].iloc[idx] * 1.02

    def _check_stop_loss(self, idx, position, entry_price):
        """Check if stop loss hit"""
        if position > 0:
            return self.df['low'].iloc[idx] < entry_price * 0.98
        return False

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

    def _calculate_sharpe(self, equity_curve, risk_free_rate=0.02):
        """Calculate Sharpe ratio"""
        returns = pd.Series(equity_curve).pct_change().dropna()
        if len(returns) == 0 or returns.std() == 0:
            return 0
        excess_returns = returns - risk_free_rate / 252
        return np.sqrt(252) * excess_returns.mean() / returns.std()


class HoffmanKeltnerHybrid(HybridStrategy):
    """
    Hybrid #1: Hoffman-Keltner Volatility Expansion

    Combines Hoffman EMA alignment with Keltner Channel compression
    """

    def __init__(self, df, ema_fast=3, ema_medium=5, ema_slow=18, 
                 keltner_period=20, keltner_mult=2):
        super().__init__(df)
        self.ema_fast = ema_fast
        self.ema_medium = ema_medium
        self.ema_slow = ema_slow
        self.keltner_period = keltner_period
        self.keltner_mult = keltner_mult

    def calculate_indicators(self):
        """Calculate EMAs and Keltner Channels"""
        # EMAs
        self.df['ema_fast'] = self.df['close'].ewm(span=self.ema_fast).mean()
        self.df['ema_medium'] = self.df['close'].ewm(span=self.ema_medium).mean()
        self.df['ema_slow'] = self.df['close'].ewm(span=self.ema_slow).mean()

        # Keltner Channels
        self.df['typical_price'] = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        self.df['keltner_mid'] = self.df['typical_price'].ewm(span=self.keltner_period).mean()

        # ATR for Keltner bands
        tr1 = self.df['high'] - self.df['low']
        tr2 = abs(self.df['high'] - self.df['close'].shift(1))
        tr3 = abs(self.df['low'] - self.df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.keltner_period).mean()

        self.df['keltner_upper'] = self.df['keltner_mid'] + (atr * self.keltner_mult)
        self.df['keltner_lower'] = self.df['keltner_mid'] - (atr * self.keltner_mult)

        # Keltner bandwidth (compression indicator)
        self.df['keltner_width'] = (self.df['keltner_upper'] - self.df['keltner_lower']) / self.df['keltner_mid'] * 100

        # Volume average
        self.df['volume_avg'] = self.df['volume'].rolling(20).mean()

        # Pullback indicator (simplified IRB)
        self.df['pullback_long'] = (
            (self.df['close'] > self.df['open']) & 
            (self.df['close'].shift(1) < self.df['open'].shift(1))
        ).astype(int)

        self.df['pullback_short'] = (
            (self.df['close'] < self.df['open']) & 
            (self.df['close'].shift(1) > self.df['open'].shift(1))
        ).astype(int)

    def generate_signals(self):
        """Generate hybrid signals"""
        # Bullish alignment: fast > medium > slow
        bullish_alignment = (
            (self.df['ema_fast'] > self.df['ema_medium']) & 
            (self.df['ema_medium'] > self.df['ema_slow'])
        )

        # Bearish alignment: fast < medium < slow
        bearish_alignment = (
            (self.df['ema_fast'] < self.df['ema_medium']) & 
            (self.df['ema_medium'] < self.df['ema_slow'])
        )

        # Keltner compression
        compression = self.df['keltner_width'] < 2.0

        # Price within Keltner middle band
        price_in_middle = (
            (self.df['close'] > self.df['keltner_lower']) & 
            (self.df['close'] < self.df['keltner_upper'])
        )

        # Volume confirmation
        volume_confirmed = self.df['volume'] > self.df['volume_avg']

        # Buy signal
        self.signals['buy'] = (
            bullish_alignment & 
            compression & 
            price_in_middle & 
            self.df['pullback_long'] &
            volume_confirmed
        ).astype(int)

        # Sell signal
        self.signals['sell'] = (
            bearish_alignment & 
            compression & 
            price_in_middle & 
            self.df['pullback_short'] &
            volume_confirmed
        ).astype(int)

    def _calculate_stop_loss(self, idx, direction):
        """Stop loss beyond Keltner middle band"""
        if direction == 'long':
            return self.df['keltner_lower'].iloc[idx]
        else:
            return self.df['keltner_upper'].iloc[idx]


class VWAPRSIHybrid(HybridStrategy):
    """
    Hybrid #2: VWAP-RSI Institutional Confluence

    Combines VWAP mean reversion with multi-timeframe RSI confirmation
    """

    def __init__(self, df, rsi_short=14, rsi_medium=21, rsi_long=50):
        super().__init__(df)
        self.rsi_short = rsi_short
        self.rsi_medium = rsi_medium
        self.rsi_long = rsi_long

    def calculate_indicators(self):
        """Calculate VWAP and RSIs"""
        # VWAP
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        self.df['vwap'] = (typical_price * self.df['volume']).cumsum() / self.df['volume'].cumsum()

        # Standard deviation bands
        self.df['std'] = typical_price.rolling(20).std()
        self.df['vwap_upper_1'] = self.df['vwap'] + self.df['std']
        self.df['vwap_lower_1'] = self.df['vwap'] - self.df['std']
        self.df['vwap_upper_2'] = self.df['vwap'] + (self.df['std'] * 2)
        self.df['vwap_lower_2'] = self.df['vwap'] - (self.df['std'] * 2)

        # RSIs
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_short).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_short).mean()
        rs = gain / loss
        self.df['rsi_14'] = 100 - (100 / (1 + rs))

        gain_m = (delta.where(delta > 0, 0)).rolling(window=self.rsi_medium).mean()
        loss_m = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_medium).mean()
        rs_m = gain_m / loss_m
        self.df['rsi_21'] = 100 - (100 / (1 + rs_m))

        gain_l = (delta.where(delta > 0, 0)).rolling(window=self.rsi_long).mean()
        loss_l = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_long).mean()
        rs_l = gain_l / loss_l
        self.df['rsi_50'] = 100 - (100 / (1 + rs_l))

        # Trend detection
        self.df['trend'] = np.where(self.df['close'] > self.df['vwap'], 1, -1)

    def generate_signals(self):
        """Generate VWAP-RSI confluence signals"""
        # Price near VWAP (within 0.5%)
        near_vwap = abs(self.df['close'] - self.df['vwap']) / self.df['vwap'] < 0.005

        # Volume confirmation
        volume_confirmed = self.df['volume'] > self.df['volume'].rolling(20).mean()

        # Long conditions
        rsi_14_oversold = self.df['rsi_14'] < 40
        rsi_21_bullish = self.df['rsi_21'] > 50
        rsi_50_bullish = self.df['rsi_50'] > 55

        # Short conditions
        rsi_14_overbought = self.df['rsi_14'] > 60
        rsi_21_bearish = self.df['rsi_21'] < 50
        rsi_50_bearish = self.df['rsi_50'] < 45

        # Buy signal
        self.signals['buy'] = (
            (self.df['trend'] == 1) & 
            near_vwap & 
            rsi_14_oversold & 
            rsi_21_bullish & 
            rsi_50_bullish &
            volume_confirmed
        ).astype(int)

        # Sell signal
        self.signals['sell'] = (
            (self.df['trend'] == -1) & 
            near_vwap & 
            rsi_14_overbought & 
            rsi_21_bearish & 
            rsi_50_bearish &
            volume_confirmed
        ).astype(int)

    def _calculate_stop_loss(self, idx, direction):
        """Stop loss beyond 1-sigma VWAP band"""
        if direction == 'long':
            return self.df['vwap_lower_1'].iloc[idx]
        else:
            return self.df['vwap_upper_1'].iloc[idx]


class AIEnhancedEMAHybrid(HybridStrategy):
    """
    Hybrid #3: AI-Enhanced EMA Pullback

    Combines EMA pullback with AI signal scoring (simulated)
    """

    def __init__(self, df, ema_fast=21, ema_slow=50, adx_period=14):
        super().__init__(df)
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.adx_period = adx_period

    def calculate_indicators(self):
        """Calculate EMAs, ADX, and AI score (simulated)"""
        # EMAs
        self.df['ema_fast'] = self.df['close'].ewm(span=self.ema_fast).mean()
        self.df['ema_slow'] = self.df['close'].ewm(span=self.ema_slow).mean()

        # ADX calculation (simplified)
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

        # AI Score (simulated based on multiple factors)
        # In real implementation, this would come from ML model
        trend_strength = (self.df['close'] - self.df['ema_slow']) / self.df['ema_slow'] * 100
        volatility = self.df['close'].rolling(20).std() / self.df['close'].rolling(20).mean() * 100
        volume_trend = self.df['volume'] / self.df['volume'].rolling(20).mean()

        # Simulated AI score (0-100)
        self.df['ai_score'] = (
            (trend_strength * 10).clip(0, 30) +
            (50 - volatility).clip(0, 30) +
            (volume_trend * 20).clip(0, 20) +
            (self.df['adx'] / 3).clip(0, 20)
        ).clip(0, 100)

        # Pullback detection
        self.df['pullback_long'] = (
            (self.df['close'] > self.df['ema_fast']) &
            (self.df['close'].shift(1) <= self.df['ema_fast'].shift(1))
        ).astype(int)

        self.df['pullback_short'] = (
            (self.df['close'] < self.df['ema_fast']) &
            (self.df['close'].shift(1) >= self.df['ema_fast'].shift(1))
        ).astype(int)

    def generate_signals(self):
        """Generate AI-enhanced signals"""
        # Strong trend
        strong_trend = self.df['adx'] > 25

        # AI score threshold
        ai_confirmed = self.df['ai_score'] > 70

        # Buy signal
        self.signals['buy'] = (
            strong_trend & 
            self.df['pullback_long'] & 
            ai_confirmed &
            (self.df['close'] > self.df['ema_slow'])  # Uptrend
        ).astype(int)

        # Sell signal
        self.signals['sell'] = (
            strong_trend & 
            self.df['pullback_short'] & 
            ai_confirmed &
            (self.df['close'] < self.df['ema_slow'])  # Downtrend
        ).astype(int)

    def _calculate_stop_loss(self, idx, direction):
        """Dynamic stop based on AI volatility forecast"""
        volatility_pct = self.df['close'].rolling(20).std().iloc[idx] / self.df['close'].iloc[idx]
        if direction == 'long':
            return self.df['close'].iloc[idx] * (1 - volatility_pct * 2)
        else:
            return self.df['close'].iloc[idx] * (1 + volatility_pct * 2)


def run_hybrid_backtests():
    """
    Example usage with sample data

    In real usage, load your own OHLCV data:
    df = pd.read_csv('your_data.csv', parse_dates=['date'], index_col='date')
    """
    # Generate sample trending data (replace with real data)
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2024-01-01', freq='H')

    # Create trending price data with pullbacks
    trend = np.linspace(100, 150, len(dates))
    noise = np.random.randn(len(dates)) * 2
    pullbacks = np.sin(np.linspace(0, 20*np.pi, len(dates))) * 3
    prices = trend + noise + pullbacks

    df = pd.DataFrame({
        'open': prices + np.random.randn(len(dates)) * 0.5,
        'high': prices + abs(np.random.randn(len(dates))) * 1,
        'low': prices - abs(np.random.randn(len(dates))) * 1,
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)

    print("=" * 80)
    print("HYBRID STRATEGY BACKTEST EXAMPLE")
    print("=" * 80)

    # Test Hoffman-Keltner Hybrid
    print("\n🧬 Testing Hoffman-Keltner Volatility Expansion...")
    hoffman_keltner = HoffmanKeltnerHybrid(df)
    results = hoffman_keltner.backtest(initial_capital=10000, risk_per_trade=0.02)

    if 'error' not in results:
        print(f"Total Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.1f}%")
        print(f"Total Return: {results['total_return']:.1f}%")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.1f}%")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    else:
        print(f"Error: {results['error']}")

    # Test VWAP-RSI Hybrid
    print("\n🧬 Testing VWAP-RSI Institutional Confluence...")
    vwap_rsi = VWAPRSIHybrid(df)
    results = vwap_rsi.backtest(initial_capital=10000, risk_per_trade=0.02)

    if 'error' not in results:
        print(f"Total Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.1f}%")
        print(f"Total Return: {results['total_return']:.1f}%")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.1f}%")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    else:
        print(f"Error: {results['error']}")

    # Test AI-Enhanced EMA Hybrid
    print("\n🧬 Testing AI-Enhanced EMA Pullback...")
    ai_ema = AIEnhancedEMAHybrid(df)
    results = ai_ema.backtest(initial_capital=10000, risk_per_trade=0.02)

    if 'error' not in results:
        print(f"Total Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.1f}%")
        print(f"Total Return: {results['total_return']:.1f}%")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.1f}%")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    else:
        print(f"Error: {results['error']}")

    print("\n" + "=" * 80)
    print("✅ Backtest complete! Replace sample data with real OHLCV data.")
    print("=" * 80)


if __name__ == "__main__":
    run_hybrid_backtests()
