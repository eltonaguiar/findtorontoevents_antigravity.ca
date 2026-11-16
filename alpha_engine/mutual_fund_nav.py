"""Mutual-fund NAV layer.

Mutual funds do not trade intraday: they price once per day at the fund's NAV.
The rest of this repo fetches OHLCV bars (`interval="1h"`), which returns an
empty frame for a `MUTUALFUND` ticker and made the class invisible to the
dashboard. This module is the NAV-specific data path:

  * ``MUTUAL_FUND_SYMBOLS`` — the fund universe (no-load, low-cost core funds).
  * ``is_mutual_fund(symbol)`` — classification used by asset_class.py.
  * ``fetch_nav(symbol)`` — latest NAV + previous NAV + daily change, from
    yfinance daily closes, cached on disk (12 h TTL) so a resolver run does not
    hammer the provider.
  * ``fetch_navs(symbols)`` / CLI for batch refresh.

Everything fails open: a missing provider or empty history returns ``None``
rather than a fabricated price. No picks are emitted here — this only makes the
class priceable and visible.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_PATH = ROOT / "alpha_engine" / "data" / "mutual_fund_nav_cache.json"
CACHE_TTL_HOURS = 12

#: No-load / low-cost core funds across the major US families.
MUTUAL_FUND_SYMBOLS: frozenset[str] = frozenset(
    {
        # Vanguard
        "VFIAX", "VTSAX", "VTIAX", "VBTLX", "VWINX", "VWELX", "VFSTX",
        "VIGAX", "VHYAX", "VEMAX", "VGTSX", "VBMFX", "VIPSX",
        # Fidelity
        "FXAIX", "FSKAX", "FTIHX", "FXNAX", "FZROX", "FZILX", "FBGRX",
        # Schwab
        "SWPPX", "SWTSX", "SWISX", "SWAGX", "SWEGX",
        # T. Rowe Price / PIMCO / others
        "PRBLX", "PIMIX", "PTTRX", "TRBCX", "DODGX", "VPMCX",
    }
)

HistoryProvider = Callable[[str, str], Sequence[Tuple[str, float]]]


def is_mutual_fund(symbol: Any) -> bool:
    """True for a mutual-fund ticker (case-insensitive, suffix-tolerant)."""
    text = str(symbol or "").strip().upper()
    if not text:
        return False
    return text in MUTUAL_FUND_SYMBOLS


def _default_history_provider(symbol: str, period: str) -> List[Tuple[str, float]]:
    """Daily closes as [(YYYY-MM-DD, close), ...] ascending. May raise."""
    import yfinance as yf  # imported lazily: tests inject their own provider

    frame = yf.Ticker(symbol).history(
        period=period, interval="1d", auto_adjust=False
    )
    if frame is None or getattr(frame, "empty", True):
        return []
    closes = frame["Close"].dropna()
    return [
        (str(idx)[:10], float(value))
        for idx, value in closes.items()
        if value == value and value > 0
    ]


def _read_cache(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _cache_is_fresh(entry: Dict[str, Any], now: datetime, ttl_hours: int) -> bool:
    raw = entry.get("fetched_at")
    if not raw:
        return False
    try:
        fetched = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return now - fetched < timedelta(hours=ttl_hours)


def _write_cache_atomic(path: Path, cache: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(cache, handle, indent=1, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def build_nav_record(
    symbol: str, history: Sequence[Tuple[str, float]]
) -> Optional[Dict[str, Any]]:
    """Latest NAV, previous NAV and daily change from ascending daily closes."""
    rows = [(str(d)[:10], float(v)) for d, v in (history or []) if v and float(v) > 0]
    if not rows:
        return None
    rows.sort(key=lambda item: item[0])
    nav_date, nav = rows[-1]
    prev_nav = rows[-2][1] if len(rows) > 1 else None
    change_pct = (
        round((nav - prev_nav) / prev_nav * 100.0, 4) if prev_nav else None
    )
    return {
        "symbol": symbol.upper(),
        "nav": round(nav, 6),
        "nav_date": nav_date,
        "prev_nav": round(prev_nav, 6) if prev_nav else None,
        "change_pct": change_pct,
        "source": "yfinance_daily_nav",
    }


def fetch_nav(
    symbol: str,
    *,
    period: str = "10d",
    cache_path: Optional[Path] = None,
    ttl_hours: int = CACHE_TTL_HOURS,
    now: Optional[datetime] = None,
    history_provider: Optional[HistoryProvider] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch one fund's NAV, served from the on-disk cache when fresh."""
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        return None
    now = now or datetime.now(timezone.utc)
    cache_path = Path(cache_path) if cache_path else DEFAULT_CACHE_PATH
    cache = _read_cache(cache_path)

    cached = cache.get(symbol)
    if isinstance(cached, dict) and _cache_is_fresh(cached, now, ttl_hours):
        return cached

    provider = history_provider or _default_history_provider
    try:
        history = provider(symbol, period)
    except Exception:
        return cached if isinstance(cached, dict) else None

    record = build_nav_record(symbol, history)
    if record is None:
        return cached if isinstance(cached, dict) else None
    record["fetched_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    cache[symbol] = record
    try:
        _write_cache_atomic(cache_path, cache)
    except OSError:
        pass
    return record


def fetch_navs(
    symbols: Iterable[str], **kwargs: Any
) -> Dict[str, Optional[Dict[str, Any]]]:
    return {str(s).upper(): fetch_nav(str(s), **kwargs) for s in symbols}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Refresh mutual-fund NAV cache")
    parser.add_argument("--symbols", nargs="*", default=sorted(MUTUAL_FUND_SYMBOLS))
    parser.add_argument("--cache", default=str(DEFAULT_CACHE_PATH))
    args = parser.parse_args(argv)
    out = fetch_navs(args.symbols, cache_path=Path(args.cache))
    ok = sum(1 for v in out.values() if v)
    print("[mf-nav] %d/%d funds priced -> %s" % (ok, len(out), args.cache))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
