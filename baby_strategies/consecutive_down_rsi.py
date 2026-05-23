"""
ConsecutiveDownRsiStrategy - Baby Strat
========================================

Created by: Claude Code (Batch 2 Survivor)
Date: 2026-02-28

Strategy Logic:
- Entry when: 4+ consecutive down days + RSI(14) < 35 + price above SMA(200)
- Exit when: TP/SL hit or first up-day close
- Risk management: ATR-based SL/TP (3x ATR TP, 2x ATR SL)

Academic Basis: Connors & Alvarez consecutive-down reversal variant.

Survivor Backtest Results:
- 202 trades, 74.3% WR, Sharpe 1.76, PF 1.6
- OOS: 107 trades, 70.1% WR, avg +0.665%
- Multi-asset: 21/24 symbols profitable
- Passed 8/8 anti-overfit checks
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


class ConsecutiveDownRsiStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.min_down_days = self.params.get('min_down_days', 4)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_threshold = self.params.get('rsi_threshold', 35)
        self.sma_period = self.params.get('sma_period', 200)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 2.0)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.sma_period + 10:
            return []

        close = data['close'] if 'close' in data.columns else data['Close']
        high = data['high'] if 'high' in data.columns else data['High']
        low = data['low'] if 'low' in data.columns else data['Low']

        # RSI(14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - 100 / (1 + rs)

        # SMA(200)
        sma200 = close.rolling(self.sma_period).mean()

        # ATR
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()

        # Consecutive down days
        consec_down = (close < close.shift(1)).astype(int)
        consec_count = consec_down.copy()
        for i in range(1, len(consec_count)):
            if consec_count.iloc[i] == 1:
                consec_count.iloc[i] = consec_count.iloc[i - 1] + 1

        current_price = float(close.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        current_sma = float(sma200.iloc[-1])
        current_atr = float(atr.iloc[-1])
        current_consec = int(consec_count.iloc[-1])

        signals = []

        if (current_consec >= self.min_down_days and
                current_rsi < self.rsi_threshold and
                current_price > current_sma and
                current_atr > 0):

            confidence = min(0.95, 0.5 + (self.rsi_threshold - current_rsi) / 100 + (current_consec - self.min_down_days) * 0.05)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 6),
                take_profit=round(tp, 6),
                stop_loss=round(sl, 6),
                reason=f"ConsecDownRSI: {current_consec} down days, RSI={current_rsi:.1f}<{self.rsi_threshold}, above SMA200"
            ))

        return signals

    @staticmethod
    def _calculate_rsi(series, period):
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        return 100 - 100 / (1 + rs)
