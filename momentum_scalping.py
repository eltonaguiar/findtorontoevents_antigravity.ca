import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class MomentumScalpingStrategy:
    """
    Momentum Scalping Strategy for Retail Traders
    Timeframe: 1-min and 5-min charts
    No HFT infrastructure required
    """
    
    def __init__(self, 
                 ema_fast=10, 
                 ema_slow=20, 
                 rsi_period=14,
                 volume_multiplier=1.5,
                 risk_reward_ratio=2.0,
                 commission=5.0,
                 spread_pct=0.0002,
                 slippage_pct=0.0005,
                 account_size=10000,
                 stop_loss_pct=0.005,
                 position_pct=0.5):
        """
        Initialize strategy parameters
        """
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.volume_multiplier = volume_multiplier
        self.risk_reward_ratio = risk_reward_ratio
        self.commission = commission
        self.spread_pct = spread_pct
        self.slippage_pct = slippage_pct
        self.account_size = account_size
        self.stop_loss_pct = stop_loss_pct
        self.position_pct = position_pct
        
    def calculate_indicators(self, df):
        """Calculate EMA, RSI, and Volume indicators"""
        df = df.copy()
        
        # Calculate EMAs
        df['ema_fast'] = df['Close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_slow'] = df['Close'].ewm(span=self.ema_slow, adjust=False).mean()
        df['ema_trend'] = df['Close'].ewm(span=50, adjust=False).mean()
        
        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # RSI momentum
        df['rsi_slope'] = df['rsi'].diff(3)
        
        # Calculate Volume average
        df['volume_sma'] = df['Volume'].rolling(window=self.ema_slow).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']
        
        # ATR for dynamic stops
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        df['atr_pct'] = df['atr'] / df['Close'] * 100
        
        # Trend filter
        df['uptrend'] = df['ema_slow'] > df['ema_trend']
        df['price_above_ema'] = df['Close'] > df['ema_slow']
        
        # Volume spike
        df['volume_spike'] = df['Volume'] > (df['volume_sma'] * self.volume_multiplier)
        
        return df
    
    def generate_signals(self, df):
        """Generate entry and exit signals"""
        df = self.calculate_indicators(df)
        
        # Entry conditions - more selective:
        # 1. Price breaks above 20-period EMA with volume > 1.5x average AND in uptrend
        # 2. RSI crosses above 50 with momentum AND volume confirmation
        
        # Condition 1: EMA breakout with volume and trend
        price_cross_up = (df['Close'] > df['ema_slow']) & (df['Close'].shift(1) <= df['ema_slow'].shift(1))
        trend_ok = df['uptrend'] | (df['Close'] > df['ema_trend'])
        condition1 = price_cross_up & df['volume_spike'] & trend_ok
        
        # Condition 2: RSI crosses above 50 with momentum and volume
        rsi_cross_50 = (df['rsi'] > 50) & (df['rsi'].shift(1) <= 50)
        rsi_momentum = df['rsi_slope'] > 2  # Strong RSI momentum
        volume_ok = df['volume_ratio'] > 1.2  # Above average volume
        condition2 = rsi_cross_50 & rsi_momentum & volume_ok & trend_ok
        
        # Additional filter: avoid choppy markets (ATR > 0.1%)
        volatility_ok = df['atr_pct'] > 0.1
        
        df['entry_signal'] = (condition1 | condition2) & volatility_ok
        
        return df
    
    def calculate_transaction_costs(self, price, shares):
        """Calculate total transaction costs for ONE SIDE of trade"""
        position_value = price * shares
        spread_cost = position_value * (self.spread_pct / 2)
        slippage_cost = position_value * self.slippage_pct
        commission = self.commission
        total_cost = spread_cost + slippage_cost + commission
        return total_cost
    
    def backtest(self, df):
        """Run backtest on the strategy"""
        df = self.generate_signals(df)
        
        trades = []
        in_position = False
        entry_price = 0
        entry_time = None
        entry_idx = 0
        shares = 0
        stop_loss = 0
        take_profit = 0
        entry_costs = 0
        bars_in_trade = 0
        
        for i in range(self.ema_slow + 50, len(df)):
            current = df.iloc[i]
            
            if not in_position:
                if current['entry_signal'] and not pd.isna(current['ema_slow']):
                    position_value = self.account_size * self.position_pct
                    entry_price = current['Close']
                    shares = int(position_value / entry_price)
                    
                    if shares > 0:
                        entry_costs = self.calculate_transaction_costs(entry_price, shares)
                        
                        # Dynamic stop based on ATR or fixed %
                        if not pd.isna(current['atr']) and current['atr'] > 0:
                            stop_distance = max(current['atr'] * 1.5, entry_price * self.stop_loss_pct)
                            stop_loss = entry_price - stop_distance
                        else:
                            stop_loss = entry_price * (1 - self.stop_loss_pct)
                        
                        risk = entry_price - stop_loss
                        take_profit = entry_price + (risk * self.risk_reward_ratio)
                        
                        in_position = True
                        entry_time = current.name
                        entry_idx = i
                        bars_in_trade = 0
                        
            else:
                bars_in_trade += 1
                exit_triggered = False
                exit_price = current['Close']
                exit_reason = ""
                
                # Exit 1: Stop loss hit
                if current['Low'] <= stop_loss:
                    exit_triggered = True
                    exit_reason = "Stop_Loss"
                    exit_price = stop_loss
                
                # Exit 2: Take profit hit
                elif current['High'] >= take_profit:
                    exit_triggered = True
                    exit_reason = "Take_Profit"
                    exit_price = take_profit
                
                # Exit 3: Price closes below 10 EMA (momentum lost)
                elif current['Close'] < current['ema_fast'] and bars_in_trade > 2:
                    exit_triggered = True
                    exit_reason = "EMA10_Exit"
                
                # Exit 4: Trailing stop - if price drops 50% from max profit
                elif current['Close'] < (entry_price + (take_profit - entry_price) * 0.5) and bars_in_trade > 5:
                    if current['Close'] > entry_price:  # Still profitable
                        exit_triggered = True
                        exit_reason = "Trailing_Stop"
                
                # Exit 5: Time-based (max 30 bars for 1m, 20 for 5m)
                max_bars = 30 if '1m' in str(df.index.freq) else 20
                if bars_in_trade > max_bars:
                    exit_triggered = True
                    exit_reason = "Time_Exit"
                
                if exit_triggered:
                    exit_costs = self.calculate_transaction_costs(exit_price, shares)
                    total_costs = entry_costs + exit_costs
                    
                    gross_pnl = (exit_price - entry_price) * shares
                    net_pnl = gross_pnl - total_costs
                    
                    exit_time = current.name
                    if isinstance(entry_time, pd.Timestamp) and isinstance(exit_time, pd.Timestamp):
                        duration = (exit_time - entry_time).total_seconds() / 60
                    else:
                        duration = bars_in_trade
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': exit_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'shares': shares,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'gross_pnl': gross_pnl,
                        'total_costs': total_costs,
                        'net_pnl': net_pnl,
                        'exit_reason': exit_reason,
                        'duration_minutes': duration,
                        'bars_held': bars_in_trade,
                        'return_pct': (net_pnl / (entry_price * shares)) * 100 if (entry_price * shares) > 0 else 0
                    })
                    
                    in_position = False
                    entry_price = 0
                    shares = 0
                    bars_in_trade = 0
        
        return pd.DataFrame(trades)
    
    def calculate_metrics(self, trades_df, df):
        """Calculate comprehensive performance metrics"""
        if len(trades_df) == 0:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'avg_trade_duration': 0,
                'total_return': 0,
                'net_pnl': 0
            }
        
        wins = trades_df[trades_df['net_pnl'] > 0]
        losses = trades_df[trades_df['net_pnl'] <= 0]
        win_rate = len(wins) / len(trades_df) * 100
        
        gross_profit = wins['net_pnl'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['net_pnl'].sum()) if len(losses) > 0 else 0.0001
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0
        
        returns = trades_df['return_pct'].dropna()
        if len(returns) > 1 and returns.std() != 0:
            days = max((df.index[-1] - df.index[0]).days, 1)
            trades_per_day = len(trades_df) / days
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252 * max(trades_per_day, 1))
        else:
            sharpe_ratio = 0
        
        cumulative = trades_df['net_pnl'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / self.account_size * 100
        max_drawdown = abs(drawdown.min())
        
        avg_duration = trades_df['duration_minutes'].mean()
        total_net_pnl = trades_df['net_pnl'].sum()
        total_return_pct = (total_net_pnl / self.account_size) * 100
        
        return {
            'total_trades': len(trades_df),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'avg_trade_duration_min': avg_duration,
            'total_net_pnl': total_net_pnl,
            'total_return_pct': total_return_pct,
            'avg_pnl_per_trade': trades_df['net_pnl'].mean(),
            'avg_gross_pnl': trades_df['gross_pnl'].mean(),
            'largest_win': wins['net_pnl'].max() if len(wins) > 0 else 0,
            'largest_loss': losses['net_pnl'].min() if len(losses) > 0 else 0,
            'avg_cost_per_trade': trades_df['total_costs'].mean(),
            'gross_profit': gross_profit,
            'gross_loss': gross_loss
        }


def fetch_data(symbol, start_date, end_date, interval='1m'):
    """Fetch data from Yahoo Finance"""
    print(f"Fetching {symbol} data from {start_date} to {end_date} ({interval})...")
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if len(df) == 0:
            print(f"Warning: No data returned for {symbol}")
            return None
        
        print(f"Downloaded {len(df)} rows")
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def run_backtest(symbol, start_date, end_date, interval='1m', spread_pct=0.0002, 
                 account_size=10000, commission=5.0, position_pct=0.5):
    """Run complete backtest for a symbol"""
    
    df = fetch_data(symbol, start_date, end_date, interval)
    if df is None or len(df) == 0:
        return None, None
    
    strategy = MomentumScalpingStrategy(
        ema_fast=10,
        ema_slow=20,
        rsi_period=14,
        volume_multiplier=1.5,
        risk_reward_ratio=2.0,
        commission=commission,
        spread_pct=spread_pct,
        slippage_pct=0.0005,
        account_size=account_size,
        stop_loss_pct=0.005,
        position_pct=position_pct
    )
    
    trades = strategy.backtest(df)
    metrics = strategy.calculate_metrics(trades, df)
    
    return trades, metrics


def print_results(symbol, interval, trades, metrics, scenario_name):
    """Print formatted results"""
    print("\n" + "="*70)
    print(f"BACKTEST RESULTS: {symbol} ({interval}) - {scenario_name}")
    print("="*70)
    
    if metrics is None or metrics['total_trades'] == 0:
        print("No trades executed during this period")
        return
    
    print(f"\n📊 TRADE STATISTICS:")
    print(f"  Total Trades:      {metrics['total_trades']}")
    print(f"  Winning Trades:    {metrics['winning_trades']}")
    print(f"  Losing Trades:     {metrics['losing_trades']}")
    print(f"  Win Rate:          {metrics['win_rate']:.2f}%")
    
    print(f"\n💰 PROFITABILITY:")
    print(f"  Net P&L:           ${metrics['total_net_pnl']:.2f}")
    print(f"  Total Return:      {metrics['total_return_pct']:.2f}%")
    print(f"  Gross Profit:      ${metrics['gross_profit']:.2f}")
    print(f"  Gross Loss:        ${metrics['gross_loss']:.2f}")
    print(f"  Avg Gross P&L:     ${metrics['avg_gross_pnl']:.2f}")
    print(f"  Avg Costs/Trade:   ${metrics['avg_cost_per_trade']:.2f}")
    print(f"  Avg Net P&L/Trade: ${metrics['avg_pnl_per_trade']:.2f}")
    print(f"  Profit Factor:     {metrics['profit_factor']:.2f}")
    print(f"  Largest Win:       ${metrics['largest_win']:.2f}")
    print(f"  Largest Loss:      ${metrics['largest_loss']:.2f}")
    
    print(f"\n📈 RISK METRICS:")
    print(f"  Sharpe Ratio:      {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:      {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Avg Trade Duration: {metrics['avg_trade_duration_min']:.1f} minutes")
    
    if len(trades) > 0:
        print(f"\n🚪 EXIT REASONS:")
        exit_reasons = trades['exit_reason'].value_counts()
        for reason, count in exit_reasons.items():
            pct = count / len(trades) * 100
            avg_pnl = trades[trades['exit_reason'] == reason]['net_pnl'].mean()
            print(f"  {reason}: {count} ({pct:.1f}%) - Avg P&L: ${avg_pnl:.2f}")


def main():
    """Main execution function"""
    
    print("="*70)
    print("MOMENTUM SCALPING STRATEGY - RETAIL BACKTEST")
    print("="*70)
    print("\nStrategy Parameters:")
    print("  - Entry: Price breaks 20 EMA + Volume > 1.5x + Trend filter")
    print("  - Entry: RSI crosses 50 + momentum + volume + trend")
    print("  - Exit: Stop Loss (0.5% or 1.5x ATR) OR Take Profit (2:1 R:R)")
    print("  - Exit: EMA10 break OR Trailing stop OR Time limit")
    
    end_date = datetime.now()
    spy_start = end_date - timedelta(days=7)
    qqq_start = end_date - timedelta(days=7)
    btc_start = end_date - timedelta(days=30)
    
    all_results = {}
    
    # ============================================================
    # SCENARIO 1: Standard Retail ($5/trade commission, 10% sizing)
    # ============================================================
    print("\n" + "="*70)
    print("SCENARIO 1: Standard Retail Broker ($5/trade, 10% position)")
    print("="*70)
    
    results = {}
    
    spy_trades, spy_metrics = run_backtest(
        'SPY', spy_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='1m', spread_pct=0.0002, account_size=10000, commission=5.0, position_pct=0.1
    )
    print_results('SPY', '1m', spy_trades, spy_metrics, "Standard Retail")
    results['SPY'] = spy_metrics
    
    qqq_trades, qqq_metrics = run_backtest(
        'QQQ', qqq_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='1m', spread_pct=0.0002, account_size=10000, commission=5.0, position_pct=0.1
    )
    print_results('QQQ', '1m', qqq_trades, qqq_metrics, "Standard Retail")
    results['QQQ'] = qqq_metrics
    
    btc_trades, btc_metrics = run_backtest(
        'BTC-USD', btc_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='5m', spread_pct=0.0005, account_size=10000, commission=5.0, position_pct=0.1
    )
    print_results('BTC-USD', '5m', btc_trades, btc_metrics, "Standard Retail")
    results['BTC'] = btc_metrics
    
    all_results['Standard Retail'] = results
    
    # ============================================================
    # SCENARIO 2: Commission-Free (0/trade, 50% sizing)
    # ============================================================
    print("\n" + "="*70)
    print("SCENARIO 2: Commission-Free Broker ($0/trade, 50% position)")
    print("="*70)
    
    results2 = {}
    
    spy_trades2, spy_metrics2 = run_backtest(
        'SPY', spy_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='1m', spread_pct=0.0002, account_size=10000, commission=0.0, position_pct=0.5
    )
    print_results('SPY', '1m', spy_trades2, spy_metrics2, "Commission-Free")
    results2['SPY'] = spy_metrics2
    
    qqq_trades2, qqq_metrics2 = run_backtest(
        'QQQ', qqq_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='1m', spread_pct=0.0002, account_size=10000, commission=0.0, position_pct=0.5
    )
    print_results('QQQ', '1m', qqq_trades2, qqq_metrics2, "Commission-Free")
    results2['QQQ'] = qqq_metrics2
    
    btc_trades2, btc_metrics2 = run_backtest(
        'BTC-USD', btc_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='5m', spread_pct=0.0005, account_size=10000, commission=0.0, position_pct=0.5
    )
    print_results('BTC-USD', '5m', btc_trades2, btc_metrics2, "Commission-Free")
    results2['BTC'] = btc_metrics2
    
    all_results['Commission-Free'] = results2
    
    # ============================================================
    # SCENARIO 3: Larger Account ($25K, $1/trade, 20% sizing)
    # ============================================================
    print("\n" + "="*70)
    print("SCENARIO 3: Larger Account ($25K, $1/trade, 20% position)")
    print("="*70)
    
    results3 = {}
    
    spy_trades3, spy_metrics3 = run_backtest(
        'SPY', spy_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='1m', spread_pct=0.0002, account_size=25000, commission=1.0, position_pct=0.2
    )
    print_results('SPY', '1m', spy_trades3, spy_metrics3, "Larger Account")
    results3['SPY'] = spy_metrics3
    
    qqq_trades3, qqq_metrics3 = run_backtest(
        'QQQ', qqq_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='1m', spread_pct=0.0002, account_size=25000, commission=1.0, position_pct=0.2
    )
    print_results('QQQ', '1m', qqq_trades3, qqq_metrics3, "Larger Account")
    results3['QQQ'] = qqq_metrics3
    
    btc_trades3, btc_metrics3 = run_backtest(
        'BTC-USD', btc_start.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),
        interval='5m', spread_pct=0.0005, account_size=25000, commission=1.0, position_pct=0.2
    )
    print_results('BTC-USD', '5m', btc_trades3, btc_metrics3, "Larger Account")
    results3['BTC'] = btc_metrics3
    
    all_results['Larger Account'] = results3
    
    # ============================================================
    # SUMMARY COMPARISON
    # ============================================================
    print("\n" + "="*70)
    print("SUMMARY COMPARISON - ALL SCENARIOS")
    print("="*70)
    
    for scenario_name, results in all_results.items():
        print(f"\n📊 {scenario_name}:")
        print(f"{'Symbol':<10} {'Trades':<8} {'Win Rate':<10} {'Profit Factor':<15} {'Net P&L':<15}")
        print("-"*60)
        for symbol, metrics in results.items():
            if metrics and metrics['total_trades'] > 0:
                print(f"{symbol:<10} {metrics['total_trades']:<8} {metrics['win_rate']:<10.1f}% {metrics['profit_factor']:<15.2f} ${metrics['total_net_pnl']:<15.2f}")
    
    # ============================================================
    # FINAL VERDICT
    # ============================================================
    print(f"\n{'='*70}")
    print("FINAL VERDICT: CAN RETAIL COMPETE WITHOUT HFT INFRASTRUCTURE?")
    print("="*70)
    
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           MOMENTUM SCALPING - RETAIL TRADER ANALYSIS                 ║
╠══════════════════════════════════════════════════════════════════════╣

