"""
Crypto Drawdown Convexity Recovery - Baby Strat
===============================================

Created by: codex_gpt5
Date: 2026-02-26

Reference mindset:
- Risk-parity drawdown-state logic
- Convex recovery capture with momentum curvature turn
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


class CryptoDrawdownConvexityRecoveryStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.dd_window = self.params.get("dd_window", 80)
        self.curve_window = self.params.get("curve_window", 6)
        self.deep_dd = self.params.get("deep_dd", -0.12)
        self.atr_period = self.params.get("atr_period", 14)
        self.volume_window = self.params.get("volume_window", 20)
        # R:R widened 2026-03-16: was 2.4, now 3.0 (target R:R >= 2.0; was 1.78, now 2.22)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 3.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.35)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.dd_window, self.curve_window, self.volume_window, self.atr_period) + 10
        if len(data) < min_bars:
            return []

        close, volume = data["close"], data["volume"]
        roll_peak = close.rolling(self.dd_window).max()
        dd = close / (roll_peak + 1e-12) - 1.0

        mom = close.pct_change(self.curve_window)
        convexity = mom.diff()  # curvature proxy
        atr = self._atr(data, self.atr_period)
        vma = volume.rolling(self.volume_window).mean()

        px, a = close.iloc[-1], atr.iloc[-1]
        dd_now = dd.iloc[-1]
        dd_prev = dd.iloc[-2]
        curv = convexity.iloc[-1]
        vol_ratio = volume.iloc[-1] / (vma.iloc[-1] + 1e-12)

        signals: List[Signal] = []
        if dd_now < self.deep_dd and dd_now > dd_prev and curv > 0 and vol_ratio > 1.05:
            edge = min(1.0, (abs(dd_now) - abs(self.deep_dd)) / 0.2 + curv * 50)
            conf = min(0.95, max(0.1, 0.45 + 0.3 * edge))
            signals.append(self._mk(symbol, "BUY", px, a, conf, f"Drawdown convexity recovery long (dd={dd_now:.1%})"))
        elif dd_now > -0.02 and curv < 0 and vol_ratio > 1.05:
            edge = min(1.0, abs(curv) * 40 + (dd_now + 0.02) / 0.06)
            conf = min(0.95, max(0.1, 0.4 + 0.25 * edge))
            signals.append(self._mk(symbol, "SELL", px, a, conf, f"Post-recovery convexity rollover short (dd={dd_now:.1%})"))
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
    np.random.seed(55)
    n = 360
    returns = np.random.normal(0.0002, 0.023, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    test = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.012, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.012, n))),
        "close": prices,
        "volume": np.random.lognormal(7.1, 0.6, n),
    })
    strat = CryptoDrawdownConvexityRecoveryStrategy()
    total = 0
    for i in range(170, len(test)):
        total += len(strat.generate_signals(test.iloc[: i + 1], "BTCUSDT"))
    print(total)

