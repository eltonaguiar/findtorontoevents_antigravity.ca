"""
CorrVwapZscoreReversionStrategy - Baby Strat
==============================================

Created by: Claude AI
Date: 2026-03-04

Confluence strategy: VWAP Reversion x Z-Score Extreme
  Double mean-reversion confirmation for higher accuracy

Strategy Logic:
- VWAP undervalued: price < VWAP (institutional fair value below)
- Z-Score extreme: z < -1.5 (statistical oversold)
- Both conditions required for BUY signal
- Both overbought conditions required for SELL signal
- TP: +6%, SL: -3%

Why it works:
- VWAP = volume-weighted fair value (institutional reference)
- Z-Score = statistical deviation from rolling mean
- Two independent mean-reversion signals confirming = reduced false positives
- Tighter TP/SL because reversion targets are well-defined
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


class CorrVwapZscoreReversionStrategy:
    NAME = "Correlation - VWAP x Z-Score"
    DESCRIPTION = "Double mean-reversion: VWAP undervalued + Z-Score extreme"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vwap_period = self.params.get("vwap_period", 50)
        self.z_lookback = self.params.get("z_lookback", 50)
        self.z_buy = self.params.get("z_buy", -1.5)
        self.z_sell = self.params.get("z_sell", 1.5)
        self.tp_pct = self.params.get("tp_pct", 0.06)
        self.sl_pct = self.params.get("sl_pct", 0.03)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.vwap_period, self.z_lookback) + 10:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # VWAP calculation
        typical_price = (high + low + close) / 3
        tp_vol = typical_price * volume
        vwap = tp_vol.rolling(self.vwap_period).sum() / volume.rolling(self.vwap_period).sum()

        # Z-Score calculation
        rolling_mean = close.rolling(self.z_lookback).mean()
        rolling_std = close.rolling(self.z_lookback).std()

        current_price = float(close.iloc[-1])
        current_vwap = float(vwap.iloc[-1])
        mean_val = float(rolling_mean.iloc[-1])
        std_val = float(rolling_std.iloc[-1])

        if any(np.isnan(x) for x in [current_vwap, mean_val, std_val]) or std_val <= 0:
            return []

        z_score = (current_price - mean_val) / std_val
        vwap_pct = (current_price - current_vwap) / current_vwap

        signals = []

        # BUY: price below VWAP AND z-score below threshold
        vwap_undervalued = current_price < current_vwap
        z_oversold = z_score < self.z_buy

        if vwap_undervalued and z_oversold:
            confidence = min(0.6 + abs(z_score) * 0.1 + abs(vwap_pct) * 2, 0.95)
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
                    reason=f"VWAP+Z confluence BUY: price {current_price:.2f} < VWAP {current_vwap:.2f} ({vwap_pct:+.2%}), z={z_score:.2f}",
                )
            )

        # SELL: price above VWAP AND z-score above threshold
        vwap_overvalued = current_price > current_vwap
        z_overbought = z_score > self.z_sell

        if vwap_overvalued and z_overbought:
            confidence = min(0.6 + abs(z_score) * 0.1 + abs(vwap_pct) * 2, 0.95)
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
                    reason=f"VWAP+Z confluence SELL: price {current_price:.2f} > VWAP {current_vwap:.2f} ({vwap_pct:+.2%}), z={z_score:.2f}",
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

    strategy = CorrVwapZscoreReversionStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
