"""
VWAP Deviation Reversion Volume Filter XRP - Baby Strat
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class VWAPDeviationReversionXRPStrategy:
    TARGET_PAIR = "XRP/USDT"
    TARGET_SYMBOL = "XRPUSDT"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vwap_window = self.params.get("vwap_window", 48)
        self.z_window = self.params.get("z_window", 48)
        self.z_entry = self.params.get("z_entry", 2.0)
        self.vol_window = self.params.get("vol_window", 24)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.2)
        self.atr_period = self.params.get("atr_period", 14)
        self.min_bars = 100

    def generate_signals(self, data: pd.DataFrame, symbol: str = "XRPUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []
        close, high, low, volume = data["close"], data["high"], data["low"], data["volume"]
        typical = (high + low + close) / 3.0
        rvwap = (typical * volume).rolling(self.vwap_window).sum() / (volume.rolling(self.vwap_window).sum() + 1e-12)
        dev = close - rvwap
        z = (dev - dev.rolling(self.z_window).mean()) / (dev.rolling(self.z_window).std() + 1e-12)
        atr = self._atr(data, self.atr_period)
        vol_ma = volume.rolling(self.vol_window).mean()
        edge = max(0.0, abs(z.iloc[-1]) - self.z_entry)
        px = close.iloc[-1]
        a = atr.iloc[-1]
        signals: List[Signal] = []
        if z.iloc[-1] < -self.z_entry and volume.iloc[-1] > vol_ma.iloc[-1]:
            conf = min(0.95, max(0.1, 0.45 + edge * 0.2))
            signals.append(self._mk(symbol, "BUY", px, a, conf, "VWAP oversold reversion"))
        elif z.iloc[-1] > self.z_entry and volume.iloc[-1] > vol_ma.iloc[-1]:
            conf = min(0.95, max(0.1, 0.45 + edge * 0.2))
            signals.append(self._mk(symbol, "SELL", px, a, conf, "VWAP overbought reversion"))
        return signals

    def _mk(self, s: str, d: str, px: float, a: float, conf: float, reason: str) -> Signal:
        tp = px + self.tp_atr_mult * a if d == "BUY" else px - self.tp_atr_mult * a
        sl = px - self.sl_atr_mult * a if d == "BUY" else px + self.sl_atr_mult * a
        return Signal(s, d, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    def _atr(self, data: pd.DataFrame, p: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(p, min_periods=1).mean()
