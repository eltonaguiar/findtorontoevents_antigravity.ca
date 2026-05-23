"""
Crypto Short-Term NR+ER Keltner Ignition - Baby Strat
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


class CryptoShortTermNRERKeltnerIgnitionStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.nr_window = self.params.get("nr_window", 7)
        self.er_period = self.params.get("er_period", 20)
        self.er_threshold = self.params.get("er_threshold", 0.25)
        self.ema_fast = self.params.get("ema_fast", 10)
        self.ema_slow = self.params.get("ema_slow", 30)
        self.vol_period = self.params.get("vol_period", 25)
        self.vol_multiplier = self.params.get("vol_multiplier", 0.95)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.4)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.0)
        self.keltner_period = self.params.get("keltner_period", 20)
        self.keltner_mult = self.params.get("keltner_mult", 1.4)
        self.min_bars = max(self.nr_window + 4, self.er_period + 30, self.atr_period + 10, 120)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        open_ = data["open"]
        high = data["high"]
        low = data["low"]
        close = data["close"]
        volume = data["volume"]

        bar_seconds = self._bar_seconds(data)
        tf_scale = max(0.6, min(1.8, bar_seconds / 180.0))

        atr = self._atr(data, self.atr_period)
        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
        vol_ma = volume.rolling(self.vol_period, min_periods=1).mean()

        direction = (close - close.shift(self.er_period)).abs()
        volatility = close.diff().abs().rolling(self.er_period, min_periods=1).sum()
        er = direction / (volatility + 1e-12)

        price = float(close.iloc[-1])
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        range_high = float(high.iloc[-self.nr_window - 1 : -1].max())
        range_low = float(low.iloc[-self.nr_window - 1 : -1].min())

        vol_ratio = float(volume.iloc[-1]) / (float(vol_ma.iloc[-1]) + 1e-12)
        vol_ok = vol_ratio >= self.vol_multiplier
        er_now = float(er.iloc[-1])
        er_ok = er_now >= self.er_threshold
        bull_trend = float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1])
        bear_trend = float(ema_fast.iloc[-1]) < float(ema_slow.iloc[-1])

        k_mid = close.ewm(span=self.keltner_period, adjust=False).mean()
        k_up = k_mid + self.keltner_mult * atr
        k_dn = k_mid - self.keltner_mult * atr

        if not (vol_ok and er_ok):
            return []

        tp_mult = self.tp_atr_mult * np.sqrt(tf_scale)
        sl_mult = self.sl_atr_mult * np.sqrt(tf_scale)

        signals: List[Signal] = []
        if price >= range_high * 0.999 and bull_trend and float(close.iloc[-1]) > float(open_.iloc[-1]) and (price > float(k_up.iloc[-1])):
            conf = min(0.95, 0.57 + min(0.18, (vol_ratio - self.vol_multiplier) * 0.11) + min(0.12, (er_now - self.er_threshold) * 0.25))
            signals.append(self._mk(symbol, "BUY", price, atr_now, tp_mult, sl_mult, conf, "short-term breakout ignition long"))
        elif price <= range_low * 1.001 and bear_trend and float(close.iloc[-1]) < float(open_.iloc[-1]) and (price < float(k_dn.iloc[-1])):
            conf = min(0.95, 0.57 + min(0.18, (vol_ratio - self.vol_multiplier) * 0.11) + min(0.12, (er_now - self.er_threshold) * 0.25))
            signals.append(self._mk(symbol, "SELL", price, atr_now, tp_mult, sl_mult, conf, "short-term breakout ignition short"))

        return signals

    def _mk(self, symbol: str, side: str, px: float, atr: float, tp_mult: float, sl_mult: float, conf: float, reason: str) -> Signal:
        if side == "BUY":
            tp = px + tp_mult * atr
            sl = px - sl_mult * atr
        else:
            tp = px - tp_mult * atr
            sl = px + sl_mult * atr
        return Signal(symbol, side, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    @staticmethod
    def _bar_seconds(data: pd.DataFrame) -> float:
        if "timestamp" not in data.columns or len(data) < 3:
            return 300.0
        ts = pd.to_datetime(data["timestamp"], errors="coerce")
        diffs = ts.diff().dropna().dt.total_seconds()
        if len(diffs) == 0:
            return 300.0
        med = float(diffs.median())
        return med if med > 0 else 300.0

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(123)
    n = 280
    r = np.random.normal(0.0004, 0.02, n)
    p = 12000 * np.exp(np.cumsum(r))
    ts = pd.date_range("2026-01-01", periods=n, freq="5min")
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "open": p * (1 + np.random.normal(0, 0.001, n)),
            "high": p * (1 + np.abs(np.random.normal(0, 0.011, n))),
            "low": p * (1 - np.abs(np.random.normal(0, 0.011, n))),
            "close": p,
            "volume": np.random.lognormal(7.0, 0.55, n),
        }
    )
    strat = CryptoShortTermNRERKeltnerIgnitionStrategy()
    print(len(strat.generate_signals(df, "BTCUSDT")))
