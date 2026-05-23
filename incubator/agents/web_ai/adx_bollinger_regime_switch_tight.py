"""
ADX-Bollinger Regime Switch — TIGHT MUTATION
==============================================
DNA Mutation A: Tighter TP/SL
- MR SL: 1.5 -> 1.2 ATR (-20%)
- BO TP: 2.5 -> 1.75 ATR (-30%)
- BO SL: 1.2 -> 0.96 ATR (-20%)
Parent: adx_bollinger_regime_switch.py (PF 1.32, 42.6% WR, 202 trades)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
import time


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    mode: str = ""


class ADXBollingerRegimeSwitchTightStrategy:
    """Tight mutation: tighter TP/SL across both modes."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_idle = self.params.get('adx_idle', 15)
        self.adx_breakout = self.params.get('adx_breakout', 25)
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.2)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_os = self.params.get('rsi_oversold', 35)
        self.rsi_ob = self.params.get('rsi_overbought', 65)
        self.atr_period = self.params.get('atr_period', 14)
        self.mr_sl_atr = self.params.get('mr_sl_atr', 1.2)    # MUTATED: 1.5 -> 1.2
        self.bo_tp_atr = self.params.get('bo_tp_atr', 1.75)   # MUTATED: 2.5 -> 1.75
        self.bo_sl_atr = self.params.get('bo_sl_atr', 0.96)   # MUTATED: 1.2 -> 0.96
        self.cooldown = self.params.get('cooldown', 4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.bb_period + self.adx_period + 20
        if len(data) < min_len:
            return []

        adx = self._calculate_adx(data)
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        bb_mid = data['close'].rolling(self.bb_period).mean()
        bb_std = data['close'].rolling(self.bb_period).std()
        bb_upper = bb_mid + self.bb_std * bb_std
        bb_lower = bb_mid - self.bb_std * bb_std

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_adx = adx.iloc[i]
            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_close = data['close'].iloc[i]
            cur_bb_upper = bb_upper.iloc[i]
            cur_bb_lower = bb_lower.iloc[i]
            cur_bb_mid = bb_mid.iloc[i]

            if any(pd.isna(v) for v in [cur_adx, cur_rsi, cur_atr, cur_bb_upper, cur_bb_lower, cur_bb_mid]):
                continue
            if cur_atr <= 0:
                continue

            if cur_adx < self.adx_idle:
                continue

            if cur_adx <= self.adx_breakout:
                adx_above = cur_adx - self.adx_idle
                conf = min(0.60 + 0.02 * adx_above, 0.85)

                if cur_close <= cur_bb_lower and cur_rsi < self.rsi_os:
                    signals.append(Signal(
                        symbol=symbol, direction="BUY", confidence=round(conf, 2),
                        entry_price=cur_close,
                        take_profit=round(cur_bb_mid, 2),
                        stop_loss=round(cur_close - cur_atr * self.mr_sl_atr, 2),
                        reason=f"MR_BUY_TIGHT ADX={cur_adx:.1f} RSI={cur_rsi:.1f}",
                        mode="MEAN_REV"
                    ))
                    last_signal_bar = i
                elif cur_close >= cur_bb_upper and cur_rsi > self.rsi_ob:
                    signals.append(Signal(
                        symbol=symbol, direction="SELL", confidence=round(conf, 2),
                        entry_price=cur_close,
                        take_profit=round(cur_bb_mid, 2),
                        stop_loss=round(cur_close + cur_atr * self.mr_sl_atr, 2),
                        reason=f"MR_SELL_TIGHT ADX={cur_adx:.1f} RSI={cur_rsi:.1f}",
                        mode="MEAN_REV"
                    ))
                    last_signal_bar = i
            else:
                adx_above = cur_adx - self.adx_breakout
                conf = min(0.60 + 0.02 * adx_above, 0.85)

                if cur_close > cur_bb_upper:
                    signals.append(Signal(
                        symbol=symbol, direction="BUY", confidence=round(conf, 2),
                        entry_price=cur_close,
                        take_profit=round(cur_close + cur_atr * self.bo_tp_atr, 2),
                        stop_loss=round(cur_close - cur_atr * self.bo_sl_atr, 2),
                        reason=f"BO_LONG_TIGHT ADX={cur_adx:.1f}",
                        mode="BREAKOUT"
                    ))
                    last_signal_bar = i
                elif cur_close < cur_bb_lower:
                    signals.append(Signal(
                        symbol=symbol, direction="SELL", confidence=round(conf, 2),
                        entry_price=cur_close,
                        take_profit=round(cur_close - cur_atr * self.bo_tp_atr, 2),
                        stop_loss=round(cur_close + cur_atr * self.bo_sl_atr, 2),
                        reason=f"BO_SHORT_TIGHT ADX={cur_adx:.1f}",
                        mode="BREAKOUT"
                    ))
                    last_signal_bar = i

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def _calculate_adx(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        n = self.adx_period
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr_smooth = tr.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/n, min_periods=n, adjust=False).mean() / atr_smooth
        minus_di = 100 * minus_dm.ewm(alpha=1/n, min_periods=n, adjust=False).mean() / atr_smooth
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1e-10)
        return dx.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
