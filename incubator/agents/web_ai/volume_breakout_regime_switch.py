"""
VolumeBreakout_RegimeSwitch - Baby Strat
========================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when: Volume spikes > 3x 20-bar average and price breaks prior 5-bar high
- Exit when: TP at +3% target or SL at -1.5%
- Risk filter: Only fires on low-volume -> high-volume regime transitions

Unique Value Proposition:
Focuses on transition dynamics (quiet -> active) instead of absolute volume
thresholds alone, aiming to catch early breakout phases before crowded entries.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class VolumeBreakoutRegimeStrategy:
    """Volume regime shift breakout detection."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.vol_lookback = self.p.get("vol_lookback", 20)
        self.price_lookback = self.p.get("price_lookback", 5)
        self.vol_spike = self.p.get("vol_spike", 3.0)
        self.vol_fade = self.p.get("vol_fade", 1.5)
        self.confidence_base = self.p.get("confidence", 0.75)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.vol_lookback, self.price_lookback) + 6
        if len(data) < min_len:
            return []

        required_cols = {"close", "high", "volume"}
        if not required_cols.issubset(set(data.columns)):
            return []

        # Exclude current bar to avoid look-ahead on baseline statistics.
        volume_avg = data["volume"].shift(1).rolling(self.vol_lookback).mean()
        breakout_high = data["high"].shift(1).rolling(self.price_lookback).max()

        current_price = data["close"].iloc[-1]
        current_volume = data["volume"].iloc[-1]
        current_vol_avg = volume_avg.iloc[-1]
        prior_breakout_high = breakout_high.iloc[-1]

        if pd.isna(current_vol_avg) or current_vol_avg <= 0 or pd.isna(prior_breakout_high):
            return []

        # Regime transition: last 5 bars were quiet vs long baseline.
        recent_quiet_ratio = data["volume"].iloc[-6:-1].mean() / current_vol_avg
        quiet_before = recent_quiet_ratio < 0.8

        vol_ratio = current_volume / current_vol_avg
        vol_regime = vol_ratio > self.vol_spike
        price_breakout = current_price >= prior_breakout_high

        if vol_regime and price_breakout and quiet_before:
            confidence_boost = min((vol_ratio - self.vol_spike) / 2.0, 0.2)
            confidence = min(0.95, self.confidence_base + confidence_boost)
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price * 1.03, 2),
                stop_loss=round(current_price * 0.985, 2),
                reason=f"RegimeShift vol={vol_ratio:.1f}x break={prior_breakout_high:,.0f} quiet={recent_quiet_ratio:.2f}x",
            )]

        return []


if __name__ == "__main__":
    np.random.seed(42)
    n = 220
    returns = np.random.normal(0.0002, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    volume = np.random.lognormal(mean=9.0, sigma=0.6, size=n)
    # Inject occasional spikes.
    spike_idx = np.random.choice(np.arange(30, n), size=12, replace=False)
    volume[spike_idx] *= np.random.uniform(2.5, 5.0, size=len(spike_idx))

    test_data = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.01, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.01, n))),
        "close": prices,
        "volume": volume,
    })

    # Force a deterministic quiet -> spike breakout transition on final bar.
    quiet_slice = slice(n - 6, n - 1)
    test_data.loc[test_data.index[quiet_slice], "volume"] = test_data["volume"].iloc[-30:-10].mean() * 0.6
    prior_high = test_data["high"].iloc[-6:-1].max()
    test_data.loc[test_data.index[-1], "close"] = prior_high * 1.01
    test_data.loc[test_data.index[-1], "high"] = prior_high * 1.02
    baseline = test_data["volume"].iloc[-21:-1].mean()
    test_data.loc[test_data.index[-1], "volume"] = baseline * 3.8

    strategy = VolumeBreakoutRegimeStrategy()
    signals = []
    for i in range(60, len(test_data)):
        signals.extend(strategy.generate_signals(test_data.iloc[: i + 1], "BTCUSDT"))

    print(f"Signals: {len(signals)}")
    for sig in signals[:3]:
        print(f"{sig.direction} {sig.symbol} - {sig.reason}")
