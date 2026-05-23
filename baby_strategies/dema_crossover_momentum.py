"""
DEMACrossoverMomentum - Baby Strat
=====================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Uses Double EMA (DEMA) crossover which has ~2x less lag than regular EMA
- Fast DEMA crosses slow DEMA with momentum confirmation (ROC filter)
- Only enters when ROC confirms trend strength (avoids weak crossovers)

Unique Value Proposition:
DEMA was invented by Patrick Mulloy (1994) specifically to reduce lag in trend signals.
It responds faster than EMA, KAMA, or TEMA while staying smooth. The ROC filter
eliminates the weak crossovers that plague standard MA strategies. No existing baby
strat uses DEMA.
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


class DEMACrossoverMomentumStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fast_period = self.params.get('fast_period', 8)
        self.slow_period = self.params.get('slow_period', 21)
        self.roc_period = self.params.get('roc_period', 10)
        self.roc_threshold = self.params.get('roc_threshold', 0.005)  # 0.5% min momentum
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.slow_period * 2, self.roc_period, self.atr_period) + 10
        if len(data) < min_bars:
            return []

        close = data['close']

        # DEMA = 2*EMA(n) - EMA(EMA(n))
        fast_dema = self._dema(close, self.fast_period)
        slow_dema = self._dema(close, self.slow_period)

        # Rate of Change
        roc = close.pct_change(self.roc_period)

        atr = self._atr(data, self.atr_period)
        current_price = close.iloc[-1]
        current_atr = atr.iloc[-1]

        fd_now = fast_dema.iloc[-1]
        fd_prev = fast_dema.iloc[-2]
        sd_now = slow_dema.iloc[-1]
        sd_prev = slow_dema.iloc[-2]
        roc_now = roc.iloc[-1]

        if any(np.isnan(v) for v in [current_atr, fd_now, fd_prev, sd_now, sd_prev, roc_now]):
            return []
        if current_atr <= 0:
            return []

        signals = []

        # Bullish crossover + positive ROC
        if fd_prev <= sd_prev and fd_now > sd_now and roc_now > self.roc_threshold:
            spread = (fd_now - sd_now) / current_atr
            confidence = min(0.6 + spread * 0.2 + roc_now * 5, 0.95)
            tp = current_price + current_atr * self.tp_atr_mult
            sl = current_price - current_atr * self.sl_atr_mult
            signals.append(Signal(
                symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"DEMA bullish cross, ROC={roc_now:.3f}"
            ))

        # Bearish crossover + negative ROC
        elif fd_prev >= sd_prev and fd_now < sd_now and roc_now < -self.roc_threshold:
            spread = (sd_now - fd_now) / current_atr
            confidence = min(0.6 + spread * 0.2 + abs(roc_now) * 5, 0.95)
            tp = current_price - current_atr * self.tp_atr_mult
            sl = current_price + current_atr * self.sl_atr_mult
            signals.append(Signal(
                symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"DEMA bearish cross, ROC={roc_now:.3f}"
            ))

        return signals

    def _dema(self, series: pd.Series, period: int) -> pd.Series:
        ema1 = series.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        return 2 * ema1 - ema2

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
