"""
Marty Schwartz 10 EMA Trend Following Strategy
Reverse Engineered from Pit Bull and Market Wizards
"""

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

class MartySchwartzEMAStrategy:
    """
    Marty Schwartz 10 EMA Strategy
    
    Rules:
    1. Use 10-period EMA as trend filter
    2. Only trade in direction of EMA (Green Light / Red Light)
    3. Enter on pullbacks to EMA
    4. Stop below swing low (not obvious level)
    5. Never fight the moving average
    """
    
    def __init__(self, ema_period=10, pullback_threshold=0.015, 
                 stop_loss_pct=0.05, take_profit_pct=0.10):
        self.ema_period = ema_period
        self.pullback_threshold = pullback_threshold  # 1.5% pullback to EMA
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
    def calculate_indicators(self, df):
        """Calculate EMA and signals"""
        df = df.copy()
        
        # 10 EMA
        df['EMA10'] = df['Close'].ewm(span=self.ema_period, adjust=False).mean()
        
        # Trend direction (Green Light / Red Light)
        df['above_ema'] = df['Close'] > df['EMA10']
        df['green_light'] = df['above_ema']  # Long only
        df['red_light'] = ~df['above_ema']   # Short only
        
        # Distance from EMA
        df['ema_distance'] = (df['Close'] - df['EMA10']) / df['EMA10']
        
        # Pullback to EMA in uptrend
        df['was_above'] = df['above_ema'].shift(1) & (df['ema_distance'].shift(1) > 0.005)
        df['pullback_long'] = (df['was_above'] & 
                               (abs(df['ema_distance']) < self.pullback_threshold) & 
                               df['above_ema'])
        
        # Pullback to EMA in downtrend
        df['was_below'] = (~df['above_ema'].shift(1)) & (df['ema_distance'].shift(1) < -0.005)
        df['pullback_short'] = (df['was_below'] & 
                               (abs(df['ema_distance']) < self.pullback_threshold) & 
                               (~df['above_ema']))
        
        # Swing high/low for stops
        df['swing_low'] = df['Low'].rolling(5).min().shift(1)
        df['swing_high'] = df['High'].rolling(5).max().shift(1)
        
        return df
    
    def backtest(self, symbol, start_date, end_date, initial_capital=100000):
        """Run backtest"""
        print(f"Downloading data for {symbol}...")
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        # Handle multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        if len(df) < self.ema_period + 10:
            return {'Error': f'Insufficient data for {symbol}'}
        
        df = self.calculate_indicators(df)
        
        capital = initial_capital
        position = 0  # 0 = flat, 1 = long, -1 = short
        entry_price = 0
        entry_date = None
        stop_loss = 0
        take_profit = 0
        shares = 0
        
        trades = []
        equity_curve = []
        
        for i in range(self.ema_period + 5, len(df)):
            date = df.index[i]
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Calculate current equity
            if position == 0:
                current_equity = capital
            elif position == 1:
                current_equity = shares * row['Close']
            else:
                current_equity = capital + (entry_price - row['Close']) * shares
            
            equity_curve.append({'Date': date, 'Equity': current_equity})
            
            # Check exits first
            if position == 1:
                # Stop loss - below swing low or percentage
                stop_price = max(stop_loss, row['swing_low'] * 0.995)
                
                if row['Low'] < stop_price:
                    exit_price = stop_price
                    pnl = (exit_price - entry_price) / entry_price
                    capital = shares * exit_price
                    
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': date,
                        'Direction': 'Long', 'Entry_Price': entry_price,
                        'Exit_Price': exit_price, 'Exit_Reason': 'Stop Loss',
                        'PnL_Pct': pnl * 100
                    })
                    position = 0
                
                # Take profit
                elif row['High'] > take_profit:
                    exit_price = take_profit
                    pnl = (exit_price - entry_price) / entry_price
                    capital = shares * exit_price
                    
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': date,
                        'Direction': 'Long', 'Entry_Price': entry_price,
                        'Exit_Price': exit_price, 'Exit_Reason': 'Take Profit',
                        'PnL_Pct': pnl * 100
                    })
                    position = 0
                
                # Trend reversal (close below EMA - "Don't fight the EMA")
                elif not row['above_ema'] and prev_row['above_ema']:
                    exit_price = row['Close']
                    pnl = (exit_price - entry_price) / entry_price
                    capital = shares * exit_price
                    
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': date,
                        'Direction': 'Long', 'Entry_Price': entry_price,
                        'Exit_Price': exit_price, 'Exit_Reason': 'Trend Reversal',
                        'PnL_Pct': pnl * 100
                    })
                    position = 0
            
            elif position == -1:
                # Stop loss for shorts
                stop_price = min(stop_loss, row['swing_high'] * 1.005)
                
                if row['High'] > stop_price:
                    exit_price = stop_price
                    pnl = (entry_price - exit_price) / entry_price
                    capital = capital + (entry_price - exit_price) * shares
                    
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': date,
                        'Direction': 'Short', 'Entry_Price': entry_price,
                        'Exit_Price': exit_price, 'Exit_Reason': 'Stop Loss',
                        'PnL_Pct': pnl * 100
                    })
                    position = 0
                
                # Take profit
                elif row['Low'] < take_profit:
                    exit_price = take_profit
                    pnl = (entry_price - exit_price) / entry_price
                    capital = capital + (entry_price - exit_price) * shares
                    
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': date,
                        'Direction': 'Short', 'Entry_Price': entry_price,
                        'Exit_Price': exit_price, 'Exit_Reason': 'Take Profit',
                        'PnL_Pct': pnl * 100
                    })
                    position = 0
                
                # Trend reversal
                elif row['above_ema'] and not prev_row['above_ema']:
                    exit_price = row['Close']
                    pnl = (entry_price - exit_price) / entry_price
                    capital = capital + (entry_price - exit_price) * shares
                    
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': date,
                        'Direction': 'Short', 'Entry_Price': entry_price,
                        'Exit_Price': exit_price, 'Exit_Reason': 'Trend Reversal',
                        'PnL_Pct': pnl * 100
                    })
                    position = 0
            
            # Check entries (only if flat)
            if position == 0:
                # Long entry: Pullback to EMA in uptrend (Green Light)
                if row['pullback_long'] and row['green_light']:
                    position = 1
                    entry_price = row['Close']
                    entry_date = date
                    shares = capital / entry_price
                    stop_loss = entry_price * (1 - self.stop_loss_pct)
                    take_profit = entry_price * (1 + self.take_profit_pct)
                
                # Short entry: Pullback to EMA in downtrend (Red Light)
                elif row['pullback_short'] and row['red_light']:
                    position = -1
                    entry_price = row['Close']
                    entry_date = date
                    shares = capital / entry_price
                    stop_loss = entry_price * (1 + self.stop_loss_pct)
                    take_profit = entry_price * (1 - self.take_profit_pct)
        
        self.trades = trades
        self.equity_curve = pd.DataFrame(equity_curve)
        
        return self.calculate_metrics(trades, initial_capital, capital)
    
    def calculate_metrics(self, trades, initial_capital, final_capital):
        """Calculate performance metrics"""
        if not trades:
            return {'Error': 'No trades executed'}
        
        trades_df = pd.DataFrame(trades)
        
        total_return = (final_capital - initial_capital) / initial_capital * 100
        n_trades = len(trades)
        
        wins = trades_df[trades_df['PnL_Pct'] > 0]
        losses = trades_df[trades_df['PnL_Pct'] <= 0]
        win_rate = len(wins) / n_trades * 100 if n_trades > 0 else 0
        
        gross_profit = wins['PnL_Pct'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['PnL_Pct'].sum()) if len(losses) > 0 else 0.001
        profit_factor = gross_profit / gross_loss
        
        avg_win = wins['PnL_Pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['PnL_Pct'].mean() if len(losses) > 0 else 0
        
        # Max drawdown
        if len(self.equity_curve) > 0:
            equity = self.equity_curve['Equity'].values
            peak = np.maximum.accumulate(equity)
            drawdown = (equity - peak) / peak * 100
            max_drawdown = drawdown.min()
            
            # Sharpe ratio
            returns = self.equity_curve['Equity'].pct_change().dropna()
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
        else:
            max_drawdown = 0
            sharpe = 0
        
        # Exit reason analysis
        exit_reasons = trades_df['Exit_Reason'].value_counts().to_dict() if 'Exit_Reason' in trades_df.columns else {}
        
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
            'Sharpe_Ratio': round(sharpe, 2),
            'Exit_Reasons': exit_reasons
        }
    
    def plot_results(self, symbol):
        """Plot equity curve and trades"""
        if not hasattr(self, 'equity_curve') or len(self.equity_curve) == 0:
            return
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # Equity curve
        axes[0].plot(self.equity_curve['Date'], self.equity_curve['Equity'], label='Strategy Equity')
        axes[0].set_title(f'Marty Schwartz 10 EMA Strategy - {symbol}')
        axes[0].set_ylabel('Equity ($)')
        axes[0].grid(True)
        axes[0].legend()
        
        # Trade distribution
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            colors = ['green' if x > 0 else 'red' for x in trades_df['PnL_Pct']]
            axes[1].bar(range(len(trades_df)), trades_df['PnL_Pct'], color=colors, alpha=0.7)
            axes[1].set_title('Trade P&L Distribution')
            axes[1].set_ylabel('P&L (%)')
            axes[1].set_xlabel('Trade Number')
            axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'schwartz_strategy_{symbol}.png', dpi=150)
        print(f"Chart saved as schwartz_strategy_{symbol}.png")
        plt.close()


