"""
Crypto Volatility Compression Trend Thrust - Baby Strat
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


class CryptoVolatilityCompressionTrendThrustStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get("ema_fast", 34)
        self.ema_slow = self.params.get("ema_slow", 89)
        self.atr_short = self.params.get("atr_short", 14)
        self.atr_long = self.params.get("atr_long", 60)
        self.breakout_lookback = self.params.get("breakout_lookback", 18)
        self.compression_threshold = self.params.get("compression_threshold", 0.90)
        self.vol_ma_period = self.params.get("vol_ma_period", 30)
        self.vol_mult = self.params.get("vol_mult", 1.05)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.4)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.4)
        self.min_bars = 140

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume = data["volume"]

        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
        atr_s = self._atr(data, self.atr_short)
        atr_l = self._atr(data, self.atr_long)
        vol_ma = volume.rolling(self.vol_ma_period, min_periods=1).mean()

        ratio = atr_s / (atr_l + 1e-12)
        ratio_now = float(ratio.iloc[-1])
        breakout_high = float(high.iloc[-self.breakout_lookback - 1 : -1].max())
        breakout_low = float(low.iloc[-self.breakout_lookback - 1 : -1].min())
        price = float(close.iloc[-1])
        atr_now = float(atr_s.iloc[-1])
        vol_ok = float(volume.iloc[-1]) > float(vol_ma.iloc[-1]) * self.vol_mult
        ratio_min_recent = float(ratio.iloc[-6:].min())
        compressed = ratio_now < self.compression_threshold or ratio_min_recent < self.compression_threshold

        if atr_now <= 0 or not compressed or not vol_ok:
            return []

        conf_boost = max(0.0, (self.compression_threshold - ratio_now) / self.compression_threshold)
        signals: List[Signal] = []

        if ema_fast.iloc[-1] > ema_slow.iloc[-1] and price > breakout_high:
            conf = min(0.95, 0.52 + 0.25 * conf_boost)
            signals.append(self._mk(symbol, "BUY", price, atr_now, conf, "Compression resolved into bullish thrust"))
        elif ema_fast.iloc[-1] < ema_slow.iloc[-1] and price < breakout_low:
            conf = min(0.95, 0.52 + 0.25 * conf_boost)
            signals.append(self._mk(symbol, "SELL", price, atr_now, conf, "Compression resolved into bearish thrust"))

        return signals

    def _mk(self, symbol: str, direction: str, px: float, atr: float, conf: float, reason: str) -> Signal:
        if direction == "BUY":
            tp = px + self.tp_atr_mult * atr
            sl = px - self.sl_atr_mult * atr
        else:
            tp = px - self.tp_atr_mult * atr
            sl = px + self.sl_atr_mult * atr
        return Signal(symbol, direction, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 320
    r = np.random.normal(0.0004, 0.018, n)
    p = 50000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.012, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.012, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.5, n),
        }
    )
    s = CryptoVolatilityCompressionTrendThrustStrategy()
    print(len(s.generate_signals(df, "BTCUSDT")))
