"""
Crypto Range-Bound Scalping Strategy
=====================================
Strategy: Mean reversion within Bollinger Bands
Assets: BTC, ETH, SOL
Timeframe: 5-minute

Author: RANGE SCALPING CODER Agent
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

# Trading fees (Binance typical)
MAKER_FEE = 0.0008  # 0.08%
TAKER_FEE = 0.0010  # 0.10%

# Spreads by asset (bps)
SPREADS = {
    'BTC': 0.0003,  # 3 bps
    'ETH': 0.0004,  # 4 bps
    'SOL': 0.0008,  # 8 bps
}

# Strategy parameters
BB_PERIOD = 20
BB_STD = 2.0
TREND_EMA_PERIOD = 12  # 1H EMA (12 x 5m)

# Risk management
STOP_LOSS_PCT = 0.005  # 0.5%
TAKE_PROFIT_PCT = 0.008  # 0.8%
MAX_POSITION_PCT = 0.95  # Use 95% of capital

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

class RangeScalpingStrategy:
    """
    Range-bound scalping strategy using Bollinger Bands
    """
    
    def __init__(self, capital: float, symbol: str, asset_type: str = 'BTC'):
        self.capital = capital
        self.symbol = symbol
        self.asset_type = asset_type
        self.spread = SPREADS.get(asset_type, 0.0005)
        self.fee = TAKER_FEE * 2  # Round-trip
        
        # State
        self.position = 0  # 0 = flat, 1 = long, -1 = short
        self.entry_price = 0
        self.trades = []
        self.equity_curve = []
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands and trend filter"""
        df = df.copy()
        
        # Bollinger Bands
        df['sma'] = df['close'].rolling(window=BB_PERIOD).mean()
        df['std'] = df['close'].rolling(window=BB_PERIOD).std()
        df['upper_band'] = df['sma'] + (df['std'] * BB_STD)
        df['lower_band'] = df['sma'] - (df['std'] * BB_STD)
        df['band_width'] = (df['upper_band'] - df['lower_band']) / df['sma']
        
        # Trend filter (EMA)
        df['ema'] = df['close'].ewm(span=TREND_EMA_PERIOD, adjust=False).mean()
        df['trend'] = np.where(df['close'] > df['ema'], 1, -1)
        
        # Band position (0 = at lower, 1 = at upper)
        df['band_position'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals"""
        df = self.calculate_indicators(df)
        
        df['signal'] = 0
        df['position'] = 0
        
        position = 0
        positions = []
        
        for i in range(len(df)):
            if i < BB_PERIOD:
                positions.append(0)
                continue
            
            row = df.iloc[i]
            prev_row = df.iloc[i-1] if i > 0 else row
            
            # Skip if bands are too wide (high volatility)
            if row['band_width'] > 0.02:  # 2% band width
                positions.append(position)
                continue
            
            # Long signal: Price touches lower band in uptrend
            if position == 0 and row['close'] <= row['lower_band'] * 1.001 and row['trend'] == 1:
                position = 1
            
            # Short signal: Price touches upper band in downtrend
            elif position == 0 and row['close'] >= row['upper_band'] * 0.999 and row['trend'] == -1:
                position = -1
            
            # Exit long: Price reaches middle band or upper band
            elif position == 1 and (row['close'] >= row['sma'] or row['close'] >= row['upper_band'] * 0.995):
                position = 0
            
            # Exit short: Price reaches middle band or lower band
            elif position == -1 and (row['close'] <= row['sma'] or row['close'] <= row['lower_band'] * 1.005):
                position = 0
            
            positions.append(position)
        
        df['position'] = positions
        df['signal'] = df['position'].diff()
        
        return df
    
    def backtest(self, df: pd.DataFrame) -> Dict:
        """Run backtest"""
        df = self.generate_signals(df)
        
        current_capital = self.capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = [current_capital]
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            signal = row['signal']
            
            # Entry
            if signal == 1 and position == 0:  # Long entry
                position_size = current_capital * MAX_POSITION_PCT
                entry_price = row['close'] * (1 + self.spread)  # Buy at ask
                position = position_size / entry_price
                
                trades.append({
                    'type': 'entry_long',
                    'price': entry_price,
                    'time': df.index[i],
                    'size': position
                })
                
            elif signal == -1 and position == 0:  # Short entry
                position_size = current_capital * MAX_POSITION_PCT
                entry_price = row['close'] * (1 - self.spread)  # Sell at bid
                position = -position_size / entry_price
                
                trades.append({
                    'type': 'entry_short',
                    'price': entry_price,
                    'time': df.index[i],
                    'size': abs(position)
                })
            
            # Exit
            elif signal == -1 and position > 0:  # Long exit
                exit_price = row['close'] * (1 - self.spread)  # Sell at bid
                pnl = position * (exit_price - entry_price)
                pnl -= position * entry_price * self.fee  # Fees
                current_capital += pnl
                
                trades.append({
                    'type': 'exit_long',
                    'price': exit_price,
                    'time': df.index[i],
                    'pnl': pnl,
                    'return': pnl / (position * entry_price)
                })
                position = 0
                
            elif signal == 1 and position < 0:  # Short exit
                exit_price = row['close'] * (1 + self.spread)  # Buy at ask
                pnl = abs(position) * (entry_price - exit_price)
                pnl -= abs(position) * entry_price * self.fee  # Fees
                current_capital += pnl
                
                trades.append({
                    'type': 'exit_short',
                    'price': exit_price,
                    'time': df.index[i],
                    'pnl': pnl,
                    'return': pnl / (abs(position) * entry_price)
                })
                position = 0
            
            equity_curve.append(current_capital)
        
        # Close any open position at the end
        if position != 0:
            final_price = df['close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = abs(position) * (entry_price - final_price)
            current_capital += pnl
        
        # Calculate metrics
        completed_trades = [t for t in trades if 'pnl' in t]
        
        if len(completed_trades) > 0:
            pnls = [t['pnl'] for t in completed_trades]
            returns = [t['return'] for t in completed_trades]
            
            win_rate = len([p for p in pnls if p > 0]) / len(pnls)
            avg_profit = np.mean([p for p in pnls if p > 0]) if any(p > 0 for p in pnls) else 0
            avg_loss = np.mean([p for p in pnls if p < 0]) if any(p < 0 for p in pnls) else 0
            profit_factor = abs(sum(p for p in pnls if p > 0) / sum(p for p in pnls if p < 0)) if any(p < 0 for p in pnls) else float('inf')
            
            # Sharpe ratio (assuming risk-free rate of 5%)
            daily_returns = pd.Series(equity_curve).pct_change().dropna()
            sharpe = (daily_returns.mean() * 365 - 0.05) / (daily_returns.std() * np.sqrt(365)) if daily_returns.std() > 0 else 0
            
            # Max drawdown
            peak = pd.Series(equity_curve).cummax()
            drawdown = (pd.Series(equity_curve) - peak) / peak
            max_drawdown = drawdown.min()
        else:
            win_rate = avg_profit = avg_loss = profit_factor = sharpe = max_drawdown = 0
        
        return {
            'final_capital': current_capital,
            'total_return': (current_capital - self.capital) / self.capital,
            'total_trades': len(completed_trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'trades': completed_trades,
            'equity_curve': equity_curve
        }


# =============================================================================
# BACKTEST RUNNER
# =============================================================================

def run_backtest(symbol: str, asset_type: str, capital: float, days: int = 30):
    """Run backtest for a specific asset"""
    
    print(f"\n{'='*60}")
    print(f"RANGE SCALPING BACKTEST: {asset_type}")
    print(f"Symbol: {symbol} | Capital: ${capital:,.0f} | Period: {days} days")
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
    strategy = RangeScalpingStrategy(capital, symbol, asset_type)
    results = strategy.backtest(df)
    
    # Display results
    print(f"\n📊 BACKTEST RESULTS:")
    print(f"  Final Capital:      ${results['final_capital']:,.2f}")
    print(f"  Total Return:       {results['total_return']*100:.2f}%")
    print(f"  Total Trades:       {results['total_trades']}")
    print(f"  Win Rate:           {results['win_rate']*100:.1f}%")
    print(f"  Avg Profit:         ${results['avg_profit']:,.2f}")
    print(f"  Avg Loss:           ${results['avg_loss']:,.2f}")
    print(f"  Profit Factor:      {results['profit_factor']:.2f}")
    print(f"  Sharpe Ratio:       {results['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:       {results['max_drawdown']*100:.2f}%")
    
    if results['total_trades'] > 0:
        daily_return = results['total_return'] / days
        annualized = (1 + daily_return) ** 365 - 1
        print(f"  Est. Annual Return: {annualized*100:.1f}%")
    
    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    
    print("="*70)
    print("CRYPTO RANGE-BOUND SCALPING STRATEGY")
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
    print("SUMMARY: RANGE SCALPING ACROSS ASSETS")
    print("="*70)
    
    for asset, results in all_results.items():
        print(f"\n{asset}:")
        print(f"  Return: {results['total_return']*100:.2f}% | Win Rate: {results['win_rate']*100:.1f}% | Trades: {results['total_trades']}")
        print(f"  Sharpe: {results['sharpe_ratio']:.2f} | Max DD: {results['max_drawdown']*100:.2f}%")
