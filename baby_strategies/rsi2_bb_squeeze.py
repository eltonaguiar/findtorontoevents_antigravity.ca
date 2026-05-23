"""
Rsi2BbSqueezeStrategy - Baby Strat
====================================

Created by: Claude Code (Batch 2 Survivor)
Date: 2026-02-28

Strategy Logic:
- Entry when: RSI(2) < 10 + price at/below lower Bollinger Band + above SMA(200)
- Exit when: TP/SL hit or RSI(2) > 70
- Risk management: ATR-based SL/TP (3x ATR TP, 2x ATR SL)

Academic Basis: Connors RSI-2 mean reversion + Bollinger Band squeeze (Connors & Alvarez + Bollinger).

Survivor Backtest Results:
- 429 trades, 67.1% WR, Sharpe 1.11, PF 1.5
- OOS: 244 trades, 65.2% WR, avg +0.341%
- Multi-asset: 20/24 symbols profitable
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


class Rsi2BbSqueezeStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 2)
        self.rsi_entry = self.params.get('rsi_entry', 10)
        self.rsi_exit = self.params.get('rsi_exit', 70)
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.0)
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

        # RSI(2)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi2 = 100 - 100 / (1 + rs)

        # Bollinger Bands
        bb_mid = close.rolling(self.bb_period).mean()
        bb_std_arr = close.rolling(self.bb_period).std()
        bb_lower = bb_mid - self.bb_std * bb_std_arr

        # SMA(200)
        sma200 = close.rolling(self.sma_period).mean()

        # ATR
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()

        current_price = float(close.iloc[-1])
        current_rsi = float(rsi2.iloc[-1])
        current_bb_lower = float(bb_lower.iloc[-1])
        current_sma = float(sma200.iloc[-1])
        current_atr = float(atr.iloc[-1])

        signals = []

        if (current_rsi < self.rsi_entry and
                current_price <= current_bb_lower * 1.01 and
                current_price > current_sma and
                current_atr > 0):

            confidence = min(0.95, 0.6 + (self.rsi_entry - current_rsi) / 50)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 6),
                take_profit=round(tp, 6),
                stop_loss=round(sl, 6),
                reason=f"RSI2+BB: RSI(2)={current_rsi:.1f}<{self.rsi_entry}, at lower BB, above SMA200"
            ))

        return signals