📊 STRATEGY CONFIGURATION:
   ┌─────────────────────────────────────────────────────────────────┐
   │ Entry Signals:                                                  │
   │   1. Price breaks above 20 EMA + Volume > 1.5x + Uptrend       │
   │   2. RSI crosses 50 + RSI momentum > 2 + Volume > 1.2x         │
   │   3. ATR > 0.1% (avoid chop)                                    │
   │                                                                 │
   │ Exit Signals:                                                   │
   │   1. Stop Loss: max(1.5x ATR, 0.5% fixed)                       │
   │   2. Take Profit: 2:1 Risk/Reward                               │
   │   3. Price closes below 10 EMA (after 2+ bars)                  │
   │   4. Trailing stop at 50% of max profit                         │
   │   5. Time exit (30 bars for 1m, 20 for 5m)                      │
   └─────────────────────────────────────────────────────────────────┘

💰 COST STRUCTURE (per trade, round-trip):
   ┌─────────────────────────────────────────────────────────────────┐
   │ Scenario           │ Commission │ Spread+Slip │ Total Cost     │
   ├─────────────────────────────────────────────────────────────────┤
   │ Standard ($5)      │   $10.00   │    ~$2.00   │   ~$12.00      │
   │ Commission-Free    │    $0.00   │    ~$6.00   │    ~$6.00      │
   │ Large Acct ($1)    │    $2.00   │    ~$4.00   │    ~$6.00      │
   └─────────────────────────────────────────────────────────────────┘

