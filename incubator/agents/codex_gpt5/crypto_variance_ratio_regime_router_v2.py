"""
Crypto Variance Ratio Regime Router - Baby Strat
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


class CryptoVarianceRatioRegimeRouterStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vr_period = self.params.get("vr_period", 8)
        self.trend_vr = self.params.get("trend_vr", 1.08)
        self.revert_vr = self.params.get("revert_vr", 0.92)
        self.ema_fast = self.params.get("ema_fast", 20)
        self.ema_slow = self.params.get("ema_slow", 50)
        self.bb_period = self.params.get("bb_period", 20)
        self.bb_std = self.params.get("bb_std", 2.0)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_trend = self.params.get("tp_trend", 2.3)
        self.sl_trend = self.params.get("sl_trend", 1.4)
        self.tp_revert = self.params.get("tp_revert", 1.6)
        self.sl_revert = self.params.get("sl_revert", 1.0)
        self.min_bars = 160

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data["close"]
        ret = close.pct_change().fillna(0.0)
        vr = self._variance_ratio(ret, self.vr_period)
        atr = self._atr(data, self.atr_period)
        rsi = self._rsi(close, self.rsi_period)
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()
        ma = close.rolling(self.bb_period, min_periods=1).mean()
        sd = close.rolling(self.bb_period, min_periods=1).std().fillna(0.0)
        upper = ma + self.bb_std * sd
        lower = ma - self.bb_std * sd

        price = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        vr_now = float(vr.iloc[-1])
        rsi_now = float(rsi.iloc[-1])
        if atr_now <= 0:
            return []

        signals: List[Signal] = []

        if vr_now >= self.trend_vr:
            if ema_f.iloc[-1] > ema_s.iloc[-1] and price > float(ma.iloc[-1]):
                conf = min(0.94, 0.52 + min(0.32, (vr_now - self.trend_vr) * 0.8))
                signals.append(self._mk(symbol, "BUY", price, atr_now, conf, self.tp_trend, self.sl_trend, "Trend regime via variance ratio"))
            elif ema_f.iloc[-1] < ema_s.iloc[-1] and price < float(ma.iloc[-1]):
                conf = min(0.94, 0.52 + min(0.32, (vr_now - self.trend_vr) * 0.8))
                signals.append(self._mk(symbol, "SELL", price, atr_now, conf, self.tp_trend, self.sl_trend, "Trend regime via variance ratio"))
        elif vr_now <= self.revert_vr:
            if price < float(lower.iloc[-1]) and rsi_now < 40:
                conf = min(0.9, 0.5 + min(0.3, (self.revert_vr - vr_now) * 1.2))
                signals.append(self._mk(symbol, "BUY", price, atr_now, conf, self.tp_revert, self.sl_revert, "Mean-revert regime via variance ratio"))
            elif price > float(upper.iloc[-1]) and rsi_now > 60:
                conf = min(0.9, 0.5 + min(0.3, (self.revert_vr - vr_now) * 1.2))
                signals.append(self._mk(symbol, "SELL", price, atr_now, conf, self.tp_revert, self.sl_revert, "Mean-revert regime via variance ratio"))

        return signals

    def _mk(
        self,
        symbol: str,
        direction: str,
        px: float,
        atr: float,
        conf: float,
        tp_mult: float,
        sl_mult: float,
        reason: str,
    ) -> Signal:
        if direction == "BUY":
            tp = px + tp_mult * atr
            sl = px - sl_mult * atr
        else:
            tp = px - tp_mult * atr
            sl = px + sl_mult * atr
        return Signal(symbol, direction, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    @staticmethod
    def _variance_ratio(returns: pd.Series, q: int) -> pd.Series:
        var_1 = returns.rolling(q * 4, min_periods=q + 2).var()
        q_ret = returns.rolling(q, min_periods=q).sum()
        var_q = q_ret.rolling(q * 4, min_periods=q + 2).var()
        return var_q / (q * var_1 + 1e-12)

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
    np.random.seed(9)
    n = 400
    r = np.random.normal(0.0003, 0.018, n)
    p = 1500 * np.exp(np.cumsum(r))
    df = pd.DataFrame(
        {
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.01, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.01, n))),
            "close": p,
            "volume": np.random.lognormal(7, 0.5, n),
        }
    )
    s = CryptoVarianceRatioRegimeRouterStrategy()
    print(len(s.generate_signals(df)))
