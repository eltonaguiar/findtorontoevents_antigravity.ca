"""
Leap - Fee Aware Sniper
Inspired by Blasik (4th place in TradingView "The Leap") — fee management insight.
Only takes highest-conviction setups: RSI extreme + volume spike + trend alignment.
Very few signals, very high confidence. Minimum confidence 0.75.
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


class LeapFeeAwareSniper:
    NAME = "Leap - Fee Aware Sniper"
    DESCRIPTION = (
        "Highest-conviction only: RSI extreme (<25/>75) + volume spike (>2x avg) + "
        "trend alignment (close vs SMA). Inspired by Blasik (4th place). "
        "TP +18%, SL -5%. Min confidence 0.75."
    )

    def __init__(self, params: Optional[dict] = None):
        defaults = {
            "rsi_period": 14,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "volume_mult": 2.0,
            "volume_avg_period": 20,
            "sma_period": 50,
            "tp_pct": 0.18,
            "sl_pct": 0.05,
            "min_confidence": 0.75,
        }
        p = {**defaults, **(params or {})}
        self.rsi_period = int(p["rsi_period"])
        self.rsi_oversold = float(p["rsi_oversold"])
        self.rsi_overbought = float(p["rsi_overbought"])
        self.volume_mult = float(p["volume_mult"])
        self.volume_avg_period = int(p["volume_avg_period"])
        self.sma_period = int(p["sma_period"])
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
        required = max(self.sma_period, self.volume_avg_period, self.rsi_period) + 5
        if len(data) < required:
            return signals

        closes = data["close"].values
        volumes = data["volume"].values if "volume" in data.columns else np.ones(len(data))

        rsi = self._rsi(closes, self.rsi_period)
        sma = pd.Series(closes).rolling(self.sma_period).mean().values

        for i in range(required, len(data)):
            if np.isnan(rsi[i]) or np.isnan(sma[i]):
                continue

            close = closes[i]
            current_rsi = rsi[i]

            # Gate 1: RSI extreme
            is_oversold = current_rsi < self.rsi_oversold
            is_overbought = current_rsi > self.rsi_overbought
            if not is_oversold and not is_overbought:
                continue

            # Gate 2: Volume spike
            avg_vol = np.mean(volumes[i - self.volume_avg_period : i])
            if avg_vol == 0:
                continue
            vol_ratio = volumes[i] / avg_vol
            if vol_ratio < self.volume_mult:
                continue

            # Gate 3: Trend alignment
            above_sma = close > sma[i]
            below_sma = close < sma[i]

            direction = None
            confluence_parts = []

            if is_oversold and above_sma:
                # Oversold in uptrend = buy the dip
                direction = "BUY"
                confluence_parts.append(f"RSI {current_rsi:.1f} < {self.rsi_oversold} (extreme oversold)")
                confluence_parts.append(f"Volume {vol_ratio:.1f}x avg (spike)")
                confluence_parts.append(f"Price above {self.sma_period}-SMA (uptrend)")
            elif is_overbought and below_sma:
                # Overbought in downtrend = sell the rally
                direction = "SELL"
                confluence_parts.append(f"RSI {current_rsi:.1f} > {self.rsi_overbought} (extreme overbought)")
                confluence_parts.append(f"Volume {vol_ratio:.1f}x avg (spike)")
                confluence_parts.append(f"Price below {self.sma_period}-SMA (downtrend)")

            if direction is None:
                continue

            entry = close
            if direction == "BUY":
                tp = entry * (1 + self.tp_pct)
                sl = entry * (1 - self.sl_pct)
            else:
                tp = entry * (1 - self.tp_pct)
                sl = entry * (1 + self.sl_pct)

            # Confidence: all three filters passed, score by extremity
            rsi_extremity = abs(current_rsi - 50) / 50
            vol_score = min(1.0, (vol_ratio - self.volume_mult) / 3)
            sma_dist = abs(close - sma[i]) / sma[i]
            confidence = min(0.95, 0.70 + rsi_extremity * 0.1 + vol_score * 0.1 + sma_dist * 2)

            if confidence < self.min_confidence:
                continue

            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(entry, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=" + ".join(confluence_parts),
            ))

        return signals


params = {
    "rsi_period": 14,
    "rsi_oversold": 25,
    "rsi_overbought": 75,
    "volume_mult": 2.0,
    "volume_avg_period": 20,
    "sma_period": 50,
    "tp_pct": 0.18,
    "sl_pct": 0.05,
    "min_confidence": 0.75,
}

if __name__ == "__main__":
    np.random.seed(42)
    n = 120
    base = 60000 + np.cumsum(np.random.randn(n) * 300)
    # Create volume with occasional spikes
    vol = np.random.uniform(100, 500, n)
    spike_indices = np.random.choice(n, size=10, replace=False)
    vol[spike_indices] *= 4

    df = pd.DataFrame({
        "open": base,
        "high": base + np.abs(np.random.randn(n) * 200),
        "low": base - np.abs(np.random.randn(n) * 200),
        "close": base + np.random.randn(n) * 100,
        "volume": vol,
    })

    strategy = LeapFeeAwareSniper(params)
    sigs = strategy.generate_signals(df)
    print(f"{strategy.NAME}: {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} {s.symbol} @ {s.entry_price} | TP {s.take_profit} | SL {s.stop_loss} | conf {s.confidence} | {s.reason}")
