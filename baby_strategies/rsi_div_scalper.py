"""
PropRSIDivScalper - Prop Firm Style Baby Strat
==============================================

RSI divergence scalper for high WR reversals.
Detects bullish/bearish divergence on 15m for quick scalps.

Logic:
1. Bull div: price makes lower low (LL), RSI makes higher low (HL) over last 5 bars
2. Bear div: price higher high (HH), RSI lower high (LH)
3. Confirmation: price near low/high of range, volume spike
4. TP: 0.7 ATR, SL: 0.5 ATR
5. Confidence based on div strength

"""

from dataclasses import dataclass
from typing import List
import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


NAME = "rsi_div_scalper"
DESCRIPTION = "RSI divergence reversal scalper + volume (0.7:0.5 R:R)"
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]


def _rsi(close, period=14):
    delta = np.diff(close)
    gain = np.maximum(delta, 0)
    loss = np.maximum(-delta, 0)
    avg_gain = np.zeros_like(close)
    avg_loss = np.zeros_like(close)
    avg_gain[period] = np.mean(gain[:period])
    avg_loss[period] = np.mean(loss[:period])
    for i in range(period+1, len(close)):
        avg_gain[i] = (avg_gain[i-1]*(period-1) + gain[i-1])/period
        avg_loss[i] = (avg_loss[i-1]*(period-1) + loss[i-1])/period
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - 100/(1+rs)
    rsi[:period] = 50
    return rsi


def _find_swing_lows(highs, lows, closes, lookback=5):
    """Simple swing low positions."""
    is_low = np.zeros_like(lows, dtype=bool)
    for i in range(lookback, len(lows)-lookback):
        if lows[i] == np.min(lows[i-lookback:i+lookback+1]):
            is_low[i] = True
    return np.where(is_low)[0]


def _atr(high, low, close, period=14):
    tr = np.maximum(high-low, np.abs(high - np.roll(close,1)), np.abs(low - np.roll(close,1)))
    atr = np.full_like(tr, np.nan)
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1]*(period-1) + tr[i])/period
    return atr


def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    if len(data) < 50:
        return []

    h, l, c, v = data['high'], data['low'], data['close'], data['volume']
    h, l, c, v = map(np.array, [h, l, c, v])

    rsi = _rsi(c)
    atr = _atr(h, l, c)
    vol_sma = pd.Series(v).rolling(20).mean().fillna(method='bfill').values

    i = len(c) - 1
    if np.isnan(atr[i]) or np.isnan(rsi[i]):
        return []

    price = c[i]
    atr_val = atr[i]
    tp_dist = 0.7 * atr_val
    sl_dist = 0.5 * atr_val

    signals = []

    lookback = 10
    price_lows = np.min(l[-lookback:])
    rsi_lows = np.min(rsi[-lookback:])
    price_highs = np.max(h[-lookback:])
    rsi_highs = np.max(rsi[-lookback:])

    # Bullish divergence: recent price near low, but RSI higher than previous low
    prev_price_low_idx = np.argmin(l[-lookback*2:-lookback])
    prev_rsi_low = np.min(rsi[-lookback*2:-lookback])
    if l[i] <= price_lows * 1.001 and rsi[i] > prev_rsi_low * 1.01 and v[i] > vol_sma[i] * 1.1:
        div_strength = (rsi[i] - prev_rsi_low) / prev_rsi_low
        conf = min(0.8, 0.5 + div_strength * 0.5)
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=price + tp_dist, stop_loss=price - sl_dist,
            reason=f"RSI bull div str={div_strength:.2f} | near LL Vol+ | ATR={atr_val:.4f}"
        ))

    # Bearish divergence
    prev_price_high_idx = np.argmax(h[-lookback*2:-lookback]) + lookback
    prev_rsi_high = np.max(rsi[-lookback*2:-lookback])
    if h[i] >= price_highs * 0.999 and rsi[i] < prev_rsi_high * 0.99 and v[i] > vol_sma[i] * 1.1:
        div_strength = (prev_rsi_high - rsi[i]) / prev_rsi_high
        conf = min(0.8, 0.5 + div_strength * 0.5)
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=price - tp_dist, stop_loss=price + sl_dist,
            reason=f"RSI bear div str={div_strength:.2f} | near HH Vol+ | ATR={atr_val:.4f}"
        ))

    return signals


if __name__ == "__main__":
    print(f"Strategy: {NAME}")
    print(f"Description: {DESCRIPTION}")
    print(f"Symbols: {SYMBOLS}")
