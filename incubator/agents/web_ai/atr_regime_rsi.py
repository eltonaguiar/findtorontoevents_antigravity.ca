"""
ATRRegimeRSI - Baby Strat
==========================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when: Low-vol regime (current ATR < rolling ATR avg × threshold) AND RSI < 35
- Exit when: TP = 2.0 × ATR, SL = 1.5 × ATR
- Risk management: Volatility regime check BEFORE any RSI signal (prevents whipsaws)

Unique Value Proposition:
Standard RSI < 30/70 (5+ duplicates in inventory) and basic momentum get destroyed
in high-vol ranging markets. This puts volatility regime detection first
(white-space risk-adjusted category) — no MA crossover, no plain Bollinger,
no simple momentum. Pure gatekeeper + mean-reversion combo.

Expected Regime: Ranging/low-volatility (calm mean-reversion setups with
smart-money accumulation). Avoids trending or high-vol chop.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str           # e.g., "BTCUSDT"
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 to 1.0
    entry_price: float    # Suggested entry
    take_profit: float    # Target price
    stop_loss: float      # Stop price
    reason: str           # Why this signal


class ATRRegimeRSIStrategy:
    """
    Low-vol regime filter + RSI mean-reversion.

    Detects low-volatility regimes with ATR first (risk-adjusted gatekeeper),
    then triggers mean-reversion BUY only on oversold RSI. Skips all signals
    in choppy high-vol periods.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data, symbol): Return List[Signal]
    """

    def __init__(self, params: Optional[Dict] = None):
        """
        Define all tunable parameters here.

        Args:
            params: Dictionary of parameters
        """
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_threshold = self.params.get('rsi_threshold', 35)
        self.atr_period = self.params.get('atr_period', 14)
        self.regime_lookback = self.params.get('regime_lookback', 50)
        self.vol_threshold = self.params.get('vol_threshold', 1.2)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main signal generation method.

        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair being analyzed

        Returns:
            List of Signal objects (empty if no signal)
        """
        # Validate minimum data length
        min_len = self.regime_lookback + self.atr_period + self.rsi_period + 10
        if len(data) < min_len:
            return []

        # Calculate indicators
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        atr_ma = atr.rolling(self.regime_lookback).mean()

        # Current values
        current_rsi = rsi.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        current_atr_ma = atr_ma.iloc[-1]
        if pd.isna(current_atr_ma):
            current_atr_ma = current_atr

        # STEP 1: Volatility regime gatekeeper (checked FIRST)
        is_low_vol = (
            (current_atr / current_atr_ma) < self.vol_threshold
            if current_atr_ma > 0
            else False
        )

        # STEP 2: Only check RSI if we're in a low-vol regime
        if is_low_vol and current_rsi < self.rsi_threshold:
            confidence = min(
                (self.rsi_threshold - current_rsi) / self.rsi_threshold * 0.8 + 0.2,
                0.95
            )
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"LowVol ATRratio={current_atr / current_atr_ma:.2f} RSI={current_rsi:.1f}"
            )]

        return []

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range."""
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


# ==============================================================================
# TESTING - Required: Verify your strategy works
# ==============================================================================

if __name__ == "__main__":
    """Quick test with synthetic data."""

    # Create synthetic OHLCV data
    np.random.seed(42)
    n = 200
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))

    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })

    # Test strategy
    strategy = ATRRegimeRSIStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
