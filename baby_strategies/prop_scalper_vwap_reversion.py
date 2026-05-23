"""
PropScalperVWAPReversion - Prop Firm Style Baby Strat
=====================================================

Mean reversion to VWAP with volume confirmation.
Prop firm optimized: revert-to-VWAP on deviation, high frequency, tight risk.

Logic:
1. VWAP deviation > 1.0 std (z-score)
2. Reversion entry: BUY if below VWAP (oversold), SELL if above (overbought)
3. Volume > 1.5x SMA20 (conviction)
4. RSI extreme filter: RSI<30 buy, >70 sell
5. TP: 0.4 ATR to VWAP or fixed, SL: 0.4 ATR
6. Max hold: 8 bars (~2h)

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


NAME = "prop_scalper_vwap_reversion"
DESCRIPTION = "VWAP z-score reversion + volume spike + RSI extreme (tight 0.4:0.4 R:R)"
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]


def _vwap(typical_price, volume):
    """VWAP cumulative."""
    vwap = np.cumsum(typical_price * volume) / np.cumsum(volume)
    return vwap


def _vwap_zscore(close, volume, period=20):
    """Rolling VWAP z-score."""
    tp = (2*close + np.roll(high,1) + np.roll(low,1)) / 4  # Approx typical
    vwap_roll = pd.Series(_vwap(tp, volume)).rolling(period).mean()
    std_roll = pd.Series(close).rolling(period).std()
    zscore = (close - vwap_roll) / std_roll
    return zscore.fillna(0).values


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


def _atr(high, low, close, period=14):
    tr = np.maximum(high-low, np.maximum(np.abs(high - np.roll(close,1)), np.abs(low - np.roll(close,1))))
    atr = np.zeros_like(tr)
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1]*(period-1) + tr[i])/period
    return atr


def _sma(series, period):
    return pd.Series(series).rolling(period).mean().values


def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    if len(data) < 50:
        return []

    h, l, c, v = data['high'], data['low'], data['close'], data['volume']
    h, l, c, v = map(np.array, [h, l, c, v])

    zscore = _vwap_zscore(c, v)
    rsi = _rsi(c)
    vol_sma = _sma(v, 20)
    atr = _atr(h, l, c)

    i = len(c) - 1
    if np.isnan(atr[i]) or np.isnan(rsi[i]):
        return []

    price = c[i]
    atr_val = atr[i]
    tp_dist = 0.4 * atr_val
    sl_dist = 0.4 * atr_val

    signals = []

    # Buy reversion: oversold below VWAP
    if zscore[i] < -1.0 and rsi[i] < 30 and v[i] > 1.5 * vol_sma[i]:
        conf = min(0.85, 0.6 + abs(zscore[i]-1.0)*0.25)
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=price + tp_dist, stop_loss=price - sl_dist,
            reason=f"VWAP zscore={zscore[i]:.2f} oversold | RSI={rsi[i]:.0f} Vol1.5x | ATR={atr_val:.4f}"
        ))

    # Sell reversion: overbought above VWAP
    if zscore[i] > 1.0 and rsi[i] > 70 and v[i] > 1.5 * vol_sma[i]:
        conf = min(0.85, 0.6 + (zscore[i]-1.0)*0.25)
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=price - tp_dist, stop_loss=price + sl_dist,
            reason=f"VWAP zscore={zscore[i]:.2f} overbought | RSI={rsi[i]:.0f} Vol1.5x | ATR={atr_val:.4f}"
        ))

    return signals


if __name__ == "__main__":
    print(f"Strategy: {NAME}")
    print(f"Description: {DESCRIPTION}")
    print(f"Symbols: {SYMBOLS}")
