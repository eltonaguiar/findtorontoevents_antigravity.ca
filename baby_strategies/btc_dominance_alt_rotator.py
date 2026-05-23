"""
BtcDominanceAltRotatorStrategy — alt-season rotation on BTC dominance regime
============================================================================

Created: 2026-05-13
Source: Leap top-16-to-100 reverse-engineering
        (reports/leap_top16_to_100_traders_research_2026-05-13.md, Pattern 1)

CONCEPT: Alt-season is real and macro-detectable via BTC dominance. When BTC.D
is falling (capital rotating BTC -> alts) AND broader crypto is in uptrend
(BTC > BTC EMA-50 daily), the strongest-momentum alt outperforms BTC by a
wide margin. This strategy rotates a single 5%-account position into the
best-momentum alt in the Leap restricted set, and flattens the instant
BTC.D turns back up (alt-season over).

NFA — research-grade only. Live-money sizing gated behind 10-step Lopez de
Prado readiness per CLAUDE.md.

Strategy logic
--------------
- Universe: SOL/DOGE/XRP USDT only (the 3 alts in Leap's 5-symbol restricted
  set; BTC excluded as base, ETH excluded as Layer-1 quasi-base — both
  underperform mid-band alts during peak alt-season rotation).
- Data source: free — CoinGecko `/global` for live BTC.D %, yfinance daily for
  alt 7-day momentum. Caller is responsible for pre-fetching and passing both.
- Regime gates (must ALL pass before any entry):
  1. BTC.D falling: today's BTC.D < BTC.D 14 days ago (alt-season trigger).
  2. BTC > BTC EMA-50 daily (overall crypto uptrend — alts don't pump in bear).
- Entry: rotate into the alt with strongest 7-day momentum (close[t]/close[t-7]
  - 1). One position at a time. Size = 5% of account.
- Rotation: switch alts mid-position when a different alt's 7-day momentum
  exceeds the current pick's by > 5 percentage points (caller-side concern;
  strategy emits the new top-momentum pick each call).
- Exit:
  - Flatten when BTC.D rising (BTC.D today > BTC.D 7 days ago) — alt-season over.
  - Hard stop: 2 ATR (daily) below entry.
  - TP: 3 ATR (daily) above entry.

Why it works
------------
The 16-100 band of the Leap leaderboard skews to mid-cap alts during the
9-day window where BTC.D dropped ~1.4 points. Mid-band winners were not
trading BTC at all; they were riding the strongest-momentum alt of the day.
The macro filter (BTC.D direction) is the discriminator that prevents
chasing alts during BTC-dominance phases where they bleed.

Acceptance gate (per CLAUDE.md tier targets)
--------------------------------------------
Shadow-mode 30 days: n >= 20 closed trades, PF >= 1.5, WR >= 45%, MDD <= 18%.
If passes: promote to baby_strats_forward via standard graduation. Comparative
head-to-head vs `LeapBandBetaChaser` + `PyramidTrend4H` over same shadow window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


SUPPORTED_SYMBOLS = ["SOLUSDT", "DOGEUSDT", "XRPUSDT"]


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    momentum_7d: float = 0.0


class BtcDominanceAltRotatorStrategy:
    """Rotate into strongest-momentum alt when BTC.D falling and BTC > EMA-50.

    Inputs:
      - data_daily: alt symbol's daily OHLCV DataFrame (>= 60 rows recommended).
      - symbol: must be in SUPPORTED_SYMBOLS.
      - btc_daily: BTC daily OHLCV DataFrame (>= daily_ema + 5 rows).
      - btc_dominance_series: pd.Series of BTC.D % indexed by date; needs at
        least 15 rows so we can look back 14 days for the falling-dominance
        gate and 7 days for the alt-season-ending flatten signal.

    The strategy emits one Signal for the supplied symbol if (and only if) it
    is the top-momentum alt across SUPPORTED_SYMBOLS. The caller is expected
    to invoke `generate_signals` once per supported symbol per cycle and pick
    the winner; alternatively, the caller can pass `peer_data_daily` (dict
    of symbol -> daily DataFrame) and let the strategy do the comparison.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.momentum_lookback_days = self.params.get("momentum_lookback_days", 7)
        self.btc_dom_lookback_days = self.params.get("btc_dom_lookback_days", 14)
        self.btc_dom_exit_lookback_days = self.params.get("btc_dom_exit_lookback_days", 7)
        self.daily_ema = self.params.get("daily_ema", 50)
        self.atr_period = self.params.get("atr_period", 14)
        self.atr_stop_mult = self.params.get("atr_stop_mult", 2.0)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 3.0)
        self.size_pct = self.params.get("size_pct", 5.0)
        self.rotation_threshold_pct = self.params.get("rotation_threshold_pct", 5.0)

    # ------------------------------------------------------------------
    # Indicator helpers
    # ------------------------------------------------------------------
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

    @staticmethod
    def _momentum_pct(close: pd.Series, lookback: int) -> Optional[float]:
        if close is None or len(close) <= lookback:
            return None
        c0 = float(close.iloc[-lookback - 1])
        c1 = float(close.iloc[-1])
        if c0 <= 0:
            return None
        return (c1 / c0) - 1.0

    # ------------------------------------------------------------------
    # Regime gate helpers
    # ------------------------------------------------------------------
    def _btc_dominance_falling(self, btc_dom: pd.Series) -> bool:
        """True if today's BTC.D < BTC.D `btc_dom_lookback_days` ago."""
        if btc_dom is None or len(btc_dom) <= self.btc_dom_lookback_days:
            return False
        today = float(btc_dom.iloc[-1])
        prior = float(btc_dom.iloc[-self.btc_dom_lookback_days - 1])
        return today < prior

    def _btc_dominance_rising_short(self, btc_dom: pd.Series) -> bool:
        """Exit signal — True if BTC.D today > BTC.D `btc_dom_exit_lookback_days` ago."""
        if btc_dom is None or len(btc_dom) <= self.btc_dom_exit_lookback_days:
            return False
        today = float(btc_dom.iloc[-1])
        prior = float(btc_dom.iloc[-self.btc_dom_exit_lookback_days - 1])
        return today > prior

    def _btc_uptrend(self, btc_daily: pd.DataFrame) -> bool:
        if btc_daily is None or len(btc_daily) < self.daily_ema:
            return False
        close = btc_daily["close"].astype(float)
        ema = self._ema(close, self.daily_ema)
        return float(close.iloc[-1]) > float(ema.iloc[-1])

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------
    def generate_signals(
        self,
        data_daily: pd.DataFrame,
        symbol: str = "SOLUSDT",
        btc_daily: Optional[pd.DataFrame] = None,
        btc_dominance_series: Optional[pd.Series] = None,
        peer_data_daily: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> List[Signal]:
        if symbol not in SUPPORTED_SYMBOLS:
            return []
        if data_daily is None or len(data_daily) < max(
            self.momentum_lookback_days + 2, self.atr_period + 2
        ):
            return []

        # Regime gate #1: BTC.D falling
        if not self._btc_dominance_falling(btc_dominance_series):
            return []
        # Exit-gate cross-check: if BTC.D is also rising vs 7-day prior, alt-season is over.
        if self._btc_dominance_rising_short(btc_dominance_series):
            return []
        # Regime gate #2: BTC > EMA-50 daily
        if not self._btc_uptrend(btc_daily):
            return []

        # Compute candidate's 7-day momentum
        close = data_daily["close"].astype(float)
        high = data_daily["high"].astype(float)
        low = data_daily["low"].astype(float)

        candidate_mom = self._momentum_pct(close, self.momentum_lookback_days)
        if candidate_mom is None or candidate_mom <= 0:
            return []

        # If peer data supplied, only emit if this symbol is the top-momentum alt.
        if peer_data_daily:
            best_symbol = symbol
            best_mom = candidate_mom
            for peer_sym, peer_df in peer_data_daily.items():
                if peer_sym == symbol or peer_sym not in SUPPORTED_SYMBOLS:
                    continue
                if peer_df is None or "close" not in peer_df.columns:
                    continue
                peer_close = peer_df["close"].astype(float)
                peer_mom = self._momentum_pct(peer_close, self.momentum_lookback_days)
                if peer_mom is None:
                    continue
                if peer_mom > best_mom:
                    best_mom = peer_mom
                    best_symbol = peer_sym
            if best_symbol != symbol:
                return []

        # ATR (daily) for stop/TP
        atr = self._atr(high, low, close, self.atr_period)
        latest_atr = float(atr.iloc[-1])
        if latest_atr <= 0:
            return []

        entry = float(close.iloc[-1])
        sl = entry - self.atr_stop_mult * latest_atr
        tp = entry + self.tp_atr_mult * latest_atr

        return [Signal(
            symbol=symbol,
            direction="LONG",
            confidence=0.6,
            entry_price=entry,
            take_profit=float(tp),
            stop_loss=float(sl),
            reason=(
                f"btc-dominance alt-rotator LONG: BTC.D falling vs "
                f"{self.btc_dom_lookback_days}d prior + BTC > EMA-{self.daily_ema} + "
                f"7d momentum {candidate_mom*100:.2f}% (top alt of SOL/DOGE/XRP). "
                f"Stop = {self.atr_stop_mult} ATR, TP = {self.tp_atr_mult} ATR. "
                f"Rotate if peer alt exceeds by > {self.rotation_threshold_pct}pp."
            ),
            momentum_7d=float(candidate_mom),
        )]

    # ------------------------------------------------------------------
    # Rotation decision (caller invokes once per cycle with current position)
    # ------------------------------------------------------------------
    def should_rotate(
        self,
        current_symbol: str,
        current_momentum_pct: float,
        peer_momentum_pct: Dict[str, float],
    ) -> Optional[str]:
        """Return symbol to rotate INTO, or None if hold current.

        Triggers rotation when any peer's 7d momentum exceeds current's by more
        than `rotation_threshold_pct` percentage points.
        """
        if current_symbol not in SUPPORTED_SYMBOLS:
            return None
        threshold = self.rotation_threshold_pct / 100.0
        best_peer = None
        best_excess = 0.0
        for peer_sym, peer_mom in peer_momentum_pct.items():
            if peer_sym == current_symbol or peer_sym not in SUPPORTED_SYMBOLS:
                continue
            excess = peer_mom - current_momentum_pct
            if excess > threshold and excess > best_excess:
                best_excess = excess
                best_peer = peer_sym
        return best_peer

    def should_flatten(self, btc_dominance_series: pd.Series) -> bool:
        """Return True when BTC.D is back to rising — alt-season over."""
        return self._btc_dominance_rising_short(btc_dominance_series)


if __name__ == "__main__":
    import numpy as np

    n = 90
    rng = np.random.RandomState(0)
    # Synthetic uptrending alt
    close = pd.Series(50 + np.cumsum(rng.normal(0.4, 0.7, n)))
    high = close + 0.5
    low = close - 0.5
    data = pd.DataFrame({"close": close, "high": high, "low": low,
                          "open": close - 0.1, "volume": [1000] * n})
    # Synthetic BTC daily, uptrending
    btc_close = pd.Series(40000 + np.cumsum(rng.normal(80, 200, n)))
    btc_daily = pd.DataFrame({"close": btc_close, "high": btc_close + 50,
                              "low": btc_close - 50, "open": btc_close,
                              "volume": [10000] * n})
    # Synthetic BTC.D falling 60 -> 55 over 30 days
    btc_dom = pd.Series(np.linspace(60, 55, 30))

    strat = BtcDominanceAltRotatorStrategy()
    signals = strat.generate_signals(data, "SOLUSDT", btc_daily=btc_daily,
                                     btc_dominance_series=btc_dom)
    print(f"signals: {len(signals)}")
    for s in signals:
        print(f"  {s}")
