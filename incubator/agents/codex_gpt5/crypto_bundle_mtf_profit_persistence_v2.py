"""
Crypto Bundle MTF Profit Persistence - Baby Strat

Design reference:
- Multi-timeframe trend persistence (4h regime + 1h execution + 15m confirmation)
- High-frequency trend pullback execution for larger sample size
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


class CryptoBundleMTFProfitPersistenceStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}

        # 1h execution layer
        self.atr_period = self.params.get("atr_period", 14)
        self.ema_fast = self.params.get("ema_fast", 8)
        self.ema_slow = self.params.get("ema_slow", 42)
        self.rsi_period = self.params.get("rsi_period", 10)

        # 4h regime layer
        self.ema4_fast = self.params.get("ema4_fast", 8)
        self.ema4_slow = self.params.get("ema4_slow", 26)
        self.slope_lookback = self.params.get("slope_lookback", 1)

        # 15m timing layer
        self.ema15_fast = self.params.get("ema15_fast", 8)
        self.ema15_slow = self.params.get("ema15_slow", 24)

        # entry gates
        self.rsi_long_min = self.params.get("rsi_long_min", 52)
        self.rsi_short_max = self.params.get("rsi_short_max", 50)
        self.pullback_max = self.params.get("pullback_max", 0.6)

        # risk/reward
        self.tp_atr_mult = self.params.get("tp_atr_mult", 1.6)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.0)

        self.min_bars = 140

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT",
        data_4h: Optional[pd.DataFrame] = None,
        data_15m: Optional[pd.DataFrame] = None,
    ) -> List[Signal]:
        bar_hours = self._bar_interval_hours(data) if data is not None else 1.0
        required_bars = 20 if bar_hours >= 12.0 else self.min_bars
        if data is None or len(data) < required_bars:
            return []

        direction_mode = str(self.params.get("direction", "BOTH")).upper()
        coarse_mode = bar_hours >= 3.5

        # Backtest utilities sometimes provide only a single timeframe input.
        # Build internal MTF fallbacks from the provided data when needed.
        if data_4h is None or len(data_4h) < 40:
            data_4h = self._fallback_htf(data)
        if data_15m is None or len(data_15m) < 40:
            data_15m = self._fallback_ltf(data)
        if data_4h is None or len(data_4h) < 20:
            return []

        close = data["close"]
        atr = self._atr(data, self.atr_period)
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
        rsi = self._rsi(close, self.rsi_period)
        rsi_now = float(rsi.iloc[-1])

        close_4h = data_4h["close"]
        ema4_fast = close_4h.ewm(span=self.ema4_fast, adjust=False).mean()
        ema4_slow = close_4h.ewm(span=self.ema4_slow, adjust=False).mean()
        if len(ema4_fast) < self.slope_lookback + 2:
            return []

        trend_up_4h = float(ema4_fast.iloc[-1]) > float(ema4_slow.iloc[-1])
        trend_dn_4h = float(ema4_fast.iloc[-1]) < float(ema4_slow.iloc[-1])
        slope_4h = float(ema4_fast.iloc[-1] - ema4_fast.iloc[-1 - self.slope_lookback])

        px = float(close.iloc[-1])
        trend_up_1h = float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1])
        trend_dn_1h = float(ema_fast.iloc[-1]) < float(ema_slow.iloc[-1])
        pullback_dist = abs(px - float(ema_fast.iloc[-1])) / (atr_now + 1e-12)

        if data_15m is not None and len(data_15m) >= 60:
            close_15m = data_15m["close"]
            ema15_fast = close_15m.ewm(span=self.ema15_fast, adjust=False).mean()
            ema15_slow = close_15m.ewm(span=self.ema15_slow, adjust=False).mean()
            trend_up_15m = float(ema15_fast.iloc[-1]) > float(ema15_slow.iloc[-1])
            trend_dn_15m = float(ema15_fast.iloc[-1]) < float(ema15_slow.iloc[-1])
        else:
            trend_up_15m = True
            trend_dn_15m = True

        long_bias = trend_up_4h and slope_4h > 0 and trend_up_1h and trend_up_15m
        short_bias = trend_dn_4h and slope_4h < 0 and trend_dn_1h and trend_dn_15m

        if coarse_mode:
            # Coarse timeframe mode (4h/1d): use slower reclaim triggers to avoid overtrading.
            long_regime = trend_up_4h and trend_up_1h
            short_regime = trend_dn_4h and trend_dn_1h
            reclaim_up = len(close) >= 2 and float(close.iloc[-2]) <= float(ema_fast.iloc[-2]) and px > float(ema_fast.iloc[-1])
            reclaim_dn = len(close) >= 2 and float(close.iloc[-2]) >= float(ema_fast.iloc[-2]) and px < float(ema_fast.iloc[-1])

            if direction_mode != "SHORT" and long_regime and reclaim_up and rsi_now >= 45:
                conf = min(0.95, 0.52 + min(0.2, (rsi_now - 50.0) / 100.0))
                return [
                    self._mk(
                        symbol,
                        "BUY",
                        px,
                        atr_now,
                        conf,
                        "MTF coarse continuation long",
                        tp_mult=self.tp_atr_mult * 1.1,
                        sl_mult=self.sl_atr_mult * 1.0,
                    )
                ]

            if direction_mode != "LONG" and short_regime and reclaim_dn and rsi_now <= 55:
                conf = min(0.95, 0.52 + min(0.2, (50.0 - rsi_now) / 100.0))
                return [
                    self._mk(
                        symbol,
                        "SELL",
                        px,
                        atr_now,
                        conf,
                        "MTF coarse continuation short",
                        tp_mult=self.tp_atr_mult * 1.1,
                        sl_mult=self.sl_atr_mult * 1.0,
                    )
                ]
        else:
            # Intraday mode (1h): high-frequency pullback entries for deep sample size.
            if direction_mode != "SHORT" and long_bias and rsi_now >= self.rsi_long_min and pullback_dist <= self.pullback_max:
                conf = min(0.95, 0.53 + min(0.2, (rsi_now - self.rsi_long_min) / 100.0))
                return [self._mk(symbol, "BUY", px, atr_now, conf, "MTF persistent uptrend pullback")]

            if direction_mode != "LONG" and short_bias and rsi_now <= self.rsi_short_max and pullback_dist <= self.pullback_max:
                conf = min(0.95, 0.53 + min(0.2, (self.rsi_short_max - rsi_now) / 100.0))
                return [self._mk(symbol, "SELL", px, atr_now, conf, "MTF persistent downtrend pullback")]

        return []

    def _mk(
        self,
        symbol: str,
        side: str,
        px: float,
        atr: float,
        conf: float,
        reason: str,
        tp_mult: Optional[float] = None,
        sl_mult: Optional[float] = None,
    ) -> Signal:
        tp_scale = self.tp_atr_mult if tp_mult is None else tp_mult
        sl_scale = self.sl_atr_mult if sl_mult is None else sl_mult
        if side == "BUY":
            tp = px + tp_scale * atr
            sl = px - sl_scale * atr
        else:
            tp = px - tp_scale * atr
            sl = px + sl_scale * atr
        return Signal(symbol, side, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    @staticmethod
    def _rsi(close: pd.Series, period: int) -> pd.Series:
        d = close.diff()
        up = d.where(d > 0, 0.0)
        dn = -d.where(d < 0, 0.0)
        avg_up = up.rolling(period, min_periods=1).mean()
        avg_dn = dn.rolling(period, min_periods=1).mean()
        rs = avg_up / (avg_dn + 1e-12)
        return 100 - 100 / (1 + rs)

    def _fallback_htf(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        x = self._to_time_indexed(data)
        if x is None or len(x) < 20:
            return data
        # Use 4h aggregation when possible; fallback to original frame otherwise.
        y = x.resample("4h").agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        ).dropna()
        if len(y) >= 20:
            return y.reset_index()
        return data

    def _fallback_ltf(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        # Without true intraday ticks, best fallback is same-frame momentum proxy.
        return data

    @staticmethod
    def _to_time_indexed(data: pd.DataFrame) -> Optional[pd.DataFrame]:
        if "timestamp" in data.columns:
            x = data.copy()
            x["timestamp"] = pd.to_datetime(x["timestamp"], errors="coerce", utc=True)
            x = x.dropna(subset=["timestamp"]).set_index("timestamp")
            return x
        if isinstance(data.index, pd.DatetimeIndex):
            return data.copy()
        return None

    @staticmethod
    def _bar_interval_hours(data: pd.DataFrame) -> float:
        if "timestamp" in data.columns:
            ts = pd.to_datetime(data["timestamp"], errors="coerce", utc=True).dropna()
        elif isinstance(data.index, pd.DatetimeIndex):
            ts = pd.to_datetime(pd.Series(data.index), errors="coerce", utc=True).dropna()
        else:
            return 1.0
        if len(ts) < 2:
            return 1.0
        dt = ts.diff().dropna().dt.total_seconds() / 3600.0
        if len(dt) == 0:
            return 1.0
        return float(dt.median())


if __name__ == "__main__":
    np.random.seed(42)
    n = 360
    returns = np.random.normal(0.0003, 0.018, n)
    prices = 12000 * np.exp(np.cumsum(returns))
    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.001, n)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.01, n))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.01, n))),
            "close": prices,
            "volume": np.random.lognormal(7, 0.55, n),
        }
    )
    s = CryptoBundleMTFProfitPersistenceStrategy()
    print(len(s.generate_signals(df)))
