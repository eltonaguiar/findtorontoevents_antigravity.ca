"""
KeltnerMomentumSqueeze - Baby Strat
=====================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Detects when Bollinger Bands contract INSIDE Keltner Channels (TTM Squeeze)
- Entry on squeeze release + momentum direction (linear regression slope)
- This is the actual John Carter TTM Squeeze — a proven institutional setup

Unique Value Proposition:
The BB squeeze strat only uses BB width. This uses the BB-inside-Keltner relationship
which is the actual TTM Squeeze used by prop desks. Momentum histogram direction
at squeeze release gives the trade direction.
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
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class KeltnerMomentumSqueezeStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_mult = self.params.get('bb_mult', 2.0)
        self.kc_period = self.params.get('kc_period', 20)
        self.kc_mult = self.params.get('kc_mult', 1.5)
        self.mom_period = self.params.get('mom_period', 12)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def _hma(self, series: pd.Series, period: int = 21) -> pd.Series:
        """Hull Moving Average -- lag-reduced trend filter."""
        half = max(1, period // 2)
        sqrt_n = max(1, int(period ** 0.5))
        wma_half = series.ewm(span=half, adjust=False).mean()
        wma_full = series.ewm(span=period, adjust=False).mean()
        raw = 2 * wma_half - wma_full
        return raw.ewm(span=sqrt_n, adjust=False).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.bb_period, self.kc_period, self.mom_period, self.atr_period) + 15
        if len(data) < min_bars:
            return []

        close = data['close']
        high = data['high']
        low = data['low']

        # Bollinger Bands
        bb_mid = close.rolling(self.bb_period).mean()
        bb_std = close.rolling(self.bb_period).std()
        bb_upper = bb_mid + bb_std * self.bb_mult
        bb_lower = bb_mid - bb_std * self.bb_mult

        # Keltner Channels
        kc_mid = close.rolling(self.kc_period).mean()
        atr = self._atr(data, self.kc_period)
        kc_upper = kc_mid + atr * self.kc_mult
        kc_lower = kc_mid - atr * self.kc_mult

        # Squeeze: BB inside KC
        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)

        # Momentum: linear regression of (close - midline) over mom_period
        delta = close - (high.rolling(self.mom_period).max() + low.rolling(self.mom_period).min()) / 2
        delta = (delta + (close - close.rolling(self.mom_period).mean())) / 2
        momentum = delta.rolling(self.mom_period).mean()

        current_atr = self._atr(data, self.atr_period).iloc[-1]
        current_price = close.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            return []

        # HMA trend filter: only trade in direction of trend
        hma_val = self._hma(close, 21)
        hma_rising = hma_val.iloc[-1] > hma_val.iloc[-2]

        signals = []

        # Squeeze just released (was on, now off)
        if len(squeeze_on) >= 3 and squeeze_on.iloc[-2] and not squeeze_on.iloc[-1]:
            mom_val = momentum.iloc[-1]
            mom_prev = momentum.iloc[-2]

            if not np.isnan(mom_val) and not np.isnan(mom_prev):
                if mom_val > 0 and mom_val > mom_prev and hma_rising:
                    # Bullish momentum at squeeze release + HMA confirms uptrend
                    confidence = min(0.6 + abs(mom_val) / current_atr * 0.1, 0.95)
                    tp = current_price + current_atr * self.tp_atr_mult
                    sl = current_price - current_atr * self.sl_atr_mult
                    signals.append(Signal(
                        symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                        entry_price=round(current_price, 2),
                        take_profit=round(tp, 2), stop_loss=round(sl, 2),
                        reason=f"TTM Squeeze release bullish (HMA trend-aligned), momentum={mom_val:.2f}"
                    ))
                elif mom_val < 0 and mom_val < mom_prev and not hma_rising:
                    # Bearish momentum at squeeze release + HMA confirms downtrend
                    confidence = min(0.6 + abs(mom_val) / current_atr * 0.1, 0.95)
                    tp = current_price - current_atr * self.tp_atr_mult
                    sl = current_price + current_atr * self.sl_atr_mult
                    signals.append(Signal(
                        symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                        entry_price=round(current_price, 2),
                        take_profit=round(tp, 2), stop_loss=round(sl, 2),
                        reason=f"TTM Squeeze release bearish (HMA trend-aligned), momentum={mom_val:.2f}"
                    ))

        return signals

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
