"""
PivotPointBounce - Baby Strat
===============================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Calculates classic floor trader pivot points (P, S1/S2/S3, R1/R2/R3) from daily OHLC
- Entry when price touches S2/S3 (buy) or R2/R3 (sell) with reversal candle confirmation
- Uses the fact that institutional algos place orders at pivot levels

Unique Value Proposition:
Pivot points are the most-watched levels by institutional and algorithmic traders.
When price reaches S2/R2+ and shows a reversal bar, the bounce probability is high.
No existing baby strat uses classic pivot point calculations.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class PivotPointBounceStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.pivot_lookback = self.params.get('pivot_lookback', 24)  # bars for "daily" pivot
        self.reversal_body_ratio = self.params.get('reversal_body_ratio', 0.4)
        self.proximity_pct = self.params.get('proximity_pct', 0.003)  # 0.3% of price
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = self.pivot_lookback + self.atr_period + 5
        if len(data) < min_bars:
            return []

        # Calculate pivots from prior "session" (lookback window)
        session = data.iloc[-(self.pivot_lookback + 1):-1]
        session_high = session['high'].max()
        session_low = session['low'].min()
        session_close = session['close'].iloc[-1]

        pivot = (session_high + session_low + session_close) / 3
        r1 = 2 * pivot - session_low
        s1 = 2 * pivot - session_high
        r2 = pivot + (session_high - session_low)
        s2 = pivot - (session_high - session_low)
        r3 = session_high + 2 * (pivot - session_low)
        s3 = session_low - 2 * (session_high - pivot)

        current = data.iloc[-1]
        prev = data.iloc[-2]
        current_price = current['close']
        atr = self._atr(data, self.atr_period)
        current_atr = atr.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            return []

        # Reversal candle: body < reversal_body_ratio of total range, with wick
        body = abs(current['close'] - current['open'])
        total_range = current['high'] - current['low']
        is_reversal = total_range > 0 and (body / total_range) < self.reversal_body_ratio

        signals = []
        prox = current_price * self.proximity_pct

        # Bullish: price near S2 or S3 with bullish reversal
        for level, name in [(s2, "S2"), (s3, "S3")]:
            if abs(current['low'] - level) < prox and current['close'] > current['open'] and is_reversal:
                confidence = 0.7 if name == "S2" else 0.8
                tp = current_price + current_atr * self.tp_atr_mult
                sl = level - current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=confidence,
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Pivot {name} bounce at {level:.2f}, reversal candle"
                ))
                break

        # Bearish: price near R2 or R3 with bearish reversal
        for level, name in [(r2, "R2"), (r3, "R3")]:
            if abs(current['high'] - level) < prox and current['close'] < current['open'] and is_reversal:
                confidence = 0.7 if name == "R2" else 0.8
                tp = current_price - current_atr * self.tp_atr_mult
                sl = level + current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=confidence,
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Pivot {name} rejection at {level:.2f}, reversal candle"
                ))
                break

        return signals

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
