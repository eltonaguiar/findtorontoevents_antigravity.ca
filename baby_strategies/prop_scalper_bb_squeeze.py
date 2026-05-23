"""
PropScalperBBSqueeze - Prop Firm Style Baby Strat
=================================================

High-frequency scalper using Bollinger Band squeeze breakout with RSI momentum filter.
Designed for prop firm challenges: high trade count, ~48% WR, tight risk (0.5:0.5 R:R), low DD.

Logic:
1. BB Squeeze: BB width < threshold (low vol contraction)
2. Breakout: close > upper BB (bull) or < lower BB (bear)
3. RSI filter: RSI(14) >50 for bull, <50 for bear (momentum alignment)
4. Volume confirmation: volume > SMA(volume,20)
5. Entry on close of breakout bar
6. TP: 0.5 ATR(14), SL: 0.5 ATR(14) - symmetric tight risk
7. Max hold: 4 bars (1h on 15m)

Symbols: High liq crypto majors
"""

from dataclasses import dataclass
from typing import List
import math

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


NAME = "prop_scalper_bb_squeeze"
DESCRIPTION = "BB squeeze breakout + RSI momentum + volume confirmation (tight 0.5:0.5 R:R)"
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]


def _sma(series, period):
    """Simple moving average."""
    return pd.Series(series).rolling(period).mean().values


def _bb_squeeze(high, low, close, period=20, std=2.0, squeeze_threshold=0.015):
    """Detect BB squeeze: low bandwidth."""
    bb_basis = _sma(close, period)
    dev = std * np.sqrt(pd.Series(close).rolling(period).var().fillna(0).values)
    upper = bb_basis + dev
    lower = bb_basis - dev
    width = (upper - lower) / bb_basis
    squeeze = width < squeeze_threshold
    return upper, lower, squeeze


def _rsi(close, period=14):
    """RSI as numpy array."""
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.zeros_like(close)
    avg_loss = np.zeros_like(close)
    avg_gain[period] = np.mean(gain[:period])
    avg_loss[period] = np.mean(loss[:period])
    for i in range(period+1, len(close)):
        avg_gain[i] = (avg_gain[i-1] * (period-1) + gain[i-1]) / period
        avg_loss[i] = (avg_loss[i-1] * (period-1) + loss[i-1]) / period
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - 100 / (1 + rs)
    rsi[:period] = 50  # Neutral start
    return rsi


def _atr(high, low, close, period=14):
    """ATR."""
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = np.zeros_like(tr)
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr


def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    if len(data) < 50:
        return []

    o, h, l, c, v = data['open'], data['high'], data['low'], data['close'], data['volume']
    o, h, l, c, v = map(np.array, [o, h, l, c, v])

    # Indicators
    upper_bb, lower_bb, squeeze = _bb_squeeze(h, l, c)
    rsi = _rsi(c)
    vol_sma = _sma(v, 20)
    atr = _atr(h, l, c)

    i = len(c) - 1
    if np.isnan(atr[i]) or np.isnan(rsi[i]):
        return []

    price = c[i]
    atr_val = atr[i]

    tp_dist = 0.5 * atr_val
    sl_dist = 0.5 * atr_val

    signals = []

    # Bull breakout
    if squeeze[i-1] and c[i] > upper_bb[i] and rsi[i] > 50 and v[i] > vol_sma[i]:
        conf = min(0.8, 0.5 + (rsi[i] - 50)/50 * 0.3)
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=price + tp_dist, stop_loss=price - sl_dist,
            reason=f"BB squeeze breakout bull | RSI={rsi[i]:.0f} Vol+ | ATR={atr_val:.4f}"
        ))

    # Bear breakout
    if squeeze[i-1] and c[i] < lower_bb[i] and rsi[i] < 50 and v[i] > vol_sma[i]:
        conf = min(0.8, 0.5 + (50 - rsi[i])/50 * 0.3)
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=price - tp_dist, stop_loss=price + sl_dist,
            reason=f"BB squeeze breakout bear | RSI={rsi[i]:.0f} Vol+ | ATR={atr_val:.4f}"
        ))

    return signals


if __name__ == "__main__":
    print(f"Strategy: {NAME}")
    print(f"Description: {DESCRIPTION}")
    print(f"Symbols: {SYMBOLS}")
