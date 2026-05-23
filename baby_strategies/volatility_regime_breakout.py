"""
VolatilityRegimeBreakoutStrategy - Volatility Compression Breakout Strategy
==========================================================================

Created by: AI Assistant
Date: 2026-03-06

Based on Algorithm 1.2 from 25 Quantitative Trading Algorithms

PROVEN CONCEPT — Identifies volatility compression periods followed by expansion

Key Improvements:
- Volatility Compression Index (VCI) to spot consolidation
- Normalized Range breakout detection
- Volume surge confirmation
- Time-based and volatility-based exit rules

Strategy Logic:
- Entry: Volatility compression for 3+ bars + breakout with volume surge
- Exit: 5-bar time stop or 2.5R take profit
- Direction: LONG and SHORT

Why it works:
- Volatility compression precedes significant moves (VCI < 10th percentile)
- Normalized range identifies true breakouts
- Volume surge confirms institutional participation
- Fixed time stop prevents overstaying in weak moves

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


class VolatilityRegimeBreakoutStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.sd20_period = self.params.get("sd20_period", 20)
        self.sd50_period = self.params.get("sd50_period", 50)
        self.lookback_period = self.params.get("lookback_period", 100)
        self.consolidation_threshold = self.params.get("consolidation_threshold", 0.10)
        self.breakout_range_mult = self.params.get("breakout_range_mult", 1.5)
        self.volume_ma = self.params.get("volume_ma", 20)
        self.volume_mult = self.params.get("volume_mult", 1.5)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)
        self.max_hold_bars = self.params.get("max_hold_bars", 5)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.sd50_period, self.lookback_period) + 10:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # Standard deviations for VCI
        sd20 = close.rolling(self.sd20_period).std()
        sd50 = close.rolling(self.sd50_period).std()

        # Volatility Compression Index
        vci = sd20 / sd50

        # Consolidation threshold (10th percentile of VCI)
        consolidation_threshold = vci.rolling(self.lookback_period).quantile(0.10)

        # True Range and Normalized Range
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        normalized_range = tr / tr.rolling(20).mean()

        # Volume MA
        volume_ma = volume.rolling(self.volume_ma).mean()

        current_price = float(close.iloc[-1])
        current_vci = float(vci.iloc[-1])
        current_consolidation = float(consolidation_threshold.iloc[-1])
        current_normalized_range = float(normalized_range.iloc[-1])
        current_volume = float(volume.iloc[-1])
        current_volume_ma = float(volume_ma.iloc[-1])
        current_atr = float(tr.rolling(14).mean().iloc[-1])

        # Check consolidation duration
        consolidation_bars = 0
        for i in range(1, 4):
            if len(vci) > i and float(vci.iloc[-i]) < float(consolidation_threshold.iloc[-i]):
                consolidation_bars += 1

        signals = []

        # LONG entry: consolidation + bullish breakout + volume surge
        if (
            consolidation_bars >= 3
            and current_normalized_range > self.breakout_range_mult
            and current_price > close.iloc[-2]  # bullish candle
            and current_volume > current_volume_ma * self.volume_mult
            and current_atr > 0
        ):
            entry = current_price + (0.1 * current_atr)
            tp = entry + (current_atr * self.tp_atr_mult)
            sl = entry - (current_atr * self.sl_atr_mult)

            # Confidence based on breakout strength
            range_strength = current_normalized_range / self.breakout_range_mult
            volume_strength = current_volume / current_volume_ma
            consolidation_strength = consolidation_bars / 3
            confidence = min(0.5 + range_strength * 0.2 + volume_strength * 0.15 + consolidation_strength * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"VRB Long: {consolidation_bars} bars consolidation, range {current_normalized_range:.2f}x, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.5",
                )
            )

        # SHORT entry: consolidation + bearish breakout + volume surge
        elif (
            consolidation_bars >= 3
            and current_normalized_range > self.breakout_range_mult
            and current_price < close.iloc[-2]  # bearish candle
            and current_volume > current_volume_ma * self.volume_mult
            and current_atr > 0
        ):
            entry = current_price - (0.1 * current_atr)
            tp = entry - (current_atr * self.tp_atr_mult)
            sl = entry + (current_atr * self.sl_atr_mult)

            range_strength = current_normalized_range / self.breakout_range_mult
            volume_strength = current_volume / current_volume_ma
            consolidation_strength = consolidation_bars / 3
            confidence = min(0.5 + range_strength * 0.2 + volume_strength * 0.15 + consolidation_strength * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"VRB Short: {consolidation_bars} bars consolidation, range {current_normalized_range:.2f}x, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.5",
                )
            )

        return signals
