"""
Crypto NR+ER Volume Regime Breakout Outperform - Baby Strat
============================================================

Reference mindset:
- Toby Crabel NR pattern (narrow-range expansion)
- Perry Kaufman efficiency ratio (trend quality filter)
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


class CryptoNREfficiencyRegimeBreakoutOutperformStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.nr_window = self.params.get("nr_window", 7)
        self.er_period = self.params.get("er_period", 20)
        self.er_threshold = self.params.get("er_threshold", 0.25)
        self.ema_fast = self.params.get("ema_fast", 10)
        self.ema_slow = self.params.get("ema_slow", 30)
        self.vol_period = self.params.get("vol_period", 25)
        self.vol_multiplier = self.params.get("vol_multiplier", 1.3)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.6)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.0)
        self.min_bars = max(self.nr_window + 4, self.er_period + 30, self.atr_period + 10, 120)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        open_ = data["open"]
        high = data["high"]
        low = data["low"]
        close = data["close"]
        volume = data["volume"]

        atr = self._atr(data, self.atr_period)
        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
        vol_ma = volume.rolling(self.vol_period, min_periods=1).mean()

        # Kaufman Efficiency Ratio (trend quality: directional move / path length)
        direction = (close - close.shift(self.er_period)).abs()
        volatility = close.diff().abs().rolling(self.er_period, min_periods=1).sum()
        er = direction / (volatility + 1e-12)

        price = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        candle_range = high - low
        nr_prev = float(candle_range.iloc[-2]) <= float(candle_range.iloc[-self.nr_window - 2 : -1].min())
        mother_high = float(high.iloc[-3])
        mother_low = float(low.iloc[-3])
        inside_prev = float(high.iloc[-2]) <= mother_high and float(low.iloc[-2]) >= mother_low
        vol_ratio = float(volume.iloc[-1]) / (float(vol_ma.iloc[-1]) + 1e-12)
        vol_ok = vol_ratio >= self.vol_multiplier
        er_now = float(er.iloc[-1])
        er_ok = er_now >= self.er_threshold
        bull_trend = float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1])
        bear_trend = float(ema_fast.iloc[-1]) < float(ema_slow.iloc[-1])

        if not (nr_prev and inside_prev and vol_ok and er_ok):
            return []

        signals: List[Signal] = []
        if price > mother_high and bull_trend and float(close.iloc[-1]) > float(open_.iloc[-1]):
            conf = min(0.95, 0.58 + min(0.2, (vol_ratio - self.vol_multiplier) * 0.12) + min(0.12, (er_now - self.er_threshold) * 0.25))
            signals.append(self._mk(symbol, "BUY", price, atr_now, conf, "NR/inside breakout + ER trend quality + volume confirmation"))
        elif price < mother_low and bear_trend and float(close.iloc[-1]) < float(open_.iloc[-1]):
            conf = min(0.95, 0.58 + min(0.2, (vol_ratio - self.vol_multiplier) * 0.12) + min(0.12, (er_now - self.er_threshold) * 0.25))
            signals.append(self._mk(symbol, "SELL", price, atr_now, conf, "NR/inside breakdown + ER trend quality + volume confirmation"))
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
    np.random.seed(77)
    n = 320
    r = np.random.normal(0.0004, 0.02, n)
    p = 15000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.0012, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.011, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.011, n))),
            "close": p,
            "volume": np.random.lognormal(7.0, 0.6, n),
        }
    )
    strat = CryptoNREfficiencyRegimeBreakoutOutperformStrategy()
    print(len(strat.generate_signals(df)))
