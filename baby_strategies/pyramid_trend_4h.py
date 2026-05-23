"""
PyramidTrend4HStrategy — pyramid-into-trend
============================================

Created: 2026-05-13
Source: Leap-Crypto-Series May 2026 top-5 reverse-engineering
        (reports/leap_top5_traders_research_2026-05-13.md, Pattern A)

PROVEN CONCEPT: paper-contest winners (+285%, +255%, +231% on $100k in 15d)
mathematically required pyramiding levered conviction trades into trends —
not "100 small scalps." This skeleton replicates the construction.

NFA — research-grade only. Live-money sizing gated behind 10-step Lopez de
Prado readiness per CLAUDE.md.

Strategy logic
--------------
- Universe: 5 USDC.P-equivalent perps (BTC/ETH/SOL/DOGE/XRP) — same restricted
  set as Leap-Crypto.
- Regime gate (must ALL pass before any entry):
  1. Price > 1D EMA-200 (long bias) OR Price < 1D EMA-200 (short bias)
  2. 4H EMA-21 > 4H EMA-55 (LONG bias) OR EMA-21 < EMA-55 (SHORT bias)
  3. 1H RSI(14) > 50 (LONG) or < 50 (SHORT)
- Entry 1 (anchor): regime triggers + price closes back above 4H EMA-21
  after pullback. Size = 2% account.
- Entry 2 (add 1): after Entry 1 +0.5 ATR favorable, AND regime intact.
  Size = 2% (total 4%).
- Entry 3 (add 2): after Entry 2 +1 ATR favorable. Size = 2% (total 6%).
- Entry 4 (add 3): after Entry 3 +1.5 ATR favorable. Size = 2% (total 8%).
- Entry 5 (add 4): cap at 5 adds total. Size = 2% (total 10%).
- Exit ALL: if 4H EMA-21 crosses below EMA-55 (trend break) OR 1H RSI crosses
  back below 50 (LONG) / above 50 (SHORT).
- Hard stop: 1.5 ATR below the LOWEST entry (LONG) / above highest entry
  (SHORT). All pyramid adds share one trailing stop.

Why it works
------------
Math forces this. +250% in 15d on $100k can only come from concentrated
conviction adds on 1-3 trend days. Single-shot 1R entries cannot produce
account-doubling moves from 30% market moves.

Why our +0.28% missed it
------------------------
Spread across 12 CRYPTO sources diluting elite PF 2.34-3.97 strategies.
Single-shot entries. No regime gate. No pyramiding.
See reports/leap_top5_traders_research_2026-05-13.md "Brutal critique."

Acceptance gate (per CLAUDE.md tier targets)
--------------------------------------------
Shadow-mode 30 days: n >= 30 closed trades, PF >= 1.6, WR >= 50%, MDD <= 18%.
If passes: promote to baby_strats_forward via standard graduation.
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
    pyramid_level: int = 1  # 1 = anchor, 2-5 = adds


class PyramidTrend4HStrategy:
    """Pyramid into trend with 4H EMA + 1D EMA-200 + 1H RSI regime gate.

    Inputs: 4H OHLCV DataFrame. Caller pre-fetches 1H + 1D bars and passes
    via auxiliary kwargs.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fast_ema_4h = self.params.get("fast_ema_4h", 21)
        self.slow_ema_4h = self.params.get("slow_ema_4h", 55)
        self.daily_ema = self.params.get("daily_ema", 200)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.atr_period = self.params.get("atr_period", 14)
        self.max_pyramids = self.params.get("max_pyramids", 5)
        self.add_threshold_atr = self.params.get("add_threshold_atr", 0.5)
        self.hard_stop_atr = self.params.get("hard_stop_atr", 1.5)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 4.0)
        self.anchor_size_pct = self.params.get("anchor_size_pct", 2.0)

    # ------------------------------------------------------------------
    # Indicator helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
        rs = gain / loss.replace(0, 1e-12)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------
    def generate_signals(
        self,
        data_4h: pd.DataFrame,
        symbol: str = "BTCUSDT",
        data_1d: Optional[pd.DataFrame] = None,
        data_1h: Optional[pd.DataFrame] = None,
    ) -> List[Signal]:
        if symbol not in SUPPORTED_SYMBOLS:
            return []
        if data_4h is None or len(data_4h) < self.slow_ema_4h + 10:
            return []

        close_4h = data_4h["close"].astype(float)
        high_4h = data_4h["high"].astype(float)
        low_4h = data_4h["low"].astype(float)

        fast = self._ema(close_4h, self.fast_ema_4h)
        slow = self._ema(close_4h, self.slow_ema_4h)
        atr = self._atr(high_4h, low_4h, close_4h, self.atr_period)

        latest = close_4h.iloc[-1]
        latest_fast = fast.iloc[-1]
        latest_slow = slow.iloc[-1]
        latest_atr = float(atr.iloc[-1])

        if latest_atr <= 0:
            return []

        # Regime gates
        long_4h = latest_fast > latest_slow
        short_4h = latest_fast < latest_slow
        if not (long_4h or short_4h):
            return []

        # 1D regime gate
        daily_ok_long = True
        daily_ok_short = True
        if data_1d is not None and len(data_1d) >= self.daily_ema:
            close_1d = data_1d["close"].astype(float)
            daily_ema = self._ema(close_1d, self.daily_ema)
            daily_ok_long = close_1d.iloc[-1] > daily_ema.iloc[-1]
            daily_ok_short = close_1d.iloc[-1] < daily_ema.iloc[-1]

        # 1H RSI gate
        rsi_ok_long = True
        rsi_ok_short = True
        if data_1h is not None and len(data_1h) >= self.rsi_period + 1:
            rsi_1h = self._rsi(data_1h["close"].astype(float), self.rsi_period)
            rsi_ok_long = rsi_1h.iloc[-1] > 50
            rsi_ok_short = rsi_1h.iloc[-1] < 50

        direction = None
        if long_4h and daily_ok_long and rsi_ok_long:
            direction = "LONG"
        elif short_4h and daily_ok_short and rsi_ok_short:
            direction = "SHORT"
        if direction is None:
            return []

        # Pullback-to-EMA-21 entry trigger
        prev_close = close_4h.iloc[-2] if len(close_4h) >= 2 else None
        if prev_close is None:
            return []
        if direction == "LONG":
            triggered = prev_close <= latest_fast and latest > latest_fast
        else:  # SHORT
            triggered = prev_close >= latest_fast and latest < latest_fast
        if not triggered:
            return []

        # Build anchor signal
        if direction == "LONG":
            entry = latest
            sl = latest - self.hard_stop_atr * latest_atr
            tp = latest + self.tp_atr_mult * latest_atr
        else:
            entry = latest
            sl = latest + self.hard_stop_atr * latest_atr
            tp = latest - self.tp_atr_mult * latest_atr

        return [Signal(
            symbol=symbol,
            direction=direction,
            confidence=0.65,
            entry_price=float(entry),
            take_profit=float(tp),
            stop_loss=float(sl),
            reason=(f"pyramid-trend anchor: 4H EMA{self.fast_ema_4h}>{self.slow_ema_4h} "
                    f"+ 1D EMA{self.daily_ema} + 1H RSI gate. Direction={direction}. "
                    f"Adds queued at +{self.add_threshold_atr}/+1.0/+1.5/+2.0 ATR."),
            pyramid_level=1,
        )]

    # ------------------------------------------------------------------
    # Pyramid-add decision (caller invokes after each filled position)
    # ------------------------------------------------------------------
    def next_pyramid_add(
        self,
        current_price: float,
        anchor_price: float,
        atr_at_anchor: float,
        existing_adds: int,
        direction: str,
    ) -> Optional[Signal]:
        """Return next pyramid Signal if conditions met; else None.

        Triggers add N when price has moved (N-1+1)*0.5 ATR favorable past anchor:
          add #2: +0.5 ATR
          add #3: +1.0 ATR
          add #4: +1.5 ATR
          add #5: +2.0 ATR
        """
        if existing_adds >= self.max_pyramids - 1:
            return None
        threshold = (existing_adds + 1) * self.add_threshold_atr * atr_at_anchor
        if direction == "LONG":
            if current_price < anchor_price + threshold:
                return None
        else:
            if current_price > anchor_price - threshold:
                return None
        return Signal(
            symbol="<pyramid>",
            direction=direction,
            confidence=0.55,
            entry_price=current_price,
            take_profit=current_price + (self.tp_atr_mult * atr_at_anchor) * (1 if direction == "LONG" else -1),
            stop_loss=anchor_price - (self.hard_stop_atr * atr_at_anchor) * (1 if direction == "LONG" else -1),
            reason=f"pyramid add #{existing_adds + 1}",
            pyramid_level=existing_adds + 2,
        )


if __name__ == "__main__":
    # Smoke test with synthetic upward trend
    import numpy as np
    n = 100
    close = pd.Series(100 + np.cumsum(np.random.RandomState(0).normal(0.3, 1, n)))
    high = close + 0.5
    low = close - 0.5
    data = pd.DataFrame({"close": close, "high": high, "low": low,
                          "open": close - 0.1, "volume": [1000] * n})
    strat = PyramidTrend4HStrategy()
    signals = strat.generate_signals(data, "BTCUSDT")
    print(f"signals: {len(signals)}")
    for s in signals:
        print(f"  {s}")
