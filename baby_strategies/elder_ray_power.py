"""
ElderRayPower - Baby Strat
============================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Implements Dr. Alexander Elder's "Elder Ray" indicator (Bull Power + Bear Power)
- Bull Power = High - EMA, Bear Power = Low - EMA
- Entry when both powers align: Bull Power rising from negative (buyers stepping in)
  or Bear Power falling from positive (sellers taking over)
- Trend filter: 13-period EMA slope must confirm direction

Unique Value Proposition:
Elder Ray isolates the battle between bulls and bears relative to the consensus (EMA).
It's one of the few indicators that separately measures buying and selling pressure.
Published in "Trading for a Living" — used by professional traders worldwide.
No existing baby strat implements Elder Ray.
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


class ElderRayPowerStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_period = self.params.get('ema_period', 13)
        self.power_lookback = self.params.get('power_lookback', 3)
        self.slope_period = self.params.get('slope_period', 5)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.ema_period, self.atr_period) + self.power_lookback + self.slope_period + 10
        if len(data) < min_bars:
            return []

        close = data['close']
        high = data['high']
        low = data['low']

        ema = close.ewm(span=self.ema_period).mean()

        # Elder Ray
        bull_power = high - ema  # Buyers' ability to push price above consensus
        bear_power = low - ema   # Sellers' ability to push price below consensus

        # EMA slope (trend direction)
        ema_slope = ema.diff(self.slope_period) / self.slope_period

        atr = self._atr(data, self.atr_period)
        current_price = close.iloc[-1]
        current_atr = atr.iloc[-1]

        bp_now = bull_power.iloc[-1]
        bp_prev = bull_power.iloc[-2]
        bear_now = bear_power.iloc[-1]
        bear_prev = bear_power.iloc[-2]
        slope_now = ema_slope.iloc[-1]

        if any(np.isnan(v) for v in [current_atr, bp_now, bp_prev, bear_now, bear_prev, slope_now]):
            return []
        if current_atr <= 0:
            return []

        signals = []

        # Bullish setup:
        # 1. EMA slope positive (uptrend)
        # 2. Bear power < 0 but rising (sellers losing grip)
        # 3. Bull power rising
        if slope_now > 0 and bear_now < 0 and bear_now > bear_prev and bp_now > bp_prev:
            # Check bear power was more negative recently (recovering)
            recent_bear = bear_power.iloc[-self.power_lookback-1:-1]
            if (recent_bear < bear_now).any():
                strength = abs(bear_now - recent_bear.min()) / current_atr
                confidence = min(0.55 + strength * 0.15, 0.95)
                tp = current_price + current_atr * self.tp_atr_mult
                sl = current_price - current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Elder Ray bullish: bear_power recovering ({bear_now:.2f}), slope positive"
                ))

        # Bearish setup:
        # 1. EMA slope negative (downtrend)
        # 2. Bull power > 0 but falling (buyers losing grip)
        # 3. Bear power falling
        elif slope_now < 0 and bp_now > 0 and bp_now < bp_prev and bear_now < bear_prev:
            recent_bull = bull_power.iloc[-self.power_lookback-1:-1]
            if (recent_bull > bp_now).any():
                strength = abs(recent_bull.max() - bp_now) / current_atr
                confidence = min(0.55 + strength * 0.15, 0.95)
                tp = current_price - current_atr * self.tp_atr_mult
                sl = current_price + current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Elder Ray bearish: bull_power fading ({bp_now:.2f}), slope negative"
                ))

        return signals

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
