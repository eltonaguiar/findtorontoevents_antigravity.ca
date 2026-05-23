"""
FearGreed_Reversion - Baby Strat
================================

Created by: web_ai
Date: 2026-02-27

Concept:
- Contrarian mean reversion on sentiment extremes.
- Buy extreme fear, sell extreme greed, with trend + volume confirmation.

Core Rules:
- BUY when Fear & Greed < 25, price < SMA(20), volume > 1.2x average.
- SELL when Fear & Greed > 75, price > SMA(20), volume > 1.2x average.
- SL fixed at 5% from entry.
- TP targets neutralization (price back toward SMA / neutral zone proxy).
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


class FearGreedReversionStrategy:
    """Sentiment-driven contrarian mean reversion."""

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.fear_threshold = p.get("fear_threshold", 25.0)
        self.greed_threshold = p.get("greed_threshold", 75.0)
        self.neutral_level = p.get("neutral_level", 50.0)
        self.sma_period = p.get("sma_period", 20)
        self.volume_period = p.get("volume_period", 20)
        self.volume_multiplier = p.get("volume_multiplier", 1.2)
        self.stop_loss_pct = p.get("stop_loss_pct", 0.05)
        self.tp_buffer_pct = p.get("tp_buffer_pct", 0.03)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        required = {"close", "high", "low", "volume"}
        if not required.issubset(data.columns):
            return []
        if len(data) < max(self.sma_period, self.volume_period) + 10:
            return []

        close = pd.to_numeric(data["close"], errors="coerce")
        volume = pd.to_numeric(data["volume"], errors="coerce")
        sma = close.rolling(self.sma_period).mean()
        vol_avg = volume.rolling(self.volume_period).mean()
        fear_greed = self._fear_greed_series(data)

        price = float(close.iloc[-1])
        sma_now = float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else price
        vol_now = float(volume.iloc[-1]) if not pd.isna(volume.iloc[-1]) else 0.0
        vol_avg_now = float(vol_avg.iloc[-1]) if not pd.isna(vol_avg.iloc[-1]) else max(vol_now, 1.0)
        fg_now = float(fear_greed.iloc[-1]) if not pd.isna(fear_greed.iloc[-1]) else 50.0

        if price <= 0 or vol_avg_now <= 0:
            return []

        volume_ok = vol_now > (vol_avg_now * self.volume_multiplier)

        # BUY: extreme fear + below SMA + confirmed volume
        if fg_now < self.fear_threshold and price < sma_now and volume_ok:
            vol_ratio = vol_now / vol_avg_now
            fear_edge = (self.fear_threshold - fg_now) / max(self.fear_threshold, 1e-9)
            confidence = min(0.95, 0.62 + fear_edge * 0.23 + min(vol_ratio - 1.0, 1.0) * 0.10)
            tp = max(sma_now, price * (1.0 + self.tp_buffer_pct))
            sl = price * (1.0 - self.stop_loss_pct)
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"FG={fg_now:.1f}< {self.fear_threshold:.0f}, price<SMA{self.sma_period}, vol={vol_ratio:.2f}x",
            )]

        # SELL: extreme greed + above SMA + confirmed volume
        if fg_now > self.greed_threshold and price > sma_now and volume_ok:
            vol_ratio = vol_now / vol_avg_now
            greed_edge = (fg_now - self.greed_threshold) / max(100.0 - self.greed_threshold, 1e-9)
            confidence = min(0.95, 0.62 + greed_edge * 0.23 + min(vol_ratio - 1.0, 1.0) * 0.10)
            tp = min(sma_now, price * (1.0 - self.tp_buffer_pct))
            sl = price * (1.0 + self.stop_loss_pct)
            return [Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"FG={fg_now:.1f}> {self.greed_threshold:.0f}, price>SMA{self.sma_period}, vol={vol_ratio:.2f}x",
            )]

        return []

    def _fear_greed_series(self, data: pd.DataFrame) -> pd.Series:
        # Preferred external sentiment feed.
        for col in ("fear_greed_index", "fear_greed", "sentiment_index"):
            if col in data.columns:
                s = pd.to_numeric(data[col], errors="coerce").fillna(self.neutral_level)
                return s.clip(0, 100)

        # Fallback proxy from market state when external feed is absent.
        close = pd.to_numeric(data["close"], errors="coerce").ffill()
        returns = close.pct_change().fillna(0.0)
        drawdown = (close / close.rolling(50, min_periods=5).max() - 1.0).fillna(0.0)

        ret_mean = returns.rolling(20, min_periods=5).mean()
        ret_std = returns.rolling(20, min_periods=5).std().replace(0, np.nan)
        ret_z = (ret_mean / ret_std).fillna(0.0)

        dd_mean = drawdown.rolling(50, min_periods=5).mean()
        dd_std = drawdown.rolling(50, min_periods=5).std().replace(0, np.nan)
        dd_z = ((drawdown - dd_mean) / dd_std).fillna(0.0)

        proxy = 50.0 + (ret_z * 18.0) + (dd_z * 12.0)
        return proxy.clip(0, 100)


if __name__ == "__main__":
    np.random.seed(42)
    n = 240
    prices = 50000 * np.exp(np.cumsum(np.random.normal(0.0002, 0.018, n)))
    fg = np.clip(50 + np.random.normal(0, 18, n), 0, 100)
    fg[-1] = 18  # force extreme fear on last bar for sanity check

    df = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.01, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.01, n))),
        "close": prices,
        "volume": np.random.uniform(100, 1200, n),
        "fear_greed_index": fg,
    })

    strat = FearGreedReversionStrategy()
    sigs = strat.generate_signals(df)
    print(f"Generated {len(sigs)} signal(s).")
    for s in sigs:
        print(s)
