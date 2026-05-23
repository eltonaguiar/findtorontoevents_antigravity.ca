import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Manual RSI implementation."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Manual ATR implementation."""
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def rsi_momentum_strategy(df: pd.DataFrame, 
                         rsi_length: int = 5, 
                         threshold: float = 70.0,
                         sl_pct: float = 0.02,
                         risk_per_trade: float = 0.01,
                         atr_length: int = 14) -> pd.DataFrame:
    """
    RSI Momentum Incubator Strategy - Long-only momentum continuation (chase strength).
    
    Entry: RSI({rsi_length}) crosses above {threshold}
    Exit: RSI({rsi_length}) crosses below {threshold}
    Risk: SL = entry_price * (1 - sl_pct)
    Sizing: risk_per_trade / sl_distance_pct
    
    Compatible with backtest engine: returns df with 'entry_long', 'exit_long', 'rsi', 'atr', 'sl_pct', 'risk_per_trade'
    """
    df = df.copy()
    
    # Compute indicators
    df['rsi'] = rsi(df['close'], rsi_length)
    df['atr'] = atr(df, atr_length)
    
    # Signals
    df['entry_long'] = (df['rsi'] > threshold) & (df['rsi'].shift(1) <= threshold)
    df['exit_long'] = (df['rsi'] < threshold) & (df['rsi'].shift(1) >= threshold)
    
    # Risk params
    df['sl_pct'] = -sl_pct
    df['risk_per_trade'] = risk_per_trade
    
    return df

def compute_position_size(equity: float, entry_price: float, sl_price: float, risk_per_trade: float) -> float:
    risk_distance = (entry_price - sl_price) / entry_price
    size_pct = (risk_per_trade / risk_distance) if risk_distance > 0 else 0.0
    return min(size_pct, 1.0)

def simple_backtest(df: pd.DataFrame, initial_equity: float = 100000.0, 
                    sl_pct: float = 0.02, risk_per_trade: float = 0.01) -> Dict[str, Any]:
    """Simple backtest simulation with fixed SL."""
    df = rsi_momentum_strategy(df)
    df = df.dropna()  # Drop NaNs
    
    trades: List[Dict] = []
    position = None
    equity = initial_equity
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        if row['entry_long'] and position is None:
            entry_price = row['close']
            sl_price = entry_price * (1 - sl_pct)
            size_pct = compute_position_size(equity, entry_price, sl_price, risk_per_trade)
            position = {
                'entry_idx': i,
                'entry_price': entry_price,
                'sl_price': sl_price,
                'peak_price': entry_price,
                'size_pct': size_pct,
                'units': (equity * size_pct) / entry_price
            }
            
        elif position is not None:
            # Update peak for potential trailing (basic)
            position['peak_price'] = max(position['peak_price'], row['high'])
            
            # SL hit?
            if row['low'] <= position['sl_price']:
                exit_price = max(position['sl_price'], row['low'])  # Conservative fill
                pnl_dollar = position['units'] * (exit_price - position['entry_price'])
                pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                equity += pnl_dollar
                trades.append({
                    'entry_idx': position['entry_idx'],
                    'exit_idx': i,
                    'pnl_pct': pnl_pct,
                    'exit_reason': 'SL Hit'
                })
                position = None
            # Signal exit
            elif row['exit_long']:
                exit_price = row['close']
                pnl_dollar = position['units'] * (exit_price - position['entry_price'])
                pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                equity += pnl_dollar
                trades.append({
                    'entry_idx': position['entry_idx'],
                    'exit_idx': i,
                    'pnl_pct': pnl_pct,
                    'exit_reason': 'RSI Exit'
                })
                position = None
    
    # Stats
    n_trades = len(trades)
    if n_trades > 0:
        pnls = [t['pnl_pct'] for t in trades]
        win_rate = sum(p > 0 for p in pnls) / n_trades
        total_return = (equity - initial_equity) / initial_equity
    else:
        win_rate = 0.0
        total_return = 0.0
    
    return {
        'n_trades': n_trades,
        'win_rate': win_rate,
        'total_return': total_return,
        'final_equity': equity,
        'trades': trades
    }

def generate_synthetic_data(n_bars: int = 2000, seed: int = 42, base_price: float = 40000.0) -> pd.DataFrame:
    np.random.seed(seed)
    t = np.linspace(0, 12 * np.pi, n_bars)
    trend_returns = 0.0003 * np.sin(t) + np.random.normal(0, 0.004, n_bars)  # Momentum-friendly
    log_prices = np.cumsum(trend_returns) + np.log(base_price)
    close = np.exp(log_prices)
    
    high = close * (1 + np.random.uniform(0.005, 0.015, n_bars))
    low = close * (1 - np.random.uniform(0.005, 0.015, n_bars))
    open_price = np.roll(close * 0.9995, 1)  # Slight gap
    open_price[0] = close[0]
    volume = np.random.uniform(100, 1000, n_bars)
    
    index = pd.date_range(start='2024-01-01', periods=n_bars, freq='1H')
    
    return pd.DataFrame({'open': open_price, 'high': high, 'low': low, 'close': close, 'volume': volume}, index=index)

def test_strategy():
    print("=== RSI(5) Momentum Strategy Test (Long-only Crypto) ===")
    print("Entry: RSI5 >70 cross | Exit: RSI5 <70 cross | SL: -2% | Risk: 1%/trade")
    
    df = generate_synthetic_data()
    bt_results = simple_backtest(df)
    
    sig_df = rsi_momentum_strategy(df)
    n_entries = sig_df['entry_long'].sum()
    n_exits = sig_df['exit_long'].sum()
    
    print(f"\nSynthetic BTC 1H (2000 bars):")
    print(f"  Entries: {int(n_entries)}")
    print(f"  Exits: {int(n_exits)}")
    print(f"  Simulated Trades: {bt_results['n_trades']}")
    print(f"  Win Rate: {bt_results['win_rate']:.1%}")
    print(f"  Total Return: {bt_results['total_return']*100:+.2f}%")
    
    if bt_results['trades']:
        print("\nSample trades:")
        for t in bt_results['trades'][:3]:
            hold = t['exit_idx'] - t['entry_idx']
            print(f"  Bar {t['entry_idx']:4d} -> {t['exit_idx']:4d} ({hold:2d} bars) | "
                  f"PnL: {t['pnl_pct']*100:+.2f}% | {t['exit_reason']}")

if __name__ == "__main__":
    test_strategy()
    print("\nReady for backtest engine integration.")