"""
Leap - Concentrated R:R
Inspired by Hakukuro (2nd place in TradingView "The Leap") — "be the minority."
Only enters when Risk:Reward > 3:1. Uses ATR for dynamic TP/SL.
Max 5 open positions enforced via confidence filter.
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class LeapConcentratedRR:
    NAME = "Leap - Concentrated R:R"
    DESCRIPTION = (
        "Only enters when R:R > 3:1 using ATR-based TP/SL. "
        "Inspired by Hakukuro (2nd place). TP = entry + 4*ATR, SL = entry - 1.3*ATR. "
        "Max 5 positions. TP +20%, SL -6%."
    )

    def __init__(self, params: Optional[dict] = None):
        defaults = {
            "atr_period": 14,
            "tp_atr_mult": 4.0,
            "sl_atr_mult": 1.3,
            "min_rr_ratio": 3.0,
            "max_tp_pct": 0.20,
            "max_sl_pct": 0.06,
            "rsi_period": 14,
            "max_signals": 5,
            "min_confidence": 0.60,
        }
        p = {**defaults, **(params or {})}
        self.atr_period = int(p["atr_period"])
        self.tp_atr_mult = float(p["tp_atr_mult"])
        self.sl_atr_mult = float(p["sl_atr_mult"])
        self.min_rr_ratio = float(p["min_rr_ratio"])
        self.max_tp_pct = float(p["max_tp_pct"])
        self.max_sl_pct = float(p["max_sl_pct"])
        self.rsi_period = int(p["rsi_period"])
        self.max_signals = int(p["max_signals"])
        self.min_confidence = float(p["min_confidence"])

    @staticmethod
    def _rsi(closes: np.ndarray, period: int) -> np.ndarray:
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        rsi = np.full(len(closes), np.nan)
        if len(deltas) < period:
            return rsi
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            rs = avg_gain / avg_loss if avg_loss != 0 else 100.0
            rsi[i + 1] = 100 - 100 / (1 + rs)
        return rsi

    @staticmethod
    def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> np.ndarray:
        atr = np.full(len(closes), np.nan)
        if len(closes) < period + 1:
            return atr
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(closes)):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        for i in range(period, len(closes)):
            atr[i] = np.mean(tr[i - period + 1 : i + 1])
        return atr

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        signals: List[Signal] = []
        required = max(self.atr_period, self.rsi_period) + 5
        if len(data) < required:
            return signals

        closes = data["close"].values
        highs = data["high"].values
        lows = data["low"].values

        atr = self._atr(highs, lows, closes, self.atr_period)
        rsi = self._rsi(closes, self.rsi_period)

        candidates = []

        for i in range(required, len(data)):
            if np.isnan(atr[i]) or np.isnan(rsi[i]):
                continue

            close = closes[i]
            current_atr = atr[i]

            # Determine direction from RSI
            if rsi[i] < 40:
                direction = "BUY"
            elif rsi[i] > 60:
                direction = "SELL"
            else:
                continue

            # ATR-based TP/SL
            if direction == "BUY":
                raw_tp = close + self.tp_atr_mult * current_atr
                raw_sl = close - self.sl_atr_mult * current_atr
                tp = min(raw_tp, close * (1 + self.max_tp_pct))
                sl = max(raw_sl, close * (1 - self.max_sl_pct))
            else:
                raw_tp = close - self.tp_atr_mult * current_atr
                raw_sl = close + self.sl_atr_mult * current_atr
                tp = max(raw_tp, close * (1 - self.max_tp_pct))
                sl = min(raw_sl, close * (1 + self.max_sl_pct))

            reward = abs(tp - close)
            risk = abs(close - sl)
            if risk == 0:
                continue

            rr_ratio = reward / risk
            if rr_ratio < self.min_rr_ratio:
                continue

            # Confidence based on R:R quality and RSI extremity
            rr_score = min(1.0, (rr_ratio - self.min_rr_ratio) / 3)
            rsi_extremity = abs(rsi[i] - 50) / 50
            confidence = min(0.95, 0.55 + rr_score * 0.2 + rsi_extremity * 0.2)

            if confidence < self.min_confidence:
                continue

            candidates.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(close, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=(
                    f"R:R {rr_ratio:.1f}:1 (min {self.min_rr_ratio}), "
                    f"ATR {current_atr:.2f}, RSI {rsi[i]:.1f}"
                ),
            ))

        # Enforce max positions: take top by confidence
        candidates.sort(key=lambda s: s.confidence, reverse=True)
        signals = candidates[: self.max_signals]
        return signals


params = {
    "atr_period": 14,
    "tp_atr_mult": 4.0,
    "sl_atr_mult": 1.3,
    "min_rr_ratio": 3.0,
    "max_tp_pct": 0.20,
    "max_sl_pct": 0.06,
    "rsi_period": 14,
    "max_signals": 5,
    "min_confidence": 0.60,
}

if __name__ == "__main__":
    np.random.seed(42)
    n = 100
    base = 60000 + np.cumsum(np.random.randn(n) * 300)
    df = pd.DataFrame({
        "open": base,
        "high": base + np.abs(np.random.randn(n) * 200),
        "low": base - np.abs(np.random.randn(n) * 200),
        "close": base + np.random.randn(n) * 100,
        "volume": np.random.uniform(100, 1000, n),
    })

    strategy = LeapConcentratedRR(params)
    sigs = strategy.generate_signals(df)
    print(f"{strategy.NAME}: {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} {s.symbol} @ {s.entry_price} | TP {s.take_profit} | SL {s.stop_loss} | conf {s.confidence} | {s.reason}")
