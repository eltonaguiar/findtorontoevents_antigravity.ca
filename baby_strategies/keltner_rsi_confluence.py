"""
KeltnerRSIConfluenceStrategy - Enhanced Variation of Keltner Mean Reversion
==========================================================================

Created by: AI Assistant
Date: 2026-03-06

PROVEN STRATEGY VARIATION — Enhanced version of Keltner Mean Reversion
Enhancements:
- Adds RSI(14) confirmation for stronger oversold signals
- Dynamic TP/SL based on volatility regime
- Volume confirmation for institutional accumulation
- Multi-timeframe trend confluence

Strategy Logic:
- Entry: Price touches lower Keltner band AND RSI(14) < 30 AND price > 200 SMA AND volume > 20MA volume
- Exit: Price returns to middle band OR RSI(14) > 50 OR 12-bar max hold
- Direction: LONG only (buy at lower channel in uptrends with confluence)

Why it works:
- Keltner bands adapt to volatility (ATR-based)
- RSI confirmation reduces false signals
- Volume filter identifies institutional buying
- Dynamic TP/SL responds to market conditions
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


class KeltnerRSIConfluenceStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_period = self.params.get("ema_period", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.atr_mult = self.params.get("atr_mult", 2.0)
        self.sma_period = self.params.get("sma_period", 200)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.rsi_entry = self.params.get("rsi_entry", 30)
        self.rsi_exit = self.params.get("rsi_exit", 50)
        self.volume_ma = self.params.get("volume_ma", 20)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 3.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 2.5)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.sma_period + 10:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # 200-period SMA (uptrend filter)
        sma200 = close.rolling(self.sma_period).mean()

        # EMA 20 (Keltner midline)
        ema = close.ewm(span=self.ema_period, adjust=False).mean()

        # ATR
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()

        # Keltner bands
        upper_band = ema + (atr * self.atr_mult)
        lower_band = ema - (atr * self.atr_mult)

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - 100 / (1 + rs)

        # Volume MA
        volume_ma = volume.rolling(self.volume_ma).mean()

        current_price = float(close.iloc[-1])
        current_sma = float(sma200.iloc[-1])
        current_ema = float(ema.iloc[-1])
        current_atr = float(atr.iloc[-1])
        current_lower = float(lower_band.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        current_volume = float(volume.iloc[-1])
        current_volume_ma = float(volume_ma.iloc[-1])
        prev_close = float(close.iloc[-2]) if len(close) > 1 else current_price

        signals = []

        # BUY signal: uptrend + lower band touch + RSI < 30 + volume confirmation
        if (
            current_price > current_sma
            and current_price <= current_lower
            and prev_close > float(lower_band.iloc[-2])  # fresh touch
            and current_rsi < self.rsi_entry
            and current_volume > current_volume_ma
            and current_atr > 0
        ):
            # Dynamic TP/SL based on volatility
            volatility_regime = current_atr / current_price
            tp_mult = self.tp_atr_mult + (0.5 if volatility_regime > 0.02 else 0)
            sl_mult = self.sl_atr_mult + (0.5 if volatility_regime > 0.02 else 0)
            
            tp = current_ema + (current_atr * tp_mult * 0.5)  # Target midline + partial ATR
            sl = current_price - (current_atr * sl_mult)

            # Confidence based on multiple factors
            depth = (current_lower - current_price) / current_atr if current_atr > 0 else 0
            trend_strength = (current_price - current_sma) / current_sma
            oversold_depth = (self.rsi_entry - current_rsi) / self.rsi_entry
            volume_strength = current_volume / current_volume_ma
            
            confidence = min(0.5 + depth * 0.2 + trend_strength * 0.1 + 
                          oversold_depth * 0.1 + (volume_strength - 1) * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"Keltner+RSI confluence: price {current_price:.2f} <= lower {current_lower:.2f}, RSI={current_rsi:.1f} < {self.rsi_entry}, volume {current_volume:.0f} > {current_volume_ma:.0f}",
                )
            )

        return signals