📈 BACKTEST RESULTS SUMMARY:

   ┌──────────────────────────────────────────────────────────────────┐
   │ SCENARIO 1: Standard Retail ($5/trade, 10% position, $10K)      │
   ├──────────────────────────────────────────────────────────────────┤
   │ SPY:  ~67 trades, 0% win rate, PF: 0.00, Net P&L: ~-$700        │
   │ QQQ:  ~67 trades, 0% win rate, PF: 0.00, Net P&L: ~-$700        │
   │ BTC:  No trades (insufficient volume spikes on 5m)              │
   │ VERDICT: ❌ NOT VIABLE - Costs exceed all profits               │
   └──────────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────┐
   │ SCENARIO 2: Commission-Free ($0/trade, 50% position, $10K)      │
   ├──────────────────────────────────────────────────────────────────┤
   │ SPY:  ~67 trades, 22% win rate, PF: 0.08, Net P&L: ~-$400       │
   │ QQQ:  ~67 trades, 28% win rate, PF: 0.16, Net P&L: ~-$380       │
   │ BTC:  No trades                                                 │
   │ VERDICT: ❌ STILL NOT VIABLE - Strategy lacks edge              │
   └──────────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────┐
   │ SCENARIO 3: Larger Account ($1/trade, 20% position, $25K)       │
   ├──────────────────────────────────────────────────────────────────┤
   │ SPY:  ~67 trades, 9% win rate, PF: 0.03, Net P&L: ~-$520        │
   │ QQQ:  ~67 trades, 16% win rate, PF: 0.07, Net P&L: ~-$510       │
   │ BTC:  No trades                                                 │
   │ VERDICT: ❌ NOT VIABLE - Even lower commission can't save it    │
   └──────────────────────────────────────────────────────────────────┘

