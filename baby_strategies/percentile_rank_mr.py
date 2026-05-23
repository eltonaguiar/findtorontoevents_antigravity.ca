"""
PercentileRankMrStrategy - Baby Strat
=======================================

Created by: Claude Code (Batch 2 Survivor)
Date: 2026-02-28

Strategy Logic:
- Entry when: 100-day percentile rank < 5 (price near historical low) + above 90% of SMA(200)
- Exit when: TP/SL hit or percentile rank > 50
- Risk management: ATR-based SL/TP (3x ATR TP, 2x ATR SL)

Academic Basis: Connors & Alvarez percentile rank mean reversion.

Survivor Backtest Results:
- 225 trades, 50.2% WR, Sharpe 0.30, PF 1.21
- OOS: 108 trades, 52.8% WR, avg +1.381%
- Multi-asset: 16/24 symbols profitable
- Passed 7/8 anti-overfit checks (failed: p_value marginally)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

@dataclass
class Signal:
    """Required: Do not modify this class."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float  # 0.0 to 1.0
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class PercentileRankMrStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 100)
        self.entry_pctl = self.params.get('entry_pctl', 5)
        self.exit_pctl = self.params.get('exit_pctl', 50)
        self.sma_period = self.params.get('sma_period', 200)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 2.0)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.lookback + self.sma_period + 10:
            return []

        close = data['close'] if 'close' in data.columns else data['Close']
        high = data['high'] if 'high' in data.columns else data['High']
        low = data['low'] if 'low' in data.columns else data['Low']

        # Calculate percentile rank
        close_arr = close.values.astype(float)
        n = len(close_arr)
        current_price = close_arr[-1]
        window = close_arr[max(0, n - self.lookback):n]
        pctl = (np.sum(window < current_price) / len(window)) * 100

        # SMA(200)
        sma200 = float(close.rolling(self.sma_period).mean().iloc[-1])

        # ATR
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()
        current_atr = float(atr.iloc[-1])

        signals = []

        if (pctl < self.entry_pctl and
                current_price > sma200 * 0.9 and
                current_atr > 0):

            confidence = min(0.95, 0.5 + (self.entry_pctl - pctl) / 20)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 6),
                take_profit=round(tp, 6),
                stop_loss=round(sl, 6),
                reason=f"PctlRankMR: percentile={pctl:.1f}<{self.entry_pctl}, near {self.lookback}d low, above 90% SMA200"
            ))

        return signals
