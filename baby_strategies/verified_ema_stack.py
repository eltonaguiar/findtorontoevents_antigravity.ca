"""
VerifiedEmaStackStrategy - Baby Strat
======================================

Created by: Claude AI
Date: 2026-03-04

Source: PickMyTrade, 59% WR, PF 1.7, BTC 1H

Strategy Logic:
- Long: EMA9 > EMA21 > EMA50 AND price above all three
- Short: EMA9 < EMA21 < EMA50 AND price below all three
- Exit on stack break (any EMA ordering violation)
- TP: +12% / SL: -5%

Why it works:
- EMA stack alignment is the purest measure of trend strength across timeframes
- When fast/medium/slow EMAs are perfectly ordered, momentum is confirmed at all scales
- Price above all three EMAs means dips are being bought aggressively
- 59% WR with 1.7 PF indicates consistent edge in trending crypto markets
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


class VerifiedEmaStackStrategy:
    NAME = "Verified EMA Stack"
    DESCRIPTION = "EMA 9/21/50 stack alignment trend following. 59% WR, PF 1.7 (PickMyTrade)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fast_period = self.params.get("fast_period", 9)
        self.mid_period = self.params.get("mid_period", 21)
        self.slow_period = self.params.get("slow_period", 50)
        self.tp_pct = self.params.get("tp_pct", 0.12)
        self.sl_pct = self.params.get("sl_pct", 0.05)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.slow_period + 10:
            return []

        close = data["close"].astype(float)

        ema_fast = close.ewm(span=self.fast_period, adjust=False).mean()
        ema_mid = close.ewm(span=self.mid_period, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_period, adjust=False).mean()

        current_price = float(close.iloc[-1])
        ef = float(ema_fast.iloc[-1])
        em = float(ema_mid.iloc[-1])
        es = float(ema_slow.iloc[-1])

        if any(np.isnan(v) for v in [ef, em, es]):
            return []

        signals = []

        # Check previous bar stack state for fresh alignment detection
        ef_prev = float(ema_fast.iloc[-2])
        em_prev = float(ema_mid.iloc[-2])
        es_prev = float(ema_slow.iloc[-2])

        bullish_stack = ef > em > es and current_price > ef
        bearish_stack = ef < em < es and current_price < ef
        prev_bullish = ef_prev > em_prev > es_prev
        prev_bearish = ef_prev < em_prev < es_prev

        if bullish_stack:
            # Confidence based on spacing between EMAs (wider = stronger trend)
            spread = (ef - es) / es
            confidence = min(0.5 + spread * 10, 0.92)
            tp = current_price * (1 + self.tp_pct)
            sl = current_price * (1 - self.sl_pct)
            fresh = " (fresh alignment)" if not prev_bullish else ""
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"EMA Stack BUY{fresh}: EMA9={ef:.2f} > EMA21={em:.2f} > EMA50={es:.2f}, price above all",
            ))
        elif bearish_stack:
            spread = (es - ef) / es
            confidence = min(0.5 + spread * 10, 0.92)
            tp = current_price * (1 - self.tp_pct)
            sl = current_price * (1 + self.sl_pct)
            fresh = " (fresh alignment)" if not prev_bearish else ""
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"EMA Stack SELL{fresh}: EMA9={ef:.2f} < EMA21={em:.2f} < EMA50={es:.2f}, price below all",
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

    strategy = VerifiedEmaStackStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