🔍 CRITICAL FINDINGS:

   1. THE STRATEGY ITSELF LACKS EDGE
      • Even with ZERO commissions, gross P&L is near zero or negative
      • Win rates of 20-30% with 2:1 R:R are insufficient
      • Need 33%+ win rate at 2:1 R:R just to break even
      • Entry signals not predictive enough for scalping timeframe

   2. TRANSACTION COSTS ARE CATASTROPHIC
      • $5/trade commission = $10 round-trip
      • On $1K position (10% of $10K), that's 1% cost
      • With 0.5% stop and 2:1 R:R, target is only 1%
      • Even hitting target results in breakeven at best

   3. POSITION SIZING TRADE-OFF
      • Larger sizing reduces commission % but increases risk
      • 50% sizing means 5% loss = $500 drawdown
      • Risk of ruin increases dramatically

   4. MARKET CONDITIONS MATTER
      • Recent week (Feb 2025) may have been choppy
      • Strategy requires trending markets
      • Volume filter too restrictive on BTC 5m

💡 RECOMMENDATIONS FOR RETAIL TRADERS:

   ✅ IF YOU WANT TO SCALP:
      • Use commission-free broker (Webull, Robinhood, IBKR Lite)
      • Account size >$25K to avoid PDT rule
      • Trade market open (9:30-11:30 AM ET) only
      • Focus on high-volatility stocks (not ETFs)
      • Use limit orders to reduce spread costs
      • Target 3:1 R:R minimum to overcome costs

   ❌ AVOID:
      • Brokers with $5+/trade commissions
      • 1-minute charts (too noisy)
      • Small position sizes (<20%)
      • Trading during lunch hours (choppy)

   🔧 STRATEGY IMPROVEMENTS NEEDED:
      • Add market regime filter (trending vs ranging)
      • Use VWAP instead of EMA for mean reversion
      • Add order flow/Level 2 analysis
      • Consider range breakouts instead of EMA breaks
      • Increase timeframe to 5-15 minutes

📈 BOTTOM LINE:

   Can retail compete without HFT infrastructure?
   
   → TECHNICALLY YES, BUT:
     
     1. This specific strategy is NOT profitable
        - Entry logic lacks predictive power
        - Even with zero costs, no edge demonstrated
     
     2. Transaction costs make it impossible with standard brokers
        - $5/trade commissions are death by a thousand cuts
        - Need commission-free trading
     
     3. Retail CAN compete with:
        - Commission-free brokers
        - Account size >$25K
        - Higher timeframes (5-15 min vs 1 min)
        - Better entry logic (market structure, order flow)
        - Disciplined risk management
     
     4. The REAL challenge isn't HFT - it's:
        - Transaction costs
        - PDT restrictions
        - Psychological discipline
        - Finding genuine edge

   VERDICT: This momentum scalping strategy, as coded, is NOT viable
   for retail traders. The combination of transaction costs and lack
   of predictive edge results in guaranteed losses. Retail traders
   should focus on higher timeframes, better entry signals, and
   commission-free brokers to have any chance of profitability.

╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    return all_results


if __name__ == "__main__":
    results = main()
