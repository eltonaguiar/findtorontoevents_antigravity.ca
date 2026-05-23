"""
PropScalperOrderflow - Prop Firm Style Baby Strat
=================================================

Order flow imbalance reversal scalper.
Detects rejection wicks (institutional order flow exhaustion), enters reversal.

Logic:
1. Imbalance: upper wick > 2x body (bear rejection), lower wick >2x body (bull rejection)
2. Volume > 1.2x SMA20
3. EMA filter: price above EMA9 for bull, below for bear
4. TP: 0.6 ATR, SL: 0.4 ATR (asymmetric reward)
5. Max hold: 6 bars

Prop optimized: high trades, controlled risk.
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


NAME = "prop_scalper_orderflow"
DESCRIPTION = "Order flow wick imbalance reversal + volume + EMA filter (0.6:0.4 R:R)"
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]


def _ema(series, period):
    k = 2 / (period + 1)
    ema = np.full_like(series, np.nan)
    ema[period-1] = np.mean(series[:period])
    for i in range(period, len(series)):
        ema[i] = series[i] * k + ema[i-1] * (1 - k)
    return ema


def _sma(series, period):
    return pd.Series(series).rolling(period).mean().fillna(method='bfill').values


def _atr(high, low, close, period=14):
    prev_close = np.roll(close, 1)
    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = np.full_like(tr, np.nan)
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period-1) + tr[i]) / period
    return atr


def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    if len(data) < 50:
        return []

    o, h, l, c, v = data['open'], data['high'], data['low'], data['close'], data['volume']
    o, h, l, c, v = map(np.array, [o, h, l, c, v])

    body = np.abs(c - o)
    upper_wick = h - np.maximum(o, c)
    lower_wick = np.minimum(o, c) - l

    ema9 = _ema(c, 9)
    vol_sma = _sma(v, 20)
    atr = _atr(h, l, c)

    i = len(c) - 1
    if np.isnan(atr[i]) or np.isnan(ema9[i]):
        return []

    price = c[i]
    atr_val = atr[i]
    tp_dist = 0.6 * atr_val
    sl_dist = 0.4 * atr_val

    signals = []

    # Bull reversal: large lower wick rejection
    if lower_wick[i] > 2 * body[i] and v[i] > 1.2 * vol_sma[i] and c[i] > ema9[i]:
        wick_ratio = lower_wick[i] / (body[i] + 1e-6)
        conf = min(0.82, 0.55 + (wick_ratio - 2)*0.1)
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=price + tp_dist, stop_loss=price - sl_dist,
            reason=f"Lower wick {wick_ratio:.1f}x body | Vol+ EMA+ | ATR={atr_val:.4f}"
        ))

    # Bear reversal: large upper wick rejection
    if upper_wick[i] > 2 * body[i] and v[i] > 1.2 * vol_sma[i] and c[i] < ema9[i]:
        wick_ratio = upper_wick[i] / (body[i] + 1e-6)
        conf = min(0.82, 0.55 + (wick_ratio - 2)*0.1)
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=price - tp_dist, stop_loss=price + sl_dist,
            reason=f"Upper wick {wick_ratio:.1f}x body | Vol+ EMA- | ATR={atr_val:.4f}"
        ))

    return signals


if __name__ == "__main__":
    print(f"Strategy: {NAME}")
    print(f"Description: {DESCRIPTION}")
    print(f"Symbols: {SYMBOLS}")
