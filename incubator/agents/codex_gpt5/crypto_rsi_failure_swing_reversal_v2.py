"""
Crypto RSI Failure Swing Reversal - Baby Strat
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


class CryptoRSIFailureSwingReversalStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get("rsi_period", 14)
        self.div_window = self.params.get("div_window", 18)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.1)
        self.min_bars = 120

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data["close"]
        high = data["high"]
        low = data["low"]
        open_ = data["open"]
        rsi = self._rsi(close, self.rsi_period)
        atr = self._atr(data, self.atr_period)

        price = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        recent_low_price = float(low.iloc[-self.div_window :].min())
        recent_high_price = float(high.iloc[-self.div_window :].max())
        recent_low_rsi = float(rsi.iloc[-self.div_window :].min())
        recent_high_rsi = float(rsi.iloc[-self.div_window :].max())

        prev_low_price = float(low.iloc[-2 * self.div_window : -self.div_window].min())
        prev_high_price = float(high.iloc[-2 * self.div_window : -self.div_window].max())
        prev_low_rsi = float(rsi.iloc[-2 * self.div_window : -self.div_window].min())
        prev_high_rsi = float(rsi.iloc[-2 * self.div_window : -self.div_window].max())

        bullish_div = recent_low_price < prev_low_price and recent_low_rsi > prev_low_rsi
        bearish_div = recent_high_price > prev_high_price and recent_high_rsi < prev_high_rsi

        bullish_confirm = float(rsi.iloc[-1]) > 40 and float(close.iloc[-1]) > float(open_.iloc[-1])
        bearish_confirm = float(rsi.iloc[-1]) < 60 and float(close.iloc[-1]) < float(open_.iloc[-1])

        signals: List[Signal] = []
        if bullish_div and bullish_confirm:
            conf = min(0.93, 0.54 + min(0.3, (recent_low_rsi - prev_low_rsi) / 20.0))
            signals.append(self._mk(symbol, "BUY", price, atr_now, conf, "Bullish RSI failure swing divergence"))
        elif bearish_div and bearish_confirm:
            conf = min(0.93, 0.54 + min(0.3, (prev_high_rsi - recent_high_rsi) / 20.0))
            signals.append(self._mk(symbol, "SELL", price, atr_now, conf, "Bearish RSI failure swing divergence"))
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
    np.random.seed(11)
    n = 340
    r = np.random.normal(0.0001, 0.022, n)
    p = 25000 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.01, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.01, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.6, n),
        }
    )
    s = CryptoRSIFailureSwingReversalStrategy()
    print(len(s.generate_signals(df)))
