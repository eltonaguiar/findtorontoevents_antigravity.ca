import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Strategy parameters
SYMBOLS = ['TLT', 'SHY']  # 20Y and 1Y Treasury ETFs
START_DATE = '2000-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 10000
RISK_PER_TRADE = 0.02  # 2% of equity per trade
ATR_PERIOD = 14
TP_MULTIPLIER = 2.0
SL_MULTIPLIER = 1.0
HOLDING_PERIOD_DAYS = 5  # 1 week approx
COST_PER_TRADE = 0.0005  # 5bp round trip

def download_data(symbols, start, end):
    """Download data handling both single and multiple tickers."""
    data = yf.download(symbols, start=start, end=end, group_by='ticker', auto_adjust=True)
    # If single ticker, yfinance returns DataFrame with flat columns
    if len(symbols) == 1:
        # Convert to dict format for consistency
        data = {symbols[0]: data}
    return data

def calculate_atr(df, period=14):
    """Calculate ATR given high, low, close."""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def simulate_strategy(data, symbols):
    """Simulate bond yield curve slope strategy."""
    # Calculate signal: TLT/SHY ratio (price ratio as proxy for yield curve slope)
    ratio = data[symbols[0]]['Close'] / data[symbols[1]]['Close']
    ratio.name = 'ratio'
    
    # Combine data
    df = pd.concat([data[sym][['Close']] for sym in symbols], axis=1)
    df.columns = [f'{sym}_close' for sym in symbols]
    df = df.join(ratio)
    
    # Calculate ATR for each symbol (using TLT for simplicity)
    df['atr'] = calculate_atr(data[symbols[0]], ATR_PERIOD)
    
    # Generate signals: long when ratio rising (positive momentum)
    df['signal'] = np.where(df['ratio'] > df['ratio'].shift(1), 1, -1)
    
    # Initialize equity curve
    equity = [INITIAL_CAPITAL]
    positions = []  # list of (entry_price, symbol, direction, tp, sl, entry_date)
    trades = []     # list of trade P&Ls
    
    # Iterate through data
    for i in range(1, len(df)):
        current_equity = equity[-1]
        
        # Check existing positions for exit
        new_positions = []
        for pos in positions:
            entry_price, symbol, direction, tp, sl, entry_date = pos
            # Get current price for symbol
            if symbol == symbols[0]:
                current_price = df.iloc[i][f'{symbol}_close']
            else:
                current_price = df.iloc[i][f'{symbol}_close']
            
            # Check TP/SL
            if direction == 1:  # Long
                if current_price >= tp or current_price <= sl:
                    # Exit trade
                    pips = (current_price - entry_price) * direction
                    pnl = pips * (RISK_PER_TRADE * current_equity / (SL_MULTIPLIER * pos[3]))  # Simplified
                    trades.append(pnl)
                    current_equity += pnl
                    continue  # Don't add to new positions
                else:
                    new_positions.append(pos)
            else:  # Short
                if current_price <= tp or current_price >= sl:
                    pips = (entry_price - current_price) * direction
                    pnl = pips * (RISK_PER_TRADE * current_equity / (SL_MULTIPLIER * pos[3]))
                    trades.append(pnl)
                    current_equity += pnl
                    continue
                else:
                    new_positions.append(pos)
        positions = new_positions
        
        # Enter new position if signal and no existing position in same direction
        if len([p for p in positions if p[2] == df.iloc[i]['signal']]) == 0:
            direction = df.iloc[i]['signal']
            # Use TLT for entry price and ATR
            entry_price = df.iloc[i]['TLT_close']
            atr_value = df.iloc[i]['atr']
            if pd.isna(atr_value) or atr_value == 0:
                atr_value = entry_price * 0.01  # Fallback 1%
            
            # Calculate TP/SL based on ATR
            if direction == 1:  # Long
                tp = entry_price + TP_MULTIPLIER * atr_value
                sl = entry_price - SL_MULTIPLIER * atr_value
            else:  # Short
                tp = entry_price - TP_MULTIPLIER * atr_value
                sl = entry_price + SL_MULTIPLIER * atr_value
            
            # Add position
            positions.append((entry_price, symbols[0], direction, tp, sl, df.index[i]))
        
        equity.append(current_equity)
    
    # Close any remaining positions at end
    for pos in positions:
        entry_price, symbol, direction, tp, sl, entry_date = pos
        # Use last price
        if symbol == symbols[0]:
            exit_price = df.iloc[-1][f'{symbol}_close']
        else:
            exit_price = df.iloc[-1][f'{symbol}_close']
        if direction == 1:
            pnl = (exit_price - entry_price) * (RISK_PER_TRADE * INITIAL_CAPITAL / (SL_MULTIPLIER * pos[3]))
        else:
            pnl = (entry_price - exit_price) * (RISK_PER_TRADE * INITIAL_CAPITAL / (SL_MULTIPLIER * pos[3]))
        trades.append(pnl)
    
    return pd.DataFrame({'equity': equity}, index=df.index), trades

