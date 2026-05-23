"""
Crypto ICT Fair Value Gap Rebalance Golden - Baby Strat

Design reference:
- ICT displacement + fair value gap (FVG) rebalance
- Toby Crabel narrow-range expansion for timing quality
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoICTFVGRebalanceGoldenStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.nr_window = self.params.get("nr_window", 6)
        self.fast_ema = self.params.get("fast_ema", 10)
        self.slow_ema = self.params.get("slow_ema", 24)
        self.atr_period = self.params.get("atr_period", 16)
        self.vol_period = self.params.get("vol_period", 25)
        self.vol_multiplier = self.params.get("vol_multiplier", 1.35)
        self.fvg_lookback = self.params.get("fvg_lookback", 40)
        self.fvg_max_age = self.params.get("fvg_max_age", 30)
        self.displacement_atr_mult = self.params.get("displacement_atr_mult", 0.65)
        self.fvg_retest_buffer_atr = self.params.get("fvg_retest_buffer_atr", 0.55)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.2)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.0)
        self.min_bars = 120

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        open_ = data["open"]
        high = data["high"]
        low = data["low"]
        close = data["close"]
        volume = data["volume"]

        atr = self._atr(data, self.atr_period)
        atr_now = float(atr.iloc[-1])
        if atr_now <= 0:
            return []

        ema_fast = close.ewm(span=self.fast_ema, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_ema, adjust=False).mean()
        vol_ma = volume.rolling(self.vol_period, min_periods=1).mean()

        if len(data) < self.nr_window + 4:
            return []

        rng = high - low
        nr_prev = float(rng.iloc[-2]) <= float(rng.iloc[-self.nr_window - 2 : -1].min())
        mother_high = float(high.iloc[-3])
        mother_low = float(low.iloc[-3])
        inside_prev = float(high.iloc[-2]) <= mother_high and float(low.iloc[-2]) >= mother_low
        vol_ratio = float(volume.iloc[-1]) / (float(vol_ma.iloc[-1]) + 1e-12)
        if not nr_prev or not inside_prev or vol_ratio < self.vol_multiplier:
            return []

        price = float(close.iloc[-1])
        trend_up = float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1])
        trend_down = float(ema_fast.iloc[-1]) < float(ema_slow.iloc[-1])

        bull_gap = self._latest_fvg(open_, high, low, close, volume, atr, vol_ma, "bull")
        bear_gap = self._latest_fvg(open_, high, low, close, volume, atr, vol_ma, "bear")

        signals: List[Signal] = []
        if trend_up and bull_gap is not None:
            gap_low, gap_high, age, disp = bull_gap
            fvg_retest_ok = float(low.iloc[-1]) <= gap_high + self.fvg_retest_buffer_atr * atr_now
            if (
                age <= self.fvg_max_age
                and fvg_retest_ok
                and price > mother_high
                and float(close.iloc[-1]) > float(open_.iloc[-1])
            ):
                conf = self._confidence(vol_ratio, disp)
                signals.append(self._mk(symbol, "BUY", price, atr_now, conf, "ICT bullish FVG rebalance + NR expansion"))

        if trend_down and bear_gap is not None:
            gap_low, gap_high, age, disp = bear_gap
            fvg_retest_ok = float(high.iloc[-1]) >= gap_low - self.fvg_retest_buffer_atr * atr_now
            if (
                age <= self.fvg_max_age
                and fvg_retest_ok
                and price < mother_low
                and float(close.iloc[-1]) < float(open_.iloc[-1])
            ):
                conf = self._confidence(vol_ratio, disp)
                signals.append(self._mk(symbol, "SELL", price, atr_now, conf, "ICT bearish FVG rebalance + NR expansion"))
        return signals

    def _latest_fvg(
        self,
        open_: pd.Series,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        atr: pd.Series,
        vol_ma: pd.Series,
        direction: str,
    ) -> Optional[Tuple[float, float, int, float]]:
        start = max(2, len(close) - self.fvg_lookback)
        for i in range(len(close) - 1, start - 1, -1):
            mid = i - 1
            if mid <= 0:
                continue

            displacement = abs(float(close.iloc[mid] - open_.iloc[mid]))
            atr_mid = float(atr.iloc[mid]) if float(atr.iloc[mid]) > 0 else 1e-9
            vol_ratio_mid = float(volume.iloc[mid]) / (float(vol_ma.iloc[mid]) + 1e-12)
            if displacement < self.displacement_atr_mult * atr_mid or vol_ratio_mid < 1.0:
                continue

            if direction == "bull" and float(low.iloc[i]) > float(high.iloc[i - 2]):
                gap_low = float(high.iloc[i - 2])
                gap_high = float(low.iloc[i])
                return gap_low, gap_high, len(close) - 1 - i, displacement / (atr_mid + 1e-12)
            if direction == "bear" and float(high.iloc[i]) < float(low.iloc[i - 2]):
                gap_low = float(high.iloc[i])
                gap_high = float(low.iloc[i - 2])
                return gap_low, gap_high, len(close) - 1 - i, displacement / (atr_mid + 1e-12)
        return None

    @staticmethod
    def _confidence(vol_ratio: float, displacement_score: float) -> float:
        vol_term = min(0.22, max(0.0, (vol_ratio - 1.0) / 2.0))
        disp_term = min(0.16, max(0.0, (displacement_score - 0.6) / 3.0))
        return round(min(0.95, 0.56 + vol_term + disp_term), 3)

    def _mk(self, symbol: str, side: str, px: float, atr: float, conf: float, reason: str) -> Signal:
        if side == "BUY":
            tp = px + self.tp_atr_mult * atr
            sl = px - self.sl_atr_mult * atr
        else:
            tp = px - self.tp_atr_mult * atr
            sl = px + self.sl_atr_mult * atr
        return Signal(symbol, side, conf, round(px, 2), round(tp, 2), round(sl, 2), reason)

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(34)
    n = 380
    ret = np.random.normal(0.00035, 0.02, n)
    px = 15000 * np.exp(np.cumsum(ret))
    df = pd.DataFrame(
        {
            "open": px * (1 + np.random.normal(0, 0.001, n)),
            "high": px * (1 + np.abs(np.random.normal(0, 0.011, n))),
            "low": px * (1 - np.abs(np.random.normal(0, 0.011, n))),
            "close": px,
            "volume": np.random.lognormal(7, 0.55, n),
        }
    )
    s = CryptoICTFVGRebalanceGoldenStrategy()
    print(len(s.generate_signals(df)))
