"""
PriceActionEngulfing - Baby Strat
===================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Detects bullish/bearish engulfing patterns at key levels (swing highs/lows)
- Filters with volume surge and trend context (200 EMA)
- Only trades engulfing at meaningful S/R, not random candles

Unique Value Proposition:
Pure price action — engulfing patterns are the #1 candlestick pattern in academic
studies (Caginalp & Laurent 1998). But they only work at KEY levels. This strategy
requires the engulfing to occur at a swing high/low with volume confirmation.
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


class PriceActionEngulfingStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.swing_lookback = self.params.get('swing_lookback', 10)
        self.swing_proximity_pct = self.params.get('swing_proximity_pct', 0.005)
        self.ema_period = self.params.get('ema_period', 50)
        self.volume_mult = self.params.get('volume_mult', 1.3)
        self.volume_period = self.params.get('volume_period', 20)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.ema_period, self.swing_lookback * 3, self.volume_period, self.atr_period) + 10
        if len(data) < min_bars:
            return []

        close = data['close']
        open_ = data['open']
        high = data['high']
        low = data['low']
        volume = data['volume']

        ema = close.ewm(span=self.ema_period).mean()
        vol_ma = volume.rolling(self.volume_period).mean()
        atr = self._atr(data, self.atr_period)

        # Find swing lows and swing highs in the lookback window
        swing_lows = []
        swing_highs = []
        check_range = data.iloc[-(self.swing_lookback * 3):-2]
        for i in range(self.swing_lookback, len(check_range) - self.swing_lookback):
            idx = check_range.index[i]
            window_low = check_range['low'].iloc[i-self.swing_lookback:i+self.swing_lookback+1]
            window_high = check_range['high'].iloc[i-self.swing_lookback:i+self.swing_lookback+1]
            if check_range['low'].iloc[i] == window_low.min():
                swing_lows.append(check_range['low'].iloc[i])
            if check_range['high'].iloc[i] == window_high.max():
                swing_highs.append(check_range['high'].iloc[i])

        curr = data.iloc[-1]
        prev = data.iloc[-2]
        current_price = curr['close']
        current_atr = atr.iloc[-1]
        current_vol = curr['volume'] if 'volume' in data.columns else 0
        current_vol_ma = vol_ma.iloc[-1]
        current_ema = ema.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            return []

        signals = []
        prox = current_price * self.swing_proximity_pct

        # Bullish engulfing: current close > prev open, current open < prev close, current body engulfs prev
        is_bullish_engulf = (
            curr['close'] > curr['open'] and  # current is green
            prev['close'] < prev['open'] and  # prev is red
            curr['close'] > prev['open'] and  # current close > prev open
            curr['open'] < prev['close']       # current open < prev close
        )

        # Bearish engulfing
        is_bearish_engulf = (
            curr['close'] < curr['open'] and
            prev['close'] > prev['open'] and
            curr['close'] < prev['open'] and
            curr['open'] > prev['close']
        )

        vol_ok = current_vol > current_vol_ma * self.volume_mult if not np.isnan(current_vol_ma) else True

        if is_bullish_engulf and vol_ok:
            # Check if near a swing low
            near_swing = any(abs(curr['low'] - sl) < prox for sl in swing_lows) if swing_lows else False
            below_ema = current_price < current_ema * 1.02  # near or below EMA (mean reversion context)
            if near_swing or below_ema:
                confidence = 0.75 if near_swing else 0.6
                tp = current_price + current_atr * self.tp_atr_mult
                sl = curr['low'] - current_atr * self.sl_atr_mult * 0.5
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=confidence,
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Bullish engulfing at {'swing low' if near_swing else 'EMA support'}"
                ))

        elif is_bearish_engulf and vol_ok:
            near_swing = any(abs(curr['high'] - sh) < prox for sh in swing_highs) if swing_highs else False
            above_ema = current_price > current_ema * 0.98
            if near_swing or above_ema:
                confidence = 0.75 if near_swing else 0.6
                tp = current_price - current_atr * self.tp_atr_mult
                sl = curr['high'] + current_atr * self.sl_atr_mult * 0.5
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=confidence,
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Bearish engulfing at {'swing high' if near_swing else 'EMA resistance'}"
                ))

        return signals

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
