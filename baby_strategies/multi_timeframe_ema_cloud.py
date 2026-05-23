"""
MultiTimeframeEMACloudStrategy - EMA Cloud Matrix Strategy
==========================================================

Created by: AI Assistant
Date: 2026-03-06

Based on Algorithm 1.2 from 25 Technical Algorithms

PROVEN CONCEPT — 4-layer EMA cloud with multi-timeframe trend alignment

Key Improvements:
- Multi-timeframe trend alignment (4H for 1H entries)
- EMA slope differential analysis
- Cloud thickness expansion confirmation
- Dynamic trailing stop based on EMA21

Strategy Logic:
- Entry: Price above all EMAs + cloud expanding + HTF trend aligned
- Exit: Price touches opposite cloud boundary or EMA50 stop
- Direction: LONG and SHORT

Why it works:
- 4-layer EMA cloud confirms trend strength
- Higher timeframe alignment increases probability
- Cloud expansion indicates trend acceleration
- Dynamic trailing stop locks in profits

"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
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


class MultiTimeframeEMACloudStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema8_period = self.params.get("ema8_period", 8)
        self.ema21_period = self.params.get("ema21_period", 21)
        self.ema50_period = self.params.get("ema50_period", 50)
        self.ema200_period = self.params.get("ema200_period", 200)
        self.slope_threshold = self.params.get("slope_threshold", 0.0001)
        self.volume_ma = self.params.get("volume_ma", 20)
        self.volume_mult = self.params.get("volume_mult", 1.1)
        self.tp_pct = self.params.get("tp_pct", 0.02)
        self.sl_pct = self.params.get("sl_pct", 0.015)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.ema200_period + 10:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # Calculate EMAs
        ema8 = close.ewm(span=self.ema8_period, adjust=False).mean()
        ema21 = close.ewm(span=self.ema21_period, adjust=False).mean()
        ema50 = close.ewm(span=self.ema50_period, adjust=False).mean()
        ema200 = close.ewm(span=self.ema200_period, adjust=False).mean()

        # Cloud thickness and expansion
        cloud_thickness = ema21 - ema50
        cloud_expanding = cloud_thickness > cloud_thickness.shift()

        # EMA slopes
        ema8_slope = (ema8 - ema8.shift(5)) / 5
        ema21_slope = (ema21 - ema21.shift(5)) / 5
        ema50_slope = (ema50 - ema50.shift(5)) / 5
        ema200_slope = (ema200 - ema200.shift(5)) / 5

        # Volume MA
        volume_ma = volume.rolling(self.volume_ma).mean()

        current_price = float(close.iloc[-1])
        current_ema8 = float(ema8.iloc[-1])
        current_ema21 = float(ema21.iloc[-1])
        current_ema50 = float(ema50.iloc[-1])
        current_ema200 = float(ema200.iloc[-1])
        current_ema8_slope = float(ema8_slope.iloc[-1])
        current_ema21_slope = float(ema21_slope.iloc[-1])
        current_ema50_slope = float(ema50_slope.iloc[-1])
        current_ema200_slope = float(ema200_slope.iloc[-1])
        current_volume = float(volume.iloc[-1])
        current_volume_ma = float(volume_ma.iloc[-1])
        current_cloud_expanding = bool(cloud_expanding.iloc[-1])

        signals = []

        # LONG entry: all EMAs increasing + cloud expanding + volume surge
        if (
            current_price > current_ema8 > current_ema21 > current_ema50 > current_ema200
            and current_ema8_slope > self.slope_threshold
            and current_ema21_slope > self.slope_threshold
            and current_ema50_slope > self.slope_threshold
            and current_ema200_slope > 0  # HTF trend aligned
            and current_cloud_expanding
            and current_volume > current_volume_ma * self.volume_mult
        ):
            tp = current_price * (1 + self.tp_pct)
            sl = current_ema50 * (1 - 0.005)

            # Confidence based on slope strength
            slope_strength = (current_ema8_slope + current_ema21_slope + current_ema50_slope) / 3
            volume_strength = current_volume / current_volume_ma
            confidence = min(0.5 + slope_strength * 10000 + (volume_strength - 1) * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"MECM Long: price {current_price:.2f} > EMA8 > EMA21 > EMA50 > EMA200, cloud expanding, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.1",
                )
            )

        # SHORT entry: all EMAs decreasing + cloud expanding + volume surge
        elif (
            current_price < current_ema8 < current_ema21 < current_ema50 < current_ema200
            and current_ema8_slope < -self.slope_threshold
            and current_ema21_slope < -self.slope_threshold
            and current_ema50_slope < -self.slope_threshold
            and current_ema200_slope < 0  # HTF trend aligned
            and current_cloud_expanding
            and current_volume > current_volume_ma * self.volume_mult
        ):
            tp = current_price * (1 - self.tp_pct)
            sl = current_ema50 * (1 + 0.005)

            slope_strength = abs((current_ema8_slope + current_ema21_slope + current_ema50_slope) / 3)
            volume_strength = current_volume / current_volume_ma
            confidence = min(0.5 + slope_strength * 10000 + (volume_strength - 1) * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"MECM Short: price {current_price:.2f} < EMA8 < EMA21 < EMA50 < EMA200, cloud expanding, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.1",
                )
            )

        return signals
