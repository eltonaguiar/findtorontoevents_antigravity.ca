from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Assume indicators imported or define simple ones
def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def hma_slope(close: pd.Series, period: int = 21) -> pd.Series:
    half = period // 2
    sqrt_n = int(np.sqrt(period))
    wma1 = close.ewm(span=half).mean() * 2
    wma2 = close.ewm(span=period).mean()
    hma = (wma1 - wma2).ewm(span=sqrt_n).mean()
    return np.sign(hma.diff().fillna(0))

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = np.abs(high - close.shift())
    tr3 = np.abs(low - close.shift())
    tr = np.max([tr1, tr2, tr3], axis=0)
    return pd.Series(tr).rolling(period).mean()

def volume_confirm(volume: pd.Series) -> bool:
    return volume.iloc[-1] > volume.tail(20).mean() * 1.2

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _atr_tp_sl(df, tp_mult=2.5, sl_mult=1.5):
    atr_val = atr(df['High'], df['Low'], df['Close']).iloc[-1]
    price = df['Close'].iloc[-1]
    tp_long = price + tp_mult * atr_val
    sl_long = price - sl_mult * atr_val
    return price, tp_long, sl_long

def connors_rsi2_prop(data: Dict[str, pd.DataFrame]) -> List[Dict]:
    '''Prop-firm: Connors RSI(2) + HMA filter + vol confirm. High WR mean-rev.'''
    signals = []
    for symbol, df in data.items():
        if len(df) < 50: continue
        r2 = rsi(df['Close'], 2)
        hs = hma_slope(df['Close'])
        vol_ok = volume_confirm(df['Volume'])
        if pd.isna(r2.iloc[-1]) or pd.isna(hs.iloc[-1]): continue
        entry, tp_long, sl_long = _atr_tp_sl(df)
        if r2.iloc[-1] < 10 and hs.iloc[-1] > 0 and vol_ok:
            signals.append({
                'strategy': 'connors_rsi2_prop',
                'symbol': symbol,
                'signal_type': 'LONG',
                'entry_price': entry,
                'take_profit': tp_long,
                'stop_loss': sl_long,
                'confidence': 0.82,
                'risk_reward': tp_mult / sl_mult,
                'reason': f'RSI2={r2.iloc[-1]:.1f} oversold + HMA up + vol on {symbol}',
                'timestamp': _now_iso()
            })
        elif r2.iloc[-1] > 90 and hs.iloc[-1] < 0 and vol_ok:
            entry, _, _ = _atr_tp_sl(df)
            atr_val = atr(df['High'], df['Low'], df['Close']).iloc[-1]
            tp = entry - 2.5 * atr_val
            sl = entry + 1.5 * atr_val
            signals.append({
                'strategy': 'connors_rsi2_prop',
                'symbol': symbol,
                'signal_type': 'SHORT',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.82,
                'risk_reward': 1.67,
                'reason': f'RSI2={r2.iloc[-1]:.1f} overbought + HMA down + vol on {symbol}',
                'timestamp': _now_iso()
            })
    return signals

def keltner_hma_prop(data: Dict[str, pd.DataFrame]) -> List[Dict]:
    '''Prop-firm: Keltner mean-rev + HMA + vol. Builds on top forward performer.'''
    # Implement similar to variation, but tighter params for prop
    # Placeholder - full impl
    return []

def williams_pr_prop(data: Dict[str, pd.DataFrame]) -> List[Dict]:
    '''Prop-firm: Williams %R extreme + low ADX regime + vol.'''
    # To implement
    return []

# General strategies placeholder
def funding_momentum_general(data: Dict[str, pd.DataFrame]) -> List[Dict]:
    '''General: Funding momentum + RSI gate.'''
    return []
