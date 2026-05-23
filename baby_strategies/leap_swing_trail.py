"""
Leap - Swing Trail
Inspired by Fractalyst (top 3% in TradingView "The Leap" in 5 days).
Breakout above 20-period high with trailing stop behind 10-period swing low.
Maximizes winner ride using dynamic trailing stop method.
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


class LeapSwingTrail:
    NAME = "Leap - Swing Trail"
    DESCRIPTION = (
        "Breakout above 20-period high with trailing stop behind 10-period swing low. "
        "Inspired by Fractalyst (top 3% in The Leap). Dynamic TP via trail, SL -3% initial."
    )

    def __init__(self, params: Optional[dict] = None):
        defaults = {
            "breakout_period": 20,
            "trail_period": 10,
            "initial_sl_pct": 0.03,
            "min_confidence": 0.55,
        }
        p = {**defaults, **(params or {})}
        self.breakout_period = int(p["breakout_period"])
        self.trail_period = int(p["trail_period"])
        self.initial_sl_pct = float(p["initial_sl_pct"])
        self.min_confidence = float(p["min_confidence"])

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        signals: List[Signal] = []
        if len(data) < self.breakout_period + 5:
            return signals

        highs = data["high"].values
        lows = data["low"].values
        closes = data["close"].values
        volumes = data["volume"].values if "volume" in data.columns else np.ones(len(data))

        for i in range(self.breakout_period, len(data)):
            highest_high = np.max(highs[i - self.breakout_period : i])
            close = closes[i]

            if close <= highest_high:
                continue

            # Breakout detected
            trail_start = max(0, i - self.trail_period)
            swing_low = np.min(lows[trail_start : i + 1])
            entry = close
            initial_sl = entry * (1 - self.initial_sl_pct)
            trail_sl = swing_low

            # Use the tighter (higher) of the two as stop loss
            stop_loss = max(initial_sl, trail_sl)
            if stop_loss >= entry:
                continue

            risk = entry - stop_loss
            take_profit = entry + risk * 3  # Dynamic TP at 3R

            # Confidence: volume confirmation + breakout strength
            avg_vol = np.mean(volumes[max(0, i - 20) : i]) if i >= 20 else np.mean(volumes[:i])
            vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 1.0
            breakout_strength = (close - highest_high) / highest_high
            confidence = min(0.95, 0.5 + breakout_strength * 10 + (vol_ratio - 1) * 0.1)

            if confidence < self.min_confidence:
                continue

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(entry, 2),
                take_profit=round(take_profit, 2),
                stop_loss=round(stop_loss, 2),
                reason=(
                    f"Breakout above {self.breakout_period}-period high "
                    f"({highest_high:.2f}), trail stop at {self.trail_period}-period "
                    f"swing low ({swing_low:.2f}), vol ratio {vol_ratio:.1f}x"
                ),
            ))

        return signals


params = {
    "breakout_period": 20,
    "trail_period": 10,
    "initial_sl_pct": 0.03,
    "min_confidence": 0.55,
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

    strategy = LeapSwingTrail(params)
    sigs = strategy.generate_signals(df)
    print(f"{strategy.NAME}: {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} {s.symbol} @ {s.entry_price} | TP {s.take_profit} | SL {s.stop_loss} | conf {s.confidence} | {s.reason}")