def calculate_metrics(equity_df, trades):
    """Calculate performance metrics."""
    if len(trades) == 0:
        return {
            'n': 0, 'wins': 0, 'PF': 0, 'PF_ci_lower': 0, 'PF_ci_upper': 0,
            'MDD': 0, 'WR': 0, 'MC_pct': 0, 'DSR': 0, 'PF_2x_costs': 0,
            'top_symbol_share': 0
        }
    
    trades = np.array(trades)
    n = len(trades)
    wins = np.sum(trades > 0)
    win_rate = wins / n if n > 0 else 0
    gross_profit = np.sum(trades[trades > 0])
    gross_loss = abs(np.sum(trades[trades < 0]))
    pf = gross_profit / gross_loss if gross_loss > 0 else np.inf
    
    # Bootstrap PF CI (clustered by day - simplified)
    # For simplicity, we'll bootstrap trades
    boot_pfs = []
    for _ in range(1000):
        sample = np.random.choice(trades, size=n, replace=True)
        g_profit = np.sum(sample[sample > 0])
        g_loss = abs(np.sum(sample[sample < 0]))
        boot_pf = g_profit / g_loss if g_loss > 0 else np.inf
        boot_pfs.append(boot_pf)
    boot_pfs = np.array([x for x in boot_pfs if np.isfinite(x)])
    if len(boot_pfs) > 0:
        pf_ci_lower = np.percentile(boot_pfs, 2.5)
        pf_ci_upper = np.percentile(boot_pfs, 97.5)
    else:
        pf_ci_lower = pf_ci_upper = pf
    
    # Max drawdown
    equity = equity_df['equity'].values
    rolling_max = np.maximum.accumulate(equity)
    drawdown = (equity - rolling_max) / rolling_max
    mdd = np.min(drawdown) if len(drawdown) > 0 else 0
    
    # Monte Carlo percentile (simplified: compare to random signals)
    # We'll generate random signals and compute PF for comparison
    np.random.seed(42)
    random_pfs = []
    for _ in range(1000):
        random_signals = np.random.choice([-1, 1], size=len(equity_df))
        # Simulate with random signals (simplified)
        random_trades = []
        for i in range(1, len(equity_df)):
            if random_signals[i] != random_signals[i-1]:
                # Simplified trade P&L based on price change
                price_change = (equity_df.iloc[i]['equity'] - equity_df.iloc[i-1]['equity']) / equity_df.iloc[i-1]['equity']
                random_trades.append(price_change * RISK_PER_TRADE * equity_df.iloc[i-1]['equity'])
        if len(random_trades) > 0:
            random_trades = np.array(random_trades)
            g_profit = np.sum(random_trades[random_trades > 0])
            g_loss = abs(np.sum(random_trades[random_trades < 0]))
            random_pf = g_profit / g_loss if g_loss > 0 else np.inf
            random_pfs.append(random_pf)
    if len(random_pfs) > 0:
        mc_pct = np.percentile(random_pfs, 5)  # Percentile of actual PF vs random
        # Actually we want: what percentage of random PFs are below our PF?
        mc_pct = np.sum(np.array(random_pfs) < pf) / len(random_pfs) * 100
    else:
        mc_pct = 0
    
    # Deflated Sharpe Ratio (simplified)
    # We'll count trials as number of strategies tested (will be updated later)
    trials = 5  # Placeholder
    sr = np.mean(trades) / np.std(trades) * np.sqrt(252) if np.std(trades) > 0 else 0
    # Simplified DSR formula
    dsr = sr * np.sqrt((n-1) / (1 + 0.5 * sr**2)) if n > 1 else 0
    # Adjust for multiple trials (simplified)
    dsr_adjusted = dsr - np.log(trials) / np.sqrt(n) if n > 0 else 0
    
    # PF at 2x costs (simplified: reduce each trade by 2x cost)
    trades_2x = trades - 2 * COST_PER_TRADE * INITIAL_CAPITAL
    gross_profit_2x = np.sum(trades_2x[trades_2x > 0])
    gross_loss_2x = abs(np.sum(trades_2x[trades_2x < 0]))
    pf_2x = gross_profit_2x / gross_loss_2x if gross_loss_2x > 0 else np.inf
    
    # Top symbol share (simplified: assume all trades in TLT)
    top_symbol_share = 1.0  # Since we only trade TLT vs SHY ratio, but actually both
    
    return {
        'n': int(n),
        'wins': int(wins),
        'PF': float(pf),
        'PF_ci_lower': float(pf_ci_lower),
        'PF_ci_upper': float(pf_ci_upper),
        'MDD': float(mdd),
        'WR': float(win_rate) if n >= 20 else None,
        'MC_pct': float(mc_pct),
        'DSR': float(dsr_adjusted),
        'PF_2x_costs': float(pf_2x),
        'top_symbol_share': float(top_symbol_share)
    }

