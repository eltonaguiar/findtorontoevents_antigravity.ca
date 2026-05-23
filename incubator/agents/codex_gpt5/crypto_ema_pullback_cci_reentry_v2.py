"""
Crypto EMA Pullback CCI Re-entry - Baby Strat
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoEMAPullbackCCIReentryStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_pullback = self.params.get("ema_pullback", 20)
        self.ema_trend = self.params.get("ema_trend", 80)
        self.cci_period = self.params.get("cci_period", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.pullback_atr_tol = self.params.get("pullback_atr_tol", 0.7)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.2)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.2)
        self.min_bars = 140

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data["close"]
        high = data["high"]
        low = data["low"]
        ema_pb = close.ewm(span=self.ema_pullback, adjust=False).mean()
        ema_tr = close.ewm(span=self.ema_trend, adjust=False).mean()
        atr = self._atr(data, self.atr_period)
        cci = self._cci(data, self.cci_period)

        px = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        dist_to_pb = abs(float(close.iloc[-1]) - float(ema_pb.iloc[-1])) / (atr_now + 1e-12)
        near_pullback = dist_to_pb <= self.pullback_atr_tol

        cci_cross_up = float(cci.iloc[-2]) < -100 and float(cci.iloc[-1]) > -100
        cci_cross_down = float(cci.iloc[-2]) > 100 and float(cci.iloc[-1]) < 100

        signals: List[Signal] = []
        if float(ema_pb.iloc[-1]) > float(ema_tr.iloc[-1]) and near_pullback and cci_cross_up:
            conf = min(0.94, 0.54 + min(0.28, (self.pullback_atr_tol - dist_to_pb) / (self.pullback_atr_tol + 1e-12)))
            signals.append(self._mk(symbol, "BUY", px, atr_now, conf, "Uptrend pullback with CCI recovery"))
        elif float(ema_pb.iloc[-1]) < float(ema_tr.iloc[-1]) and near_pullback and cci_cross_down:
            conf = min(0.94, 0.54 + min(0.28, (self.pullback_atr_tol - dist_to_pb) / (self.pullback_atr_tol + 1e-12)))
            signals.append(self._mk(symbol, "SELL", px, atr_now, conf, "Downtrend pullback with CCI rejection"))
        return signals

    def _mk(self, symbol: str, side: str, px: float, atr: float, conf: float, reason: str) -> Signal:
        if side == "BUY":
            tp = px + self.tp_atr_mult * atr
            sl = px - self.sl_atr_mult * atr
        else:
            tp = px - self.tp_atr_mult * atr
            sl = px + self.sl_atr_mult * atr
        return Signal(symbol, side, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    @staticmethod
    def _cci(data: pd.DataFrame, period: int) -> pd.Series:
        tp = (data["high"] + data["low"] + data["close"]) / 3.0
        ma = tp.rolling(period, min_periods=1).mean()
        md = (tp - ma).abs().rolling(period, min_periods=1).mean()
        return (tp - ma) / (0.015 * md + 1e-12)


if __name__ == "__main__":
    np.random.seed(15)
    n = 320
    r = np.random.normal(0.0003, 0.018, n)
    p = 45000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.011, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.011, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.5, n),
        }
    )
    s = CryptoEMAPullbackCCIReentryStrategy()
    print(len(s.generate_signals(df)))
