"""
RSI Volatility Bounce v2 — Symbol-Expanded for Fast n Growth
=============================================================

DNA Lineage
-----------
Parent:  st_rsi_vol_bounce
         (WR 93.8%, n=16, DSR=PASS, FDR=PASS — needs only 14 more trades
          to clear the n≥30 promotion gate and become the first fully
          promoted strategy since the registry was last populated)
Axis:    #1 Symbol expansion (6 → 18 symbols)

Mutation Rationale (per docs/MUTATION_THREE_AXIS_PROTOCOL.md)
-------------------------------------------------------------
st_rsi_vol_bounce passes BOTH DSR and FDR with p=0.0005 and WR=93.8%.
It is the highest-quality strategy in the pipeline. The sole barrier to
promotion is n=16 (<30 required). This variant expands the symbol universe
from 6 core tokens to 18 liquid perpetuals, generating more trades per day
so the strategy accumulates the required 14 additional closed trades faster
while preserving the same core signal logic.

The RSI+Vol bounce signal:
  - RSI(7) < 25 (oversold) AND ATR expansion (vol spike)
  - Entry on close of the triggering bar
  - TP = entry + 2×ATR, SL = entry − 1.2×ATR (asymmetric 1.67:1 RR)
  - Max hold: 24 bars (avoids stale positions)

Symbol selection: top-18 by USDT perpetual OI on Binance, all >$500M
daily volume — liquid enough to fill without slippage distortion.

Author: Claude Sonnet 4.6 — DNA mutation 2026-06-06
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

# Expanded symbol universe (parent used ~6; we add liquid mid-caps)
SYMBOLS = [
    # Core (in parent)
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    # Expansion — high-OI liquid perps
    "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
    "NEARUSDT", "INJUSDT", "SUIUSDT", "OPUSDT",
    "AAVEUSDT", "UNIUSDT", "ATOMUSDT", "FTMUSDT",
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


class RsiVolBounceV2Expanded:
    """
    RSI + volatility-spike bounce, long-only, symbol-expanded.

    Mutation axes applied:
      Axis 1 (Symbol): 6 → 18 liquid perps for faster n accumulation

    Signal logic preserved from parent st_rsi_vol_bounce:
      Entry: RSI(7) < 25 AND current ATR > 1.4 × 20-bar ATR average
      TP:    entry + 2.0 × ATR
      SL:    entry − 1.2 × ATR
      Max hold: 24 bars
    """

    MUTATION_PARENT = "st_rsi_vol_bounce"
    MUTATION_AXES = ["symbol:expanded_18"]

    def __init__(self, params: Optional[dict] = None) -> None:
        p = params or {}
        self.rsi_period = p.get("rsi_period", 7)
        self.rsi_oversold = p.get("rsi_oversold", 25)
        self.atr_period = p.get("atr_period", 14)
        self.atr_lookback = p.get("atr_lookback", 20)
        self.atr_expansion_mult = p.get("atr_expansion_mult", 1.4)
        self.tp_atr_mult = p.get("tp_atr_mult", 2.0)
        self.sl_atr_mult = p.get("sl_atr_mult", 1.2)
        self.max_hold_bars = p.get("max_hold_bars", 24)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if symbol not in SYMBOLS:
            return []
        if len(data) < max(self.rsi_period + 1, self.atr_period, self.atr_lookback) + 5:
            return []

        rsi = self._rsi(data["close"])
        atr = self._atr(data)
        atr_avg = atr.rolling(self.atr_lookback).mean()

        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        current_atr_avg = atr_avg.iloc[-1]
        px = data["close"].iloc[-1]

        if any(pd.isna(v) or v <= 0 for v in [current_atr, current_atr_avg]):
            return []

        oversold = current_rsi < self.rsi_oversold
        vol_spike = current_atr > self.atr_expansion_mult * current_atr_avg

        if oversold and vol_spike:
            # Confidence scales with how deep the oversold reading is
            rsi_depth = max(0, self.rsi_oversold - current_rsi)
            confidence = min(0.92, 0.70 + rsi_depth * 0.01)
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(px, 4),
                take_profit=round(px + current_atr * self.tp_atr_mult, 4),
                stop_loss=round(px - current_atr * self.sl_atr_mult, 4),
                reason=(
                    f"RSI({self.rsi_period})={current_rsi:.1f} oversold + "
                    f"ATR spike {current_atr/current_atr_avg:.2f}x avg"
                ),
            )]

        return []

    # ── internals ──────────────────────────────────────────────────────────

    def _rsi(self, close: pd.Series) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(self.rsi_period).mean()
        loss = (-delta.clip(upper=0)).rolling(self.rsi_period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - 100 / (1 + rs)

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    np.random.seed(7)
    n = 200
    rets = np.random.normal(0.0001, 0.02, n)
    px = 2500 * np.exp(np.cumsum(rets))
    # Inject vol spike at end to trigger signal
    px[-5:] *= np.linspace(0.97, 0.94, 5)
    df = pd.DataFrame({
        "open": px, "high": px * 1.015, "low": px * 0.985,
        "close": px, "volume": np.random.uniform(1000, 5000, n),
    })
    df.loc[df.index[-5:], "high"] *= 1.03
    strat = RsiVolBounceV2Expanded()
    sigs = strat.generate_signals(df, "ETHUSDT")
    print(f"Signals generated: {len(sigs)}")
    for s in sigs:
        print(f"  {s}")
