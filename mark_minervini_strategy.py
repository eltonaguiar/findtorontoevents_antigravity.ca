"""
Mark Minervini SEPA/VCP Strategy
Reverse Engineered from Trade Like a Stock Market Wizard
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt

class MinerviniSEPA:
    """
    Mark Minervini SEPA Strategy
    
    SEPA Framework:
    S - Specific Entry Point (VCP pattern)
    E - Earnings (20%+ growth, accelerating)
    P - Price Action (Stage 2 uptrend)
    A - Announcement (catalyst present)
    
    Rules:
    1. Trend Template: 8 criteria for Stage 2 uptrend
    2. VCP: Volatility Contraction Pattern
    3. Entry: Breakout on volume 40-50% above average
    4. Exit: 7-8% stop or trend violation
    """
    
    def __init__(self, 
                 stop_loss_pct=0.075,  # 7.5%
                 min_volume_surge=1.4,  # 40% above average
                 vcp_lookback=20,
                 min_trend_score=7):  # 7 of 8 criteria
        
        self.stop_loss_pct = stop_loss_pct
        self.min_volume_surge = min_volume_surge
        self.vcp_lookback = vcp_lookback
        self.min_trend_score = min_trend_score
    
    def calculate_trend_template(self, df):
        """Calculate 8-point Trend Template for Stage 2 uptrend"""
        df = df.copy()
        
        # Moving averages
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA150'] = df['Close'].rolling(150).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # 52-week high
        df['52wk_high'] = df['Close'].rolling(252).max()
        
        # Trend Template criteria
        df['c1_price_above_150sma'] = df['Close'] > df['SMA150']
        df['c2_150sma_above_200sma'] = df['SMA150'] > df['SMA200']
        df['c3_50sma_above_150sma'] = df['SMA50'] > df['SMA150']
        df['c4_price_above_50sma'] = df['Close'] > df['SMA50']
        df['c5_price_near_high'] = df['Close'] > df['52wk_high'] * 0.75
        df['c7_close_above_open'] = df['Close'] > df['Open']
        df['c8_close_upper_half'] = df['Close'] > (df['High'] + df['Low']) / 2
        
        # Count of criteria met (RS not included - requires external data)
        criteria_cols = ['c1_price_above_150sma', 'c2_150sma_above_200sma',
                        'c3_50sma_above_150sma', 'c4_price_above_50sma',
                        'c5_price_near_high', 'c7_close_above_open', 'c8_close_upper_half']
        
        df['trend_score'] = df[criteria_cols].sum(axis=1)
        df['trend_template_pass'] = df['trend_score'] >= self.min_trend_score
        
        # Stage classification
        df['stage'] = 0
        df.loc[df['Close'] > df['SMA50'], 'stage'] = 2  # Uptrend
        df.loc[(df['Close'] > df['SMA150']) & (df['Close'] < df['SMA50']), 'stage'] = 3  # Top
        df.loc[df['Close'] < df['SMA150'], 'stage'] = 4  # Downtrend
        df.loc[(df['Close'] < df['SMA200']) & (df['Close'] > df['SMA150']), 'stage'] = 1  # Bottom
        
        return df
    
    def identify_vcp(self, df):
        """Identify Volatility Contraction Pattern"""
        df = df.copy()
        
        # Average volume
        df['avg_volume'] = df['Volume'].rolling(20).mean()
        
        # Calculate volatility (range as % of price)
        df['range_pct'] = (df['High'] - df['Low']) / df['Close']
        df['avg_range'] = df['range_pct'].rolling(10).mean()
        
        # VCP detection
        df['vcp_candidate'] = False
        df['vcp_quality'] = 0
        
        for i in range(self.vcp_lookback + 50, len(df)):
            window = df.iloc[i-self.vcp_lookback:i]
            
            if len(window) < self.vcp_lookback:
                continue
            
            highs = window['High'].values
            lows = window['Low'].values
            closes = window['Close'].values
            
            # Find consolidation range
            range_high = highs.max()
            range_low = lows.min()
            total_range = (range_high - range_low) / range_low
            
            # Check for contraction pattern
            first_half = window.iloc[:len(window)//2]
            second_half = window.iloc[len(window)//2:]
            
            first_range = (first_half['High'].max() - first_half['Low'].min()) / first_half['Low'].min()
            second_range = (second_half['High'].max() - second_half['Low'].min()) / second_half['Low'].min()
            
            # VCP: second half more contracted than first
            is_contracting = second_range < first_range * 0.7
            
            # Price near highs of consolidation
            near_highs = closes[-1] > range_high * 0.95
            
            # Minimum consolidation size
            sufficient_range = total_range > 0.08  # 8% minimum range
            
            if is_contracting and near_highs and sufficient_range:
                df.loc[df.index[i], 'vcp_candidate'] = True
                # Quality score based on contraction tightness
                contraction_ratio = second_range / first_range if first_range > 0 else 1
                df.loc[df.index[i], 'vcp_quality'] = 1 - contraction_ratio
        
        return df
    
    def generate_signals(self, df):
        """Generate entry and exit signals"""
        df = self.calculate_trend_template(df)
        df = self.identify_vcp(df)
        
        # Volume surge (40%+ above average)
        df['volume_surge'] = df['Volume'] > df['avg_volume'] * self.min_volume_surge
        
        # Breakout above recent highs
        df['recent_high'] = df['High'].rolling(10).max().shift(1)
        df['breakout'] = df['Close'] > df['recent_high']
        
        # Entry signal: All conditions met
        df['entry_signal'] = (df['trend_template_pass'] & 
                              df['vcp_candidate'].shift(1) &  # VCP formed
                              df['volume_surge'] &
                              df['breakout'])
        
        return df
    
    def backtest(self, symbol, start_date, end_date, initial_capital=100000):
        """Run backtest"""
        print(f"Downloading data for {symbol}...")
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        # Handle multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        # Need enough data for 200 SMA
        if len(df) < 300:
            return {'Error': f'Insufficient data for {symbol}'}
        
        df = self.generate_signals(df)
        
        capital = initial_capital
        position = 0
        entry_price = 0
        stop_loss = 0
        entry_date = None
        max_price = 0
        shares = 0
        
        trades = []
        equity_curve = []
        
        for i in range(252, len(df)):  # Start after SMAs calculated
            date = df.index[i]
            row = df.iloc[i]
            
            # Calculate current equity
            if position == 0:
                current_equity = capital
            else:
                current_equity = shares * row['Close']
            
            equity_curve.append({'Date': date, 'Equity': current_equity})
            
            # Update max price for trailing stop
            if position == 1:
                max_price = max(max_price, row['Close'])
            
            # Check exits
            if position == 1:
                # Initial stop loss (7-8%)
                stop_price = max(stop_loss, max_price * 0.92)  # Trailing stop at 8%
                
                if row['Low'] < stop_price:
                    exit_price = max(stop_price, row['Open']) if row['Open'] < stop_price else stop_price
                    pnl = (exit_price - entry_price) / entry_price
                    capital = shares * exit_price
                    
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': date,
                        'Direction': 'Long', 'Entry_Price': entry_price,
                        'Exit_Price': exit_price, 'Exit_Reason': 'Stop Loss',
                        'PnL_Pct': pnl * 100
                    })
                    position = 0
                    max_price = 0
                
                # Trend violation (close below 50 SMA)
                elif row['Close'] < row['SMA50'] * 0.98:  # 2% buffer
                    exit_price = row['Close']
                    pnl = (exit_price - entry_price) / entry_price
                    capital = shares * exit_price
                    
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': date,
                        'Direction': 'Long', 'Entry_Price': entry_price,
                        'Exit_Price': exit_price, 'Exit_Reason': 'Trend Violation',
                        'PnL_Pct': pnl * 100
                    })
                    position = 0
                    max_price = 0
            
            # Check entries
            if position == 0 and row['entry_signal']:
                position = 1
                entry_price = row['Close']
                stop_loss = entry_price * (1 - self.stop_loss_pct)
                entry_date = date
                max_price = entry_price
                shares = capital / entry_price
        
        self.trades = trades
        self.df = df
        self.equity_curve = pd.DataFrame(equity_curve)
        
        return self.calculate_metrics(trades, initial_capital, capital)
    
    def calculate_metrics(self, trades, initial_capital, final_capital):
        """Calculate performance metrics"""
        if not trades:
            return {'Error': 'No trades executed'}
        
        trades_df = pd.DataFrame(trades)
        
        # Calculate years for CAGR
        if len(trades_df) > 0:
            first_date = pd.to_datetime(trades_df['Entry_Date'].iloc[0])
            last_date = pd.to_datetime(trades_df['Exit_Date'].iloc[-1])
            years = (last_date - first_date).days / 365.25
        else:
            years = 1
        
        total_return = (final_capital - initial_capital) / initial_capital * 100
        cagr = ((final_capital / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
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
            'CAGR_%': round(cagr, 2),
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
        """Plot equity curve and chart with signals"""
        if not hasattr(self, 'equity_curve') or len(self.equity_curve) == 0:
            return
        
        fig, axes = plt.subplots(3, 1, figsize=(16, 14))
        
        # Get data with signals
        df = self.df
        
        # Price chart with signals
        ax1 = axes[0]
        ax1.plot(df.index, df['Close'], label='Close', alpha=0.8)
        ax1.plot(df.index, df['SMA50'], label='SMA50', alpha=0.6)
        ax1.plot(df.index, df['SMA150'], label='SMA150', alpha=0.6)
        ax1.plot(df.index, df['SMA200'], label='SMA200', alpha=0.6)
        
        # Mark entry signals
        entries = df[df['entry_signal']]
        if len(entries) > 0:
            ax1.scatter(entries.index, entries['Close'], color='green', 
                      marker='^', s=100, label='Entry', zorder=5)
        
        ax1.set_title(f'Minervini SEPA Strategy - {symbol}')
        ax1.set_ylabel('Price ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Volume
        ax2 = axes[1]
        ax2.bar(df.index, df['Volume'], alpha=0.5, color='blue')
        ax2.plot(df.index, df['avg_volume'], color='red', label='Avg Volume')
        ax2.set_ylabel('Volume')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Equity curve
        ax3 = axes[2]
        ax3.plot(self.equity_curve['Date'], self.equity_curve['Equity'], 
                label='Strategy Equity', color='green', linewidth=2)
        ax3.set_ylabel('Equity ($)')
        ax3.set_xlabel('Date')
        ax3.legend()
        ax3.grid(True)
        
        plt.tight_layout()
        plt.savefig(f'minervini_strategy_{symbol}.png', dpi=150)
        print(f"Chart saved as minervini_strategy_{symbol}.png")
        plt.close()


# Run backtest
if __name__ == "__main__":
    print("=" * 70)
    print("MARK MINERVINI SEPA STRATEGY BACKTEST")
    print("=" * 70)
    print("\nStrategy Rules:")
    print("- Trend Template: 7 of 8 criteria for Stage 2 uptrend")
    print("- VCP: Volatility Contraction Pattern (progressive contractions)")
    print("- Entry: Breakout on volume 40%+ above average")
    print("- Stop: 7.5% initial, trailing at 8%")
    print("- Exit: Stop loss or trend violation (close below 50 SMA)")
    
    # Test on growth stocks
    test_assets = [
        ('AAPL', 'Apple'),
        ('MSFT', 'Microsoft'),
        ('NVDA', 'NVIDIA'),
        ('AMD', 'AMD'),
        ('CRM', 'Salesforce'),
        ('NFLX', 'Netflix'),
        ('AMZN', 'Amazon'),
        ('GOOGL', 'Alphabet'),
    ]
    
    all_results = {}
    
    for symbol, name in test_assets:
        print(f"\n{'='*70}")
        print(f"Testing: {name} ({symbol})")
        print('='*70)
        
        strategy = MinerviniSEPA()
        
        try:
            results = strategy.backtest(symbol, '2019-01-01', '2024-01-01')
            
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
        
        # Calculate portfolio average
        print(f"\n{'='*70}")
        print("PORTFOLIO AVERAGE METRICS")
        print('='*70)
        numeric_cols = ['Total_Return_%', 'CAGR_%', 'Win_Rate_%', 'Profit_Factor', 
                       'Max_Drawdown_%', 'Sharpe_Ratio']
        for col in numeric_cols:
            if col in summary_df.columns:
                avg_val = summary_df[col].mean()
                print(f"  Average {col}: {avg_val:.2f}")
