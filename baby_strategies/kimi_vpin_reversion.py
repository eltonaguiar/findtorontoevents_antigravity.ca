"""
KimiVpinReversionStrategy - Baby Strat
=======================================

Created by: Claude AI
Date: 2026-03-04

Academic Source: Easley, Lopez de Prado & O'Hara (2012),
  "Flow Toxicity and Liquidity in a High-Frequency World"
  Renaissance-style statistical arbitrage via VPIN metric.

Strategy Logic:
- VPIN = |buy_vol - sell_vol| / total_vol over rolling 20 bars
  - buy_vol = volume * (close - low) / (high - low)
  - sell_vol = volume - buy_vol
- Z-Score = (close - EMA(close, 20)) / rolling_std(close, 20)
- Entry BUY:  Z-score < -2.0 AND VPIN < 0.5 (clean flow, oversold)
- Entry SELL: Z-score > +2.0 AND VPIN < 0.5 (clean flow, overbought)
- Skip when VPIN > 0.6 (toxic flow regime)
- TP: +6%, SL: -3% (2*ATR proxy)

Why it works:
- VPIN detects informed trading (toxic flow) before volatility spikes
- Low VPIN + extreme Z-score = dislocation in clean market = high reversion probability
- Avoids entries when smart money is actively pushing price (high VPIN)
- Combines microstructure (VPIN) with statistical (Z-score) for robust edge
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


def calc_vpin(high: pd.Series, low: pd.Series, close: pd.Series,
              volume: pd.Series, period: int = 20) -> pd.Series:
    """Volume-Synchronized Probability of Informed Trading (approximation)."""
    price_range = high - low
    price_range = price_range.replace(0, np.nan)
    buy_vol = volume * (close - low) / price_range
    sell_vol = volume - buy_vol
    abs_diff = (buy_vol - sell_vol).abs()
    vpin = abs_diff.rolling(period).sum() / volume.rolling(period).sum()
    return vpin


def calc_zscore(close: pd.Series, period: int = 20) -> pd.Series:
    """Z-score of close relative to its EMA and rolling std."""
    ema = close.ewm(span=period, adjust=False).mean()
    std = close.rolling(period).std()
    std = std.replace(0, np.nan)
    return (close - ema) / std


class KimiVpinReversionStrategy:
    NAME = "Kimi VPIN Reversion"
    DESCRIPTION = "VPIN flow toxicity filter + Z-score mean reversion (Easley/O'Hara 2012)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vpin_period = self.params.get("vpin_period", 20)
        self.zscore_period = self.params.get("zscore_period", 20)
        self.zscore_entry = self.params.get("zscore_entry", 2.0)
        self.vpin_clean = self.params.get("vpin_clean", 0.5)
        self.vpin_toxic = self.params.get("vpin_toxic", 0.6)
        self.tp_pct = self.params.get("tp_pct", 0.06)
        self.sl_pct = self.params.get("sl_pct", 0.03)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        min_bars = max(self.vpin_period, self.zscore_period) + 10
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        vpin = calc_vpin(high, low, close, volume, self.vpin_period)
        zscore = calc_zscore(close, self.zscore_period)

        current_price = float(close.iloc[-1])
        current_vpin = float(vpin.iloc[-1])
        current_z = float(zscore.iloc[-1])

        if np.isnan(current_vpin) or np.isnan(current_z):
            return []

        # Skip toxic flow regime
        if current_vpin > self.vpin_toxic:
            return []

        signals = []

        if current_z < -self.zscore_entry and current_vpin < self.vpin_clean:
            confidence = min(0.5 + abs(current_z) * 0.1 + (self.vpin_clean - current_vpin), 0.95)
            tp = current_price * (1 + self.tp_pct)
            sl = current_price * (1 - self.sl_pct)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"VPIN reversion BUY: Z={current_z:.2f} < -{self.zscore_entry}, VPIN={current_vpin:.3f} (clean flow)",
                )
            )
        elif current_z > self.zscore_entry and current_vpin < self.vpin_clean:
            confidence = min(0.5 + abs(current_z) * 0.1 + (self.vpin_clean - current_vpin), 0.95)
            tp = current_price * (1 - self.tp_pct)
            sl = current_price * (1 + self.sl_pct)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"VPIN reversion SELL: Z={current_z:.2f} > +{self.zscore_entry}, VPIN={current_vpin:.3f} (clean flow)",
                )
            )

        return signals


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))

    test_data = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.001, n)),
            "high": prices * (1 + abs(np.random.normal(0, 0.01, n))),
            "low": prices * (1 - abs(np.random.normal(0, 0.01, n))),
            "close": prices,
            "volume": np.random.uniform(100, 1000, n),
        }
    )

    strategy = KimiVpinReversionStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
