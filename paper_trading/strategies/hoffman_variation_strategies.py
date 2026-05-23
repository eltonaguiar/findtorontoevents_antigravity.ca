"""Hoffman IRB Variation strategies — 7 incubator-portfolio wrappers.

Wraps the baby_strategies.hoffman_variations signal generators into the
paper-trading BaseStrategy interface.  Each variation explores a different
edge on top of the core Hoffman IRB + EMA-angle system:

  1. HoffmanAdaptiveATR_PT   — ATR-percentile-scaled TP/SL
  2. HoffmanKalmanTrend_PT   — Kalman filter replaces EMA angle
  3. HoffmanTrailingATR_PT   — trailing ATR stop
  4. HoffmanMomentumTP_PT    — ROC-scaled take-profit
  5. HoffmanKellySized_PT    — Kelly criterion position sizing
  6. HoffmanHTFConfluence_PT — dual 1H + 4H trend confirmation
  7. Hoffman45Degree_PT      — relaxed 20-degree entry threshold

All use 15-minute Binance klines for: BTCUSDT, DOGEUSDT, LTCUSDT, SOLUSDT,
XRPUSDT.  Picks are routed to the **incubator** portfolio.
"""

import logging
from typing import List

import pandas as pd

from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

from baby_strategies.hoffman_variations import (
    hoffman_adaptive_atr_signals,
    hoffman_kalman_trend_signals,
    hoffman_trailing_atr_signals,
    hoffman_momentum_tp_signals,
    hoffman_kelly_sized_signals,
    hoffman_htf_confluence_signals,
    hoffman_45_degree_relaxed_signals,
    hoffman_scalper_signals,
)

logger = logging.getLogger("paper_trading")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
]


# ── Base class for all 7 variations ──────────────────────────────────

class _HoffmanVariationBase(BaseStrategy):
    """Shared fetch / generate logic for Hoffman IRB variation wrappers."""

    source: str = "Multi-Source"
    category: str = "crypto"
    portfolio_type: str = "incubator"

    # Subclasses set these:
    _variation_name: str = ""
    _signal_fn = None  # callable(df, symbol) -> List[Signal]

    # ── data ─────────────────────────────────────────────────────────

    def fetch_data(self):
        """Fetch 15-min klines for every symbol.  Returns {symbol: DataFrame}."""
        all_data = {}
        for sym in SYMBOLS:
            try:
                all_data[sym] = self._fetch_klines(sym)
            except Exception as exc:
                logger.warning("  %s: fetch failed for %s — %s",
                               self.name, sym, exc)
        return all_data

    def _fetch_klines(self, symbol: str) -> pd.DataFrame:
        """Fetch 500 bars of 15-min klines with multi-source fallback."""
        raw = self.fetch_klines(symbol, interval="15m", limit=500)
        if not raw:
            raise ValueError(f"No kline data for {symbol} from any source")
        df = pd.DataFrame(raw, columns=KLINE_COLUMNS)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = df[col].astype(float)
        return df

    # ── picks ────────────────────────────────────────────────────────

    def generate_picks(self, data=None) -> List[NormalizedPick]:
        all_data = data if data else self.fetch_data()
        picks: List[NormalizedPick] = []

        for symbol, df in all_data.items():
            if df is None or len(df) < 100:
                continue
            try:
                signals = self._signal_fn(df, symbol)
            except Exception as exc:
                logger.warning("  %s: signal generation failed for %s — %s",
                               self.name, symbol, exc)
                continue

            for sig in signals:
                direction = "LONG" if sig.direction == "BUY" else "SHORT"
                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction=direction,
                    confidence=sig.confidence,
                    entry_price=sig.entry_price,
                    tp=sig.take_profit,
                    sl=sig.stop_loss,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    reason=sig.reason,
                ))

        # Return top 3 picks by confidence
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ── 7 Variation Classes ──────────────────────────────────────────────

class HoffmanAdaptiveATR_PT(_HoffmanVariationBase):
    """Adaptive ATR-scaled TP/SL — wider in volatile periods, tighter in calm."""
    name = "hoffman_adaptive_atr"
    display_name = "Hoffman Adaptive ATR"
    source = "Hoffman IRB + adaptive ATR scaling"
    _variation_name = "hoffman_adaptive_atr"
    _signal_fn = staticmethod(hoffman_adaptive_atr_signals)


class HoffmanKalmanTrend_PT(_HoffmanVariationBase):
    """Kalman filter trend estimation replaces EMA angle for regime detection."""
    name = "hoffman_kalman_trend"
    display_name = "Hoffman Kalman Trend"
    source = "Hoffman IRB + Kalman filter"
    _variation_name = "hoffman_kalman_trend"
    _signal_fn = staticmethod(hoffman_kalman_trend_signals)


class HoffmanTrailingATR_PT(_HoffmanVariationBase):
    """Trailing ATR stop — initial SL at 1x ATR, trails at 1.5x from best."""
    name = "hoffman_trailing_atr"
    display_name = "Hoffman Trailing ATR"
    source = "Hoffman IRB + trailing ATR stop"
    _variation_name = "hoffman_trailing_atr"
    _signal_fn = staticmethod(hoffman_trailing_atr_signals)


class HoffmanMomentumTP_PT(_HoffmanVariationBase):
    """Momentum-scaled take-profit — TP expands with strong ROC."""
    name = "hoffman_momentum_tp"
    display_name = "Hoffman Momentum TP"
    source = "Hoffman IRB + ROC momentum scaling"
    _variation_name = "hoffman_momentum_tp"
    _signal_fn = staticmethod(hoffman_momentum_tp_signals)


class HoffmanKellySized_PT(_HoffmanVariationBase):
    """Kelly criterion position sizing — confidence encodes Kelly fraction."""
    name = "hoffman_kelly_sized"
    display_name = "Hoffman Kelly Sized"
    source = "Hoffman IRB + Kelly criterion"
    _variation_name = "hoffman_kelly_sized"
    _signal_fn = staticmethod(hoffman_kelly_sized_signals)


class HoffmanHTFConfluence_PT(_HoffmanVariationBase):
    """Dual HTF confirmation — requires both 1H and 4H trend alignment."""
    name = "hoffman_htf_confluence"
    display_name = "Hoffman HTF Confluence"
    source = "Hoffman IRB + dual HTF confirmation"
    _variation_name = "hoffman_htf_confluence"
    _signal_fn = staticmethod(hoffman_htf_confluence_signals)


class Hoffman45Degree_PT(_HoffmanVariationBase):
    """Relaxed 20-degree entry threshold — catches more moderate-trend setups."""
    name = "hoffman_45_degree"
    display_name = "Hoffman 45 Degree"
    source = "Hoffman IRB + relaxed angle threshold"
    _variation_name = "hoffman_45_degree"
    _signal_fn = staticmethod(hoffman_45_degree_relaxed_signals)


class HoffmanScalper_PT(_HoffmanVariationBase):
    """20-minute scalper — rapid fire signals with EMA(9), tight TP/SL."""
    name = "hoffman_scalper_20m"
    display_name = "Hoffman Scalper 20m"
    source = "Hoffman IRB scalper (EMA9, 15° angle, 0.75x/0.5x ATR)"
    _variation_name = "hoffman_scalper_20m"
    _signal_fn = staticmethod(hoffman_scalper_signals)
