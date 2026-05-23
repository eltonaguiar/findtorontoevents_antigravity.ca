"""Signal-type registry for P3 backtest runner.

v3a: keyword-based dispatch from `spec.entry` text. Each handler
returns a pd.Series of {0, 1} positions (long-only for now) aligned
to the input price index. Walks NO_EDGE → MIXED → potentially GO
verdicts as signal types diversify.

v3b (next): LLM-driven translation of `spec.entry` natural-language
into a structured `signal_spec` dict, then dispatched to these
handlers. Less brittle than keyword regex.
"""

from __future__ import annotations

import re
from typing import Callable

import numpy as np
import pandas as pd

# Handler signature: (prices: pd.Series, params: dict) -> pd.Series of positions
SignalHandler = Callable[[pd.Series, dict], pd.Series]


# ──────────────────────────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────────────────────────


def sma_crossover(prices: pd.Series, params: dict) -> pd.Series:
    fast = int(params.get("fast", 50))
    slow = int(params.get("slow", 200))
    sma_fast = prices.rolling(fast).mean()
    sma_slow = prices.rolling(slow).mean()
    pos = (sma_fast > sma_slow).astype(float)
    return pos.shift(1).fillna(0)


def rsi_mean_reversion(prices: pd.Series, params: dict) -> pd.Series:
    period = int(params.get("period", 14))
    oversold = float(params.get("oversold", 30))
    overbought = float(params.get("overbought", 70))
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # Enter long when oversold; exit when crossing overbought
    pos = pd.Series(0.0, index=prices.index)
    in_pos = False
    for i in range(len(rsi)):
        r = rsi.iat[i] if not np.isnan(rsi.iat[i]) else 50
        if not in_pos and r < oversold:
            in_pos = True
        elif in_pos and r > overbought:
            in_pos = False
        pos.iat[i] = 1.0 if in_pos else 0.0
    return pos.shift(1).fillna(0)


def momentum(prices: pd.Series, params: dict) -> pd.Series:
    lookback = int(params.get("lookback", 60))
    threshold = float(params.get("threshold", 0))
    mom = prices.pct_change(lookback)
    pos = (mom > threshold).astype(float)
    return pos.shift(1).fillna(0)


def mean_reversion_zscore(prices: pd.Series, params: dict) -> pd.Series:
    window = int(params.get("window", 60))
    threshold = float(params.get("threshold", 1.5))
    rolling_mean = prices.rolling(window).mean()
    rolling_std = prices.rolling(window).std()
    z = (prices - rolling_mean) / rolling_std.replace(0, np.nan)
    pos = pd.Series(0.0, index=prices.index)
    in_pos = False
    for i in range(len(z)):
        zi = z.iat[i] if not np.isnan(z.iat[i]) else 0
        if not in_pos and zi < -threshold:
            in_pos = True
        elif in_pos and zi > 0:
            in_pos = False
        pos.iat[i] = 1.0 if in_pos else 0.0
    return pos.shift(1).fillna(0)


def buy_and_hold(prices: pd.Series, params: dict) -> pd.Series:
    return pd.Series(1.0, index=prices.index)


def breakout(prices: pd.Series, params: dict) -> pd.Series:
    window = int(params.get("window", 50))
    highest = prices.rolling(window).max()
    pos = (prices >= highest).astype(float)
    # Hold position for `hold_days` after breakout
    hold = int(params.get("hold_days", 20))
    held_pos = pos.copy()
    for i in range(len(held_pos)):
        if held_pos.iat[i] > 0:
            for j in range(min(hold, len(held_pos) - i - 1)):
                held_pos.iat[i + j + 1] = max(held_pos.iat[i + j + 1], 1.0)
    return held_pos.shift(1).fillna(0)


# ──────────────────────────────────────────────────────────────────
# Registry + dispatcher
# ──────────────────────────────────────────────────────────────────


HANDLERS: dict[str, SignalHandler] = {
    "sma_cross": sma_crossover,
    "rsi_mr": rsi_mean_reversion,
    "momentum": momentum,
    "mean_reversion_zscore": mean_reversion_zscore,
    "buy_and_hold": buy_and_hold,
    "breakout": breakout,
}


def classify_from_text(text: str) -> str:
    """Keyword route — returns handler key based on spec.entry text.

    Order matters: more-specific matches checked first.
    """
    t = (text or "").lower()
    if re.search(r"\brsi\b|relative\s+strength", t):
        return "rsi_mr"
    if "z-score" in t or "zscore" in t or "mean revert" in t or "mean-revert" in t:
        return "mean_reversion_zscore"
    if "breakout" in t or "donchian" in t or "highest" in t:
        return "breakout"
    if "buy and hold" in t or "buy-and-hold" in t:
        return "buy_and_hold"
    if "momentum" in t or "trend" in t or "60d" in t or "12m change" in t:
        return "momentum"
    # Default: SMA crossover
    return "sma_cross"


def positions_for_spec(spec_entry_text: str, prices: pd.Series, params: dict | None = None) -> tuple[pd.Series, str]:
    """Return (position_series, signal_type_used)."""
    sig = classify_from_text(spec_entry_text)
    handler = HANDLERS[sig]
    pos = handler(prices, params or {})
    return pos, sig
