#!/usr/bin/env python3
"""
RSI Prediction by Range Segmentation — Python Port
====================================================

Ported from: LuxAlgo RSI Prediction by Range Segmentation (Pine Script v6)
License: CC BY-NC-SA 4.0 — adapted for non-commercial research
Date: 2026-03-13

Core Concept:
  1. Divide RSI scale (0-100) into N segments (default 10)
  2. For every historical bar, store the RSI path of length L
  3. File each path under the segment where it started
  4. On current bar: look up segment → average all stored paths → forecast
  5. If projected endpoint > current RSI → BULLISH signal

Integration:
  Use as confluence filter for any signal generator. If RSI prediction
  agrees with the trade direction, boost confidence. If it disagrees, skip.
"""

from __future__ import annotations

import math
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore


def _calc_rsi(closes: List[float], period: int = 14) -> List[float]:
    """Calculate RSI series from close prices."""
    rsi = [float('nan')] * len(closes)
    if len(closes) < period + 1:
        return rsi

    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi


class RSIRangePredictor:
    """
    LuxAlgo RSI Prediction by Range Segmentation — Python port.

    Segments the RSI range (0-100) into N horizontal zones. When the current
    RSI value falls into a specific zone, the predictor retrieves all historical
    RSI paths that started in that same zone and computes the average trajectory.

    Usage:
        predictor = RSIRangePredictor(segments=10, forecast_len=50)
        predictor.train_from_closes(close_prices)  # feed 500+ bars
        result = predictor.predict(current_rsi=55.0)
        # result.direction = "BULLISH" | "BEARISH" | "NEUTRAL"
        # result.endpoint = 62.3  (projected RSI endpoint)
        # result.confidence = 0.42
    """

    def __init__(
        self,
        segments: int = 10,
        forecast_len: int = 50,
        history_limit: int = 200,
        rsi_period: int = 14,
        significance_threshold: float = 2.0,
    ):
        self.segments = segments
        self.step = 100.0 / segments
        self.forecast_len = forecast_len
        self.limit = history_limit
        self.rsi_period = rsi_period
        self.significance = significance_threshold
        self.buckets: List[List[List[float]]] = [[] for _ in range(segments)]

    def _clamp_segment(self, rsi_value: float) -> int:
        return max(0, min(self.segments - 1, int(rsi_value / self.step)))

    def train(self, rsi_series: List[float]) -> int:
        """
        Feed historical RSI values to build segment database.
        Returns the total number of patterns stored.
        """
        total = 0
        for i in range(self.forecast_len, len(rsi_series)):
            anchor = rsi_series[i - self.forecast_len]
            if anchor != anchor:  # NaN check
                continue

            seg = self._clamp_segment(anchor)
            pattern = rsi_series[i - self.forecast_len: i + 1]

            # Skip patterns with NaN
            if any(v != v for v in pattern):
                continue

            self.buckets[seg].append(pattern)
            if len(self.buckets[seg]) > self.limit:
                self.buckets[seg].pop(0)
            total += 1

        logger.info("RSI predictor trained: %d patterns across %d segments", total, self.segments)
        return total

    def train_from_closes(self, closes: List[float]) -> int:
        """Calculate RSI from close prices, then train."""
        rsi_series = _calc_rsi(closes, self.rsi_period)
        return self.train(rsi_series)

    def predict(self, current_rsi: float) -> dict:
        """
        Predict future RSI path from current value.

        Returns dict with:
          - endpoint: projected final RSI value
          - direction: "BULLISH" | "BEARISH" | "NEUTRAL"
          - confidence: 0.0-1.0
          - path: list of averaged RSI steps
          - sample_count: how many historical patterns were averaged
          - segment: which RSI segment was matched
        """
        seg = self._clamp_segment(current_rsi)
        history = self.buckets[seg]

        if len(history) < 3:
            return {
                "endpoint": current_rsi,
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "path": [current_rsi],
                "sample_count": len(history),
                "segment": (seg * self.step, (seg + 1) * self.step),
            }

        # Average all historical paths at each step
        max_len = max(len(h) for h in history)
        avg_path = []
        for step in range(max_len):
            vals = [h[step] for h in history if step < len(h)]
            avg_path.append(sum(vals) / len(vals))

        endpoint = avg_path[-1]
        delta = endpoint - current_rsi

        if delta > self.significance:
            direction = "BULLISH"
        elif delta < -self.significance:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Confidence: based on magnitude of move + sample count
        magnitude = min(1.0, abs(delta) / 20.0)  # 20-point swing = max magnitude
        sample_factor = min(1.0, len(history) / 50.0)  # 50+ samples = full factor
        confidence = min(0.95, magnitude * sample_factor * 2.0)

        return {
            "endpoint": round(endpoint, 2),
            "direction": direction,
            "confidence": round(confidence, 4),
            "path": [round(v, 2) for v in avg_path],
            "sample_count": len(history),
            "segment": (round(seg * self.step, 1), round((seg + 1) * self.step, 1)),
        }

    def should_enter(self, current_rsi: float, trade_direction: str) -> Tuple[bool, float]:
        """
        Confluence check: should we enter a trade in this direction?

        Returns (should_enter, confidence_boost).
        confidence_boost is 0.0-0.15 (to add to pick confidence).
        """
        result = self.predict(current_rsi)

        if result["direction"] == "NEUTRAL":
            return True, 0.0  # neutral = don't block, but no boost

        if trade_direction in ("BUY", "LONG") and result["direction"] == "BULLISH":
            return True, result["confidence"] * 0.15  # max +15%

        if trade_direction in ("SELL", "SHORT") and result["direction"] == "BEARISH":
            return True, result["confidence"] * 0.15

        # Disagreement: RSI prediction opposes the trade
        if result["confidence"] > 0.5:
            return False, 0.0  # strong disagreement = block

        return True, 0.0  # weak disagreement = allow but no boost

    def summary(self) -> dict:
        """Return summary of trained model."""
        filled = sum(1 for b in self.buckets if len(b) > 0)
        total = sum(len(b) for b in self.buckets)
        return {
            "segments": self.segments,
            "filled_segments": filled,
            "total_patterns": total,
            "forecast_length": self.forecast_len,
            "segment_ranges": [
                f"{round(i * self.step)}-{round((i+1) * self.step)}: {len(self.buckets[i])} patterns"
                for i in range(self.segments)
            ],
        }


# ── Standalone test ──────────────────────────────────────────────────

def main():
    """Test with live Binance data."""
    import json
    try:
        import requests
    except ImportError:
        print("requests not available")
        return

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
    predictor = RSIRangePredictor(segments=10, forecast_len=50, history_limit=200)

    for sym in symbols:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&limit=500"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            closes = [float(k[4]) for k in data]

            predictor.train_from_closes(closes)
            rsi_series = _calc_rsi(closes, 14)
            current_rsi = rsi_series[-1]

            result = predictor.predict(current_rsi)

            print(f"\n{sym}")
            print(f"  Current RSI: {current_rsi:.1f} (segment {result['segment']})")
            print(f"  Predicted:   {result['endpoint']} → {result['direction']}")
            print(f"  Confidence:  {result['confidence']:.1%}")
            print(f"  Samples:     {result['sample_count']}")

        except Exception as e:
            print(f"  {sym}: Error — {e}")

    print(f"\nModel summary: {json.dumps(predictor.summary(), indent=2)}")


if __name__ == "__main__":
    main()
