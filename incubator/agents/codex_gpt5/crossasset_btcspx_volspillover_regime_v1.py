"""
Cross-Asset BTC-SPX Volatility Spillover Regime - Baby Strat
=============================================================

Created by: codex_gpt5
Date: 2026-02-26

Reference mindset:
- AQR-style cross-asset regime modeling
- Lopez de Prado-style volatility-state conditioning
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


class MockSPXVolBridge:
    """Synthetic SPX proxy bridge for sandbox testing."""

    @staticmethod
    def synth_spx_returns(btc_returns: pd.Series, seed: int = 2026) -> pd.Series:
        rng = np.random.default_rng(seed)
        noise = pd.Series(rng.normal(0.0002, 0.011, len(btc_returns)), index=btc_returns.index)
        regime = pd.Series(rng.choice([0.3, 0.6], size=len(btc_returns), p=[0.35, 0.65]), index=btc_returns.index)
        return regime * btc_returns + (1.0 - regime) * noise


class BTCSPXVolSpilloverRegimeStrategy:
    """
    Long/short BTC when SPX volatility regime shifts spill over into BTC.

    Logic:
    - Build rolling realized vol for BTC/SPX
    - Track SPX vol impulse and BTC lagged response
    - Trade when BTC overreacts to spillover impulse and then mean-reverts
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.realized_window = self.params.get("realized_window", 20)
        self.spill_window = self.params.get("spill_window", 30)
        self.spill_z_entry = self.params.get("spill_z_entry", 1.5)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.3)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.4)
        self.bridge = MockSPXVolBridge()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.realized_window, self.spill_window, self.atr_period) + 15
        if len(data) < min_bars:
            return []

        close = data["close"]
        btc_r = close.pct_change().fillna(0.0)
        spx_r = self.bridge.synth_spx_returns(btc_r)

        btc_rv = btc_r.rolling(self.realized_window).std()
        spx_rv = spx_r.rolling(self.realized_window).std()

        spx_vol_impulse = spx_rv.diff()
        spill_signal = spx_vol_impulse.rolling(self.spill_window).corr(btc_r.shift(-1))
        spread = (btc_rv - spx_rv)
        spread_z = (spread - spread.rolling(self.spill_window).mean()) / (spread.rolling(self.spill_window).std() + 1e-12)

        atr = self._atr(data, self.atr_period)
        px = close.iloc[-1]
        a = atr.iloc[-1]
        z = spread_z.iloc[-1]
        spill = spill_signal.iloc[-1]

        if pd.isna(z) or pd.isna(spill):
            return []

        signals: List[Signal] = []
        if z > self.spill_z_entry and spill > 0:
            edge = min(1.0, (z - self.spill_z_entry) / 2.0 + spill)
            conf = min(0.95, max(0.1, 0.4 + 0.4 * edge))
            signals.append(self._mk(symbol, "SELL", px, a, conf, f"BTC vol overreaction vs SPX spillover (z={z:.2f}, spill={spill:.2f})"))
        elif z < -self.spill_z_entry and spill > 0:
            edge = min(1.0, (abs(z) - self.spill_z_entry) / 2.0 + spill)
            conf = min(0.95, max(0.1, 0.4 + 0.4 * edge))
            signals.append(self._mk(symbol, "BUY", px, a, conf, f"BTC vol underreaction vs SPX spillover (z={z:.2f}, spill={spill:.2f})"))
        return signals

    def _mk(self, symbol: str, direction: str, px: float, atr: float, conf: float, reason: str) -> Signal:
        if direction == "BUY":
            tp = px + self.tp_atr_mult * atr
            sl = px - self.sl_atr_mult * atr
        else:
            tp = px - self.tp_atr_mult * atr
            sl = px + self.sl_atr_mult * atr
        return Signal(symbol, direction, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 360
    returns = np.random.normal(0.0003, 0.021, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    test = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.011, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.011, n))),
        "close": prices,
        "volume": np.random.lognormal(7.0, 0.5, n),
    })
    strat = BTCSPXVolSpilloverRegimeStrategy()
    total = 0
    for i in range(160, len(test)):
        total += len(strat.generate_signals(test.iloc[: i + 1], "BTCUSDT"))
    print(total)

