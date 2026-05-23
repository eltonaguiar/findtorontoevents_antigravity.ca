"""
Crypto Efficiency Ratio Channel Break - Baby Strat
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


class CryptoEfficiencyRatioChannelBreakStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.er_period = self.params.get("er_period", 20)
        self.er_threshold = self.params.get("er_threshold", 0.55)
        self.channel_period = self.params.get("channel_period", 30)
        self.vol_period = self.params.get("vol_period", 30)
        self.ema_fast = self.params.get("ema_fast", 21)
        self.ema_slow = self.params.get("ema_slow", 55)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.3)
        self.min_bars = 150

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume = data["volume"]
        atr = self._atr(data, self.atr_period)
        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()

        direction = (close - close.shift(self.er_period)).abs()
        volatility = close.diff().abs().rolling(self.er_period, min_periods=1).sum()
        er = direction / (volatility + 1e-12)

        ch_high = high.rolling(self.channel_period, min_periods=1).max().shift(1)
        ch_low = low.rolling(self.channel_period, min_periods=1).min().shift(1)
        vol_ma = volume.rolling(self.vol_period, min_periods=1).mean()

        px = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        er_now = float(er.iloc[-1])
        if atr_now <= 0 or er_now < self.er_threshold:
            return []

        vol_ok = float(volume.iloc[-1]) > float(vol_ma.iloc[-1]) * 1.1
        if not vol_ok:
            return []

        signals: List[Signal] = []
        if px > float(ch_high.iloc[-1]) and float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1]):
            conf = min(0.95, 0.54 + min(0.28, (er_now - self.er_threshold)))
            signals.append(self._mk(symbol, "BUY", px, atr_now, conf, "High-efficiency directional break upward"))
        elif px < float(ch_low.iloc[-1]) and float(ema_fast.iloc[-1]) < float(ema_slow.iloc[-1]):
            conf = min(0.95, 0.54 + min(0.28, (er_now - self.er_threshold)))
            signals.append(self._mk(symbol, "SELL", px, atr_now, conf, "High-efficiency directional break downward"))
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
    np.random.seed(3)
    n = 320
    r = np.random.normal(0.0003, 0.018, n)
    p = 8000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.011, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.011, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.55, n),
        }
    )
    s = CryptoEfficiencyRatioChannelBreakStrategy()
    print(len(s.generate_signals(df)))
