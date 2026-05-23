"""
Larry Williams Smash Day Strategy Backtest
Reverse Engineered from documented trades and books
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

class LarryWilliamsSmashDay:
    """
    Smash Day Strategy Implementation
    
    Rules:
    1. Bullish Smash: Close below prev low AND below N-day low
    2. Entry: Next day trades above Smash Day high
    3. Exit: Opposite signal or bailout
    """
    
    def __init__(self, lookback=8, use_bailout=True):
        self.lookback = lookback  # 3-8 days for trend context
        self.use_bailout = use_bailout
        self.trades = []
        
    def identify_smash_days(self, df):
        """Identify smash day patterns"""
        df = df.copy()
        
        # Bullish Smash Day conditions
        df['prev_low'] = df['Low'].shift(1)
        df['close_below_prev_low'] = df['Close'] < df['prev_low']
        
        # N-day low
        df['n_day_low'] = df['Low'].rolling(window=self.lookback).min()
        df['breaks_n_day_low'] = df['Close'] < df['n_day_low'].shift(1)
        
        # Bullish Smash Day
        df['bullish_smash'] = df['close_below_prev_low'] & df['breaks_n_day_low']
        
        # Bearish Smash Day conditions
        df['prev_high'] = df['High'].shift(1)
        df['close_above_prev_high'] = df['Close'] > df['prev_high']
        df['n_day_high'] = df['High'].rolling(window=self.lookback).max()
        df['breaks_n_day_high'] = df['Close'] > df['n_day_high'].shift(1)
        df['bearish_smash'] = df['close_above_prev_high'] & df['breaks_n_day_high']
        
        return df
    
    def generate_signals(self, df):
        """Generate entry and exit signals"""
        df = self.identify_smash_days(df)
        
        # Entry signals (next day after smash)
        df['bullish_entry'] = False
        df['bearish_entry'] = False
        
        for i in range(1, len(df)):
            # Bullish entry: trade above previous day's high after bullish smash
            if df['bullish_smash'].iloc[i-1] and df['High'].iloc[i] > df['High'].iloc[i-1]:
                df.loc[df.index[i], 'bullish_entry'] = True
            
            # Bearish entry: trade below previous day's low after bearish smash
            if df['bearish_smash'].iloc[i-1] and df['Low'].iloc[i] < df['Low'].iloc[i-1]:
                df.loc[df.index[i], 'bearish_entry'] = True
        
        return df
    
    def backtest(self, symbol, start_date, end_date, initial_capital=100000):
        """Run backtest on historical data"""
        # Download data
        print(f"Downloading data for {symbol}...")
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        # Handle multi-index columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        if len(df) < self.lookback + 10:
            return {'Error': f'Insufficient data for {symbol}'}
        
        df = self.generate_signals(df)
        
        # Simulation variables
        capital = initial_capital
        position = 0  # 0 = flat, 1 = long, -1 = short
        entry_price = 0
        entry_date = None
        shares = 0
        
        trades = []
        equity_curve = []
        
        for i in range(len(df)):
            date = df.index[i]
            row = df.iloc[i]
            
            # Calculate current position value
            if position == 0:
                current_equity = capital
            elif position == 1:
                current_equity = shares * row['Close']
            else:  # short
                current_equity = capital + (entry_price - row['Close']) * shares
            
            equity_curve.append({'Date': date, 'Equity': current_equity})
            
            # Check for exits first (opposite signal)
            if position == 1:  # Long position
                if row['bearish_entry']:
                    # Exit long and go short
                    exit_price = row['Open']
                    pnl = (exit_price - entry_price) / entry_price
                    capital = shares * exit_price
                    
                    trades.append({
                        'Entry_Date': entry_date,
                        'Exit_Date': date,
                        'Direction': 'Long',
                        'Entry_Price': entry_price,
                        'Exit_Price': exit_price,
                        'PnL_Pct': pnl * 100,
                        'Capital': capital
                    })
                    
                    # Reverse to short
                    position = -1
                    entry_price = row['Open']
                    entry_date = date
                    shares = capital / entry_price
                    
            elif position == -1:  # Short position
                if row['bullish_entry']:
                    # Exit short and go long
                    exit_price = row['Open']
                    pnl = (entry_price - exit_price) / entry_price
                    capital = capital + (entry_price - exit_price) * shares
                    
                    trades.append({
                        'Entry_Date': entry_date,
                        'Exit_Date': date,
                        'Direction': 'Short',
                        'Entry_Price': entry_price,
                        'Exit_Price': exit_price,
                        'PnL_Pct': pnl * 100,
                        'Capital': capital
                    })
                    
                    # Reverse to long
                    position = 1
                    entry_price = row['Open']
                    entry_date = date
                    shares = capital / entry_price
            
            # Check for new entries (if flat)
            if position == 0:
                if row['bullish_entry']:
                    position = 1
                    entry_price = max(row['Open'], row['High'])  # Above smash day high
                    entry_date = date
                    shares = capital / entry_price
                elif row['bearish_entry']:
                    position = -1
                    entry_price = min(row['Open'], row['Low'])  # Below smash day low
                    entry_date = date
                    shares = capital / entry_price
        
        self.trades = trades
        self.equity_curve = pd.DataFrame(equity_curve)
        
        return self.calculate_metrics(trades, initial_capital, capital)
    
    def calculate_metrics(self, trades, initial_capital, final_capital):
        """Calculate performance metrics"""
        if not trades:
            return {'Error': 'No trades executed'}
        
        trades_df = pd.DataFrame(trades)
        
        # Basic metrics
        total_return = (final_capital - initial_capital) / initial_capital * 100
        n_trades = len(trades)
        
        # Win rate
        wins = trades_df[trades_df['PnL_Pct'] > 0]
        losses = trades_df[trades_df['PnL_Pct'] <= 0]
        win_rate = len(wins) / n_trades * 100 if n_trades > 0 else 0
        
        # Profit factor
        gross_profit = wins['PnL_Pct'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['PnL_Pct'].sum()) if len(losses) > 0 else 0.001
        profit_factor = gross_profit / gross_loss
        
        # Average win/loss
        avg_win = wins['PnL_Pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['PnL_Pct'].mean() if len(losses) > 0 else 0
        
        # Max drawdown
        if len(self.equity_curve) > 0:
            equity = self.equity_curve['Equity'].values
            peak = np.maximum.accumulate(equity)
            drawdown = (equity - peak) / peak * 100
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0
        
        # Sharpe ratio (simplified)
        if len(self.equity_curve) > 1:
            returns = self.equity_curve['Equity'].pct_change().dropna()
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
        else:
            sharpe = 0
        
        return {
            'Total_Return_%': round(total_return, 2),
            'Final_Capital': round(final_capital, 2),
            'Number_of_Trades': n_trades,
            'Win_Rate_%': round(win_rate, 2),
            'Profit_Factor': round(profit_factor, 2),
            'Avg_Win_%': round(avg_win, 2),
            'Avg_Loss_%': round(avg_loss, 2),
            'Win_Loss_Ratio': round(abs(avg_win/avg_loss), 2) if avg_loss != 0 else 0,
            'Max_Drawdown_%': round(max_drawdown, 2),
            'Sharpe_Ratio': round(sharpe, 2)
        }
    
    def plot_equity_curve(self, symbol):
        """Plot equity curve"""
        if hasattr(self, 'equity_curve') and len(self.equity_curve) > 0:
            plt.figure(figsize=(12, 6))
            plt.plot(self.equity_curve['Date'], self.equity_curve['Equity'])
            plt.title(f'Larry Williams Smash Day Strategy - {symbol}')
            plt.xlabel('Date')
            plt.ylabel('Equity ($)')
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(f'williams_equity_{symbol}.png', dpi=150)
            print(f"Chart saved as williams_equity_{symbol}.png")
            plt.close()


# Run backtest
if __name__ == "__main__":
    print("=" * 70)
    print("LARRY WILLIAMS SMASH DAY STRATEGY BACKTEST")
    print("=" * 70)
    print("\nStrategy Rules:")
    print("- Bullish Smash: Close below prev low AND below N-day low")
    print("- Entry: Next day trades above Smash Day high")
    print("- Exit: Opposite signal (reverse position)")
    print("- Lookback: 8 days (optimal per research)")
    
    # Test on multiple markets
    test_assets = [
        ('SLV', 'Silver ETF'),
        ('GLD', 'Gold ETF'),
        ('SPY', 'S&P 500 ETF'),
        ('QQQ', 'Nasdaq ETF'),
        ('EURUSD=X', 'EUR/USD'),
    ]
    
    all_results = {}
    
    for symbol, name in test_assets:
        print(f"\n{'='*70}")
        print(f"Testing: {name} ({symbol})")
        print('='*70)
        
        strategy = LarryWilliamsSmashDay(lookback=8)
        
        try:
            results = strategy.backtest(symbol, '2014-01-01', '2024-01-01')
            
            if 'Error' in results:
                print(f"Error: {results['Error']}")
                continue
            
            all_results[symbol] = results
            
            print(f"\nResults:")
            for key, val in results.items():
                print(f"  {key}: {val}")
            
            # Plot equity curve
            strategy.plot_equity_curve(symbol)
            
        except Exception as e:
            print(f"Error testing {symbol}: {e}")
    
    # Summary comparison
    print(f"\n{'='*70}")
    print("SUMMARY COMPARISON")
    print('='*70)
    
    if all_results:
        summary_df = pd.DataFrame(all_results).T
        print("\n", summary_df.to_string())
