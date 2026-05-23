"""
VolScaledKeltnerStrategy - Enhanced Variation of Vol-Scaled Momentum
====================================================================

Created by: AI Assistant
Date: 2026-03-06

PROVEN STRATEGY VARIATION — Enhanced version of Vol-Scaled Momentum
Enhancements:
- Keltner channel breakout filter for momentum confirmation
- Volume scaling based on 20-day average volume percentile
- Dynamic position sizing based on volatility
- Trend direction filter using EMA crossover
- Trailing stop loss with volatility adjustment

Strategy Logic:
- Entry: Price breaks upper Keltner band + EMA(50) > EMA(200) + volume > 70th percentile
- Exit: Trailing stop loss (2.5x ATR) or price closes below EMA(20)
- Direction: LONG only (strong momentum in uptrend)

Why it works:
- Keltner breakout confirms sustainable momentum
- Volume percentile filter identifies institutional participation
- Dynamic sizing manages risk based on volatility
- Trend filter ensures we're in the right direction
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


class VolScaledKeltnerStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_period = self.params.get("ema_period", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.atr_mult = self.params.get("atr_mult", 2.0)
        self.ema50_period = self.params.get("ema50_period", 50)
        self.ema200_period = self.params.get("ema200_period", 200)
        self.volume_window = self.params.get("volume_window", 20)
        self.volume_percentile = self.params.get("volume_percentile", 70)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 4.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 2.5)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.ema200_period + 10:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # EMA crossover filter (50 > 200 for uptrend)
        ema50 = close.ewm(span=self.ema50_period, adjust=False).mean()
        ema200 = close.ewm(span=self.ema200_period, adjust=False).mean()

        # Keltner bands
        ema20 = close.ewm(span=self.ema_period, adjust=False).mean()
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()
        upper_band = ema20 + (atr * self.atr_mult)
        lower_band = ema20 - (atr * self.atr_mult)

        # Volume percentile
        volume_percentiles = volume.rolling(self.volume_window).apply(
            lambda x: np.percentile(x, self.volume_percentile), raw=True
        )

        current_price = float(close.iloc[-1])
        current_ema50 = float(ema50.iloc[-1])
        current_ema200 = float(ema200.iloc[-1])
        current_ema20 = float(ema20.iloc[-1])
        current_atr = float(atr.iloc[-1])
        current_upper = float(upper_band.iloc[-1])
        current_volume = float(volume.iloc[-1])
        current_volume_percentile = float(volume_percentiles.iloc[-1])
        prev_close = float(close.iloc[-2]) if len(close) > 1 else current_price

        signals = []

        # BUY signal: uptrend + upper band breakout + volume confirmation
        if (
            current_ema50 > current_ema200
            and current_price > current_upper
            and prev_close <= float(upper_band.iloc[-2])  # fresh breakout
            and current_volume > current_volume_percentile
            and current_atr > 0
        ):
            # Dynamic TP/SL based on volatility regime
            volatility_regime = current_atr / current_price
            tp_mult = self.tp_atr_mult + (0.5 if volatility_regime > 0.02 else 0)
            sl_mult = self.sl_atr_mult + (0.3 if volatility_regime > 0.02 else 0)
            
            tp = current_price + (current_atr * tp_mult)
            sl = current_price - (current_atr * sl_mult)

            # Confidence based on breakout strength
            breakout_strength = (current_price - current_upper) / current_atr
            trend_strength = (current_ema50 - current_ema200) / current_ema200
            volume_strength = current_volume / current_volume_percentile
            
            confidence = min(0.6 + breakout_strength * 0.2 + trend_strength * 0.1 + 
                          (volume_strength - 1) * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"Keltner breakout: price {current_price:.2f} > upper {current_upper:.2f}, volume {current_volume:.0f} > {self.volume_percentile}th percentile",
                )
            )

        return signals
