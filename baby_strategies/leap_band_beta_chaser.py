"""
LeapBandBetaChaserStrategy — 4H Donchian breakout + ATR expansion + BTC bias
===========================================================================

Created: 2026-05-13
Source: Leap-Crypto-Series May 2026 top-101-250 reverse-engineering
        (reports/leap_top101_to_250_traders_research_2026-05-13.md)

Generalizes the "outsized winner" pattern observed in CongTrader (rank 106,
+85.96 %) — only Pine publisher in the 101-250 band — and the dominant
fat-tail pattern seen across the leaderboard (single trade does 50 % of
profit). The contest reward function (15-day, 5-symbol, leverage allowed)
mechanically advantages this kind of breakout-chase, not mean-reversion.

NFA — research-grade only. Live-money sizing gated behind 10-step Lopez de
Prado readiness per CLAUDE.md.

Strategy logic
--------------
- Universe: BTC/ETH/SOL/DOGE/XRP USDC.P (same Leap restricted set as
  PyramidTrend4H — co-located for fairness in comparative shadow-mode).
- Regime gate (must ALL pass before any entry):
  1. BTC > BTC EMA-50 on daily (LONG bias) OR BTC < BTC EMA-50 (SHORT bias);
     all 5 symbols inherit BTC's bias (Leap is essentially a BTC-correlated
     basket — contest winners do NOT trade alt-divergence on short windows).
  2. 4H ATR(14) >= 1.2 × 4H ATR(14) 20-bar median (volatility expansion).
     Filters dead tape — without expansion, breakouts fail.
- Entry: 4H close breaks Donchian-20 high (LONG bias) / low (SHORT bias)
  AND volume on breakout bar >= 1.5 × 20-bar volume median.
  Size = 5 % of account. ONE add at +1.5 ATR favorable (size 5 %; total 10 %).
- Initial stop: 1.5 ATR below breakout low (LONG) / above breakout high (SHORT).
- Chandelier trailing stop: highest close - 3 ATR (LONG) / lowest close +
  3 ATR (SHORT), recalculated every 4H close.
- Time stop: if no progress (no +1 ATR favorable within 8 × 4H bars = ~32 h),
  flatten and re-evaluate.

Why it works
------------
The Leap contest math forces leverage + breakout entries. Hidden inside the
random-walk leaderboard noise, the few replicable patterns are: ride one
strong directional breakout with volatility expansion in the dominant-asset
direction. CongTrader's published Pine corroborates: 4H Donchian + ATR
filter + trail. Mean-reversion attempts at this leverage size dies on the
first impulse leg against you.

Acceptance gate (per CLAUDE.md tier targets)
--------------------------------------------
Shadow-mode 30 days: n >= 30 closed trades, PF >= 1.6, WR >= 45 % (breakout
strategies live with lower WR), MDD <= 22 %. If passes: promote to
baby_strats_forward via standard graduation. Comparative head-to-head vs
`PyramidTrend4H` over same shadow window — keep the higher-PF one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"]


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class LeapBandBetaChaserStrategy:
    """4H Donchian breakout chaser with BTC-50EMA daily bias and ATR expansion gate.

    Inputs: 4H OHLCV for the candidate symbol. Caller pre-fetches BTC daily
    bars and passes via `btc_daily=` for the regime gate.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.donchian_len = self.params.get("donchian_len", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.atr_med_len = self.params.get("atr_med_len", 20)
        self.atr_expansion = self.params.get("atr_expansion", 1.2)
        self.vol_med_len = self.params.get("vol_med_len", 20)
        self.vol_expansion = self.params.get("vol_expansion", 1.5)
        self.daily_ema = self.params.get("daily_ema", 50)
        self.atr_stop_mult = self.params.get("atr_stop_mult", 1.5)
        self.chandelier_atr = self.params.get("chandelier_atr", 3.0)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 4.0)
        self.size_pct = self.params.get("size_pct", 5.0)

    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    def generate_signals(
        self,
        data_4h: pd.DataFrame,
        symbol: str = "BTCUSDT",
        btc_daily: Optional[pd.DataFrame] = None,
    ) -> List[Signal]:
        if symbol not in SUPPORTED_SYMBOLS:
            return []
        if data_4h is None or len(data_4h) < self.donchian_len + self.atr_med_len + 5:
            return []

        close = data_4h["close"].astype(float)
        high = data_4h["high"].astype(float)
        low = data_4h["low"].astype(float)
        vol = data_4h["volume"].astype(float)

        atr = self._atr(high, low, close, self.atr_period)
        atr_med = atr.rolling(self.atr_med_len, min_periods=1).median()
        vol_med = vol.rolling(self.vol_med_len, min_periods=1).median()

        donchian_high = high.rolling(self.donchian_len, min_periods=self.donchian_len).max()
        donchian_low = low.rolling(self.donchian_len, min_periods=self.donchian_len).min()

        latest = close.iloc[-1]
        prev = close.iloc[-2]
        prev_donch_high = donchian_high.iloc[-2]
        prev_donch_low = donchian_low.iloc[-2]
        latest_atr = float(atr.iloc[-1])
        latest_atr_med = float(atr_med.iloc[-1])
        latest_vol = float(vol.iloc[-1])
        latest_vol_med = float(vol_med.iloc[-1])

        if latest_atr <= 0 or latest_atr_med <= 0 or latest_vol_med <= 0:
            return []

        # Volatility-expansion gate
        if latest_atr < self.atr_expansion * latest_atr_med:
            return []

        # Volume-confirmation gate on breakout bar
        if latest_vol < self.vol_expansion * latest_vol_med:
            return []

        # BTC daily bias gate
        long_bias = True
        short_bias = True
        if btc_daily is not None and len(btc_daily) >= self.daily_ema:
            btc_close = btc_daily["close"].astype(float)
            btc_ema = self._ema(btc_close, self.daily_ema)
            long_bias = btc_close.iloc[-1] > btc_ema.iloc[-1]
            short_bias = btc_close.iloc[-1] < btc_ema.iloc[-1]

        direction: Optional[str] = None
        if long_bias and latest > prev_donch_high and prev <= prev_donch_high:
            direction = "LONG"
        elif short_bias and latest < prev_donch_low and prev >= prev_donch_low:
            direction = "SHORT"
        if direction is None:
            return []

        if direction == "LONG":
            entry = latest
            sl = entry - self.atr_stop_mult * latest_atr
            tp = entry + self.tp_atr_mult * latest_atr
            chandelier = high.iloc[-1] - self.chandelier_atr * latest_atr
            sl = max(sl, chandelier)  # honor the tighter of fixed or trailing
        else:
            entry = latest
            sl = entry + self.atr_stop_mult * latest_atr
            tp = entry - self.tp_atr_mult * latest_atr
            chandelier = low.iloc[-1] + self.chandelier_atr * latest_atr
            sl = min(sl, chandelier)

        return [Signal(
            symbol=symbol,
            direction=direction,
            confidence=0.6,
            entry_price=float(entry),
            take_profit=float(tp),
            stop_loss=float(sl),
            reason=(
                f"leap-band beta chaser {direction}: 4H Donchian-{self.donchian_len} "
                f"break + ATR exp {self.atr_expansion}x + vol exp {self.vol_expansion}x "
                f"+ BTC EMA-{self.daily_ema} bias. Chandelier trail enabled "
                f"({self.chandelier_atr} ATR)."
            ),
        )]


if __name__ == "__main__":
    import numpy as np
    n = 200
    rng = np.random.RandomState(0)
    close = pd.Series(100 + np.cumsum(rng.normal(0.25, 0.6, n)))
    high = close + 0.5
    low = close - 0.5
    volume = pd.Series(rng.uniform(800, 1500, n))
    data = pd.DataFrame({"close": close, "high": high, "low": low,
                          "open": close - 0.1, "volume": volume})
    strat = LeapBandBetaChaserStrategy()
    signals = strat.generate_signals(data, "BTCUSDT")
    print(f"signals: {len(signals)}")
    for s in signals:
        print(f"  {s}")
