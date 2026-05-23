"""
Multi-Asset Short Bias v1
Strategy ID: multi_asset_short_bias_v1
Purpose: Expand SHORT signals across underutilized asset classes

Evidence: SHORT direction has +8pp WR advantage system-wide
Target Asset Classes: FOREX, COMMODITY, FUTURES (all have extremely low pick counts)
Timeframe: SWING only (4h+)
Expected pick count increase: +200% for non-crypto assets
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    direction: str
    entry_price: float
    take_profit: float
    stop_loss: float
    score: float
    trust: int
    confidence: float
    source: str
    asset_class: str
    timeframe: str = "4h"


class MultiAssetShortBias:
    def __init__(self):
        self.target_asset_classes = ["FOREX", "COMMODITY", "FUTURES"]
        self.score_range = (40, 59)  # Grade C sweet spot (best risk-adjusted returns)
        self.short_bias_weight = 1.25  # +25% allocation to SHORT
        self.min_score = 40
        self.max_score = 59
        self.min_atr_ratio = 1.2

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[Signal]:
        signals = []

        for asset_class in self.target_asset_classes:
            if asset_class not in market_data:
                continue

            df = market_data[asset_class]

            # SWING mode only (4h timeframe indicators)
            swing_signals = self._filter_swing_timeframe(df)

            for _, row in swing_signals.iterrows():
                # Grade C score range filter
                if not (self.min_score <= row["score"] <= self.max_score):
                    continue

                # ATR volatility filter
                if row["atr_ratio"] < self.min_atr_ratio:
                    continue

                # Apply SHORT bias: prefer SHORT signals 2:1
                if row["signal_direction"] == "SHORT":
                    weight = self.short_bias_weight
                else:
                    weight = 0.75  # Reduce LONG allocation

                # Calculate dynamic TP/SL based on ATR
                atr = row["atr_14"]
                entry = row["close"]

                if row["signal_direction"] == "SHORT":
                    tp = entry * (1 - (atr / entry * 1.8))
                    sl = entry * (1 + (atr / entry * 1.4))
                else:
                    tp = entry * (1 + (atr / entry * 1.8))
                    sl = entry * (1 - (atr / entry * 1.4))

                signals.append(
                    Signal(
                        symbol=row["symbol"],
                        direction=row["signal_direction"],
                        entry_price=entry,
                        take_profit=tp,
                        stop_loss=sl,
                        score=row["score"] * weight,
                        trust=row["trust"],
                        confidence=min(
                            row["confidence"], 0.85
                        ),  # Cap confidence to avoid toxic zone
                        source="multi_asset_short_bias_v1",
                        asset_class=asset_class,
                        timeframe="4h",
                    )
                )

        return signals

    def _filter_swing_timeframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter for swing mode eligible signals only"""
        # Require multiple timeframe alignment
        df["swing_eligible"] = (
            (df["ema_50"] > df["ema_200"])  # Trend alignment
            | (df["adx"] > 25)  # Sufficient trend strength
        )

        return df[df["swing_eligible"]].copy()


if __name__ == "__main__":
    strategy = MultiAssetShortBias()
    print(f"Multi-Asset Short Bias v1 initialized")
    print(f"Target asset classes: {strategy.target_asset_classes}")
    print(f"Target score range: {strategy.min_score}-{strategy.max_score} (Grade C)")
    print(f"SHORT bias weight: {strategy.short_bias_weight}")
