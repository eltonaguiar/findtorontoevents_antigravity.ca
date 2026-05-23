"""
DXY_Divergence_Alpha - Baby Strat
=================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when BTC-DXY rolling correlation decouples above -0.2,
  BTC is above EMA(50), and ATR regime is expanding.
- Exit model embedded in signal levels:
  - TP uses ATR-based expansion target
  - SL uses ATR-based protective stop

Reference mindset:
- Bridgewater-style macro relative-strength divergence
- CTA trend filter to avoid catching weak decouplings
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple


@dataclass
class Signal:
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class DXYDivergenceStrategy:
    """BTC relative strength vs DXY decoupling."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.corr_window = self.p.get("corr_window", 20)
        self.corr_threshold = self.p.get("corr_threshold", -0.2)
        self.exit_corr_threshold = self.p.get("exit_corr_threshold", -0.7)
        self.ma_period = self.p.get("ma_period", 50)
        self.atr_mult = self.p.get("atr_mult", 2.5)
        self.atr_period = self.p.get("atr_period", 14)
        self.atr_expand_window = self.p.get("atr_expand_window", 30)
        self.atr_expand_ratio = self.p.get("atr_expand_ratio", 1.05)

    def generate_signals(
        self,
        btc_data: pd.DataFrame,
        dxy_data: pd.DataFrame,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if not {"close", "high", "low"}.issubset(set(btc_data.columns)):
            return []
        if "close" not in dxy_data.columns:
            return []

        btc_close, dxy_close = self._align_close_series(btc_data["close"], dxy_data["close"])
        if btc_close is None or dxy_close is None:
            return []

        min_len = max(self.ma_period, self.corr_window, self.atr_expand_window, self.atr_period) + 5
        if len(btc_close) < min_len or len(btc_data) < min_len:
            return []

        corr = btc_close.rolling(self.corr_window).corr(dxy_close)
        curr_corr = corr.iloc[-1]
        if pd.isna(curr_corr):
            return []

        ema = btc_close.ewm(span=self.ma_period, adjust=False).mean()
        price = btc_close.iloc[-1]
        in_uptrend = price > ema.iloc[-1]

        atr_series = self._calc_atr(btc_data, self.atr_period)
        atr = atr_series.iloc[-1]
        atr_avg = atr_series.rolling(self.atr_expand_window).mean().iloc[-1]
        atr_expanding = (atr > atr_avg * self.atr_expand_ratio) if (not pd.isna(atr_avg) and atr_avg > 0) else False

        # Exit condition model note:
        # correlation reversion below -0.7 would be handled by position manager;
        # this stateless generator focuses on new entry gating.
        if curr_corr > self.corr_threshold and in_uptrend and atr_expanding:
            edge_corr = min(max((curr_corr - self.corr_threshold) / 0.8, 0.0), 1.0)
            edge_trend = min(max((price / (ema.iloc[-1] + 1e-12) - 1.0) / 0.05, 0.0), 1.0)
            edge_vol = min(max((atr / (atr_avg + 1e-12) - self.atr_expand_ratio) / 0.5, 0.0), 1.0)
            confidence = float(round(min(0.9, 0.52 + 0.2 * edge_corr + 0.1 * edge_trend + 0.08 * edge_vol), 2))

            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=confidence,
                entry_price=float(round(price, 2)),
                take_profit=float(round(price + (atr * self.atr_mult * 1.5), 2)),
                stop_loss=float(round(price - (atr * self.atr_mult), 2)),
                reason=(
                    f"DXY Decoupling corr={curr_corr:.2f} > {self.corr_threshold:.2f} | "
                    f"EMA50 trend UP | ATR expanding ({atr / (atr_avg + 1e-12):.2f}x)"
                ),
            )]
        return []

    @staticmethod
    def _align_close_series(btc_close: pd.Series, dxy_close: pd.Series) -> Tuple[Optional[pd.Series], Optional[pd.Series]]:
        if isinstance(btc_close.index, pd.DatetimeIndex) and isinstance(dxy_close.index, pd.DatetimeIndex):
            aligned = pd.concat(
                [btc_close.rename("btc"), dxy_close.rename("dxy")],
                axis=1,
                join="inner",
            ).dropna()
            if len(aligned) == 0:
                return None, None
            return aligned["btc"], aligned["dxy"]

        n = min(len(btc_close), len(dxy_close))
        if n == 0:
            return None, None
        return btc_close.iloc[-n:].reset_index(drop=True), dxy_close.iloc[-n:].reset_index(drop=True)

    @staticmethod
    def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()


if __name__ == "__main__":
    np.random.seed(123)
    t = np.linspace(0, 120, 260)

    # Synthetic regime: BTC uptrend while DXY also trends up (decoupling)
    btc_close = 50000 + t * 120 + np.random.randn(len(t)) * 80
    dxy_close = 100 + t * 0.08 + np.random.randn(len(t)) * 0.06

    btc = pd.DataFrame({
        "close": btc_close,
        "high": btc_close + np.random.rand(len(t)) * 30,
        "low": btc_close - np.random.rand(len(t)) * 30,
    })
    dxy = pd.DataFrame({"close": dxy_close})

    strat = DXYDivergenceStrategy()
    signals = []
    for i in range(90, len(btc)):
        signals.extend(strat.generate_signals(btc.iloc[: i + 1], dxy.iloc[: i + 1]))

    print(f"Generated {len(signals)} signal(s).")
    for s in signals[:3]:
        print(f"{s.direction} {s.symbol} - {s.reason}")

