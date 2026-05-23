"""
KamaVolatilityAdaptiveStrategy - Kaufman Adaptive Moving Average System
======================================================================

Created by: AI Assistant
Date: 2026-03-06

Based on Algorithm 1.1 from 25 Technical Algorithms

PROVEN CONCEPT — Kaufman Adaptive Moving Average (KAMA) with Efficiency Ratio (ER) and ATR volatility bands

Key Improvements:
- KAMA adapts to market efficiency
- Efficiency Ratio (ER) measures trend strength
- ATR-based volatility bands
- Volume-weighted price momentum confirmation

Strategy Logic:
- Entry: Price crosses KAMA ± ATR band + ER > 0.6 + volume surge
- Exit: 2.5R take profit or KAMA ± 1.5 ATR stop
- Direction: LONG and SHORT

Why it works:
- KAMA adapts to volatility (fast in trends, slow in ranges)
- ER confirms trend efficiency
- Volume validation ensures breakout strength
- Dynamic bands adjust to market conditions

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


class KamaVolatilityAdaptiveStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.kama_period = self.params.get("kama_period", 10)
        self.fastest = self.params.get("fastest", 0.666)
        self.slowest = self.params.get("slowest", 0.0645)
        self.atr_period = self.params.get("atr_period", 14)
        self.band_mult = self.params.get("band_mult", 0.5)
        self.er_threshold = self.params.get("er_threshold", 0.6)
        self.volume_ma = self.params.get("volume_ma", 20)
        self.volume_mult = self.params.get("volume_mult", 1.2)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)
        self.max_hold_bars = self.params.get("max_hold_bars", 10)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.kama_period + 20:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # KAMA calculation
        kama = self._calculate_kama(close, self.kama_period, self.fastest, self.slowest)

        # Efficiency Ratio (ER)
        er = self._calculate_er(close, self.kama_period)

        # ATR for volatility bands
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()

        # KAMA volatility bands
        upper_band = kama + (atr * self.band_mult)
        lower_band = kama - (atr * self.band_mult)

        # Volume MA
        volume_ma = volume.rolling(self.volume_ma).mean()

        current_price = float(close.iloc[-1])
        current_kama = float(kama.iloc[-1])
        current_upper = float(upper_band.iloc[-1])
        current_lower = float(lower_band.iloc[-1])
        current_er = float(er.iloc[-1])
        current_volume = float(volume.iloc[-1])
        current_volume_ma = float(volume_ma.iloc[-1])
        current_atr = float(atr.iloc[-1])
        prev_price = float(close.iloc[-2]) if len(close) > 1 else current_price

        signals = []

        # LONG entry: price crosses above upper band + ER > 0.6 + volume surge
        if (
            current_price > current_upper
            and prev_price <= float(upper_band.iloc[-2])  # fresh cross
            and current_er > self.er_threshold
            and current_volume > current_volume_ma * self.volume_mult
            and current_atr > 0
        ):
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_kama - (current_atr * self.sl_atr_mult)

            # Confidence based on ER and volume
            er_strength = (current_er - self.er_threshold) / (1 - self.er_threshold)
            volume_strength = current_volume / current_volume_ma
            confidence = min(0.5 + er_strength * 0.3 + (volume_strength - 1) * 0.15, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"KAMAS Long: price {current_price:.2f} > KAMA+band {current_upper:.2f}, ER={current_er:.2f} > 0.6, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.2",
                )
            )

        # SHORT entry: price crosses below lower band + ER > 0.6 + volume surge
        elif (
            current_price < current_lower
            and prev_price >= float(lower_band.iloc[-2])  # fresh cross
            and current_er > self.er_threshold
            and current_volume > current_volume_ma * self.volume_mult
            and current_atr > 0
        ):
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_kama + (current_atr * self.sl_atr_mult)

            er_strength = (current_er - self.er_threshold) / (1 - self.er_threshold)
            volume_strength = current_volume / current_volume_ma
            confidence = min(0.5 + er_strength * 0.3 + (volume_strength - 1) * 0.15, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"KAMAS Short: price {current_price:.2f} < KAMA-band {current_lower:.2f}, ER={current_er:.2f} > 0.6, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.2",
                )
            )

        return signals

    def _calculate_kama(self, close: pd.Series, period: int, fastest: float, slowest: float) -> pd.Series:
        """Calculate Kaufman Adaptive Moving Average"""
        er = self._calculate_er(close, period)
        sc = (er * (fastest - slowest) + slowest) ** 2
        
        kama = pd.Series(index=close.index, dtype=float)
        kama.iloc[period-1] = close.iloc[period-1]
        
        for i in range(period, len(close)):
            kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (close.iloc[i] - kama.iloc[i-1])
        
        return kama

    def _calculate_er(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate Efficiency Ratio"""
        price_change = abs(close - close.shift(period))
        volatility = close.diff().abs().rolling(period).sum()
        er = price_change / volatility
        er = er.replace([np.inf, -np.inf], np.nan).fillna(0)
        return er
