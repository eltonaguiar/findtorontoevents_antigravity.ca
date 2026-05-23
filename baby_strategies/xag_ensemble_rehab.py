"""
XagEnsembleRehabStrategy - COMMODITY (Silver) expansion of high-performing ML strategies
==========================================================================================
The daily ML strategy on FETUSDT showed 80% WR with PF=43. This strategy adapts that
logic to silver (XAGUSDT) which has similar trending characteristics to crypto alts.

TESTING_PROTOCOL.MD: Run Layers 1-5 before production.

Direction: LONG based on trend following + momentum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


# Silver as USDT token on Binance (or closest proxy)
SYMBOLS = ["XAGUSDT", "XLMUSDT"]  # XLM as silver proxy if XAG not available


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class XagEnsembleRehabStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.sma_short = self.params.get("sma_short", 20)
        self.sma_long = self.params.get("sma_long", 50)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.tp_pct = self.params.get("tp_pct", 5.0)
        self.sl_pct = self.params.get("sl_pct", 3.0)
        
    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "XAGUSDT"
    ) -> List[Signal]:
        min_bars = max(self.sma_short, self.sma_long, self.rsi_period) + 20
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        
        # Trend: SMA crossover
        sma20 = close.rolling(self.sma_short).mean()
        sma50 = close.rolling(self.sma_long).mean()
        
        # Momentum: RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        current_price = float(close.iloc[-1])
        current_sma20 = float(sma20.iloc[-1])
        current_sma50 = float(sma50.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        prev_sma20 = float(sma20.iloc[-2])
        prev_sma50 = float(sma50.iloc[-2])
        
        signals: List[Signal] = []
        
        # Ensemble: Trend up (sma20 crosses above sma50) + RSI not overbought
        long_condition = (
            current_sma20 > current_sma50 and 
            prev_sma20 <= prev_sma50 and  # Just crossed up
            current_rsi < 70  # Not overbought
        )
        
        if long_condition:
            tp = current_price * (1 + self.tp_pct / 100)
            sl = current_price * (1 - self.sl_pct / 100)
            
            # Confidence based on RSI proximity to oversold
            rsi_conf = (70 - current_rsi) / 50  # 0 at rsi=70, 1 at rsi=20
            confidence = min(0.60 + rsi_conf * 0.25, 0.90)
            
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(float(confidence), 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"xag_ensemble_d1 LONG: trend up + RSI {current_rsi:.1f}"
                )
            )
        
        return signals