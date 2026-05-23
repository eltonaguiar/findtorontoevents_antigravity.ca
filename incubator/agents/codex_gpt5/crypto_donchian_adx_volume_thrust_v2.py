"""
Crypto Donchian ADX Volume Thrust - Baby Strat
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoDonchianADXVolumeThrustStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.donchian = self.params.get("donchian", 40)
        self.adx_period = self.params.get("adx_period", 14)
        self.adx_min = self.params.get("adx_min", 21)
        self.vol_period = self.params.get("vol_period", 30)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.6)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.3)
        self.atr_period = self.params.get("atr_period", 14)
        self.min_bars = 150

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        high = data["high"]
        low = data["low"]
        close = data["close"]
        volume = data["volume"]

        upper = high.rolling(self.donchian, min_periods=1).max().shift(1)
        lower = low.rolling(self.donchian, min_periods=1).min().shift(1)
        atr = self._atr(data, self.atr_period)
        adx = self._adx(data, self.adx_period)
        vol_ma = volume.rolling(self.vol_period, min_periods=1).mean()
        vol_z = (volume - vol_ma) / (volume.rolling(self.vol_period, min_periods=1).std() + 1e-12)

        price = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        adx_now = float(adx.iloc[-1])
        adx_prev = float(adx.iloc[-2])
        upper_now = float(upper.iloc[-1])
        lower_now = float(lower.iloc[-1])
        volz_now = float(vol_z.iloc[-1])

        if atr_now <= 0:
            return []

        adx_rising = adx_now > adx_prev
        if adx_now < self.adx_min or not adx_rising or volz_now < 0.5:
            return []

        signals: List[Signal] = []
        if price > upper_now:
            conf = min(0.95, 0.53 + min(0.3, (adx_now - self.adx_min) / 40.0))
            signals.append(self._mk(symbol, "BUY", price, atr_now, conf, "Donchian breakout with rising ADX and volume"))
        elif price < lower_now:
            conf = min(0.95, 0.53 + min(0.3, (adx_now - self.adx_min) / 40.0))
            signals.append(self._mk(symbol, "SELL", price, atr_now, conf, "Donchian breakdown with rising ADX and volume"))
        return signals

    def _mk(self, symbol: str, direction: str, px: float, atr: float, conf: float, reason: str) -> Signal:
        if direction == "BUY":
            tp = px + self.tp_atr_mult * atr
            sl = px - self.sl_atr_mult * atr
        else:
            tp = px - self.tp_atr_mult * atr
            sl = px + self.sl_atr_mult * atr
        return Signal(symbol, direction, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    def _adx(self, data: pd.DataFrame, period: int) -> pd.Series:
        high = data["high"]
        low = data["low"]
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=data.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=data.index)
        atr = self._atr(data, period)
        plus_di = 100 * plus_dm.rolling(period, min_periods=1).mean() / (atr + 1e-12)
        minus_di = 100 * minus_dm.rolling(period, min_periods=1).mean() / (atr + 1e-12)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-12)
        return dx.rolling(period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(7)
    n = 320
    r = np.random.normal(0.0005, 0.02, n)
    p = 20000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.012, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.012, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.65, n),
        }
    )
    s = CryptoDonchianADXVolumeThrustStrategy()
    print(len(s.generate_signals(df)))
