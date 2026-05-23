"""
VerifiedWavetrendStrategy - Baby Strat
=======================================

Created by: Claude AI
Date: 2026-03-04

Source: PickMyTrade, 58% WR on BTC 1H, PF 1.9, 1000+ trades

Strategy Logic:
- WaveTrend: WT1 = EMA(EMA((close - EMA(close, 10)), 10), 21); WT2 = SMA(WT1, 4)
- Long: WT1 crosses above WT2 below oversold zone (-60)
- Short: WT1 crosses below WT2 above overbought zone (+60)
- TP: +10% / SL: -5%

Why it works:
- WaveTrend is a smoothed oscillator that identifies exhaustion points
- The double-EMA smoothing eliminates noise while preserving turning points
- Oversold/overbought zones (-60/+60) filter to only extreme reversals
- Cross confirmation (WT1 x WT2) provides timing precision for entries
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


def calc_wavetrend(close: pd.Series, channel_len: int = 10,
                   avg_len: int = 21, signal_len: int = 4) -> pd.DataFrame:
    """WaveTrend Oscillator: WT1 and WT2 lines."""
    esa = close.ewm(span=channel_len, adjust=False).mean()
    d = (close - esa).abs().ewm(span=channel_len, adjust=False).mean()
    ci = (close - esa) / (0.015 * d.replace(0, np.nan))
    ci = ci.fillna(0)
    wt1 = ci.ewm(span=avg_len, adjust=False).mean()
    wt2 = wt1.rolling(signal_len).mean()
    return pd.DataFrame({"wt1": wt1, "wt2": wt2})


class VerifiedWavetrendStrategy:
    NAME = "Verified WaveTrend"
    DESCRIPTION = "WaveTrend oscillator reversals at extremes. 58% WR, PF 1.9, 1000+ trades (PickMyTrade)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.channel_len = self.params.get("channel_len", 10)
        self.avg_len = self.params.get("avg_len", 21)
        self.signal_len = self.params.get("signal_len", 4)
        self.oversold = self.params.get("oversold", -60)
        self.overbought = self.params.get("overbought", 60)
        self.tp_pct = self.params.get("tp_pct", 0.10)
        self.sl_pct = self.params.get("sl_pct", 0.05)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = self.avg_len + self.signal_len + 10
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        wt = calc_wavetrend(close, self.channel_len, self.avg_len, self.signal_len)

        wt1_now = float(wt["wt1"].iloc[-1])
        wt2_now = float(wt["wt2"].iloc[-1])
        wt1_prev = float(wt["wt1"].iloc[-2])
        wt2_prev = float(wt["wt2"].iloc[-2])

        if np.isnan(wt1_now) or np.isnan(wt2_now) or np.isnan(wt1_prev) or np.isnan(wt2_prev):
            return []

        current_price = float(close.iloc[-1])
        signals = []

        # Long: WT1 crosses above WT2 below oversold
        cross_up = wt1_prev <= wt2_prev and wt1_now > wt2_now
        if cross_up and wt1_now < self.oversold:
            depth = abs(wt1_now - self.oversold)
            confidence = min(0.5 + depth / 100, 0.92)
            tp = current_price * (1 + self.tp_pct)
            sl = current_price * (1 - self.sl_pct)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"WaveTrend BUY: WT1={wt1_now:.1f} crossed above WT2={wt2_now:.1f} in oversold zone",
            ))

        # Short: WT1 crosses below WT2 above overbought
        cross_down = wt1_prev >= wt2_prev and wt1_now < wt2_now
        if cross_down and wt1_now > self.overbought:
            depth = abs(wt1_now - self.overbought)
            confidence = min(0.5 + depth / 100, 0.92)
            tp = current_price * (1 - self.tp_pct)
            sl = current_price * (1 + self.sl_pct)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"WaveTrend SELL: WT1={wt1_now:.1f} crossed below WT2={wt2_now:.1f} in overbought zone",
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

    strategy = VerifiedWavetrendStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
