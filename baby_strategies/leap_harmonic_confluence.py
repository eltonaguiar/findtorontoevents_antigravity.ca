"""
Leap - Harmonic Confluence
Inspired by Magicfingers0T0 (#2 Feb 2026, +88% in The Leap).
Simplified harmonic pattern detection using Fibonacci ratios (38.2%, 61.8%).
Entry at Fib retracement zone with RSI divergence confirmation.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
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


class LeapHarmonicConfluence:
    NAME = "Leap - Harmonic Confluence"
    DESCRIPTION = (
        "Simplified harmonic pattern detection via Fibonacci 38.2%/61.8% retracements. "
        "Inspired by Magicfingers0T0 (#2 Feb 2026, +88%). "
        "Entry at Fib zone + RSI divergence. TP +12%, SL -5%."
    )

    def __init__(self, params: Optional[dict] = None):
        defaults = {
            "swing_lookback": 10,
            "fib_low": 0.382,
            "fib_high": 0.618,
            "rsi_period": 14,
            "tp_pct": 0.12,
            "sl_pct": 0.05,
            "min_confidence": 0.55,
        }
        p = {**defaults, **(params or {})}
        self.swing_lookback = int(p["swing_lookback"])
        self.fib_low = float(p["fib_low"])
        self.fib_high = float(p["fib_high"])
        self.rsi_period = int(p["rsi_period"])
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

    def _find_swing_points(self, data: np.ndarray, lookback: int) -> Tuple[List[int], List[int]]:
        """Find swing highs and swing lows."""
        swing_highs = []
        swing_lows = []
        for i in range(lookback, len(data) - lookback):
            if data[i] == np.max(data[i - lookback : i + lookback + 1]):
                swing_highs.append(i)
            if data[i] == np.min(data[i - lookback : i + lookback + 1]):
                swing_lows.append(i)
        return swing_highs, swing_lows

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        signals: List[Signal] = []
        required = self.swing_lookback * 4 + self.rsi_period + 5
        if len(data) < required:
            return signals

        closes = data["close"].values
        highs = data["high"].values
        lows = data["low"].values

        rsi = self._rsi(closes, self.rsi_period)
        swing_highs, swing_lows = self._find_swing_points(closes, self.swing_lookback)

        for i in range(required, len(data)):
            if np.isnan(rsi[i]):
                continue

            close = closes[i]

            # Find recent swing high and swing low before current bar
            recent_highs = [sh for sh in swing_highs if sh < i]
            recent_lows = [sl for sl in swing_lows if sl < i]

            if len(recent_highs) < 2 or len(recent_lows) < 1:
                continue

            # XABCD approximation: use last two swing highs and last swing low
            swing_h1 = closes[recent_highs[-2]]  # X or A point
            swing_l = closes[recent_lows[-1]]     # B point (retracement)
            swing_h2 = closes[recent_highs[-1]]   # C point

            # Check bullish harmonic: price retraced into Fib zone
            if swing_h2 > swing_h1:
                move = swing_h2 - swing_l
                if move <= 0:
                    continue
                retrace = swing_h2 - close
                retrace_ratio = retrace / move

                if self.fib_low <= retrace_ratio <= self.fib_high:
                    # RSI divergence: price lower but RSI higher (bullish)
                    rsi_confirm = rsi[i] > rsi[max(0, i - 5)]
                    if not rsi_confirm:
                        continue

                    entry = close
                    tp = entry * (1 + self.tp_pct)
                    sl = entry * (1 - self.sl_pct)

                    fib_accuracy = 1.0 - abs(retrace_ratio - 0.5) / 0.5
                    confidence = min(0.95, 0.5 + fib_accuracy * 0.25 + 0.1)

                    if confidence < self.min_confidence:
                        continue

                    signals.append(Signal(
                        symbol=symbol,
                        direction="BUY",
                        confidence=round(confidence, 3),
                        entry_price=round(entry, 2),
                        take_profit=round(tp, 2),
                        stop_loss=round(sl, 2),
                        reason=(
                            f"Harmonic Fib {retrace_ratio:.1%} retracement "
                            f"(zone {self.fib_low:.1%}-{self.fib_high:.1%}), "
                            f"RSI divergence confirmed ({rsi[i]:.1f})"
                        ),
                    ))

            # Check bearish harmonic
            elif swing_h2 < swing_h1:
                move = swing_h1 - swing_l
                if move <= 0:
                    continue
                retrace = close - swing_l
                retrace_ratio = retrace / move

                if self.fib_low <= retrace_ratio <= self.fib_high:
                    rsi_confirm = rsi[i] < rsi[max(0, i - 5)]
                    if not rsi_confirm:
                        continue

                    entry = close
                    tp = entry * (1 - self.tp_pct)
                    sl = entry * (1 + self.sl_pct)

                    fib_accuracy = 1.0 - abs(retrace_ratio - 0.5) / 0.5
                    confidence = min(0.95, 0.5 + fib_accuracy * 0.25 + 0.1)

                    if confidence < self.min_confidence:
                        continue

                    signals.append(Signal(
                        symbol=symbol,
                        direction="SELL",
                        confidence=round(confidence, 3),
                        entry_price=round(entry, 2),
                        take_profit=round(tp, 2),
                        stop_loss=round(sl, 2),
                        reason=(
                            f"Bearish harmonic Fib {retrace_ratio:.1%} retracement "
                            f"(zone {self.fib_low:.1%}-{self.fib_high:.1%}), "
                            f"RSI divergence confirmed ({rsi[i]:.1f})"
                        ),
                    ))

        return signals


params = {
    "swing_lookback": 10,
    "fib_low": 0.382,
    "fib_high": 0.618,
    "rsi_period": 14,
    "tp_pct": 0.12,
    "sl_pct": 0.05,
    "min_confidence": 0.55,
}

if __name__ == "__main__":
    np.random.seed(42)
    n = 150
    # Create data with some swing pattern
    t = np.linspace(0, 4 * np.pi, n)
    base = 60000 + 2000 * np.sin(t) + np.cumsum(np.random.randn(n) * 100)
    df = pd.DataFrame({
        "open": base,
        "high": base + np.abs(np.random.randn(n) * 200),
        "low": base - np.abs(np.random.randn(n) * 200),
        "close": base + np.random.randn(n) * 80,
        "volume": np.random.uniform(100, 1000, n),
    })

    strategy = LeapHarmonicConfluence(params)
    sigs = strategy.generate_signals(df)
    print(f"{strategy.NAME}: {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} {s.symbol} @ {s.entry_price} | TP {s.take_profit} | SL {s.stop_loss} | conf {s.confidence} | {s.reason}")
