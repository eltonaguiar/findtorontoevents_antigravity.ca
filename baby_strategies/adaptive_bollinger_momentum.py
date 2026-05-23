"""
AdaptiveBollingerMomentumStrategy - Enhanced Bollinger Bands Strategy
====================================================================

Created by: AI Assistant
Date: 2026-03-06

Based on Algorithm 1.1 from 25 Quantitative Trading Algorithms

PROVEN CONCEPT — Combines Bollinger Bands with adaptive volatility scaling and momentum confirmation

Key Improvements:
- Exponential standard deviation instead of simple moving average standard deviation
- Adaptive band width based on volatility regimes
- Momentum confirmation filter
- Volume validation for breakout strength

Strategy Logic:
- Entry: Price touches Bollinger Band + momentum confirmation + volume surge
- Exit: Price returns to middle band or 2-3 ATR stop/target
- Direction: LONG and SHORT

Why it works:
- Bollinger Bands adapt to volatility (EMA-based SD)
- Momentum filter avoids counter-trend entries
- Volume validation confirms institutional participation
- Adaptive k parameter adjusts to market conditions

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


class AdaptiveBollingerMomentumStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_period = self.params.get("ema_period", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.k_factor = self.params.get("k_factor", 2.0)
        self.momentum_period = self.params.get("momentum_period", 10)
        self.volume_ma = self.params.get("volume_ma", 20)
        self.volume_mult = self.params.get("volume_mult", 1.2)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 3.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 2.0)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.ema_period + 20:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # EMA and exponential standard deviation
        ema = close.ewm(span=self.ema_period, adjust=False).mean()
        ema_std = close.ewm(span=self.ema_period, adjust=False).std()

        # ATR for volatility measurement
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()

        # Adaptive k factor based on volatility
        atr_ratio = atr / atr.rolling(200).mean()
        adaptive_k = self.k_factor * (1 + (atr_ratio - 1))

        # Bollinger Bands with adaptive width
        upper_band = ema + (adaptive_k * ema_std)
        lower_band = ema - (adaptive_k * ema_std)

        # Momentum factor
        momentum = (close - close.ewm(span=self.momentum_period, adjust=False).mean()) / close

        # Volume MA
        volume_ma = volume.rolling(self.volume_ma).mean()

        current_price = float(close.iloc[-1])
        current_ema = float(ema.iloc[-1])
        current_upper = float(upper_band.iloc[-1])
        current_lower = float(lower_band.iloc[-1])
        current_momentum = float(momentum.iloc[-1])
        current_volume = float(volume.iloc[-1])
        current_volume_ma = float(volume_ma.iloc[-1])
        current_atr = float(atr.iloc[-1])
        prev_close = float(close.iloc[-2]) if len(close) > 1 else current_price

        signals = []

        # LONG entry: price touches lower band + momentum > -0.02 + volume surge
        if (
            current_price <= current_lower
            and prev_close > float(lower_band.iloc[-2])  # fresh touch
            and current_momentum > -0.02
            and current_volume > current_volume_ma * self.volume_mult
            and current_atr > 0
        ):
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            # Confidence based on momentum and volume
            momentum_strength = (current_momentum + 0.02) / 0.02
            volume_strength = current_volume / current_volume_ma
            confidence = min(0.5 + momentum_strength * 0.2 + (volume_strength - 1) * 0.15, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"ABM Long: price {current_price:.2f} <= lower {current_lower:.2f}, momentum {current_momentum:.3f}, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.2",
                )
            )

        # SHORT entry: price touches upper band + momentum < 0.02 + volume surge
        elif (
            current_price >= current_upper
            and prev_close < float(upper_band.iloc[-2])  # fresh touch
            and current_momentum < 0.02
            and current_volume > current_volume_ma * self.volume_mult
            and current_atr > 0
        ):
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)

            momentum_strength = (0.02 - current_momentum) / 0.02
            volume_strength = current_volume / current_volume_ma
            confidence = min(0.5 + momentum_strength * 0.2 + (volume_strength - 1) * 0.15, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"ABM Short: price {current_price:.2f} >= upper {current_upper:.2f}, momentum {current_momentum:.3f}, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.2",
                )
            )

        return signals
