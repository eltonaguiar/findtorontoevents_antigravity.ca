"""
DailyBreakoutVolumeConfirmStrategy — daily Donchian-20 breakout + volume confirm
================================================================================

Created: 2026-05-13
Source: Leap top-16 to top-100 reverse-engineering, Pattern 2
        (reports/leap_top16_to_100_traders_research_2026-05-13.md)

PROVEN CONCEPT: across the top-16 to top-100 leaderboard, the dominant
replicable pattern was daily-bar breakouts of a 20-day range, confirmed by
volume expansion on the breakout bar. Unlike 4H scalp strategies, this is a
multi-day swing skeleton that catches the meaty middle of a continuation move
rather than chasing every intraday pop.

NFA — research-grade only. Live-money sizing gated behind 10-step Lopez de
Prado readiness per CLAUDE.md.

Strategy logic
--------------
- Universe: 5 USDT perps (BTC/ETH/SOL/DOGE/XRP) — same Leap-restricted set
  as PyramidTrend4H + LeapBandBetaChaser for fair shadow-mode comparison.
- Entry trigger (LONG only — this is a momentum-continuation breakout
  strategy, not a regime-bias strategy):
    1. Daily close breaks above the 20-day high (Donchian-20 on DAILY bars,
       NOT 4H). Prior bar must be at-or-below the 20-day high.
    2. Volume on breakout day >= 1.5 × 20-day median volume.
- Optional regime gate (only applied if `btc_dominance_series` is passed):
    * For alt-coins (ETH/SOL/DOGE/XRP): BTC.D today < BTC.D 7 days ago
      (falling BTC dominance == alt-season tailwind).
    * For BTC itself: gate is ignored — BTC.D direction is uninformative for
      BTC's own breakouts.
    * If `btc_dominance_series` is None, the gate is skipped entirely
      (caller may not have CoinGecko `/global` available).
- Initial SL: 1.5 ATR(14) below breakout-bar close.
- TP: 4 ATR(14) above breakout-bar close.
- Size: 3% per signal. No pyramiding (a key contrast vs PyramidTrend4H).

Why it works
------------
Daily Donchian-20 breakouts capture the start of multi-day trend legs that
the 4H strategies often miss because they're already chasing. Volume-confirm
filters most failed breakouts (the classic "fakeout" that produces -1R losses
in scan-without-confirm setups). BTC.D-falling gate prevents stepping into
alt-coin breakouts during BTC-dominance regimes where alts under-perform.

Acceptance gate (per CLAUDE.md tier targets)
--------------------------------------------
Shadow-mode 30 days: n >= 20 closed trades, PF >= 1.5, WR >= 42% (breakout
strategies live with lower WR), MDD <= 20%. If passes: promote to
baby_strats_forward via standard graduation. Comparative head-to-head vs
`PyramidTrend4H` and `LeapBandBetaChaser` over same shadow window.
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


class DailyBreakoutVolumeConfirmStrategy:
    """Daily Donchian-20 breakout with volume confirmation and optional BTC.D gate.

    Inputs: daily OHLCV DataFrame for the candidate symbol. Optionally a
    BTC dominance pandas Series (most-recent values last) for the alt-coin
    regime gate.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.donchian_len = self.params.get("donchian_len", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.vol_med_len = self.params.get("vol_med_len", 20)
        self.vol_expansion = self.params.get("vol_expansion", 1.5)
        self.atr_stop_mult = self.params.get("atr_stop_mult", 1.5)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 4.0)
        self.size_pct = self.params.get("size_pct", 3.0)
        self.btc_dom_lookback = self.params.get("btc_dom_lookback", 7)

    # ------------------------------------------------------------------
    # Indicator helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    def _btc_dominance_falling(self, btc_dominance_series: pd.Series) -> bool:
        """True iff today's BTC.D < BTC.D `btc_dom_lookback` bars ago."""
        s = pd.Series(btc_dominance_series).astype(float).dropna()
        if len(s) < self.btc_dom_lookback + 1:
            return False
        return float(s.iloc[-1]) < float(s.iloc[-(self.btc_dom_lookback + 1)])

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------
    def generate_signals(
        self,
        data_daily: pd.DataFrame,
        symbol: str = "BTCUSDT",
        btc_dominance_series: Optional[pd.Series] = None,
    ) -> List[Signal]:
        if symbol not in SUPPORTED_SYMBOLS:
            return []
        if data_daily is None or len(data_daily) < self.donchian_len + 2:
            return []

        close = data_daily["close"].astype(float)
        high = data_daily["high"].astype(float)
        low = data_daily["low"].astype(float)
        vol = data_daily["volume"].astype(float)

        atr = self._atr(high, low, close, self.atr_period)
        vol_med = vol.rolling(self.vol_med_len, min_periods=1).median()

        # Donchian-20 high computed on PRIOR `donchian_len` bars (excluding today),
        # so a "break" means today's close > that high. We compute the rolling max
        # over `donchian_len` bars ending at t-1.
        donchian_high_prev = high.shift(1).rolling(
            self.donchian_len, min_periods=self.donchian_len
        ).max()

        latest_close = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        prev_donch_high = donchian_high_prev.iloc[-1]
        latest_atr = float(atr.iloc[-1])
        latest_vol = float(vol.iloc[-1])
        latest_vol_med = float(vol_med.iloc[-1])

        if pd.isna(prev_donch_high) or latest_atr <= 0 or latest_vol_med <= 0:
            return []

        # Breakout: today's close above the 20-day high, AND prior close at/below it
        # (prevents re-triggering once we're already above the range).
        if not (latest_close > float(prev_donch_high) and prev_close <= float(prev_donch_high)):
            return []

        # Volume confirmation
        if latest_vol < self.vol_expansion * latest_vol_med:
            return []

        # Optional BTC.D-falling gate for alt-coins
        if btc_dominance_series is not None and symbol != "BTCUSDT":
            if not self._btc_dominance_falling(btc_dominance_series):
                return []

        entry = latest_close
        sl = entry - self.atr_stop_mult * latest_atr
        tp = entry + self.tp_atr_mult * latest_atr

        return [Signal(
            symbol=symbol,
            direction="LONG",
            confidence=0.6,
            entry_price=float(entry),
            take_profit=float(tp),
            stop_loss=float(sl),
            reason=(
                f"daily breakout LONG: close>Donchian-{self.donchian_len} high "
                f"+ volume {self.vol_expansion}x 20-day median"
                + (
                    f" + BTC.D falling vs {self.btc_dom_lookback}d ago"
                    if (btc_dominance_series is not None and symbol != "BTCUSDT")
                    else ""
                )
                + f". SL=-{self.atr_stop_mult} ATR, TP=+{self.tp_atr_mult} ATR. "
                f"Size={self.size_pct}% (no pyramiding)."
            ),
        )]


if __name__ == "__main__":
    import numpy as np
    n = 100
    rng = np.random.RandomState(0)
    close = pd.Series(100 + np.cumsum(rng.normal(0.2, 0.5, n)))
    high = close + 0.4
    low = close - 0.4
    volume = pd.Series(rng.uniform(800, 1200, n))
    # Force a breakout on the last bar
    close.iloc[-1] = close.iloc[:-1].max() + 5.0
    high.iloc[-1] = close.iloc[-1] + 1.0
    volume.iloc[-1] = volume.iloc[:-1].median() * 3.0
    data = pd.DataFrame({"close": close, "high": high, "low": low,
                         "open": close - 0.1, "volume": volume})
    strat = DailyBreakoutVolumeConfirmStrategy()
    signals = strat.generate_signals(data, "BTCUSDT")
    print(f"signals: {len(signals)}")
    for s in signals:
        print(f"  {s}")
