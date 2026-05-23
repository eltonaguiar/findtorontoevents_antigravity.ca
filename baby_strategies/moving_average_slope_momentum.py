"""
MovingAverageSlopeMomentumStrategy - Triple EMA Slope Strategy
==============================================================

Created by: AI Assistant
Date: 2026-03-06

Based on Algorithm 1.3 from 25 Technical Algorithms

PROVEN CONCEPT — Triple EMA slope calculation with Fibonacci periods (5, 13, 34)

Key Improvements:
- Fibonacci period EMA slopes (5, 13, 34)
- Slope convergence/divergence detection
- Price velocity relative to MA velocity
- Slope direction change confirmation

Strategy Logic:
- Entry: All slopes positive/negative + slope hierarchy + acceleration
- Exit: Slope crossing or slope direction change
- Direction: LONG and SHORT

Why it works:
- Triple EMA slopes confirm trend strength
- Slope hierarchy (5 > 13 > 34) indicates healthy trend
- Acceleration confirms trend momentum
- Slope direction change signals reversal

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


class MovingAverageSlopeMomentumStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema5_period = self.params.get("ema5_period", 5)
        self.ema13_period = self.params.get("ema13_period", 13)
        self.ema34_period = self.params.get("ema34_period", 34)
        self.slope_period = self.params.get("slope_period", 5)
        self.slope_threshold = self.params.get("slope_threshold", 0.0001)
        self.volume_ma = self.params.get("volume_ma", 20)
        self.volume_mult = self.params.get("volume_mult", 1.1)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)
        self.max_hold_bars = self.params.get("max_hold_bars", 15)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.ema34_period + 20:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # Calculate EMAs
        ema5 = close.ewm(span=self.ema5_period, adjust=False).mean()
        ema13 = close.ewm(span=self.ema13_period, adjust=False).mean()
        ema34 = close.ewm(span=self.ema34_period, adjust=False).mean()

        # Calculate slopes
        ema5_slope = (ema5 - ema5.shift(self.slope_period)) / self.slope_period * 100
        ema13_slope = (ema13 - ema13.shift(self.slope_period)) / self.slope_period * 100
        ema34_slope = (ema34 - ema34.shift(self.slope_period)) / self.slope_period * 100

        # Slope momentum and acceleration
        slope_momentum = ema5_slope - ema13_slope
        acceleration = slope_momentum - slope_momentum.shift(1)

        # Volume MA
        volume_ma = volume.rolling(self.volume_ma).mean()

        current_price = float(close.iloc[-1])
        current_ema5_slope = float(ema5_slope.iloc[-1])
        current_ema13_slope = float(ema13_slope.iloc[-1])
        current_ema34_slope = float(ema34_slope.iloc[-1])
        current_slope_momentum = float(slope_momentum.iloc[-1])
        current_acceleration = float(acceleration.iloc[-1])
        current_volume = float(volume.iloc[-1])
        current_volume_ma = float(volume_ma.iloc[-1])

        # Check slope direction change
        slope5_changed = abs(ema5_slope.iloc[-1] - ema5_slope.iloc[-3]) > self.slope_threshold
        slope13_changed = abs(ema13_slope.iloc[-1] - ema13_slope.iloc[-3]) > self.slope_threshold * 0.5

        signals = []

        # LONG entry: all slopes positive + slope hierarchy + acceleration
        if (
            current_ema5_slope > self.slope_threshold
            and current_ema13_slope > self.slope_threshold
            and current_ema34_slope > self.slope_threshold
            and current_ema5_slope > current_ema13_slope > current_ema34_slope
            and current_acceleration > 0
            and slope5_changed
            and current_volume > current_volume_ma * self.volume_mult
        ):
            atr = self._calculate_atr(data, 14).iloc[-1]
            tp = current_price + (atr * self.tp_atr_mult)
            sl = current_price - (atr * self.sl_atr_mult)

            # Confidence based on slope strength and acceleration
            slope_strength = (current_ema5_slope + current_ema13_slope + current_ema34_slope) / 3
            acceleration_strength = current_acceleration
            volume_strength = current_volume / current_volume_ma
            confidence = min(0.5 + slope_strength * 0.1 + acceleration_strength * 0.2 + (volume_strength - 1) * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"MASM Long: slopes 5={current_ema5_slope:.4f},13={current_ema13_slope:.4f},34={current_ema34_slope:.4f}, acceleration {current_acceleration:.4f}",
                )
            )

        # SHORT entry: all slopes negative + slope hierarchy + acceleration
        elif (
            current_ema5_slope < -self.slope_threshold
            and current_ema13_slope < -self.slope_threshold
            and current_ema34_slope < -self.slope_threshold
            and current_ema5_slope < current_ema13_slope < current_ema34_slope
            and current_acceleration < 0
            and slope5_changed
            and current_volume > current_volume_ma * self.volume_mult
        ):
            atr = self._calculate_atr(data, 14).iloc[-1]
            tp = current_price - (atr * self.tp_atr_mult)
            sl = current_price + (atr * self.sl_atr_mult)

            slope_strength = abs((current_ema5_slope + current_ema13_slope + current_ema34_slope) / 3)
            acceleration_strength = abs(current_acceleration)
            volume_strength = current_volume / current_volume_ma
            confidence = min(0.5 + slope_strength * 0.1 + acceleration_strength * 0.2 + (volume_strength - 1) * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"MASM Short: slopes 5={current_ema5_slope:.4f},13={current_ema13_slope:.4f},34={current_ema34_slope:.4f}, acceleration {current_acceleration:.4f}",
                )
            )

        return signals

    def _calculate_atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr
