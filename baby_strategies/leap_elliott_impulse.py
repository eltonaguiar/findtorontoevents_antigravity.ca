"""
Leap - Elliott Impulse
Inspired by Melissa2018 (1st place, $25K winner in TradingView "The Leap").
Detects Wave 3 entry after Wave 2 retracement of 38.2-61.8% of Wave 1.
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


class LeapElliottImpulse:
    NAME = "Leap - Elliott Impulse"
    DESCRIPTION = (
        "Detect Wave 3 entry after Wave 2 retraces 38.2-61.8% of Wave 1. "
        "Inspired by Melissa2018 (1st place, $25K). "
        "Wave 1 = breakout above 20-period high. TP +15%, SL -6%."
    )

    def __init__(self, params: Optional[dict] = None):
        defaults = {
            "wave1_period": 20,
            "fib_low": 0.382,
            "fib_high": 0.618,
            "retrace_lookback": 15,
            "tp_pct": 0.15,
            "sl_pct": 0.06,
            "min_confidence": 0.55,
        }
        p = {**defaults, **(params or {})}
        self.wave1_period = int(p["wave1_period"])
        self.fib_low = float(p["fib_low"])
        self.fib_high = float(p["fib_high"])
        self.retrace_lookback = int(p["retrace_lookback"])
        self.tp_pct = float(p["tp_pct"])
        self.sl_pct = float(p["sl_pct"])
        self.min_confidence = float(p["min_confidence"])

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        signals: List[Signal] = []
        required = self.wave1_period + self.retrace_lookback + 10
        if len(data) < required:
            return signals

        closes = data["close"].values
        highs = data["high"].values
        lows = data["low"].values

        i = self.wave1_period + 5
        while i < len(data) - self.retrace_lookback:
            # Step 1: Detect Wave 1 — significant up move
            # Wave 1 starts at a swing low and breaks above the prior 20-period high
            wave1_start_idx = i - self.wave1_period
            period_high = np.max(highs[wave1_start_idx : i])
            period_low = np.min(lows[wave1_start_idx : i])

            # Wave 1 needs meaningful range
            wave1_range = period_high - period_low
            if wave1_range <= 0 or wave1_range / period_low < 0.02:
                i += 1
                continue

            # Find where Wave 1 peaked
            wave1_peak_offset = np.argmax(highs[wave1_start_idx : i])
            wave1_peak_idx = wave1_start_idx + wave1_peak_offset
            wave1_peak = highs[wave1_peak_idx]
            wave1_bottom = period_low

            # Step 2: Detect Wave 2 — pullback into 38.2-61.8% of Wave 1
            # Look for pullback after the peak
            search_end = min(i + self.retrace_lookback, len(data))
            if search_end <= wave1_peak_idx + 1:
                i += 1
                continue

            retrace_section = closes[wave1_peak_idx + 1 : search_end]
            if len(retrace_section) == 0:
                i += 1
                continue

            wave2_low = np.min(retrace_section)
            wave2_low_offset = np.argmin(retrace_section)
            wave2_low_idx = wave1_peak_idx + 1 + wave2_low_offset

            retrace_amount = wave1_peak - wave2_low
            retrace_ratio = retrace_amount / wave1_range if wave1_range > 0 else 0

            if not (self.fib_low <= retrace_ratio <= self.fib_high):
                i += 1
                continue

            # Step 3: Wave 3 entry — price breaks above Wave 1 midpoint
            wave1_midpoint = (wave1_peak + wave1_bottom) / 2

            for j in range(wave2_low_idx + 1, min(wave2_low_idx + 10, len(data))):
                if closes[j] > wave1_midpoint and closes[j - 1] <= wave1_midpoint:
                    entry = closes[j]
                    tp = entry * (1 + self.tp_pct)
                    sl = entry * (1 - self.sl_pct)

                    # Confidence: retracement precision + wave 1 strength
                    fib_center = (self.fib_low + self.fib_high) / 2
                    fib_precision = 1.0 - abs(retrace_ratio - fib_center) / (self.fib_high - self.fib_low)
                    wave1_strength = min(1.0, wave1_range / (period_low * 0.1))
                    confidence = min(0.95, 0.5 + fib_precision * 0.2 + wave1_strength * 0.15)

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
                            f"Elliott Wave 3 entry: W1 range {wave1_range:.0f} "
                            f"({wave1_bottom:.0f}->{wave1_peak:.0f}), "
                            f"W2 retrace {retrace_ratio:.1%}, "
                            f"breakout above midpoint {wave1_midpoint:.0f}"
                        ),
                    ))
                    break

            i = wave2_low_idx + 5 if wave2_low_idx > i else i + 1

        return signals


params = {
    "wave1_period": 20,
    "fib_low": 0.382,
    "fib_high": 0.618,
    "retrace_lookback": 15,
    "tp_pct": 0.15,
    "sl_pct": 0.06,
    "min_confidence": 0.55,
}

if __name__ == "__main__":
    np.random.seed(42)
    n = 150
    # Create data with impulse-correction pattern
    trend = np.linspace(0, 3000, n)
    cycle = 1500 * np.sin(np.linspace(0, 3 * np.pi, n))
    base = 60000 + trend + cycle + np.cumsum(np.random.randn(n) * 100)
    df = pd.DataFrame({
        "open": base,
        "high": base + np.abs(np.random.randn(n) * 300),
        "low": base - np.abs(np.random.randn(n) * 300),
        "close": base + np.random.randn(n) * 100,
        "volume": np.random.uniform(100, 1000, n),
    })

    strategy = LeapElliottImpulse(params)
    sigs = strategy.generate_signals(df)
    print(f"{strategy.NAME}: {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} {s.symbol} @ {s.entry_price} | TP {s.take_profit} | SL {s.stop_loss} | conf {s.confidence} | {s.reason}")
