"""
Crypto Kalman Trend Residual Reversion v2 — Long-Only + Symbol Gate
====================================================================

DNA Lineage
-----------
Parent:  crypto_kalman_trend_residual_reversion_v1
         (WR 72.2%, n=18, FDR p=0.096 — 1 trade from p<0.05 territory)
Axes:    #2 Direction gate (LONG_ONLY) + #1 Symbol allowlist

Mutation Rationale (per docs/MUTATION_THREE_AXIS_PROTOCOL.md)
-------------------------------------------------------------
The parent had 72.2% WR over 18 trades with p=0.096, barely missing the FDR
threshold. Graveyard lesson #5: "Mean reversion works — crypto dominated by
retail overreaction which naturally mean-reverts."  SHORT mean-reversion
fights funding-rate bias and liquidation cascades; LONG mean-reversion fades
over-sold dips where the structural bid (spot buyers, funding arbitrageurs)
supports recovery.

This variant:
  - Removes SELL signals entirely (LONG_ONLY)
  - Restricts to 8 high-liquidity, lower-correlation symbols where mean-
    reversion is most reliable (confirmed survivors from graveyard analysis)
  - Tightens z_entry from 1.7 → 2.0 to reduce noise entries
  - Adds a 24h volume filter: only trade if current volume > 0.7x 20-bar avg
    (avoids low-liquidity fakeouts)

Graduation target: n≥30, WR≥60%, FDR p<0.05 → eligible for promotion gate.

Author: Claude Sonnet 4.6 — DNA mutation 2026-06-06
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

# Symbol allowlist — graveyard-validated, high-liquidity, mean-reversion
# friendly (excludes meme coins and low-float alts that trend strongly)
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "LINKUSDT", "NEARUSDT", "INJUSDT",
]


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoKalmanResidualV2LongGated:
    """
    Long-only Kalman residual mean-reversion with symbol allowlist.

    Mutation axes applied:
      Axis 1 (Symbol):    8-symbol allowlist, graveyard-filtered
      Axis 2 (Direction): LONG_ONLY — removes SELL to eliminate funding drag
    """

    # Mutation tag used by the backtest harness to track lineage
    MUTATION_PARENT = "crypto_kalman_trend_residual_reversion_v1"
    MUTATION_AXES = ["direction:long_only", "symbol:allowlist_8"]

    def __init__(self, params: Optional[dict] = None) -> None:
        p = params or {}
        self.q = p.get("q", 1e-5)           # Kalman process noise
        self.r = p.get("r", 0.01)           # Kalman observation noise
        self.z_entry = p.get("z_entry", 2.0)  # tighter than parent (1.7)
        self.atr_period = p.get("atr_period", 14)
        self.tp_atr_mult = p.get("tp_atr_mult", 2.0)   # slightly wider TP
        self.sl_atr_mult = p.get("sl_atr_mult", 1.2)
        self.vol_ratio_min = p.get("vol_ratio_min", 0.7)  # volume filter
        self.vol_lookback = p.get("vol_lookback", 20)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if symbol not in SYMBOLS:
            return []
        if len(data) < 50:
            return []

        # Volume filter — skip low-liquidity bars
        if "volume" in data.columns:
            vol_avg = data["volume"].rolling(self.vol_lookback).mean().iloc[-1]
            if vol_avg > 0 and data["volume"].iloc[-1] < self.vol_ratio_min * vol_avg:
                return []

        trend = self._kalman(data["close"].values)
        resid = data["close"].values - trend
        z = (resid[-1] - resid.mean()) / (resid.std() + 1e-9)

        atr = self._atr(data).iloc[-1]
        px = data["close"].iloc[-1]
        if pd.isna(atr) or atr <= 0:
            return []

        # LONG_ONLY: only fade oversold residual (z < -threshold)
        if z < -self.z_entry:
            confidence = min(0.88, 0.65 + abs(z) * 0.06)
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(px, 2),
                take_profit=round(px + atr * self.tp_atr_mult, 2),
                stop_loss=round(px - atr * self.sl_atr_mult, 2),
                reason=f"Kalman residual z={z:.2f} (long_only gate) mean-revert dip",
            )]

        return []

    # ── internals ──────────────────────────────────────────────────────────

    def _kalman(self, y: np.ndarray) -> np.ndarray:
        n = len(y)
        x = np.zeros(n)
        p = 1.0
        x[0] = y[0]
        for t in range(1, n):
            x_pred = x[t - 1]
            p_pred = p + self.q
            k = p_pred / (p_pred + self.r)
            x[t] = x_pred + k * (y[t] - x_pred)
            p = (1 - k) * p_pred
        return x

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    rets = np.random.normal(0.0001, 0.02, n)
    px = 51000 * np.exp(np.cumsum(rets))
    df = pd.DataFrame({
        "open": px, "high": px * 1.01, "low": px * 0.99,
        "close": px, "volume": np.random.uniform(500, 2000, n),
    })
    strat = CryptoKalmanResidualV2LongGated()
    sigs = strat.generate_signals(df, "BTCUSDT")
    print(f"Signals: {sigs}")
