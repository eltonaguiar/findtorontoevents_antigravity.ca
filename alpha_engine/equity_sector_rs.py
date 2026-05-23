"""IDEA-A factor: Sector ETF Relative Strength for EQUITY picks.

Swarm consensus 2026-05-19 (cerebras + deepseek + inception unanimous):
Sector ETF RS is the lowest-complexity / highest-consensus IDEA-A factor.
Implementation complexity 1/5, free via yfinance, expected WR lift +5-8%.

Returns a score in [0, 100]:
  >60 = stock's sector is in the top third by 30-day return → bullish
  40-60 = neutral
  <40 = sector in bottom third → bearish

Fail-open: returns 50.0 (neutral) on any fetch failure so it never blocks
picks. Cached for 60 minutes in-process (module-level dict).

Reference:
  Moskowitz & Grinblatt (1999) — Do Industries Explain Momentum? J Finance.
  Jegadeesh & Titman (1993) — Returns to Buying Winners. J Finance.
"""
from __future__ import annotations

import os
import time
from typing import Optional

SECTOR_ETFS: dict[str, str] = {
    "Technology":              "XLK",
    "Energy":                  "XLE",
    "Financials":              "XLF",
    "Health Care":             "XLV",
    "Consumer Discretionary":  "XLY",
    "Consumer Staples":        "XLP",
    "Industrials":             "XLI",
    "Materials":               "XLB",
    "Real Estate":             "XLRE",
    "Communication Services":  "XLC",
    "Utilities":               "XLU",
}

LOOKBACK_DAYS = 30       # 30-calendar-day sector RS window (≈20 trading days)
CACHE_TTL_S   = 3600     # 60 minutes

# Module-level caches
_sector_returns_cache: dict[str, tuple[float, dict[str, float]]] = {}
_symbol_sector_cache:  dict[str, tuple[float, Optional[str]]] = {}


def _fetch_sector_returns(lookback_days: int = LOOKBACK_DAYS) -> dict[str, float]:
    """Fetch 30-day price returns for all sector ETFs.

    Returns {sector_name: pct_return} or {} on failure.
    """
    now = time.time()
    cached = _sector_returns_cache.get("all")
    if cached and now - cached[0] < CACHE_TTL_S:
        return cached[1]

    try:
        import yfinance as yf  # noqa: PLC0415
        etf_tickers = list(SECTOR_ETFS.values())
        period = f"{lookback_days + 5}d"
        data = yf.download(
            etf_tickers, period=period, interval="1d",
            auto_adjust=True, progress=False, group_by="ticker",
        )
        returns: dict[str, float] = {}
        for sector, etf in SECTOR_ETFS.items():
            try:
                if hasattr(data, "columns") and hasattr(data.columns, "levels"):
                    closes = data[etf]["Close"].dropna()
                else:
                    closes = data["Close"].dropna()
                if len(closes) < 2:
                    continue
                ret = float(closes.iloc[-1] / closes.iloc[0] - 1.0)
                returns[sector] = ret
            except Exception:
                continue
        if returns:
            _sector_returns_cache["all"] = (now, returns)
        return returns
    except Exception:
        return {}


def _lookup_sector(symbol: str) -> Optional[str]:
    """Return the GICS sector string for a symbol via yfinance, cached."""
    now = time.time()
    cached = _symbol_sector_cache.get(symbol)
    if cached and now - cached[0] < CACHE_TTL_S:
        return cached[1]

    try:
        import yfinance as yf  # noqa: PLC0415
        info = yf.Ticker(symbol).info
        sector = info.get("sector") or info.get("sectorDisp") or None
        _symbol_sector_cache[symbol] = (now, sector)
        return sector
    except Exception:
        _symbol_sector_cache[symbol] = (now, None)
        return None


def sector_rs_score(symbol: str, lookback_days: int = LOOKBACK_DAYS) -> float:
    """Return sector relative-strength score in [0, 100].

    Mapping:
      sector ranked #1-#3 (top third)  → ~70-90
      sector ranked #4-#8 (mid)        → ~40-60
      sector ranked #9-#11 (bot third) → ~10-30
      unknown / fetch failure           → 50.0 (neutral, fail-open)
    """
    returns = _fetch_sector_returns(lookback_days)
    if not returns:
        return 50.0

    sector = _lookup_sector(symbol)
    if not sector or sector not in returns:
        return 50.0

    # Rank all sectors: 1 = best
    sorted_sectors = sorted(returns, key=returns.get, reverse=True)
    rank = sorted_sectors.index(sector) + 1  # 1-indexed
    n = len(sorted_sectors)

    # Map rank to [0, 100] linearly, inverted (rank 1 → 100, rank n → 0)
    score = 100.0 * (1.0 - (rank - 1) / max(n - 1, 1))
    return round(score, 2)


def sector_rs_feature(pick: dict, lookback_days: int = LOOKBACK_DAYS) -> float:
    """Extract sector_rs_score from pick dict or compute it fresh.

    Checks pick['sector_rs_score'] first (pre-stamped by score_pick).
    Falls back to computing from pick['symbol']. Always fail-open (50.0).
    """
    precomputed = pick.get("sector_rs_score")
    if precomputed is not None:
        try:
            return float(precomputed)
        except (TypeError, ValueError):
            pass
    symbol = pick.get("symbol", "")
    if not symbol:
        return 50.0
    return sector_rs_score(symbol, lookback_days)


def stamp_pick(pick: dict, lookback_days: int = LOOKBACK_DAYS) -> dict:
    """Compute and stamp sector_rs_score on the pick dict in-place.

    Returns the pick dict for chaining. Fail-open: on any error the
    pick is unchanged (no sector_rs_score key added).
    """
    try:
        asset_class = str(pick.get("asset_class", "")).upper()
        if asset_class != "EQUITY":
            return pick
        symbol = pick.get("symbol", "")
        if not symbol:
            return pick
        pick["sector_rs_score"] = sector_rs_score(symbol, lookback_days)
    except Exception:
        pass
    return pick
