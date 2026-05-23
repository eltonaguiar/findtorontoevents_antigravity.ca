"""
Leap - HTF Momentum
Inspired by multiple TradingView "The Leap" winners using top-down analysis.
Weekly bias via 50-period SMA, entry on RSI pullback/bounce.
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


class LeapHTFMomentum:
    NAME = "Leap - HTF Momentum"
    DESCRIPTION = (
        "Weekly bias (50-SMA) with RSI pullback entry. "
        "Bullish above SMA + RSI<45 = BUY; bearish below SMA + RSI>55 = SELL. "
        "TP +15%, SL -6%."
    )

    def __init__(self, params: Optional[dict] = None):
        defaults = {
            "sma_period": 50,
            "rsi_period": 14,
            "rsi_buy_threshold": 45,
            "rsi_sell_threshold": 55,
            "tp_pct": 0.15,
            "sl_pct": 0.06,
            "min_confidence": 0.50,
        }
        p = {**defaults, **(params or {})}
        self.sma_period = int(p["sma_period"])
        self.rsi_period = int(p["rsi_period"])
        self.rsi_buy_threshold = float(p["rsi_buy_threshold"])
        self.rsi_sell_threshold = float(p["rsi_sell_threshold"])
        self.tp_pct = float(p["tp_pct"])
        self.sl_pct = float(p["sl_pct"])
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

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        signals: List[Signal] = []
        required = self.sma_period + self.rsi_period + 5
        if len(data) < required:
            return signals

        closes = data["close"].values
        sma = pd.Series(closes).rolling(self.sma_period).mean().values
        rsi = self._rsi(closes, self.rsi_period)

        for i in range(required, len(data)):
            if np.isnan(sma[i]) or np.isnan(rsi[i]):
                continue

            close = closes[i]
            above_sma = close > sma[i]
            below_sma = close < sma[i]

            direction = None
            reason_parts = []

            if above_sma and rsi[i] < self.rsi_buy_threshold:
                direction = "BUY"
                reason_parts.append(f"Price above 50-SMA (bullish HTF)")
                reason_parts.append(f"RSI {rsi[i]:.1f} < {self.rsi_buy_threshold} (pullback)")
            elif below_sma and rsi[i] > self.rsi_sell_threshold:
                direction = "SELL"
                reason_parts.append(f"Price below 50-SMA (bearish HTF)")
                reason_parts.append(f"RSI {rsi[i]:.1f} > {self.rsi_sell_threshold} (bounce)")

            if direction is None:
                continue

            entry = close
            if direction == "BUY":
                tp = entry * (1 + self.tp_pct)
                sl = entry * (1 - self.sl_pct)
            else:
                tp = entry * (1 - self.tp_pct)
                sl = entry * (1 + self.sl_pct)

            # Confidence: distance from SMA + RSI extremity
            sma_dist = abs(close - sma[i]) / sma[i]
            if direction == "BUY":
                rsi_score = (self.rsi_buy_threshold - rsi[i]) / self.rsi_buy_threshold
            else:
                rsi_score = (rsi[i] - self.rsi_sell_threshold) / (100 - self.rsi_sell_threshold)

            confidence = min(0.95, 0.5 + sma_dist * 5 + rsi_score * 0.3)

            if confidence < self.min_confidence:
                continue

            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(entry, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason="; ".join(reason_parts),
            ))

        return signals


params = {
    "sma_period": 50,
    "rsi_period": 14,
    "rsi_buy_threshold": 45,
    "rsi_sell_threshold": 55,
    "tp_pct": 0.15,
    "sl_pct": 0.06,
    "min_confidence": 0.50,
}

if __name__ == "__main__":
    np.random.seed(42)
    n = 120
    base = 60000 + np.cumsum(np.random.randn(n) * 300)
    df = pd.DataFrame({
        "open": base,
        "high": base + np.abs(np.random.randn(n) * 200),
        "low": base - np.abs(np.random.randn(n) * 200),
        "close": base + np.random.randn(n) * 100,
        "volume": np.random.uniform(100, 1000, n),
    })

    strategy = LeapHTFMomentum(params)
    sigs = strategy.generate_signals(df)
    print(f"{strategy.NAME}: {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} {s.symbol} @ {s.entry_price} | TP {s.take_profit} | SL {s.stop_loss} | conf {s.confidence} | {s.reason}")
