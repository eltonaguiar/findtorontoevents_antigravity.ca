"""
Crypto Range Expansion Trend Thrust - Baby Strat

Design reference:
- Toby Crabel-style narrow-range expansion
- Donchian-style momentum continuation framing
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


class CryptoRangeExpansionTrendThrustStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.nr_window = self.params.get("nr_window", 6)
        self.ema_fast = self.params.get("ema_fast", 10)
        self.ema_slow = self.params.get("ema_slow", 24)
        self.atr_period = self.params.get("atr_period", 16)
        self.vol_period = self.params.get("vol_period", 25)
        self.vol_mult = self.params.get("vol_mult", 1.35)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.2)
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
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
        vol_ma = volume.rolling(self.vol_period, min_periods=1).mean()

        rng = high - low
        if len(rng) < self.nr_window + 4:
            return []

        nr_prev = float(rng.iloc[-2]) <= float(rng.iloc[-self.nr_window - 2 : -1].min())
        mother_high = float(high.iloc[-3])
        mother_low = float(low.iloc[-3])
        inside_prev = float(high.iloc[-2]) <= mother_high and float(low.iloc[-2]) >= mother_low
        vol_ratio = float(volume.iloc[-1]) / (float(vol_ma.iloc[-1]) + 1e-12)

        if not nr_prev or not inside_prev or vol_ratio < self.vol_mult:
            return []

        px = float(close.iloc[-1])
        is_bull = float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1])
        is_bear = float(ema_fast.iloc[-1]) < float(ema_slow.iloc[-1])

        if px > mother_high and is_bull and float(close.iloc[-1]) > float(open_.iloc[-1]):
            conf = min(0.95, 0.55 + min(0.28, (vol_ratio - self.vol_mult) / 1.8))
            return [self._mk(symbol, "BUY", px, atr_now, conf, "NR/inside-bar upside thrust with trend alignment")]

        if px < mother_low and is_bear and float(close.iloc[-1]) < float(open_.iloc[-1]):
            conf = min(0.95, 0.55 + min(0.28, (vol_ratio - self.vol_mult) / 1.8))
            return [self._mk(symbol, "SELL", px, atr_now, conf, "NR/inside-bar downside thrust with trend alignment")]

        return []

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
        high = data["high"]
        low = data["low"]
        close = data["close"]
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(21)
    n = 320
    returns = np.random.normal(0.00035, 0.02, n)
    prices = 16000 * np.exp(np.cumsum(returns))
    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.001, n)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.011, n))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.011, n))),
            "close": prices,
            "volume": np.random.lognormal(7, 0.6, n),
        }
    )
    s = CryptoRangeExpansionTrendThrustStrategy()
    print(len(s.generate_signals(df)))
