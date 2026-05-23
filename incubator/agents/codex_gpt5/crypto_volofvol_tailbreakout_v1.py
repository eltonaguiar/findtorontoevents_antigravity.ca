"""
Crypto Vol-of-Vol Tail Breakout - Baby Strat
============================================

Created by: codex_gpt5
Date: 2026-02-26

Reference mindset:
- Brevan Howard-style volatility regime timing
- Convexity capture in volatility expansion tails
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


class CryptoVolOfVolTailBreakoutStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rvol_window = self.params.get("rvol_window", 20)
        self.vov_window = self.params.get("vov_window", 40)
        self.range_window = self.params.get("range_window", 25)
        self.vov_quantile = self.params.get("vov_quantile", 0.75)
        self.volume_window = self.params.get("volume_window", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.7)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.vov_window, self.range_window, self.volume_window, self.atr_period) + 10
        if len(data) < min_bars:
            return []

        close, high, low, volume = data["close"], data["high"], data["low"], data["volume"]
        ret = close.pct_change()
        rvol = ret.rolling(self.rvol_window).std()
        vov = rvol.rolling(self.vov_window).std()
        vov_threshold = vov.rolling(self.vov_window).quantile(self.vov_quantile)

        hi = high.rolling(self.range_window).max().shift(1)
        lo = low.rolling(self.range_window).min().shift(1)
        vma = volume.rolling(self.volume_window).mean()
        atr = self._atr(data, self.atr_period)

        px, a = close.iloc[-1], atr.iloc[-1]
        vov_now, vov_q = vov.iloc[-1], vov_threshold.iloc[-1]
        vol_ratio = volume.iloc[-1] / (vma.iloc[-1] + 1e-12)

        if pd.isna(vov_now) or pd.isna(vov_q):
            return []

        tail_regime = vov_now > vov_q
        signals: List[Signal] = []
        if tail_regime and px > hi.iloc[-1] and vol_ratio > 1.2:
            edge = min(1.0, (vov_now - vov_q) / (vov_q + 1e-12) + (vol_ratio - 1.2))
            conf = min(0.95, max(0.1, 0.42 + 0.33 * edge))
            signals.append(self._mk(symbol, "BUY", px, a, conf, f"Tail vol expansion breakout up (vov={vov_now:.4f})"))
        elif tail_regime and px < lo.iloc[-1] and vol_ratio > 1.2:
            edge = min(1.0, (vov_now - vov_q) / (vov_q + 1e-12) + (vol_ratio - 1.2))
            conf = min(0.95, max(0.1, 0.42 + 0.33 * edge))
            signals.append(self._mk(symbol, "SELL", px, a, conf, f"Tail vol expansion breakout down (vov={vov_now:.4f})"))
        return signals

    def _mk(self, symbol: str, direction: str, px: float, atr: float, conf: float, reason: str) -> Signal:
        if direction == "BUY":
            tp, sl = px + self.tp_atr_mult * atr, px - self.sl_atr_mult * atr
        else:
            tp, sl = px - self.tp_atr_mult * atr, px + self.sl_atr_mult * atr
        return Signal(symbol, direction, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(7)
    n = 360
    returns = np.random.normal(0.0002, 0.022, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    test = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.012, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.012, n))),
        "close": prices,
        "volume": np.random.lognormal(7.0, 0.6, n),
    })
    strat = CryptoVolOfVolTailBreakoutStrategy()
    total = 0
    for i in range(170, len(test)):
        total += len(strat.generate_signals(test.iloc[: i + 1], "BTCUSDT"))
    print(total)

