"""
EQUITY FACTOR MODEL & EARNINGS MOMENTUM
========================================
Multi-factor scoring and Post-Earnings Announcement Drift (PEAD) for equity picks.

Factors:
  1. Value: P/E ratio (lower = better) — Fama & French (1992)
  2. Momentum: 6-month price return (higher = better) — Jegadeesh & Titman (1993)
  3. Quality: ROE (higher = better) — Asness, Frazzini & Pedersen (2019)
  4. Earnings Momentum: Recent earnings surprise — Ball & Brown (1968) PEAD

Usage in equity_strategies.py or smart_picks_engine.py:
    from equity_factor_model import compute_factor_boost, compute_earnings_boost

    # Factor composite: returns +0.10 if strong alignment, 0.0 otherwise
    factor_adj = compute_factor_boost(symbol)

    # Earnings: +0.05 if beat >5%, -0.10 if missed >5%, 0.0 otherwise
    earnings_adj = compute_earnings_boost(symbol)

    confidence = base_confidence + factor_adj + earnings_adj
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("equity_factor_model")

# ---------------------------------------------------------------------------
# In-memory cache to avoid hammering yfinance on every pick evaluation
# Cache TTL: 6 hours (factor data doesn't change intraday)
# ---------------------------------------------------------------------------
_CACHE: dict[str, dict] = {}
_CACHE_TTL = 6 * 3600  # seconds


def _get_stock_info(symbol: str) -> Optional[dict]:
    """Fetch stock info via yfinance with caching. Returns None on failure."""
    now = time.time()
    cached = _CACHE.get(symbol)
    if cached and (now - cached.get("_ts", 0)) < _CACHE_TTL:
        return cached

    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        info["_ts"] = now
        _CACHE[symbol] = info
        return info
    except ImportError:
        log.debug("yfinance not installed — factor model disabled")
        return None
    except Exception as exc:
        log.debug("yfinance fetch failed for %s: %s", symbol, exc)
        return None


def _get_earnings_data(symbol: str) -> Optional[dict]:
    """Fetch earnings surprise data via yfinance. Returns dict with surprise_pct or None."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)

        # Try earnings_dates first (has surprise data)
        try:
            ed = ticker.earnings_dates
            if ed is not None and len(ed) > 0:
                # Find most recent past earnings
                now_utc = datetime.now(timezone.utc)
                past = ed[ed.index <= now_utc]
                if len(past) > 0:
                    latest = past.iloc[0]
                    # Columns vary: "Surprise(%)" or "EPS Surprise %"
                    surprise_pct = None
                    for col in ["Surprise(%)", "EPS Surprise %", "Surprise (%)"]:
                        if col in ed.columns:
                            val = latest.get(col)
                            if val is not None and str(val) not in ("nan", "None", ""):
                                try:
                                    surprise_pct = float(val)
                                except (ValueError, TypeError):
                                    pass
                            break

                    if surprise_pct is not None:
                        return {
                            "surprise_pct": surprise_pct,
                            "date": str(past.index[0]),
                        }
        except Exception:
            pass

        # Fallback: quarterly earnings from financials
        try:
            qe = ticker.quarterly_earnings
            if qe is not None and len(qe) > 0:
                latest = qe.iloc[0]
                actual = float(latest.get("Actual", 0) or 0)
                estimate = float(latest.get("Estimate", 0) or 0)
                if estimate != 0:
                    surprise_pct = ((actual - estimate) / abs(estimate)) * 100
                    return {"surprise_pct": surprise_pct, "date": str(qe.index[0])}
        except Exception:
            pass

        return None
    except ImportError:
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# FACTOR COMPOSITE SCORE
# ---------------------------------------------------------------------------

