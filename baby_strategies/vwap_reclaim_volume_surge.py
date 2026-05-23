"""
VWAPReclaimVolumeSurge - Baby Strat
======================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Tracks session VWAP (rolling) as institutional fair value
- Entry when price reclaims VWAP from below/above on a volume surge
- The "reclaim" is the key — not just touching VWAP, but crossing back through it
  after being displaced, which signals institutional re-engagement

Unique Value Proposition:
Existing VWAP strat trades deviation FROM VWAP. This trades the RECLAIM — when price
returns TO VWAP on heavy volume. This is the opposite trade: deviation strat is mean
reversion, reclaim strat is momentum confirmation. Institutions use VWAP as their
benchmark; when price reclaims it on volume, they're re-entering.
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


class VWAPReclaimVolumeSurgeStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vwap_period = self.params.get('vwap_period', 24)  # 24 hours = session
        self.displacement_bars = self.params.get('displacement_bars', 5)
        self.displacement_pct = self.params.get('displacement_pct', 0.005)  # 0.5% away from VWAP
        self.volume_surge_mult = self.params.get('volume_surge_mult', 1.5)
        self.volume_period = self.params.get('volume_period', 20)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.vwap_period, self.volume_period, self.atr_period) + self.displacement_bars + 10
        if len(data) < min_bars:
            return []

        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']

        # Rolling VWAP
        typical_price = (high + low + close) / 3
        cum_tp_vol = (typical_price * volume).rolling(self.vwap_period).sum()
        cum_vol = volume.rolling(self.vwap_period).sum()
        vwap = cum_tp_vol / (cum_vol + 1e-10)

        vol_ma = volume.rolling(self.volume_period).mean()
        atr = self._atr(data, self.atr_period)

        current_price = close.iloc[-1]
        current_vwap = vwap.iloc[-1]
        current_atr = atr.iloc[-1]
        current_vol = volume.iloc[-1]
        current_vol_ma = vol_ma.iloc[-1]

        if any(np.isnan(v) for v in [current_atr, current_vwap, current_vol_ma]):
            return []
        if current_atr <= 0:
            return []

        signals = []

        # Check displacement: was price below VWAP for N bars, now crossing above?
        recent_below = close.iloc[-(self.displacement_bars+1):-1]
        recent_vwap = vwap.iloc[-(self.displacement_bars+1):-1]

        was_below = (recent_below < recent_vwap * (1 - self.displacement_pct)).any()
        was_above = (recent_below > recent_vwap * (1 + self.displacement_pct)).any()

        vol_surge = current_vol > current_vol_ma * self.volume_surge_mult

        # Bullish reclaim: was below VWAP, now crossing above on volume
        if was_below and current_price > current_vwap and close.iloc[-2] < vwap.iloc[-2] and vol_surge:
            pct_above = (current_price - current_vwap) / current_vwap
            confidence = min(0.6 + pct_above * 10 + (current_vol / current_vol_ma - 1) * 0.1, 0.95)
            tp = current_price + current_atr * self.tp_atr_mult
            sl = current_vwap - current_atr * self.sl_atr_mult * 0.5  # SL below VWAP
            signals.append(Signal(
                symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"VWAP reclaim from below on {current_vol/current_vol_ma:.1f}x volume"
            ))

        # Bearish reclaim: was above VWAP, now crossing below on volume
        elif was_above and current_price < current_vwap and close.iloc[-2] > vwap.iloc[-2] and vol_surge:
            pct_below = (current_vwap - current_price) / current_vwap
            confidence = min(0.6 + pct_below * 10 + (current_vol / current_vol_ma - 1) * 0.1, 0.95)
            tp = current_price - current_atr * self.tp_atr_mult
            sl = current_vwap + current_atr * self.sl_atr_mult * 0.5
            signals.append(Signal(
                symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"VWAP lost from above on {current_vol/current_vol_ma:.1f}x volume"
            ))

        return signals

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
