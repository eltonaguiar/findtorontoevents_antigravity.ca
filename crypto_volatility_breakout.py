"""
Crypto Volatility Breakout Scalping Strategy
=============================================
Strategy: ATR-based breakout with volume confirmation
Test Period: Feb 2026 crash (high volatility regime)
Assets: BTC, ETH, SOL
Timeframe: 5-minute

Author: VOLATILITY BREAKOUT AGENT
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

# Trading fees
MAKER_FEE = 0.0008  # 0.08%
TAKER_FEE = 0.0010  # 0.10%
FEE_PER_TRADE = TAKER_FEE * 2  # Round-trip

# Slippage by asset
SLIPPAGE = {
    'BTC': 0.0002,  # 0.02%
    'ETH': 0.0005,  # 0.05%
    'SOL': 0.0005,  # 0.05%
}

# Strategy parameters
ATR_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2.0
SQUEEZE_THRESHOLD = 0.10  # Bandwidth < 10% of average
VOLUME_THRESHOLD = 1.5    # Volume > 1.5x average

# Risk management
ATR_MULTIPLIER_STOP = 1.0
ATR_MULTIPLIER_TARGET = 2.0
MAX_POSITION_PCT = 0.95

# Feb 2026 volatility regime (annualized)
FEB_2026_VOL = {
    'BTC': 0.674,  # 67.4%
    'ETH': 0.975,  # 97.5%
    'SOL': 0.927,  # 92.7%
}

# =============================================================================
# DATA FETCHING
# =============================================================================

class CryptoDataFetcher:
    """Fetch crypto data from Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.session = requests.Session()
    
    def fetch_klines(self, symbol: str, interval: str = '5m',
                     start_time: int = None, end_time: int = None,
                     limit: int = 1000) -> pd.DataFrame:
        """Fetch klines/candlestick data"""
        url = f"{self.base_url}/api/v3/klines"
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df.set_index('timestamp', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()


# =============================================================================
# STRATEGY IMPLEMENTATION
# =============================================================================

class VolatilityBreakoutStrategy:
    """
    Volatility breakout scalping strategy
    - Detects Bollinger Band squeezes (low volatility periods)
    - Enters on breakout with volume confirmation
    - Uses ATR for stop loss and take profit levels
    """
    
    def __init__(self, capital: float, symbol: str, asset_type: str = 'BTC'):
        self.capital = capital
        self.symbol = symbol
        self.asset_type = asset_type
        self.slippage = SLIPPAGE.get(asset_type, 0.0005)
        self.fee = FEE_PER_TRADE
        
        # State
        self.position = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trades = []
        self.equity_curve = []
        
    def calculate_atr(self, df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        df = df.copy()
        
        # ATR
        df['atr'] = self.calculate_atr(df)
        
        # Bollinger Bands
        df['sma'] = df['close'].rolling(window=BB_PERIOD).mean()
        df['std'] = df['close'].rolling(window=BB_PERIOD).std()
        df['upper_band'] = df['sma'] + (df['std'] * BB_STD)
        df['lower_band'] = df['sma'] - (df['std'] * BB_STD)
        df['band_width'] = (df['upper_band'] - df['lower_band']) / df['sma']
        df['avg_band_width'] = df['band_width'].rolling(window=BB_PERIOD).mean()
        
        # Squeeze detection
        df['squeeze'] = df['band_width'] < (df['avg_band_width'] * SQUEEZE_THRESHOLD)
        
        # Volume
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_spike'] = df['volume'] > (df['volume_sma'] * VOLUME_THRESHOLD)
        
        # Breakout signals
        df['breakout_up'] = (df['close'] > df['upper_band'].shift(1)) & df['volume_spike']
        df['breakout_down'] = (df['close'] < df['lower_band'].shift(1)) & df['volume_spike']
        
        return df
    
    def backtest(self, df: pd.DataFrame) -> Dict:
        """Run backtest"""
        df = self.calculate_indicators(df)
        
        current_capital = self.capital
        position = 0  # 0 = flat, 1 = long, -1 = short
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        trades = []
        equity_curve = [current_capital]
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Skip if not enough data
            if pd.isna(row['atr']) or pd.isna(row['upper_band']):
                equity_curve.append(current_capital)
                continue
            
            # Check stop loss / take profit for existing position
            if position == 1:  # Long
                if row['low'] <= stop_loss:
                    # Stop loss hit
                    exit_price = stop_loss * (1 - self.slippage)
                    pnl = (exit_price - entry_price) / entry_price
                    pnl -= self.fee
                    current_capital *= (1 + pnl)
                    
                    trades.append({
                        'type': 'long',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl_pct': pnl * 100,
                        'exit_reason': 'stop_loss',
                        'time': df.index[i]
                    })
                    position = 0
                    
                elif row['high'] >= take_profit:
                    # Take profit hit
                    exit_price = take_profit * (1 - self.slippage)
                    pnl = (exit_price - entry_price) / entry_price
                    pnl -= self.fee
                    current_capital *= (1 + pnl)
                    
                    trades.append({
                        'type': 'long',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl_pct': pnl * 100,
                        'exit_reason': 'take_profit',
                        'time': df.index[i]
                    })
                    position = 0
            
            elif position == -1:  # Short
                if row['high'] >= stop_loss:
                    # Stop loss hit
                    exit_price = stop_loss * (1 + self.slippage)
                    pnl = (entry_price - exit_price) / entry_price
                    pnl -= self.fee
                    current_capital *= (1 + pnl)
                    
                    trades.append({
                        'type': 'short',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl_pct': pnl * 100,
                        'exit_reason': 'stop_loss',
                        'time': df.index[i]
                    })
                    position = 0
                    
                elif row['low'] <= take_profit:
                    # Take profit hit
                    exit_price = take_profit * (1 + self.slippage)
                    pnl = (entry_price - exit_price) / entry_price
                    pnl -= self.fee
                    current_capital *= (1 + pnl)
                    
                    trades.append({
                        'type': 'short',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl_pct': pnl * 100,
                        'exit_reason': 'take_profit',
                        'time': df.index[i]
                    })
                    position = 0
            
            # Check for new entry signals (only if flat)
            if position == 0:
                # Long breakout
                if row['breakout_up'] and prev_row['squeeze']:
                    position = 1
                    entry_price = row['close'] * (1 + self.slippage)
                    stop_loss = entry_price - (row['atr'] * ATR_MULTIPLIER_STOP)
                    take_profit = entry_price + (row['atr'] * ATR_MULTIPLIER_TARGET)
                
                # Short breakout
                elif row['breakout_down'] and prev_row['squeeze']:
                    position = -1
                    entry_price = row['close'] * (1 - self.slippage)
                    stop_loss = entry_price + (row['atr'] * ATR_MULTIPLIER_STOP)
                    take_profit = entry_price - (row['atr'] * ATR_MULTIPLIER_TARGET)
            
            equity_curve.append(current_capital)
        
        # Close any open position at the end
        if position != 0:
            final_price = df['close'].iloc[-1]
            if position == 1:
                pnl = (final_price - entry_price) / entry_price
            else:
                pnl = (entry_price - final_price) / entry_price
            pnl -= self.fee
            current_capital *= (1 + pnl)
        
        # Calculate metrics
        if len(trades) > 0:
            pnls = [t['pnl_pct'] for t in trades]
            win_rate = len([p for p in pnls if p > 0]) / len(pnls)
            avg_win = np.mean([p for p in pnls if p > 0]) if any(p > 0 for p in pnls) else 0
            avg_loss = np.mean([p for p in pnls if p < 0]) if any(p < 0 for p in pnls) else 0
            
            # False signal rate (stop loss hits)
            stop_losses = len([t for t in trades if t['exit_reason'] == 'stop_loss'])
            false_signal_rate = stop_losses / len(trades)
            
            # Profit factor
            gross_profit = sum(p for p in pnls if p > 0)
            gross_loss = abs(sum(p for p in pnls if p < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Sharpe ratio
            daily_returns = pd.Series(equity_curve).pct_change().dropna()
            sharpe = (daily_returns.mean() * 365 - 0.05) / (daily_returns.std() * np.sqrt(365)) if daily_returns.std() > 0 else 0
            
            # Max drawdown
            peak = pd.Series(equity_curve).cummax()
            drawdown = (pd.Series(equity_curve) - peak) / peak
            max_drawdown = drawdown.min()
        else:
            win_rate = avg_win = avg_loss = false_signal_rate = profit_factor = sharpe = max_drawdown = 0
        
        return {
            'final_capital': current_capital,
            'total_return': (current_capital - self.capital) / self.capital,
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'false_signal_rate': false_signal_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'trades': trades,
            'equity_curve': equity_curve
        }


# =============================================================================
# BACKTEST RUNNER
# =============================================================================

def run_backtest(symbol: str, asset_type: str, capital: float, days: int = 30):
    """Run backtest for a specific asset"""
    
    print(f"\n{'='*60}")
    print(f"VOLATILITY BREAKOUT BACKTEST: {asset_type}")
    print(f"Symbol: {symbol} | Capital: ${capital:,.0f} | Period: {days} days")
    print(f"Feb 2026 Volatility: {FEB_2026_VOL.get(asset_type, 0.5)*100:.1f}%")
    print(f"{'='*60}\n")
    
    # Fetch data
    fetcher = CryptoDataFetcher()
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    df = fetcher.fetch_klines(symbol, '5m', start_time, end_time)
    
    if df.empty:
        print(f"❌ No data available for {symbol}")
        return None
    
    print(f"✓ Retrieved {len(df)} 5-minute candles")
    
    # Run backtest
    strategy = VolatilityBreakoutStrategy(capital, symbol, asset_type)
    results = strategy.backtest(df)
    
    # Display results
    print(f"\n📊 BACKTEST RESULTS:")
    print(f"  Final Capital:       ${results['final_capital']:,.2f}")
    print(f"  Total Return:        {results['total_return']*100:.2f}%")
    print(f"  Total Trades:        {results['total_trades']}")
    print(f"  Win Rate:            {results['win_rate']*100:.1f}%")
    print(f"  Avg Win:             {results['avg_win']:.2f}%")
    print(f"  Avg Loss:            {results['avg_loss']:.2f}%")
    print(f"  False Signal Rate:   {results['false_signal_rate']*100:.1f}%")
    print(f"  Profit Factor:       {results['profit_factor']:.2f}")
    print(f"  Sharpe Ratio:        {results['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:        {results['max_drawdown']*100:.2f}%")
    
    if results['total_trades'] > 0:
        daily_return = results['total_return'] / days
        annualized = (1 + daily_return) ** 365 - 1
        print(f"  Est. Annual Return:  {annualized*100:.1f}%")
    
    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    
    print("="*70)
    print("CRYPTO VOLATILITY BREAKOUT SCALPING STRATEGY")
    print("Tested on Feb 2026 High Volatility Regime")
    print("="*70)
    
    # Test configurations
    configs = [
        ('BTCUSDT', 'BTC', 10000),
        ('ETHUSDT', 'ETH', 10000),
        ('SOLUSDT', 'SOL', 10000),
    ]
    
    all_results = {}
    
    for symbol, asset, capital in configs:
        results = run_backtest(symbol, asset, capital, days=30)
        if results:
            all_results[asset] = results
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY: VOLATILITY BREAKOUT ACROSS ASSETS")
    print("="*70)
    
    for asset, results in all_results.items():
        print(f"\n{asset} (Vol: {FEB_2026_VOL.get(asset, 0.5)*100:.1f}%):")
        print(f"  Return: {results['total_return']*100:.2f}% | Win Rate: {results['win_rate']*100:.1f}% | Trades: {results['total_trades']}")
        print(f"  False Signals: {results['false_signal_rate']*100:.1f}% | Sharpe: {results['sharpe_ratio']:.2f} | Max DD: {results['max_drawdown']*100:.2f}%")
