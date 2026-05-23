"""
VerifiedStochRsiStrategy - Baby Strat
======================================

Created by: Claude AI
Date: 2026-03-04

Source: QuantifiedStrategies, 78% WR, 228 trades

Strategy Logic:
- StochRSI: RSI(14), then Stochastic(14) of RSI, K smoothed by 3, D = SMA(K, 3)
- Long: StochRSI K crosses above D below 20
- Short: StochRSI K crosses below D above 80
- TP: +8% / SL: -4%

Why it works:
- RSI alone is noisy; applying stochastic to RSI amplifies extreme readings
- 78% WR over 228 trades is statistically significant (p < 0.001)
- The K/D cross adds timing precision to the oversold/overbought condition
- Conservative TP/SL (2:1) captures quick mean reversion moves
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


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_stoch_rsi(close: pd.Series, rsi_period: int = 14,
                   stoch_period: int = 14, k_smooth: int = 3,
                   d_smooth: int = 3) -> pd.DataFrame:
    """Stochastic RSI: K and D lines."""
    rsi = calc_rsi(close, rsi_period)
    rsi_low = rsi.rolling(stoch_period).min()
    rsi_high = rsi.rolling(stoch_period).max()
    stoch_rsi_raw = (rsi - rsi_low) / (rsi_high - rsi_low).replace(0, np.nan) * 100
    k = stoch_rsi_raw.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return pd.DataFrame({"k": k, "d": d})


class VerifiedStochRsiStrategy:
    NAME = "Verified Stoch RSI"
    DESCRIPTION = "Stochastic RSI mean reversion at extremes. 78% WR, 228 trades (QuantifiedStrategies)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get("rsi_period", 14)
        self.stoch_period = self.params.get("stoch_period", 14)
        self.k_smooth = self.params.get("k_smooth", 3)
        self.d_smooth = self.params.get("d_smooth", 3)
        self.oversold = self.params.get("oversold", 20)
        self.overbought = self.params.get("overbought", 80)
        self.tp_pct = self.params.get("tp_pct", 0.08)
        self.sl_pct = self.params.get("sl_pct", 0.04)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = self.rsi_period + self.stoch_period + self.k_smooth + self.d_smooth + 10
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        sr = calc_stoch_rsi(close, self.rsi_period, self.stoch_period,
                            self.k_smooth, self.d_smooth)

        k_now = float(sr["k"].iloc[-1])
        d_now = float(sr["d"].iloc[-1])
        k_prev = float(sr["k"].iloc[-2])
        d_prev = float(sr["d"].iloc[-2])

        if any(np.isnan(v) for v in [k_now, d_now, k_prev, d_prev]):
            return []

        current_price = float(close.iloc[-1])
        signals = []

        # Long: K crosses above D below oversold
        cross_up = k_prev <= d_prev and k_now > d_now
        if cross_up and k_now < self.oversold:
            depth = (self.oversold - k_now) / self.oversold
            confidence = min(0.55 + depth * 0.4, 0.93)
            tp = current_price * (1 + self.tp_pct)
            sl = current_price * (1 - self.sl_pct)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"StochRSI BUY: K={k_now:.1f} crossed above D={d_now:.1f} in oversold zone",
            ))

        # Short: K crosses below D above overbought
        cross_down = k_prev >= d_prev and k_now < d_now
        if cross_down and k_now > self.overbought:
            depth = (k_now - self.overbought) / (100 - self.overbought)
            confidence = min(0.55 + depth * 0.4, 0.93)
            tp = current_price * (1 - self.tp_pct)
            sl = current_price * (1 + self.sl_pct)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"StochRSI SELL: K={k_now:.1f} crossed below D={d_now:.1f} in overbought zone",
            ))

        return signals


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))

    test_data = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + abs(np.random.normal(0, 0.01, n))),
        "low": prices * (1 - abs(np.random.normal(0, 0.01, n))),
        "close": prices,
        "volume": np.random.uniform(100, 1000, n),
    })

    strategy = VerifiedStochRsiStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
