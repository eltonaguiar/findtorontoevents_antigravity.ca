"""H-002: PEAD (Post-Earnings Announcement Drift) — SHADOW / OPT-IN sidecar.

Academic basis: Bernard & Thomas (1989), Livnat & Mendenhall (2006).
Edge: stocks systematically drift in the direction of earnings surprises for 30-60 days.
Pooled WR=53.2% on n=1964 events (forward_signal_research_2026-05-18.md), harness UNTESTED
(too few per-window events for walk-forward; collecting live data for future harness run).

Wire-up: OPT-IN ONLY — default gate is OFF (EQUITY_PEAD_ENABLED=0).
Wiring plan: will be wired into equity_scanner.py ONLY after harness confirms eff>=0.30
on >=3 walk-forward windows with >=30 events each (M-107 gate).

Data source: yfinance ticker.get_earnings_dates() — free, no API key required.
Fail-open on all fetch errors (never blocks production pick flow).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    yf = None  # type: ignore[assignment]
    _HAS_YFINANCE = False

_CACHE_PATH = Path(__file__).parent / "data" / "pead_earnings_cache.json"
_REPO_EARNINGS_DIR = Path(__file__).resolve().parent.parent / "data" / "earnings"
_CACHE_TTL_HOURS = 6
_MIN_SURPRISE_PCT = 5.0  # ≥5% beat to qualify
_HOLD_DAYS = 30
_DRIFT_MAX_DAYS = int(os.environ.get("PEAD_DRIFT_MAX_DAYS", "3") or "3")
_TP_PCT = 0.06  # 6% take-profit
_SL_PCT = 0.03  # 3% stop-loss

_PEAD_UNIVERSE = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM",
    "V", "MA", "UNH", "HD", "PG", "JNJ", "XOM", "CVX", "KO", "PEP",
    "WMT", "COST", "BAC", "DIS", "ADBE", "CRM", "NFLX", "INTC",
    "AMD", "QCOM", "TXN", "ORCL", "CSCO", "MCD", "NKE", "ABBV",
    "MRK", "PFE", "T", "VZ", "CAT", "BA", "GE", "IBM", "GS", "MS", "C",
]


def _load_cache() -> dict[str, Any]:
    try:
        if _CACHE_PATH.exists():
            data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_cache(cache: dict[str, Any]) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_repo_earnings(symbol: str, cache: dict[str, Any], now: datetime) -> float | None:
    path = _REPO_EARNINGS_DIR / symbol.upper() / "latest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("history") or []:
            surprise = row.get("surprise_pct")
            edate = row.get("date")
            if surprise is None or not edate:
                continue
            ed = datetime.fromisoformat(str(edate)).replace(tzinfo=timezone.utc)
            if ed >= now:
                continue
            cache[f"pead_{symbol}"] = {
                "surprise_pct": round(float(surprise), 2),
                "earnings_date": str(ed.date()),
                "cached_at": now.timestamp(),
                "source": "repo_earnings_cache",
            }
            return float(surprise)
    except Exception as e:
        logger.debug("Repo earnings cache failed for %s: %s", symbol, e)
    return None


def _fetch_earnings_surprise(symbol: str, cache: dict[str, Any]) -> float | None:
    """Return earnings surprise % for the most recent quarter, or None if unavailable.

    Surprise = (actual_eps - estimate_eps) / |estimate_eps| * 100.
    Uses yfinance get_earnings_dates(). Returns None on any error (fail-open).
    Cache TTL: 6 hours to avoid rate limits.
    """
    cache_key = f"pead_{symbol}"
    cached = cache.get(cache_key, {})
    cached_at = cached.get("cached_at")
    if cached_at:
        age_hours = (datetime.now(timezone.utc).timestamp() - cached_at) / 3600
        if age_hours < _CACHE_TTL_HOURS:
            return cached.get("surprise_pct")

    now = datetime.now(timezone.utc)
    repo_surprise = _load_repo_earnings(symbol, cache, now)
    if repo_surprise is not None:
        return repo_surprise

    try:
        if not _HAS_YFINANCE:
            return None
        ticker = yf.Ticker(symbol)
        # get_earnings_dates returns a DataFrame with 'Reported EPS' and 'EPS Estimate'
        ed = ticker.get_earnings_dates(limit=8)
        if ed is None or ed.empty:
            return None

        past = ed[ed.index < now].dropna(subset=["Reported EPS", "EPS Estimate"])
        if past.empty:
            return None

        latest = past.iloc[0]
        reported = float(latest["Reported EPS"])
        estimate = float(latest["EPS Estimate"])
        if abs(estimate) < 0.001:
            return None

        surprise_pct = (reported - estimate) / abs(estimate) * 100.0
        entry_date = past.index[0]

        result = {
            "surprise_pct": round(surprise_pct, 2),
            "reported": reported,
            "estimate": estimate,
            "earnings_date": str(entry_date.date()),
            "cached_at": now.timestamp(),
        }
        cache[cache_key] = result
        return surprise_pct

    except Exception as e:
        logger.debug("PEAD fetch failed for %s: %s", symbol, e)
        return None


def _earnings_days_ago(symbol: str, cache: dict[str, Any]) -> int | None:
    """Return days since last earnings announcement, or None."""
    cache_key = f"pead_{symbol}"
    cached = cache.get(cache_key, {})
    ed_str = cached.get("earnings_date")
    if not ed_str:
        return None
    try:
        ed = datetime.fromisoformat(ed_str).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ed).days
    except Exception:
        return None


def equity_pead_signals(symbols: list[str] | None = None) -> list[dict]:
    """Generate PEAD BUY signals for recent positive earnings surprises.

    OPT-IN ONLY — gate: EQUITY_PEAD_ENABLED (default 1=ON per PR4 2026-05-27).
    Returns empty list when gate is off or on any error (fail-open).

    Entry: 1-3 days after positive earnings surprise (≥5% beat).
    Hold: 30 trading days (PEAD drift window).
    TP: +6%, SL: -3%.
    """
    if os.environ.get("EQUITY_PEAD_ENABLED", "1").strip().lower() not in ("1", "true", "yes", "on"):
        return []

    universe = symbols or _PEAD_UNIVERSE
    cache = _load_cache()
    signals = []
    cache_dirty = False

    for symbol in universe:
        try:
            surprise_pct = _fetch_earnings_surprise(symbol, cache)
            cache_dirty = True

            if surprise_pct is None or surprise_pct < _MIN_SURPRISE_PCT:
                continue

            days_since = _earnings_days_ago(symbol, cache)
            if days_since is None or days_since > _DRIFT_MAX_DAYS:
                continue

            # Fetch current price via yfinance
            try:
                if _HAS_YFINANCE:
                    ticker = yf.Ticker(symbol)
                    fast_info = ticker.fast_info
                    entry_price = float(getattr(fast_info, "last_price", 0) or 0)
                else:
                    entry_price = 0.0
            except Exception:
                entry_price = 0.0

            if entry_price <= 0:
                continue

            # Scale confidence with surprise magnitude (5%→0.60, 20%→0.75 cap)
            confidence = min(0.75, 0.60 + (surprise_pct - _MIN_SURPRISE_PCT) / 100.0)
            tp = round(entry_price * (1 + _TP_PCT), 4)
            sl = round(entry_price * (1 - _SL_PCT), 4)
            rr = _TP_PCT / _SL_PCT  # 2.0

            cache_entry = cache.get(f"pead_{symbol}", {})
            signals.append({
                "symbol": symbol,
                "strategy": "equity_pead",
                "signal_type": "BUY",
                "direction": "LONG",
                "asset_class": "EQUITY",
                "entry_price": entry_price,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "hold_days": _HOLD_DAYS,
                "earnings_surprise_pct": round(surprise_pct, 2),
                "earnings_date": cache_entry.get("earnings_date"),
                "days_since_earnings": days_since,
                "_h002_shadow": True,
                "_pead_signal": True,
            })

        except Exception as e:  # noqa: BLE001
            logger.debug("PEAD signal error for %s: %s", symbol, e)
            continue

    if cache_dirty:
        _save_cache(cache)

    return signals
