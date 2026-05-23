"""
CorrKamaRsiTrendStrategy - Baby Strat
=======================================

Created by: Claude AI
Date: 2026-03-04

Confluence strategy: KAMA Adaptive x RSI Momentum
  Trend direction (KAMA) + momentum confirmation (RSI)

Strategy Logic:
- KAMA trend direction: Close > KAMA = uptrend
- RSI momentum: RSI < 40 = pullback in uptrend (buy the dip)
- BUY: Close > KAMA AND RSI < 40 (uptrend pullback)
- SELL: Close < KAMA AND RSI > 60 (downtrend rally)
- TP: +10%, SL: -5%

Why it works:
- KAMA identifies trend with adaptive smoothing (+0.973 corr)
- RSI identifies momentum exhaustion within the trend
- Buying pullbacks in uptrends is one of the most reliable setups
- Selling rallies in downtrends catches mean-reversion within trend
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


def _calc_kama(close: pd.Series, er_period: int = 10, fast: int = 2, slow: int = 30) -> pd.Series:
    change = close.diff().abs()
    volatility = close.diff().abs().rolling(er_period).sum()
    er = change / volatility.replace(0, np.nan)
    fast_sc = 2 / (fast + 1)
    slow_sc = 2 / (slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama_vals = np.full(len(close), np.nan)
    kama_vals[er_period] = float(close.iloc[er_period])
    for i in range(er_period + 1, len(close)):
        sc_val = float(sc.iloc[i]) if not np.isnan(sc.iloc[i]) else 0
        kama_vals[i] = kama_vals[i - 1] + sc_val * (float(close.iloc[i]) - kama_vals[i - 1])

    return pd.Series(kama_vals, index=close.index)


def _calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


class CorrKamaRsiTrendStrategy:
    NAME = "Correlation - KAMA x RSI"
    DESCRIPTION = "KAMA trend direction + RSI momentum confluence"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.er_period = self.params.get("er_period", 10)
        self.kama_fast = self.params.get("kama_fast", 2)
        self.kama_slow = self.params.get("kama_slow", 30)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.rsi_buy_max = self.params.get("rsi_buy_max", 40)
        self.rsi_sell_min = self.params.get("rsi_sell_min", 60)
        self.tp_pct = self.params.get("tp_pct", 0.10)
        self.sl_pct = self.params.get("sl_pct", 0.05)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        min_bars = max(self.er_period + 20, self.rsi_period + 10)
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        kama = _calc_kama(close, self.er_period, self.kama_fast, self.kama_slow)
        rsi = _calc_rsi(close, self.rsi_period)

        current_price = float(close.iloc[-1])
        current_kama = float(kama.iloc[-1])
        current_rsi = float(rsi.iloc[-1])

        if any(np.isnan(x) for x in [current_kama, current_rsi]):
            return []

        kama_pct = (current_price - current_kama) / current_kama
        signals = []

        # BUY: uptrend (price > KAMA) + pullback (RSI < 40)
        if current_price > current_kama and current_rsi < self.rsi_buy_max:
            confidence = min(0.55 + abs(kama_pct) * 3 + (self.rsi_buy_max - current_rsi) / 100, 0.95)
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
                    reason=f"KAMA+RSI trend BUY: price {current_price:.2f} > KAMA {current_kama:.2f}, RSI={current_rsi:.1f} (pullback in uptrend)",
                )
            )

        # SELL: downtrend (price < KAMA) + rally (RSI > 60)
        elif current_price < current_kama and current_rsi > self.rsi_sell_min:
            confidence = min(0.55 + abs(kama_pct) * 3 + (current_rsi - self.rsi_sell_min) / 100, 0.95)
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
                    reason=f"KAMA+RSI trend SELL: price {current_price:.2f} < KAMA {current_kama:.2f}, RSI={current_rsi:.1f} (rally in downtrend)",
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

    strategy = CorrKamaRsiTrendStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
