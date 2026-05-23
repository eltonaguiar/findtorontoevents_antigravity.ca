"""
Crypto Regime Fusion Breakout Persistence - Baby Strat

This variant keeps the robust NR/inside-bar expansion structure
and tunes reward/risk for better live sweep risk-adjusted returns.
Reference style: Linda Raschke trend-persistence filtering.
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


class CryptoRegimeFusionBreakoutPersistenceStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.nr_window = self.params.get("nr_window", 7)
        self.ema_fast = self.params.get("ema_fast", 10)
        self.ema_slow = self.params.get("ema_slow", 30)
        self.atr_period = self.params.get("atr_period", 14)
        self.vol_period = self.params.get("vol_period", 25)
        self.vol_multiplier = self.params.get("vol_multiplier", 1.3)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.1)
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
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()
        vol_ma = volume.rolling(self.vol_period, min_periods=1).mean()

        px = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0 or len(data) < self.nr_window + 4:
            return []

        rng = high - low
        nr_prev = float(rng.iloc[-2]) <= float(rng.iloc[-self.nr_window - 2 : -1].min())
        mother_high = float(high.iloc[-3])
        mother_low = float(low.iloc[-3])
        inside_prev = float(high.iloc[-2]) <= mother_high and float(low.iloc[-2]) >= mother_low
        vol_ok = float(volume.iloc[-1]) > float(vol_ma.iloc[-1]) * self.vol_multiplier

        if not nr_prev or not inside_prev or not vol_ok:
            return []

        signals: List[Signal] = []
        if (
            px > mother_high
            and float(ema_f.iloc[-1]) > float(ema_s.iloc[-1])
            and float(close.iloc[-1]) > float(open_.iloc[-1])
        ):
            conf = min(0.95, 0.56 + min(0.3, (float(volume.iloc[-1]) / (float(vol_ma.iloc[-1]) + 1e-12) - 1.0) / 2.0))
            signals.append(self._mk(symbol, "BUY", px, atr_now, conf, "NR/inside-bar trend expansion upward"))
        elif (
            px < mother_low
            and float(ema_f.iloc[-1]) < float(ema_s.iloc[-1])
            and float(close.iloc[-1]) < float(open_.iloc[-1])
        ):
            conf = min(0.95, 0.56 + min(0.3, (float(volume.iloc[-1]) / (float(vol_ma.iloc[-1]) + 1e-12) - 1.0) / 2.0))
            signals.append(self._mk(symbol, "SELL", px, atr_now, conf, "NR/inside-bar trend expansion downward"))
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
    np.random.seed(16)
    n = 320
    r = np.random.normal(0.0003, 0.019, n)
    p = 1200 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.011, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.011, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.55, n),
        }
    )
    s = CryptoRegimeFusionBreakoutPersistenceStrategy()
    print(len(s.generate_signals(df)))