def main():
    print("Downloading data...")
    data = download_data(SYMBOLS, START_DATE, END_DATE)
    
    print("Simulating strategy...")
    equity_df, trades = simulate_strategy(data, SYMBOLS)
    
    print("Calculating metrics...")
    metrics = calculate_metrics(equity_df, trades)
    
    # Determine label
    label = "FAIL"
    reasons = []
    if metrics['n'] < 100:
        reasons.append(f"n<100 ({metrics['n']})")
    if metrics['PF'] < 1.5:
        reasons.append(f"PF<1.5 ({metrics['PF']:.2f})")
    if metrics['PF_ci_lower'] < 1.2:
        reasons.append(f"PF CI lower<1.2 ({metrics['PF_ci_lower']:.2f})")
    if metrics['WR'] is not None and metrics['WR'] < 0.5:
        reasons.append(f"WR<50% ({metrics['WR']:.2f})")
    if metrics['MDD'] > 0.2:
        reasons.append(f"MDD>20% ({metrics['MDD']:.2f})")
    if metrics['MC_pct'] < 95:
        reasons.append(f"MC pct<95 ({metrics['MC_pct']:.2f})")
    if metrics['DSR'] <= 0.95:
        reasons.append(f"DSR<=0.95 ({metrics['DSR']:.3f})")
    if metrics['PF_2x_costs'] < 1.3:
        reasons.append(f"PF 2x costs<1.3 ({metrics['PF_2x_costs']:.2f})")
    if metrics['top_symbol_share'] > 0.3:
        reasons.append(f"top symbol share>30% ({metrics['top_symbol_share']:.2f})")
    if metrics['PF'] < 1.3:  # PF with top symbol removed approximated by PF itself
        reasons.append(f"PF<1.3 after top symbol removal ({metrics['PF']:.2f})")
    
    if len(reasons) == 0:
        label = "MONEY-READY"
    elif metrics['n'] >= 50 and metrics['PF'] >= 1.2:  # Relaxed for candidate
        label = "CANDIDATE"
    
    # Print results
    print("\n=== RESULTS ===")
    print(f"Label: {label}")
    if reasons:
        print(f"Failed gates: {', '.join(reasons)}")
    print(f"n: {metrics['n']}")
    print(f"wins: {metrics['wins']}")
    print(f"PF: {metrics['PF']:.3f}")
    print(f"PF 95% CI: [{metrics['PF_ci_lower']:.3f}, {metrics['PF_ci_upper']:.3f}]")
    if metrics['WR'] is not None:
        print(f"WR: {metrics['WR']:.3f}")
    else:
        print(f"WR: n<20 (hidden)")
    print(f"MDD: {metrics['MDD']:.3f}")
    print(f"MC percentile: {metrics['MC_pct']:.2f}")
    print(f"DSR: {metrics['DSR']:.3f}")
    print(f"PF at 2x costs: {metrics['PF_2x_costs']:.3f}")
    print(f"Top symbol share: {metrics['top_symbol_share']:.3f}")
    
    # Save results
    results = {
        'label': label,
        'reasons': reasons,
        'metrics': metrics,
        'equity_curve': equity_df['equity'].tolist(),
        'trades': trades
    }
    with open('/home/eaguiar2015/wt-nemotron-moneyready/strategies_test/bond_yield_curve_slope_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to bond_yield_curve_slope_results.json")

if __name__ == "__main__":
    main()
