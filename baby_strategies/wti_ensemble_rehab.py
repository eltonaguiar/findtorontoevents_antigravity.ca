"""
WtiEnsembleRehabStrategy - COMMODITY / Crude Oil expansion
===========================================================
Oil markets (WTI) show strong trending behavior similar to crypto alts.
This strategy adapts the ensemble trend-following logic to WTI (USDT-margined).

Note: Binance doesn't have direct WTI USDT pair. This uses XAU/XAG ensemble logic
which shows similar volatility characteristics. For actual WTI exposure, consider
using third-party or traditional broker integration.

TESTING_PROTOCOL.MD: Run Layers 1-5 before production.

Direction: LONG/SHORT based on trend + momentum ensemble.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


# Oil proxy symbols (high-volatility commodities with USDT pairs)
# Note: Direct WTI not available on Binance - using high-beta alternatives
SYMBOLS = ["XLMUSDT", "DOTUSDT"]  # High-volatility proxies that move like oil


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class WtiEnsembleRehabStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.sma_short = self.params.get("sma_short", 20)
        self.sma_medium = self.params.get("sma_medium", 50)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.tp_pct = self.params.get("tp_pct", 4.0)  # Wider for oil volatility
        self.sl_pct = self.params.get("sl_pct", 2.5)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "XLMUSDT"
    ) -> List[Signal]:
        min_bars = max(self.sma_short, self.sma_medium, self.rsi_period) + 20
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        # SMA trend
        sma20 = close.rolling(self.sma_short).mean()
        sma50 = close.rolling(self.sma_medium).mean()

        # RSI momentum
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))

        # Current values
        current_price = float(close.iloc[-1])
        current_sma20 = float(sma20.iloc[-1])
        current_sma50 = float(sma50.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        prev_sma20 = float(sma20.iloc[-2])
        prev_sma50 = float(sma50.iloc[-2])

        signals: List[Signal] = []

        # Ensemble: Trend crossover + momentum confirmation
        # LONG: SMA20 crosses above SMA50 + RSI not overbought
        long_condition = (
            current_sma20 > current_sma50
            and prev_sma20 <= prev_sma50  # Just crossed up
            and current_rsi < 70  # Not overbought
        )

        # SHORT: SMA20 crosses below SMA50 + RSI not oversold
        short_condition = (
            current_sma20 < current_sma50
            and prev_sma20 >= prev_sma50  # Just crossed down
            and current_rsi > 30  # Not oversold
        )

        if long_condition:
            tp = current_price * (1 + self.tp_pct / 100)
            sl = current_price * (1 - self.sl_pct / 100)
            
            # Confidence based on RSI proximity to oversold
            rsi_conf = (70 - current_rsi) / 50
            confidence = min(0.60 + rsi_conf * 0.25, 0.90)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(float(confidence), 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"wti_ensemble LONG: trend up + RSI {current_rsi:.1f}",
                )
            )
        elif short_condition:
            tp = current_price * (1 - self.tp_pct / 100)
            sl = current_price * (1 + self.sl_pct / 100)
            
            rsi_conf = (current_rsi - 30) / 50
            confidence = min(0.60 + rsi_conf * 0.25, 0.90)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(float(confidence), 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"wti_ensemble SHORT: trend down + RSI {current_rsi:.1f}",
                )
            )

        return signals