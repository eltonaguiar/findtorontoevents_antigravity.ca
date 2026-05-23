#!/usr/bin/env python3
"""
Simpleton KIMI Backtesting Tool
Comprehensive backtesting engine for Simpleton KIMI strategies

Usage:
    python simpleton_backtest.py --symbol BTCUSD --strategy all --timeframe 4h
    python simpleton_backtest.py --symbol all --strategy Multi-Indicator --optimize
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import json
import argparse
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

@dataclass
class TradeResult:
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    position_type: str
    pnl: float
    pnl_percent: float
    exit_reason: str
    strategy_name: str
    timeframe: str

@dataclass
class StrategyPerformance:
    strategy_name: str
    symbol: str
    timeframe: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_percent: float
    avg_hold_period: float
    best_trade: float
    worst_trade: float
    expectancy: float

class SimpletonBacktester:
    """Backtesting engine for Simpleton KIMI strategies"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades: List[TradeResult] = []
        self.performance_history: List[Dict] = []
        
    def fetch_data(self, symbol: str, timeframe: str, days: int = 365) -> pd.DataFrame:
        """Fetch historical data from yfinance"""
        # Convert crypto symbols to yfinance format
        if 'USD' in symbol and symbol != 'USD':
            symbol = symbol.replace('USD', '-USD')
        
        interval_map = {'1h': '1h', '4h': '1h', '1d': '1d'}
        interval = interval_map.get(timeframe, '1d')
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d", interval=interval)
        
        if timeframe == '4h' and interval == '1h':
            df = df.resample('4H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
        
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        result = df.copy()
        
        # RSI-2
        result['rsi2'] = self._rsi(result['close'], 2)
        
        # RSI-14
        result['rsi14'] = self._rsi(result['close'], 14)
        
        # SuperTrend
        result['supertrend'], result['st_direction'] = self._supertrend(result, 3.0, 10)
        
        # MACD
        result['macd'], result['signal_line'], result['hist'] = self._macd(result['close'])
        
        # EMAs
        result['ema9'] = result['close'].ewm(span=9).mean()
        result['ema21'] = result['close'].ewm(span=21).mean()
        result['ema50'] = result['close'].ewm(span=50).mean()
        result['ema200'] = result['close'].ewm(span=200).mean()
        
        # Bollinger Bands
        result['bb_middle'] = result['close'].rolling(20).mean()
        bb_std = result['close'].rolling(20).std()
        result['bb_upper'] = result['bb_middle'] + 2 * bb_std
        result['bb_lower'] = result['bb_middle'] - 2 * bb_std
        
        # ATR
        result['atr'] = self._atr(result, 14)
        
        # Volume
        result['volume_sma'] = result['volume'].rolling(20).mean()
        
        return result
    
    def _rsi(self, series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(period).mean()
    
    def _supertrend(self, df: pd.DataFrame, factor: float, period: int) -> Tuple[pd.Series, pd.Series]:
        atr = self._atr(df, period)
        hl2 = (df['high'] + df['low']) / 2
        
        upperband = hl2 + factor * atr
        lowerband = hl2 - factor * atr
        
        direction = pd.Series(1, index=df.index)
        supertrend = pd.Series(lowerband, index=df.index)
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > supertrend.iloc[i-1]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = max(lowerband.iloc[i], supertrend.iloc[i-1])
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = min(upperband.iloc[i], supertrend.iloc[i-1])
        
        return supertrend, direction
    
    def _macd(self, series: pd.Series, fast=12, slow=26, signal=9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = series.ewm(span=fast).mean()
        ema_slow = series.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def generate_signals(self, df: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """Generate trading signals"""
        result = df.copy()
        result['signal'] = 0  # 1 = buy, -1 = sell
        
        if strategy == 'RSI-2':
            result['signal'] = np.where(
                (result['rsi2'] < 30) & (result['rsi2'].shift(1) >= 30), 1,
                np.where((result['rsi2'] > 70) & (result['rsi2'].shift(1) <= 70), -1, 0)
            )
        
        elif strategy == 'SuperTrend':
            result['signal'] = np.where(
                (result['st_direction'] < 0) & (result['st_direction'].shift(1) > 0), 1,
                np.where((result['st_direction'] > 0) & (result['st_direction'].shift(1) < 0), -1, 0)
            )
        
        elif strategy == 'MACD':
            result['signal'] = np.where(
                (result['macd'] > result['signal_line']) & (result['macd'].shift(1) <= result['signal_line'].shift(1)), 1,
                np.where((result['macd'] < result['signal_line']) & (result['macd'].shift(1) >= result['signal_line'].shift(1)), -1, 0)
            )
        
        elif strategy == 'Triple EMA':
            bullish = (result['ema9'] > result['ema21']) & (result['ema21'] > result['ema50'])
            bearish = (result['ema9'] < result['ema21']) & (result['ema21'] < result['ema50'])
            result['signal'] = np.where(
                bullish & ~bullish.shift(1).fillna(False), 1,
                np.where(bearish & ~bearish.shift(1).fillna(False), -1, 0)
            )
        
        elif strategy == 'Bollinger Bands':
            result['signal'] = np.where(
                (result['close'] < result['bb_lower']) & (result['close'].shift(1) >= result['bb_lower'].shift(1)), 1,
                np.where((result['close'] > result['bb_upper']) & (result['close'].shift(1) <= result['bb_upper'].shift(1)), -1, 0)
            )
        
        elif strategy == 'Multi-Indicator':
            # Count confirmations
            buy_votes = (
                (result['rsi2'] < 30).astype(int) +
                ((result['st_direction'] < 0) & (result['st_direction'].shift(1) > 0)).astype(int) +
                ((result['macd'] > result['signal_line']) & (result['macd'].shift(1) <= result['signal_line'].shift(1))).astype(int) +
                ((result['ema9'] > result['ema21']) & (result['ema21'] > result['ema50'])).astype(int)
            )
            
            sell_votes = (
                (result['rsi2'] > 70).astype(int) +
                ((result['st_direction'] > 0) & (result['st_direction'].shift(1) < 0)).astype(int) +
                ((result['macd'] < result['signal_line']) & (result['macd'].shift(1) >= result['signal_line'].shift(1))).astype(int) +
                ((result['ema9'] < result['ema21']) & (result['ema21'] < result['ema50'])).astype(int)
            )
            
            result['signal'] = np.where(buy_votes >= 2, 1, np.where(sell_votes >= 2, -1, 0))
            result['buy_votes'] = buy_votes
            result['sell_votes'] = sell_votes
        
        return result
    
    def run_backtest(self, df: pd.DataFrame, strategy: str, tp_pct: float = 3.0, sl_pct: float = 2.0) -> StrategyPerformance:
        """Run backtest and return performance metrics"""
        df = self.generate_signals(df, strategy)
        
        trades = []
        position = 0  # 0 = flat, 1 = long, -1 = short
        entry_price = 0
        entry_time = None
        
        for i in range(len(df)):
            current = df.iloc[i]
            
            # Check for exit if in position
            if position != 0:
                pnl_pct = (current['close'] - entry_price) / entry_price * position
                
                # Check TP/SL
                hit_tp = pnl_pct >= tp_pct / 100
                hit_sl = pnl_pct <= -sl_pct / 100
                signal_exit = (position == 1 and current['signal'] == -1) or (position == -1 and current['signal'] == 1)
                
                if hit_tp or hit_sl or signal_exit:
                    exit_reason = 'TP' if hit_tp else 'SL' if hit_sl else 'SIGNAL'
                    trades.append(TradeResult(
                        entry_time=entry_time,
                        exit_time=df.index[i],
                        entry_price=entry_price,
                        exit_price=current['close'],
                        position_type='long' if position == 1 else 'short',
                        pnl=(current['close'] - entry_price) * position,
                        pnl_percent=pnl_pct * 100,
                        exit_reason=exit_reason,
                        strategy_name=strategy,
                        timeframe=''
                    ))
                    position = 0
            
            # Check for entry if flat
            if position == 0 and current['signal'] != 0:
                position = 1 if current['signal'] == 1 else -1
                entry_price = current['close']
                entry_time = df.index[i]
        
        # Calculate metrics
        if len(trades) == 0:
            return StrategyPerformance(
                strategy_name=strategy, symbol='', timeframe='',
                total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
                total_pnl=0, avg_win=0, avg_loss=0, profit_factor=0,
                sharpe_ratio=0, max_drawdown=0, max_drawdown_percent=0,
                avg_hold_period=0, best_trade=0, worst_trade=0, expectancy=0
            )
        
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(t.pnl_percent for t in trades)
        avg_win = np.mean([t.pnl_percent for t in wins]) if wins else 0
        avg_loss = np.mean([abs(t.pnl_percent) for t in losses]) if losses else 0
        profit_factor = sum(t.pnl_percent for t in wins) / sum(abs(t.pnl_percent) for t in losses) if losses else float('inf')
        
        # Sharpe ratio (simplified)
        returns = [t.pnl_percent for t in trades]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Max drawdown
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_dd = np.min(drawdown)
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)
        
        return StrategyPerformance(
            strategy_name=strategy,
            symbol=df.index[0],
            timeframe='',
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            max_drawdown_percent=max_dd,
            avg_hold_period=np.mean([(t.exit_time - t.entry_time).total_seconds() / 3600 for t in trades]),
            best_trade=max(returns),
            worst_trade=min(returns),
            expectancy=expectancy
        )
    
    def optimize_parameters(self, df: pd.DataFrame, strategy: str) -> Dict:
        """Find optimal parameters for a strategy"""
        best_sharpe = -999
        best_params = {}
        
        if strategy == 'RSI-2':
            for oversold in [20, 25, 30, 35]:
                for overbought in [65, 70, 75, 80]:
                    df['rsi2'] = self._rsi(df['close'], 2)
                    df['signal'] = np.where(
                        (df['rsi2'] < oversold) & (df['rsi2'].shift(1) >= oversold), 1,
                        np.where((df['rsi2'] > overbought) & (df['rsi2'].shift(1) <= overbought), -1, 0)
                    )
                    perf = self.run_backtest(df.copy(), 'RSI-2')
                    if perf.sharpe_ratio > best_sharpe:
                        best_sharpe = perf.sharpe_ratio
                        best_params = {'oversold': oversold, 'overbought': overbought}
        
        return {'best_sharpe': best_sharpe, 'best_params': best_params}

def main():
    parser = argparse.ArgumentParser(description='Simpleton KIMI Backtesting Tool')
    parser.add_argument('--symbol', type=str, default='BTCUSD', help='Symbol to test (or "all")')
    parser.add_argument('--strategy', type=str, default='all', help='Strategy to test')
    parser.add_argument('--timeframe', type=str, default='1d', help='Timeframe (1h, 4h, 1d)')
    parser.add_argument('--optimize', action='store_true', help='Run parameter optimization')
    parser.add_argument('--report', action='store_true', help='Save results to file')
    parser.add_argument('--days', type=int, default=365, help='Days of history to fetch')
    
    args = parser.parse_args()
    
    strategies = ['RSI-2', 'SuperTrend', 'MACD', 'Triple EMA', 'Bollinger Bands', 'Multi-Indicator'] if args.strategy == 'all' else [args.strategy]
    symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD', 'MATIC-USD'] if args.symbol == 'all' else [args.symbol]
    
    backtester = SimpletonBacktester()
    all_results = []
    
    print("=" * 80)
    print("SIMPleton KIMI Backtesting Tool v0.01")
    print("=" * 80)
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol} on {args.timeframe} timeframe...")
        try:
            df = backtester.fetch_data(symbol, args.timeframe, args.days)
            df = backtester.calculate_indicators(df)
            
            for strategy in strategies:
                perf = backtester.run_backtest(df.copy(), strategy)
                perf.symbol = symbol
                perf.timeframe = args.timeframe
                all_results.append(asdict(perf))
                
                print(f"\n  📈 {strategy}:")
                print(f"     Trades: {perf.total_trades} | Win Rate: {perf.win_rate:.1f}%")
                print(f"     Profit Factor: {perf.profit_factor:.2f} | Sharpe: {perf.sharpe_ratio:.2f}")
                print(f"     Total P&L: {perf.total_pnl:.2f}% | Max DD: {perf.max_drawdown:.2f}%")
        
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    # Save results
    if args.report:
        with open('simpleton_best_strategies.json', 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\n💾 Results saved to simpleton_best_strategies.json")
    
    print("\n" + "=" * 80)
    print("Backtesting complete!")
    print("=" * 80)

if __name__ == '__main__':
    main()