def compute_factor_score(symbol: str) -> tuple[float, str]:
    """Compute multi-factor composite for an equity symbol.

    Returns:
        (score, explanation) where score is 0.0 to 1.0
        Score >= 0.65 = strong factor alignment
    """
    info = _get_stock_info(symbol)
    if info is None:
        return (0.5, "no data")

    scores = []
    parts = []

    # Factor 1: VALUE — P/E ratio (lower = better, inverted and normalized)
    pe = info.get("trailingPE") or info.get("forwardPE")
    if pe is not None:
        try:
            pe = float(pe)
            if 0 < pe < 200:  # Sane range
                # P/E of 10 = excellent (1.0), P/E of 50+ = poor (0.0)
                value_score = max(0.0, min(1.0, 1.0 - (pe - 10) / 40.0))
                scores.append(("value", value_score, 0.30))
                parts.append(f"PE={pe:.1f}(v={value_score:.2f})")
        except (ValueError, TypeError):
            pass

    # Factor 2: MOMENTUM — 6-month return (from yfinance or price history)
    # Use 52WeekChange as proxy (annualized); halve for ~6mo estimate
    week52_change = info.get("52WeekChange")
    if week52_change is not None:
        try:
            mom_6m = float(week52_change) / 2.0  # Rough 6-month proxy
            # +30% = excellent (1.0), -10% = poor (0.0)
            momentum_score = max(0.0, min(1.0, (mom_6m + 0.10) / 0.40))
            scores.append(("momentum", momentum_score, 0.35))
            parts.append(f"6mRet~{mom_6m*100:.1f}%(m={momentum_score:.2f})")
        except (ValueError, TypeError):
            pass

    # Factor 3: QUALITY — ROE (higher = better)
    roe = info.get("returnOnEquity")
    if roe is not None:
        try:
            roe = float(roe)
            # ROE of 25%+ = excellent (1.0), 0% = poor (0.0)
            quality_score = max(0.0, min(1.0, roe / 0.25))
            scores.append(("quality", quality_score, 0.35))
            parts.append(f"ROE={roe*100:.1f}%(q={quality_score:.2f})")
        except (ValueError, TypeError):
            pass

    if not scores:
        return (0.5, "insufficient factor data")

    # Weighted composite
    total_weight = sum(w for _, _, w in scores)
    composite = sum(s * w for _, s, w in scores) / total_weight if total_weight > 0 else 0.5

    explanation = ", ".join(parts)
    return (round(composite, 3), explanation)


def compute_factor_boost(symbol: str) -> float:
    """Return confidence boost from factor model.

    Returns:
        +0.10 if factor composite >= 0.65 (strong alignment)
        +0.05 if factor composite >= 0.50 (moderate alignment)
         0.00 otherwise (weak or no data)
        -0.05 if factor composite < 0.30 (poor factors — value trap or junk)
    """
    score, _ = compute_factor_score(symbol)
    if score >= 0.65:
        return 0.10
    elif score >= 0.50:
        return 0.05
    elif score < 0.30:
        return -0.05
    return 0.0


# ---------------------------------------------------------------------------
# EARNINGS MOMENTUM (PEAD — Post-Earnings Announcement Drift)
# ---------------------------------------------------------------------------

def compute_earnings_boost(symbol: str) -> float:
    """Return confidence adjustment based on recent earnings surprise.

    Returns:
        +0.05 if beat by >5% (positive PEAD drift)
         0.00 if no data or within +/-5% (neutral)
        -0.10 if missed by >5% (negative PEAD drift — asymmetric penalty)

    The asymmetry is intentional: negative earnings surprises create larger
    and longer-lasting price effects than positive ones (Livnat & Mendenhall 2006).
    """
    data = _get_earnings_data(symbol)
    if data is None:
        return 0.0

    surprise = data.get("surprise_pct", 0.0)
    if surprise is None:
        return 0.0

    try:
        surprise = float(surprise)
    except (ValueError, TypeError):
        return 0.0

    if surprise > 5.0:
        return 0.05   # Beat earnings by >5% — bullish PEAD
    elif surprise < -5.0:
        return -0.10  # Missed earnings by >5% — bearish PEAD (asymmetric)
    return 0.0


# ---------------------------------------------------------------------------
# COMBINED EQUITY ENHANCEMENT (single call for convenience)
# ---------------------------------------------------------------------------

def enhance_equity_confidence(symbol: str, base_confidence: float) -> tuple[float, str]:
    """Apply factor model + earnings momentum to an equity pick's confidence.

    Returns:
        (adjusted_confidence, explanation_string)
    """
    factor_boost = compute_factor_boost(symbol)
    earnings_boost = compute_earnings_boost(symbol)

    factor_score, factor_detail = compute_factor_score(symbol)
    earnings_data = _get_earnings_data(symbol)
    earnings_detail = ""
    if earnings_data:
        earnings_detail = f"EPS surprise={earnings_data.get('surprise_pct', 0):.1f}%"

    total_adj = factor_boost + earnings_boost
    new_conf = round(max(0.30, min(0.95, base_confidence + total_adj)), 2)

    parts = []
    if factor_boost != 0:
        parts.append(f"factor({factor_boost:+.2f}, {factor_detail})")
    if earnings_boost != 0:
        parts.append(f"PEAD({earnings_boost:+.2f}, {earnings_detail})")

    explanation = " | ".join(parts) if parts else "no factor/earnings adjustment"
    return (new_conf, explanation)
