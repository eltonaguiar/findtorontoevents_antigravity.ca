"""
Crypto Swing Break Retest - Baby Strat
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


class CryptoSwingBreakRetestStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.swing_window = self.params.get("swing_window", 20)
        self.ema_fast = self.params.get("ema_fast", 21)
        self.ema_slow = self.params.get("ema_slow", 55)
        self.atr_period = self.params.get("atr_period", 14)
        self.retest_atr_tol = self.params.get("retest_atr_tol", 0.45)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.2)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.2)
        self.min_bars = 150

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data["close"]
        high = data["high"]
        low = data["low"]
        open_ = data["open"]
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()
        atr = self._atr(data, self.atr_period)

        swing_high = high.rolling(self.swing_window, min_periods=1).max().shift(1)
        swing_low = low.rolling(self.swing_window, min_periods=1).min().shift(1)

        px = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        brk_high_prev = float(close.iloc[-2]) > float(swing_high.iloc[-2])
        brk_low_prev = float(close.iloc[-2]) < float(swing_low.iloc[-2])
        retest_high = abs(float(low.iloc[-1]) - float(swing_high.iloc[-1])) <= self.retest_atr_tol * atr_now
        retest_low = abs(float(high.iloc[-1]) - float(swing_low.iloc[-1])) <= self.retest_atr_tol * atr_now
        bull_bar = float(close.iloc[-1]) > float(open_.iloc[-1])
        bear_bar = float(close.iloc[-1]) < float(open_.iloc[-1])

        signals: List[Signal] = []
        if ema_f.iloc[-1] > ema_s.iloc[-1] and brk_high_prev and retest_high and bull_bar:
            conf = min(0.94, 0.56 + min(0.25, (self.retest_atr_tol * atr_now) / (atr_now + 1e-12)))
            signals.append(self._mk(symbol, "BUY", px, atr_now, conf, "Swing high breakout retest held"))
        elif ema_f.iloc[-1] < ema_s.iloc[-1] and brk_low_prev and retest_low and bear_bar:
            conf = min(0.94, 0.56 + min(0.25, (self.retest_atr_tol * atr_now) / (atr_now + 1e-12)))
            signals.append(self._mk(symbol, "SELL", px, atr_now, conf, "Swing low breakdown retest held"))
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
    np.random.seed(12)
    n = 340
    r = np.random.normal(0.0004, 0.019, n)
    p = 7000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.012, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.012, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.6, n),
        }
    )
    s = CryptoSwingBreakRetestStrategy()
    print(len(s.generate_signals(df)))