# Run backtest
if __name__ == "__main__":
    print("=" * 70)
    print("MARTY SCHWARTZ 10 EMA STRATEGY BACKTEST")
    print("=" * 70)
    print("\nStrategy Rules:")
    print("- Use 10-period EMA as trend filter")
    print("- Green Light (Price > EMA): Long only")
    print("- Red Light (Price < EMA): Short only")
    print("- Enter on pullbacks to EMA")
    print("- Stop below swing low")
    print("- Never fight the moving average!")
    
    # Test on major indices
    test_assets = [
        ('SPY', 'S&P 500 ETF'),
        ('QQQ', 'Nasdaq ETF'),
        ('IWM', 'Russell 2000 ETF'),
        ('DIA', 'Dow Jones ETF'),
        ('EFA', 'EAFE ETF'),
    ]
    
    all_results = {}
    
    for symbol, name in test_assets:
        print(f"\n{'='*70}")
        print(f"Testing: {name} ({symbol})")
        print('='*70)
        
        strategy = MartySchwartzEMAStrategy()
        
        try:
            results = strategy.backtest(symbol, '2015-01-01', '2024-01-01')
            
            if 'Error' in results:
                print(f"Error: {results['Error']}")
                continue
            
            all_results[symbol] = {k: v for k, v in results.items() if k != 'Exit_Reasons'}
            
            print(f"\nResults:")
            for key, val in results.items():
                if key != 'Exit_Reasons':
                    print(f"  {key}: {val}")
            
            if 'Exit_Reasons' in results:
                print(f"\n  Exit Reasons:")
                for reason, count in results['Exit_Reasons'].items():
                    print(f"    {reason}: {count}")
            
            # Plot results
            strategy.plot_results(symbol)
            
        except Exception as e:
            print(f"Error testing {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary comparison
    print(f"\n{'='*70}")
    print("SUMMARY COMPARISON")
    print('='*70)
    
    if all_results:
        summary_df = pd.DataFrame(all_results).T
        print("\n", summary_df.to_string())
