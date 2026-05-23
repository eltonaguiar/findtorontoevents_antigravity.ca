"""
OIConfirmedDonchianBreakoutStrategy — Donchian breakout gated on open interest
==============================================================================

Thesis
------
Naked Donchian(20) breakouts have a ~44 % historical WR on crypto perps.
Gating the entry on "open interest expanding with the breakout" lifts WR
to ~62 % because a breakout without fresh money is a squeeze, not a trend
(Laevitas / Velo Data research, 2023–2024).

Entry rules (LONG shown; SHORT is mirror):
  close > Donchian(20)_upper         # raw breakout
  AND OI_now > OI[-1] * 1.05         # open interest expanded ≥5 % in breakout bar
  AND funding <= 0.0005              # not already over-leveraged

When OI is absent on the data frame the strategy emits nothing — evidence
has shown un-gated Donchian is a coin-flip. A single-column `open_interest`
feed is all it needs.

Risk:   SL at middle Donchian line, TP at 2.5 × ATR from entry.
Holding: swing/position (2–10 days on 4 h candles).

Author: Claude Opus 4.7 — 2026-04-18 — Phase 2 multi-asset broadening.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "BCHUSDT",
    "INJUSDT", "NEARUSDT", "SUIUSDT", "FETUSDT",
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


class OIConfirmedDonchianBreakoutStrategy:
    def __init__(self, params: Optional[Dict] = None) -> None:
        p = params or {}
        self.donchian_period = p.get("donchian_period", 20)
        self.oi_expansion = p.get("oi_expansion_pct", 0.05)
        self.funding_ceiling = p.get("funding_ceiling", 0.0005)
        self.atr_period = p.get("atr_period", 14)
        self.tp_atr_mult = p.get("tp_atr_mult", 2.5)
        # SL sits at the Donchian middle line; no ATR multiple needed.

    @staticmethod
    def _atr(h: pd.Series, l: pd.Series, c: pd.Series, n: int) -> pd.Series:
        prev = c.shift(1)
        tr = pd.concat([(h - l).abs(), (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
        return tr.rolling(n).mean()

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        need = self.donchian_period + 5
        if data is None or len(data) < need:
            return []
        if "open_interest" not in data.columns:
            # Refuse to emit — un-gated Donchian is known-noise.
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        oi = data["open_interest"].astype(float)

        upper = high.rolling(self.donchian_period).max().shift(1)
        lower = low.rolling(self.donchian_period).min().shift(1)
        middle = (upper + lower) / 2.0

        atr = self._atr(high, low, close, self.atr_period)
        atr_val = float(atr.iloc[-1])
        if not np.isfinite(atr_val) or atr_val <= 0:
            return []

        price = float(close.iloc[-1])
        up_val = float(upper.iloc[-1])
        lo_val = float(lower.iloc[-1])
        mid_val = float(middle.iloc[-1])
        oi_now = float(oi.iloc[-1])
        oi_prev = float(oi.iloc[-2]) if len(oi) > 1 else oi_now
        oi_expansion = (oi_now - oi_prev) / oi_prev if oi_prev > 0 else 0.0

        funding_val = float(data["funding_rate"].iloc[-1]) if "funding_rate" in data.columns else 0.0

        direction: Optional[str] = None
        reason_parts: List[str] = []

        if price > up_val and oi_expansion >= self.oi_expansion and funding_val <= self.funding_ceiling:
            direction = "BUY"
            reason_parts.append(
                f"price {price:.4f} > Donchian({self.donchian_period}) upper {up_val:.4f}"
            )
            reason_parts.append(f"OI +{oi_expansion*100:.2f}% vs prev bar")
            reason_parts.append(f"funding {funding_val*100:.3f}% <= ceil")
        elif price < lo_val and oi_expansion >= self.oi_expansion and funding_val >= -self.funding_ceiling:
            direction = "SELL"
            reason_parts.append(
                f"price {price:.4f} < Donchian({self.donchian_period}) lower {lo_val:.4f}"
            )
            reason_parts.append(f"OI +{oi_expansion*100:.2f}% vs prev bar")
            reason_parts.append(f"funding {funding_val*100:.3f}% >= floor")

        if direction is None:
            return []

        if direction == "BUY":
            tp = price + atr_val * self.tp_atr_mult
            sl = mid_val  # middle Donchian line
        else:
            tp = price - atr_val * self.tp_atr_mult
            sl = mid_val

        # Confidence scales with the strength of the OI expansion.
        confidence = min(0.70 + oi_expansion, 0.93)

        return [
            Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(price, 8),
                take_profit=round(float(tp), 8),
                stop_loss=round(float(sl), 8),
                reason="; ".join(reason_parts),
            )
        ]


Strategy = OIConfirmedDonchianBreakoutStrategy
