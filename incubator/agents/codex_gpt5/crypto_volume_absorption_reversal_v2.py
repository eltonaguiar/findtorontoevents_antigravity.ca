"""
Crypto Volume Absorption Reversal - Baby Strat
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


class CryptoVolumeAbsorptionReversalStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vol_period = self.params.get("vol_period", 30)
        self.move_lookback = self.params.get("move_lookback", 6)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 1.9)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.0)
        self.min_bars = 120

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        open_ = data["open"]
        high = data["high"]
        low = data["low"]
        close = data["close"]
        volume = data["volume"]
        atr = self._atr(data, self.atr_period)
        vol_ma = volume.rolling(self.vol_period, min_periods=1).mean()

        px = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        body = (close - open_).abs() + 1e-12
        lower_wick = (pd.concat([open_, close], axis=1).min(axis=1) - low).clip(lower=0.0)
        upper_wick = (high - pd.concat([open_, close], axis=1).max(axis=1)).clip(lower=0.0)
        close_pos = (close - low) / (high - low + 1e-12)
        recent_ret = close.pct_change(self.move_lookback).fillna(0.0)

        vol_spike = float(volume.iloc[-1]) > float(vol_ma.iloc[-1]) * 1.5
        if not vol_spike:
            return []

        bullish_absorption = (
            float(lower_wick.iloc[-1] / body.iloc[-1]) > 1.8
            and float(close_pos.iloc[-1]) > 0.65
            and float(recent_ret.iloc[-1]) < -0.02
        )
        bearish_absorption = (
            float(upper_wick.iloc[-1] / body.iloc[-1]) > 1.8
            and float(close_pos.iloc[-1]) < 0.35
            and float(recent_ret.iloc[-1]) > 0.02
        )

        signals: List[Signal] = []
        if bullish_absorption:
            conf = min(0.93, 0.56 + min(0.25, float(lower_wick.iloc[-1] / body.iloc[-1]) / 6.0))
            signals.append(self._mk(symbol, "BUY", px, atr_now, conf, "High-volume lower-wick absorption"))
        elif bearish_absorption:
            conf = min(0.93, 0.56 + min(0.25, float(upper_wick.iloc[-1] / body.iloc[-1]) / 6.0))
            signals.append(self._mk(symbol, "SELL", px, atr_now, conf, "High-volume upper-wick absorption"))
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


if __name__ == "__main__":
    np.random.seed(13)
    n = 320
    r = np.random.normal(0.0002, 0.021, n)
    p = 10000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.01, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.01, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.7, n),
        }
    )
    s = CryptoVolumeAbsorptionReversalStrategy()
    print(len(s.generate_signals(df)))
