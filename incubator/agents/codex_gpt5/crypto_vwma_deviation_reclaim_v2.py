"""
Crypto VWMA Deviation Reclaim - Baby Strat
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


class CryptoVWMADDeviationReclaimStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vwma_period = self.params.get("vwma_period", 34)
        self.trend_period = self.params.get("trend_period", 120)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.atr_period = self.params.get("atr_period", 14)
        self.dev_threshold = self.params.get("dev_threshold", 1.0)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 1.8)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.2)
        self.min_bars = 120

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data["close"]
        volume = data["volume"]
        atr = self._atr(data, self.atr_period)
        rsi = self._rsi(close, self.rsi_period)

        pv = close * volume
        vwma = pv.rolling(self.vwma_period, min_periods=1).sum() / (volume.rolling(self.vwma_period, min_periods=1).sum() + 1e-12)
        trend_ema = close.ewm(span=self.trend_period, adjust=False).mean()
        dev = (close - vwma) / (atr + 1e-12)

        price = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        dev_now = float(dev.iloc[-1])
        dev_prev = float(dev.iloc[-2])
        rsi_now = float(rsi.iloc[-1])

        if atr_now <= 0:
            return []

        signals: List[Signal] = []
        uptrend = float(close.iloc[-1]) > float(trend_ema.iloc[-1])
        downtrend = float(close.iloc[-1]) < float(trend_ema.iloc[-1])

        reclaim_up = float(close.iloc[-2]) < float(vwma.iloc[-2]) and float(close.iloc[-1]) > float(vwma.iloc[-1])
        reclaim_down = float(close.iloc[-2]) > float(vwma.iloc[-2]) and float(close.iloc[-1]) < float(vwma.iloc[-1])

        if uptrend and dev_prev < -self.dev_threshold and reclaim_up and rsi_now < 55:
            conf = min(0.92, 0.52 + min(0.33, abs(dev_prev) / 5.0))
            signals.append(self._mk(symbol, "BUY", price, atr_now, conf, "Uptrend VWMA pullback reclaimed"))
        elif downtrend and dev_prev > self.dev_threshold and reclaim_down and rsi_now > 45:
            conf = min(0.92, 0.52 + min(0.33, abs(dev_prev) / 5.0))
            signals.append(self._mk(symbol, "SELL", price, atr_now, conf, "Downtrend VWMA pullback rejected"))
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

    @staticmethod
    def _rsi(prices: pd.Series, period: int) -> pd.Series:
        d = prices.diff()
        up = d.where(d > 0, 0.0)
        dn = -d.where(d < 0, 0.0)
        avg_up = up.rolling(period, min_periods=1).mean()
        avg_dn = dn.rolling(period, min_periods=1).mean()
        rs = avg_up / (avg_dn + 1e-12)
        return 100 - 100 / (1 + rs)


if __name__ == "__main__":
    np.random.seed(1)
    n = 260
    r = np.random.normal(0.0002, 0.02, n)
    p = 3000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.01, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.01, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.5, n),
        }
    )
    s = CryptoVWMADDeviationReclaimStrategy()
    print(len(s.generate_signals(df)))
