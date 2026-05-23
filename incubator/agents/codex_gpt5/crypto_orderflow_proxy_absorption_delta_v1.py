"""
Crypto Orderflow Proxy Absorption Delta - Baby Strat
====================================================

Created by: codex_gpt5
Date: 2026-02-26

Reference mindset:
- Market microstructure absorption logic (orderflow-style)
- Point72/flow-desk style delta divergence confirmation
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


class CryptoOrderflowProxyAbsorptionDeltaStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.div_window = self.params.get("div_window", 35)
        self.delta_window = self.params.get("delta_window", 20)
        self.volume_window = self.params.get("volume_window", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.1)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.25)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.div_window, self.delta_window, self.volume_window, self.atr_period) + 10
        if len(data) < min_bars:
            return []

        o, h, l, c, v = data["open"], data["high"], data["low"], data["close"], data["volume"]
        rng = (h - l).replace(0, np.nan).fillna(method="bfill").fillna(1e-6)
        delta_proxy = ((c - o) / rng) * v
        cum_delta = delta_proxy.rolling(self.delta_window).sum()

        price_ll = c.iloc[-1] < c.rolling(self.div_window).min().shift(1).iloc[-1]
        price_hh = c.iloc[-1] > c.rolling(self.div_window).max().shift(1).iloc[-1]
        delta_hl = cum_delta.iloc[-1] > cum_delta.rolling(self.div_window).min().shift(1).iloc[-1]
        delta_lh = cum_delta.iloc[-1] < cum_delta.rolling(self.div_window).max().shift(1).iloc[-1]

        vma = v.rolling(self.volume_window).mean()
        vol_ratio = v.iloc[-1] / (vma.iloc[-1] + 1e-12)
        atr = self._atr(data, self.atr_period)

        px, a = c.iloc[-1], atr.iloc[-1]
        signals: List[Signal] = []
        if price_ll and delta_hl and vol_ratio > 1.1:
            edge = min(1.0, (vol_ratio - 1.1) + abs(cum_delta.iloc[-1]) / (v.iloc[-1] + 1e-12) / 2)
            conf = min(0.95, max(0.1, 0.43 + 0.3 * edge))
            signals.append(self._mk(symbol, "BUY", px, a, conf, "Absorption long: lower low in price, higher low in delta"))
        elif price_hh and delta_lh and vol_ratio > 1.1:
            edge = min(1.0, (vol_ratio - 1.1) + abs(cum_delta.iloc[-1]) / (v.iloc[-1] + 1e-12) / 2)
            conf = min(0.95, max(0.1, 0.43 + 0.3 * edge))
            signals.append(self._mk(symbol, "SELL", px, a, conf, "Absorption short: higher high in price, lower high in delta"))
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
    np.random.seed(21)
    n = 360
    returns = np.random.normal(0.00025, 0.023, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    test = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.0012, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.012, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.012, n))),
        "close": prices,
        "volume": np.random.lognormal(7.1, 0.65, n),
    })
    strat = CryptoOrderflowProxyAbsorptionDeltaStrategy()
    total = 0
    for i in range(170, len(test)):
        total += len(strat.generate_signals(test.iloc[: i + 1], "BTCUSDT"))
    print(total)

