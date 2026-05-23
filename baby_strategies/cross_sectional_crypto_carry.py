"""
CrossSectionalCryptoCarryStrategy — Rank perpetuals by funding and trade
the carry spread (long lowest-funding, short highest-funding).

Thesis
------
Individual perpetual funding rates mean-revert (see
funding_rate_mean_reversion_v1.py, which fades single-name extremes). The
cross-sectional version is different: at each rebalance, rank a universe of
perps by their current 8h funding. The cheapest carry (most negative funding
= shorts paying longs) is structurally compensated to hold long; the most
expensive (very positive funding = longs paying shorts) is compensated to hold
short. Spread-trading the top- vs bottom-funding quintiles earns a carry
premium that historically persists in crypto (see ChatGPT_STRATS.MD §206 and
Kimi V3 "Funding Term-Structure Divergence").

Edge cited
----------
- AQR "Value & Momentum Everywhere" (2013) — cross-sectional carry works in FX,
  commodities, bonds. Crypto extension published in multiple SSRN papers
  2022-2025 finds Sharpe 0.8-1.4 on 20+ symbol universes rebalanced weekly.
- Distinct from funding_rate_mean_reversion_v1 which trades SINGLE-NAME
  extremes; this trades CROSS-SECTIONAL spread with market-neutral sizing.

Data requirements
-----------------
Per-bar `funding_rate` column for each symbol. If the column is missing the
strategy emits no signals (no proxy fallback — the cross-sectional edge
requires real funding data).

NOTE: This class produces signals per symbol by reading the snapshot of the
wider universe from `universe_funding` supplied via `context`. If `context`
is absent, degrades to no signals — consistent with baby_strategies convention.

Author: seeded 2026-04-20 from peer research (ChatGPT §206 + Kimi V3).
Status: UNBACKTESTED — baby tier. Graduate to main pipeline only after
≥60 days of paper-trading with Sharpe > 0.6 and max DD < 12%.
"""
from __future__ import annotations

from typing import Optional
import pandas as pd
import numpy as np


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SUIUSDT", "INJUSDT",
    "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT", "FETUSDT",
]


class CrossSectionalCryptoCarryStrategy:
    NAME = "cross_sectional_crypto_carry"
    DESCRIPTION = "Cross-sectional carry: long bottom-quintile funding, short top-quintile funding"
    ENTRY_RULES = (
        "Rank universe by 8h funding_rate. LONG if symbol is in bottom 20% "
        "AND |funding| > 0.01% (noise gate). SHORT if in top 20% with same gate. "
        "Rebalance weekly."
    )
    EXIT_RULES = "Exit at next weekly rebalance OR if symbol leaves the quintile OR 7d hard stop."
    ACADEMIC_SOURCE = "ChatGPT_STRATS.MD §206; Kimi V3 Funding Term-Structure Divergence"
    EXPECTED_WR = "55-62%"
    EXPECTED_TRADES_PER_YEAR = "~50 per symbol"

    def __init__(self, quintile_fraction: float = 0.20, noise_gate_bps: float = 1.0,
                 hold_bars: int = 21):  # 21 * 8h = 7 days
        self.quintile_fraction = quintile_fraction
        self.noise_gate = noise_gate_bps / 10000.0
        self.hold_bars = hold_bars

    def generate_signals(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
        context: Optional[dict] = None,
    ) -> list[dict]:
        """
        df: 8h OHLCV for `symbol`; must include `funding_rate` column.
        context: optional dict with key `universe_funding` = {sym: latest_funding_rate}
                 for cross-sectional ranking. Without it, emit no signals.
        """
        if len(df) < 50 or "funding_rate" not in df.columns:
            return []
        if context is None or "universe_funding" not in context:
            return []

        universe = context["universe_funding"]
        if not isinstance(universe, dict) or len(universe) < 5:
            return []

        my_fr = df["funding_rate"].iloc[-1]
        if pd.isna(my_fr) or abs(my_fr) < self.noise_gate:
            return []

        # Rank this symbol within the universe
        rates = sorted([(s, r) for s, r in universe.items() if r is not None and not pd.isna(r)],
                       key=lambda x: x[1])
        n = len(rates)
        if n < 5:
            return []

        k = max(1, int(n * self.quintile_fraction))
        bottom_k = {s for s, _ in rates[:k]}
        top_k = {s for s, _ in rates[-k:]}

        curr_close = float(df["close"].iloc[-1])

        # ATR for stop sizing
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        atr = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
        if pd.isna(atr) or atr <= 0:
            return []

        signals = []
        if symbol in bottom_k:
            signals.append({
                "symbol": symbol,
                "side": "LONG",
                "entry_price": curr_close,
                "stop_loss": curr_close - 2.0 * atr,
                "take_profit": curr_close + 3.0 * atr,
                "strategy": self.NAME,
                "strength": min(100, int(abs(my_fr) * 1e6)),
                "meta": {"funding_rate": float(my_fr), "universe_size": n,
                         "quintile": "bottom", "hold_bars": self.hold_bars},
            })
        elif symbol in top_k:
            signals.append({
                "symbol": symbol,
                "side": "SHORT",
                "entry_price": curr_close,
                "stop_loss": curr_close + 2.0 * atr,
                "take_profit": curr_close - 3.0 * atr,
                "strategy": self.NAME,
                "strength": min(100, int(abs(my_fr) * 1e6)),
                "meta": {"funding_rate": float(my_fr), "universe_size": n,
                         "quintile": "top", "hold_bars": self.hold_bars},
            })
        return signals
