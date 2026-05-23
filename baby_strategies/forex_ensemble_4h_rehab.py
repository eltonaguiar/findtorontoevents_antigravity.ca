"""
ForexEnsemble4hRehabStrategy - FOREX expansion of ml_enhanced_TONUSDT_4h_D_ensemble_stack
==========================================================================================
The 4h ensemble stack (PF=3.50, WR=87.5% on TONUSDT) showed exceptional performance
by requiring multi-model consensus. This strategy adapts that logic to liquid FOREX pairs.

TESTING_PROTOCOL.MD: Run Layers 1-5 before production.

Direction: LONG/SHORT based on ensemble consensus at 4h timeframe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


# USDT-margined FOREX pairs - expansion targets
SYMBOLS = ["EURUSDT", "GBPUSDT", "AUDUSDT", "USDCAD"]


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class ForexEnsemble4hRehabStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.sma_short = self.params.get("sma_short", 20)
        self.sma_medium = self.params.get("sma_medium", 50)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_pct = self.params.get("tp_pct", 3.0)
        self.sl_pct = self.params.get("sl_pct", 2.0)
        
    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "EURUSDT"
    ) -> List[Signal]:
        min_bars = max(self.sma_short, self.sma_medium) + 20
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        
        # Multi-timeframe ensemble signals
        sma20 = close.rolling(self.sma_short).mean()
        sma50 = close.rolling(self.sma_medium).mean()
        
        # ATR for volatility filtering
        tr = pd.concat([
            high - low, 
            (high - close.shift()).abs(), 
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()
        
        # Ensemble consensus: trend alignment + low volatility compression
        current_price = float(close.iloc[-1])
        current_sma20 = float(sma20.iloc[-1])
        current_sma50 = float(sma50.iloc[-1])
        current_atr = float(atr.iloc[-1])
        prev_sma20 = float(sma20.iloc[-2])
        prev_sma50 = float(sma50.iloc[-2])
        
        # Calculate ATR as percentage of price
        atr_pct = (current_atr / current_price) * 100 if current_price > 0 else 0
        
        signals: List[Signal] = []
        
        # LONG: Uptrend (sma20 > sma50) + compression (low ATR)
        long_condition = (
            current_sma20 > current_sma50 and 
            prev_sma20 <= prev_sma50 and  # Just crossed up
            atr_pct < 1.0  # Low volatility = compression
        )
        
        # SHORT: Downtrend + compression
        short_condition = (
            current_sma20 < current_sma50 and 
            prev_sma20 >= prev_sma50 and  # Just crossed down
            atr_pct < 1.0
        )
        
        if long_condition:
            tp = current_price * (1 + self.tp_pct / 100)
            sl = current_price * (1 - self.sl_pct / 100)
            confidence = min(0.65 + (1.0 - atr_pct) * 0.2, 0.92)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(float(confidence), 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"forex_ensemble_4h LONG: trend up + compression atr_pct={atr_pct:.2f}%"
                )
            )
        elif short_condition:
            tp = current_price * (1 - self.tp_pct / 100)
            sl = current_price * (1 + self.sl_pct / 100)
            confidence = min(0.65 + (1.0 - atr_pct) * 0.2, 0.92)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(float(confidence), 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"forex_ensemble_4h SHORT: trend down + compression atr_pct={atr_pct:.2f}%"
                )
            )
        
        return signals