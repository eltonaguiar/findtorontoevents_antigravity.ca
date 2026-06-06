"""
Fear & Greed Extreme Long v2 — Tighter Threshold + Long-Only
=============================================================

DNA Lineage
-----------
Parent:  st_fear_greed_contrarian / fear_greed_contrarian
         (WR 53% n=430, DSR+FDR PASS — just promoted to anti-overfit registry)
Axes:    #2 Direction gate (LONG_ONLY) + threshold tightening (Axis 4 variant)

Mutation Rationale (per docs/MUTATION_THREE_AXIS_PROTOCOL.md)
-------------------------------------------------------------
st_fear_greed_contrarian was just promoted (WR 53%, n=430). However, the
SHORT signals (fade Extreme Greed) drag down avg return — timing short
entries via sentiment alone is notoriously hard. The LONG direction (buy
Extreme Fear) has a clearer mechanical backing:

  1. Extreme Fear (FNG ≤ 20) historically precedes 30-90d recoveries in crypto
  2. Forced selling / liquidation cascades exhaust at these levels
  3. Funding rates go deeply negative → funding arbitrage creates structural bid
  4. Retail capitulates → smart money accumulates

This variant:
  - LONG_ONLY: removes all SHORT/contrarian-sell signals
  - Tightens FNG threshold: ≤ 15 (Extreme Fear only, not just Fear)
  - Expands to 10 symbols (parent used 5) to grow n
  - Uses 5-day FNG trend: only fire if FNG has been declining ≥ 3 of last 5 days
    (confirms capitulation phase, not just a brief dip)
  - Wider TP (8% → 12%) to let winners run on actual recoveries
  - Tighter SL (3% → 2.5%) since Extreme Fear entries have cleaner structure

Author: Claude Sonnet 4.6 — DNA mutation 2026-06-06
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

# Expanded symbol universe (parent used 5 SENTIMENT_TOKENS)
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "INJUSDT",
]

# Tighter threshold: only Extreme Fear (≤15 vs parent ≤20)
FNG_EXTREME_FEAR_THRESHOLD = 15
TP_PCT = 0.12   # wider TP — let recoveries run (parent: 0.06)
SL_PCT = 0.025  # tighter SL — cleaner structure at extreme fear entries


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class FearGreedExtremeLongV2:
    """
    Buy-only contrarian on extreme crypto fear with tightened FNG filter.

    This is a standalone version that can be backtested against historical
    FNG data + price OHLCV without requiring the live fear_greed_contrarian
    paper_trading infrastructure.

    For live use, pass fng_data (list of dicts with 'value' key, newest first)
    and price_data (dict of symbol → current_price).
    """

    MUTATION_PARENT = "st_fear_greed_contrarian"
    MUTATION_AXES = ["direction:long_only", "threshold:fng_leq15", "symbol:expanded_10"]

    def __init__(self, params: Optional[dict] = None) -> None:
        p = params or {}
        self.fng_threshold = p.get("fng_threshold", FNG_EXTREME_FEAR_THRESHOLD)
        self.tp_pct = p.get("tp_pct", TP_PCT)
        self.sl_pct = p.get("sl_pct", SL_PCT)
        self.trend_window = p.get("trend_window", 5)   # FNG lookback days
        self.min_declining_days = p.get("min_declining_days", 3)  # trend confirm

    def generate_signals(
        self,
        fng_data: List[dict],
        prices: dict,
    ) -> List[Signal]:
        """
        Args:
            fng_data: list of dicts [{value, value_classification, timestamp}, ...]
                      ordered newest-first (Alternative.me API format)
            prices:   {symbol: float} current prices

        Returns:
            List of Signal (LONG only, fires when Extreme Fear confirmed)
        """
        if not fng_data or len(fng_data) < self.trend_window:
            return []

        current_value = int(fng_data[0].get("value", 50))

        # Gate 1: must be Extreme Fear
        if current_value > self.fng_threshold:
            return []

        # Gate 2: FNG must have been declining ≥ min_declining_days
        # (confirms capitulation, not a one-day blip)
        recent_values = [int(d.get("value", 50)) for d in fng_data[:self.trend_window]]
        declining_days = sum(
            1 for i in range(len(recent_values) - 1)
            if recent_values[i] < recent_values[i + 1]  # lower than prior day
        )
        if declining_days < self.min_declining_days:
            return []

        # Scale confidence with depth below threshold
        depth = max(0, self.fng_threshold - current_value)
        confidence = min(0.92, 0.72 + depth * 0.02)

        signals = []
        for symbol in SYMBOLS:
            price = prices.get(symbol, 0.0)
            if price <= 0:
                continue
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(price, 6),
                take_profit=round(price * (1 + self.tp_pct), 6),
                stop_loss=round(price * (1 - self.sl_pct), 6),
                reason=(
                    f"FNG={current_value} (Extreme Fear ≤{self.fng_threshold}), "
                    f"{declining_days}/{self.trend_window - 1}d declining trend, "
                    f"TP={self.tp_pct:.0%} SL={self.sl_pct:.1%}"
                ),
            ))

        return signals

    def generate_signals_from_ohlcv(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT",
        fng_series: Optional[pd.Series] = None,
    ) -> List[Signal]:
        """
        Backtest-friendly interface: uses a synthetic FNG proxy (RSI(14) on
        BTC as a fear proxy) when real FNG data is unavailable.

        fng_series: pd.Series of daily FNG values indexed by date.
                    If None, uses RSI(14) rescaled to 0-100 as proxy.
        """
        if len(data) < 20:
            return []

        if fng_series is not None:
            # Use real FNG data aligned to data index
            fng_val = fng_series.reindex(data.index, method="ffill").iloc[-1]
            fng_vals = fng_series.reindex(data.index, method="ffill").iloc[-self.trend_window:].tolist()
        else:
            # Proxy: invert RSI (low RSI = high fear)
            rsi = self._rsi(data["close"], 14)
            fng_val = max(0, min(100, 100 - rsi.iloc[-1]))
            fng_vals = [max(0, min(100, 100 - v)) for v in rsi.iloc[-self.trend_window:].tolist()]

        if fng_val > self.fng_threshold:
            return []

        declining_days = sum(
            1 for i in range(len(fng_vals) - 1)
            if fng_vals[i] < fng_vals[i + 1]
        )
        if declining_days < self.min_declining_days:
            return []

        px = data["close"].iloc[-1]
        atr = self._atr(data).iloc[-1]
        if pd.isna(atr) or atr <= 0:
            return []

        depth = max(0, self.fng_threshold - fng_val)
        confidence = min(0.92, 0.72 + depth * 0.02)

        return [Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(confidence, 3),
            entry_price=round(px, 4),
            take_profit=round(px * (1 + self.tp_pct), 4),
            stop_loss=round(px * (1 - self.sl_pct), 4),
            reason=f"FNG_proxy={fng_val:.0f} Extreme Fear (≤{self.fng_threshold}), {declining_days}d decline",
        )]

    def _rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - 100 / (1 + rs)

    def _atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()


if __name__ == "__main__":
    # Quick smoke test using OHLCV proxy
    np.random.seed(99)
    n = 300
    rets = np.random.normal(-0.002, 0.025, n)  # downtrend to trigger fear
    px = 60000 * np.exp(np.cumsum(rets))
    df = pd.DataFrame({
        "open": px, "high": px * 1.01, "low": px * 0.99,
        "close": px, "volume": np.random.uniform(1000, 5000, n),
    })
    strat = FearGreedExtremeLongV2()
    sigs = strat.generate_signals_from_ohlcv(df, "BTCUSDT")
    print(f"Signals: {len(sigs)}")
    for s in sigs:
        print(f"  {s}")
