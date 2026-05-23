"""IDEA-A factor: Earnings Surprise Momentum for EQUITY picks.

Swarm consensus 2026-05-19 (deepseek #1 pick, cerebras #4, inception confirmed):
Post-Earnings-Announcement Drift (PEAD). Stocks with positive earnings surprises
continue drifting upward 20-60 trading days as institutions gradually adjust.

Reference:
  Bernard & Thomas (1989) — PEAD: Delayed Price Response or Risk Premium?
                              J Accounting Research.
  Livnat & Mendenhall (2006) — Comparing PEAD for Analyst vs Time-Series Surprises.
                                J Accounting Research.

Score in [0, 100]:
  >60 = recent positive earnings surprise (EPS beat) within 30 days → bullish drift
  40-60 = neutral (no recent data or minimal surprise)
  <40 = negative surprise or miss

Fail-open: returns 50.0 on any fetch failure. Cached 60 minutes in-process.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

LOOKBACK_DAYS = 45   # earnings within this window count
CACHE_TTL_S   = 3600 # 60 minutes

_earnings_cache: dict[str, tuple[float, float]] = {}  # {symbol: (ts, score)}


def _days_since(date_str: str) -> Optional[int]:
    """Return days since a date string (ISO or pandas Timestamp string). None on failure."""
    try:
        if hasattr(date_str, 'date'):
            d = date_str.date()
        else:
            d = datetime.fromisoformat(str(date_str)[:10]).date()
        return (datetime.now(timezone.utc).date() - d).days
    except Exception:
        return None


def earnings_surprise_score(symbol: str, lookback_days: int = LOOKBACK_DAYS) -> float:
    """Return earnings surprise score in [0, 100].

    Checks yfinance earnings_dates for the most recent quarter's EPS surprise.
    Positive surprise within lookback_days → score > 60.
    No recent data or negative surprise → ≤ 50.
    """
    now = time.time()
    cached = _earnings_cache.get(symbol)
    if cached and now - cached[0] < CACHE_TTL_S:
        return cached[1]

    score = 50.0  # default neutral
    try:
        import yfinance as yf  # noqa: PLC0415
        tk = yf.Ticker(symbol)
        dates_df = tk.earnings_dates

        if dates_df is None or dates_df.empty:
            _earnings_cache[symbol] = (now, score)
            return score

        # Filter to past dates only (handle both tz-aware and tz-naive indices)
        now_dt = datetime.now(timezone.utc)
        try:
            if dates_df.index.tzinfo is not None or (
                hasattr(dates_df.index, 'tz') and dates_df.index.tz is not None
            ):
                past = dates_df[dates_df.index <= now_dt]
            else:
                past = dates_df[dates_df.index <= now_dt.replace(tzinfo=None)]
        except Exception:
            past = dates_df  # fallback: use all rows
        if past.empty:
            _earnings_cache[symbol] = (now, score)
            return score

        # Most recent past earnings date
        latest = past.sort_index(ascending=False).iloc[0]
        days_ago = _days_since(latest.name)
        if days_ago is None or days_ago > lookback_days:
            # Too old → neutral
            _earnings_cache[symbol] = (now, score)
            return score

        # Extract surprise percentage
        surprise_pct = None
        for col in ["Surprise(%)", "Surprise", "surprise_pct", "EPS Surprise %"]:
            if col in latest.index:
                try:
                    surprise_pct = float(latest[col])
                    break
                except (TypeError, ValueError):
                    pass

        if surprise_pct is None:
            # Try computing from estimate vs reported
            try:
                estimate = float(latest.get("EPS Estimate", 0) or 0)
                reported = float(latest.get("Reported EPS", 0) or 0)
                if estimate != 0:
                    surprise_pct = (reported - estimate) / abs(estimate) * 100
            except (TypeError, ValueError):
                pass

        if surprise_pct is None:
            _earnings_cache[symbol] = (now, score)
            return score

        # Map surprise % → score [0, 100]
        # surprise_pct > +10% → 90+
        # surprise_pct 0-10% → 60-90
        # surprise_pct < 0% → 10-50
        # Recency boost: very recent earnings get full score, older get discounted
        recency_factor = max(0.5, 1.0 - (days_ago / lookback_days) * 0.5)

        if surprise_pct >= 10.0:
            base = 90.0
        elif surprise_pct >= 5.0:
            base = 80.0
        elif surprise_pct >= 2.0:
            base = 70.0
        elif surprise_pct >= 0.0:
            base = 60.0
        elif surprise_pct >= -5.0:
            base = 35.0
        else:
            base = 10.0

        score = round(base * recency_factor + 50.0 * (1.0 - recency_factor), 2)
        score = max(0.0, min(100.0, score))

    except Exception:
        score = 50.0

    _earnings_cache[symbol] = (now, score)
    return score


def earnings_surprise_feature(pick: dict, lookback_days: int = LOOKBACK_DAYS) -> float:
    """Extract earnings_surprise_score from pick or compute it. Fail-open (50.0)."""
    precomputed = pick.get("earnings_surprise_score")
    if precomputed is not None:
        try:
            return float(precomputed)
        except (TypeError, ValueError):
            pass
    symbol = pick.get("symbol", "")
    if not symbol:
        return 50.0
    return earnings_surprise_score(symbol, lookback_days)


def stamp_pick(pick: dict, lookback_days: int = LOOKBACK_DAYS) -> dict:
    """Stamp earnings_surprise_score on EQUITY pick dict in-place. Fail-open."""
    try:
        if str(pick.get("asset_class", "")).upper() != "EQUITY":
            return pick
        symbol = pick.get("symbol", "")
        if not symbol:
            return pick
        pick["earnings_surprise_score"] = earnings_surprise_score(symbol, lookback_days)
    except Exception:
        pass
    return pick
