"""
WhaleVWAP_Breakout - Baby Strat
===============================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when:
  1) Price > 1-hour rolling VWAP by >= 0.5%
  2) Whale net inflow (last hour) > 2x 24-hour rolling average
  3) Funding rate < 0
- Exit when:
  - TP: +2x ATR(14)
  - SL: -1.5x ATR(14)
- Filter:
  - Skip entries when realized volatility is in extreme spike regime

Reference mindset:
- Flow-desk confirmation first, breakout second.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class Signal:
    symbol: str
    direction: str          # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class WhaleVWAPBreakoutStrategy:
    """VWAP breakout + whale inflow confirmation."""

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.vwap_window = p.get("vwap_window", 60)          # minutes
        self.vwap_thr = p.get("vwap_thr", 0.005)            # 0.5%
        self.whale_mult = p.get("whale_mult", 2.0)          # 2x avg inflow
        self.atr_period = p.get("atr_period", 14)
        self.tp_atr = p.get("tp_atr", 2.0)
        self.sl_atr = p.get("sl_atr", 1.5)
        self.vol_window = p.get("vol_window", 30)           # days
        self.vol_thr = p.get("vol_thr", 1.20)               # 120%

    def generate_signals(
        self,
        data: pd.DataFrame,
        whale_inflow: Optional[pd.Series] = None,
        funding_rate: float = 0.0,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        """Return at most one BUY signal."""
        min_len = max(self.vwap_window, self.atr_period) + 10
        if len(data) < min_len:
            return []

        required_cols = {"close", "high", "low", "volume"}
        if not required_cols.issubset(set(data.columns)):
            return []

        if whale_inflow is None or len(whale_inflow) < 25:
            return []

        # ---- indicators -------------------------------------------------
        vwap = self._vwap(data["close"], data["volume"], self.vwap_window)
        atr = self._atr(data, self.atr_period)

        price = data["close"].iloc[-1]
        cur_vwap = vwap.iloc[-1]
        cur_atr = atr.iloc[-1]
        if pd.isna(cur_vwap) or pd.isna(cur_atr):
            return []

        # ---- whale confirmation -----------------------------------------
        whale_hourly = self._to_hourly_inflow(whale_inflow, data.index)
        if whale_hourly is None or len(whale_hourly) < 24:
            return []
        inflow_hour = whale_hourly.iloc[-1]
        inflow_avg_24h = whale_hourly.rolling(24).mean().iloc[-1]
        if pd.isna(inflow_avg_24h) or inflow_avg_24h <= 0:
            return []
        inflow_ratio = inflow_hour / inflow_avg_24h
        whale_ok = inflow_ratio > self.whale_mult

        # ---- volatility filter ------------------------------------------
        vol_ok = self._volatility_filter_ok(data["close"])

        # ---- entry condition --------------------------------------------
        vwap_gap = price / cur_vwap - 1.0
        if vwap_gap >= self.vwap_thr and whale_ok and funding_rate < 0 and vol_ok:
            confidence = 0.75 + min(max((inflow_ratio - self.whale_mult) / 3.0, 0.0), 0.2)
            tp = price + cur_atr * self.tp_atr
            sl = price - cur_atr * self.sl_atr
            reason = (
                f"VWAP breakout {vwap_gap:.2%} | "
                f"Whale inflow {inflow_hour:.0f} ({inflow_ratio:.1f}x 24h avg) | "
                f"Funding {funding_rate:.4f}"
            )
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=float(round(min(confidence, 0.95), 2)),
                entry_price=float(round(price, 2)),
                take_profit=float(round(tp, 2)),
                stop_loss=float(round(sl, 2)),
                reason=reason,
            )]
        return []

    def _volatility_filter_ok(self, close: pd.Series) -> bool:
        """
        Realized volatility spike filter.

        Uses the requested 30-day design on minute data where possible.
        If history is shorter, falls back to an adaptive proxy to avoid dead
        strategy behavior during bootstrap periods.
        """
        returns = close.pct_change()
        full_window = self.vol_window * 24 * 60  # 30 days in minutes

        if len(close) >= full_window * 2:
            vol_now = returns.rolling(full_window).std().iloc[-1]
            vol_avg = returns.rolling(full_window).std().rolling(full_window).mean().iloc[-1]
        else:
            short_w = max(240, min(len(close) // 2, 1440))  # 4h to 1d proxy
            vol_series = returns.rolling(short_w).std()
            vol_now = vol_series.iloc[-1]
            vol_avg = vol_series.rolling(short_w).mean().iloc[-1]

        if pd.isna(vol_now) or pd.isna(vol_avg) or vol_avg <= 0:
            return False
        return (vol_now / vol_avg) < self.vol_thr

    @staticmethod
    def _to_hourly_inflow(whale_inflow: pd.Series, price_index: pd.Index) -> Optional[pd.Series]:
        """
        Convert whale inflow to hourly series robustly.
        """
        s = whale_inflow.copy()
        if not isinstance(s.index, pd.DatetimeIndex):
            # If non-datetime, treat as already hourly samples.
            return s.dropna()

        # Align to market data timeline and forward fill latest inflow.
        if isinstance(price_index, pd.DatetimeIndex):
            s = s.reindex(price_index.union(s.index)).sort_index().ffill()
            s = s.reindex(price_index).ffill()

        hourly = s.resample("1h").last().dropna()
        return hourly

    @staticmethod
    def _vwap(price: pd.Series, volume: pd.Series, window: int) -> pd.Series:
        """Rolling VWAP over `window` periods."""
        pv = price * volume
        return pv.rolling(window).sum() / (volume.rolling(window).sum() + 1e-12)

    @staticmethod
    def _atr(df: pd.DataFrame, period: int) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()


if __name__ == "__main__":
    # Synthetic OHLCV data (1-min candles)
    np.random.seed(42)
    n = 3000
    rng = pd.date_range("2026-01-01", periods=n, freq="min")
    close = np.cumsum(np.random.randn(n) * 4) + 20000
    high = close + np.random.rand(n) * 3
    low = close - np.random.rand(n) * 3
    volume = np.random.rand(n) * 10 + 1

    data = pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume}, index=rng)

    # Synthetic hourly whale inflow
    whale_hourly = pd.Series(np.random.randn(n // 60 + 5) * 200 + 2000, index=pd.date_range(rng[0], periods=n // 60 + 5, freq="1h"))
    whale_minute = whale_hourly.reindex(rng, method="ffill")

    # Force last-hour confirmation for deterministic signal path
    data.iloc[-1, data.columns.get_loc("close")] = data["close"].iloc[-120:-1].max() * 1.01
    data.iloc[-1, data.columns.get_loc("high")] = data["close"].iloc[-1] * 1.001
    whale_minute.iloc[-1] = whale_minute.iloc[-24 * 60:-1].mean() * 2.4

    strat = WhaleVWAPBreakoutStrategy({"vol_thr": 10.0})
    sigs = strat.generate_signals(
        data,
        whale_inflow=whale_minute,
        funding_rate=-0.015,
        symbol="BTCUSDT",
    )
    print(f"Generated {len(sigs)} signal(s).")
    for s in sigs:
        print(s)
