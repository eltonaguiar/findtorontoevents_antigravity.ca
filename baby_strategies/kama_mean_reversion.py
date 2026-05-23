"""
KamaMeanReversionStrategy - Baby Strat
=======================================

Created by: Mistral AI
Date: 2026-02-28

Academic Source: Perry Kaufman, "Trading Systems and Methods" (2013), Ch. 17
  KAMA dynamically adjusts smoothing based on market volatility.

Strategy Logic:
- Entry: Price closes below KAMA by z_threshold std devs AND price > 200 SMA
- Exit: ATR-based TP/SL or max hold period
- Direction: LONG only (buy oversold in uptrends)

Why it works:
- KAMA adapts its smoothing period to volatility: responsive in trends, smooth in chop
- Creates a dynamic equilibrium that price oscillates around
- Unlike static RSI/BB, KAMA self-tunes to each asset's volatility profile
- 200 SMA filter avoids bear-market traps

Differentiation from existing survivors:
- Not RSI: Uses KAMA (adaptive MA), not momentum oscillator
- Not Bollinger: KAMA bands adapt via efficiency ratio, not standard deviation
- Not VWAP: Price-based, not volume-weighted
- Not MACD: No momentum crossover; purely mean-reversion around dynamic equilibrium
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


class KamaMeanReversionStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.z_threshold = self.params.get("z_threshold", 1.5)
        self.kama_fast = self.params.get("kama_fast", 2)
        self.kama_slow = self.params.get("kama_slow", 30)
        self.sma_period = self.params.get("sma_period", 200)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 3.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 2.0)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.sma_period + 20:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        # 200 SMA trend filter
        sma200 = close.rolling(self.sma_period).mean()

        # ATR
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()

        # KAMA calculation
        er_period = 10
        change = close.diff().abs()
        volatility = close.diff().abs().rolling(er_period).sum()
        er = change / volatility.replace(0, np.nan)
        fast_sc = 2 / (self.kama_fast + 1)
        slow_sc = 2 / (self.kama_slow + 1)
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

        kama_vals = np.full(len(close), np.nan)
        kama_vals[er_period] = float(close.iloc[er_period])
        for i in range(er_period + 1, len(close)):
            sc_val = float(sc.iloc[i]) if not np.isnan(sc.iloc[i]) else 0
            kama_vals[i] = kama_vals[i - 1] + sc_val * (float(close.iloc[i]) - kama_vals[i - 1])

        kama = pd.Series(kama_vals, index=close.index)

        # Z-score of price deviation from KAMA
        kama_std = kama.rolling(20).std()
        kama_z = (close - kama) / kama_std.replace(0, np.nan)

        current_price = float(close.iloc[-1])
        current_z = float(kama_z.iloc[-1]) if np.isfinite(kama_z.iloc[-1]) else 0
        current_sma = float(sma200.iloc[-1])
        current_atr = float(atr.iloc[-1])
        current_kama = float(kama.iloc[-1]) if np.isfinite(kama.iloc[-1]) else 0

        if current_atr <= 0 or not np.isfinite(current_z):
            return []

        signals = []

        # LONG: price below KAMA by z_threshold std devs + uptrend
        if current_z < -self.z_threshold and current_price > current_sma:
            tp = current_price + self.tp_atr_mult * current_atr
            sl = current_price - self.sl_atr_mult * current_atr
            confidence = min(0.5 + abs(current_z) * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"KAMA z={current_z:.2f} < -{self.z_threshold}, price {current_price:.2f} > SMA200 {current_sma:.2f}, KAMA={current_kama:.2f}",
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

    strategy = KamaMeanReversionStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
