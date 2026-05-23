"""Earnings calendar fetcher with Finnhub primary + EDGAR 8-K + yfinance failover.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 6 value_screener.py + Phase 11 dashboard.

Design (per findings/SYNTHESIS.md §1):
  Primary:   Finnhub free tier (60 rpm, 1M/mo) — `/calendar/earnings` + `/stock/earnings`
  Fallback:  SEC EDGAR 8-K parsing (Phase 14+ stub for now)
  Final:     yfinance (.calendar / .earnings_dates) — lazy import
  Cache:     JSON at data/earnings/{ticker}/latest.json, TTL 24h

Returns standardized `EarningsRecord` records whose `history` field conforms exactly
to the `EarningsRow` TypedDict in `alpha_engine.long_term_pick_contract`.

Stdlib HTTP only (urllib). Set FINNHUB_API_KEY env var to enable the primary path.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.error import HTTPError, URLError

from alpha_engine.long_term_pick_contract import EarningsRow

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
FINNHUB_EARNINGS_HISTORY_URL = FINNHUB_BASE + "/stock/earnings?symbol={ticker}&token={token}"
FINNHUB_EARNINGS_CALENDAR_URL = (
    FINNHUB_BASE + "/calendar/earnings?from={from_d}&to={to_d}&symbol={ticker}&token={token}"
)
DEFAULT_CACHE_DIR = Path("data/earnings")
DEFAULT_TTL_HOURS = 24
EarningsSource = Literal["finnhub", "edgar_8k", "yfinance", "missing"]


@dataclass
class EarningsRecord:
    """Standardized earnings snapshot for one ticker."""
    ticker: str
    next_earnings_date: str | None = None
    next_earnings_estimate: float | None = None
    history: list[EarningsRow] = field(default_factory=list)
    fetched_at: str = ""
    source: EarningsSource = "missing"
    cache_hit: bool = False

    def is_complete(self) -> bool:
        """A record is 'complete' if we have at least one historical earnings row.

        next_earnings_date can legitimately be None for tickers between announce cycles,
        so we don't require it.
        """
        return bool(self.history)


def _stdlib_http_get(url: str, user_agent: str = "alpha_engine-earnings/1.0") -> str:
    """Plain stdlib HTTP GET. Injectable on adapters via `_http_get` attribute."""
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


class FinnhubEarningsAdapter:
    """Primary adapter — Finnhub free tier."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else os.environ.get("FINNHUB_API_KEY")
        self._http_get: Callable[[str, str], str] = _stdlib_http_get

    def fetch(self, ticker: str) -> EarningsRecord | None:
        if not self.api_key:
            logger.debug("FinnhubEarningsAdapter: FINNHUB_API_KEY not set, skipping")
            return None
        ticker_u = ticker.upper().strip()
        history = self._fetch_history(ticker_u)
        next_date, next_est = self._fetch_calendar(ticker_u)
        if not history and next_date is None:
            return None
        return EarningsRecord(
            ticker=ticker_u,
            next_earnings_date=next_date,
            next_earnings_estimate=next_est,
            history=history,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="finnhub",
        )

    def _fetch_history(self, ticker: str) -> list[EarningsRow]:
        url = FINNHUB_EARNINGS_HISTORY_URL.format(ticker=ticker, token=self.api_key)
        try:
            raw = self._http_get(url, "alpha_engine-earnings/1.0")
            data = json.loads(raw)
        except (HTTPError, URLError, json.JSONDecodeError, OSError) as e:
            logger.warning("Finnhub earnings history failed for %s: %s", ticker, e)
            return []
        return self._parse_history(data)

    @staticmethod
    def _parse_history(data: Any) -> list[EarningsRow]:
        if not isinstance(data, list):
            return []
        rows: list[EarningsRow] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            date = entry.get("period") or entry.get("date") or ""
            if not date:
                continue
            actual = entry.get("actual")
            estimate = entry.get("estimate")
            surprise_pct = entry.get("surprisePercent")
            row: EarningsRow = {
                "date": str(date),
                "eps_actual": float(actual) if actual is not None else None,
                "eps_estimate": float(estimate) if estimate is not None else None,
                "surprise_pct": float(surprise_pct) if surprise_pct is not None else None,
            }
            rows.append(row)
        # Newest first, capped at 8 quarters.
        rows.sort(key=lambda r: r["date"], reverse=True)
        return rows[:8]

    def _fetch_calendar(self, ticker: str) -> tuple[str | None, float | None]:
        # Look ahead 120 days for next announce.
        today = datetime.now(timezone.utc).date()
        from_d = today.isoformat()
        to_d = today.replace(year=today.year + (1 if today.month > 8 else 0)).isoformat()
        url = FINNHUB_EARNINGS_CALENDAR_URL.format(
            from_d=from_d, to_d=to_d, ticker=ticker, token=self.api_key
        )
        try:
            raw = self._http_get(url, "alpha_engine-earnings/1.0")
            data = json.loads(raw)
        except (HTTPError, URLError, json.JSONDecodeError, OSError) as e:
            logger.warning("Finnhub earnings calendar failed for %s: %s", ticker, e)
            return (None, None)
        if not isinstance(data, dict):
            return (None, None)
        events = data.get("earningsCalendar") or []
        if not isinstance(events, list) or not events:
            return (None, None)
        # Prefer earliest upcoming.
        events_sorted = sorted(
            (e for e in events if isinstance(e, dict) and e.get("date")),
            key=lambda e: e.get("date", ""),
        )
        if not events_sorted:
            return (None, None)
        first = events_sorted[0]
        date = first.get("date")
        est = first.get("epsEstimate")
        return (
            str(date) if date else None,
            float(est) if est is not None else None,
        )


class EdgarEightKAdapter:
    """Stub adapter — SEC 8-K parsing for earnings is a Phase 14+ deliverable.

    Returns None unconditionally. Wired in for failover-chain symmetry only.
    """

    def __init__(self) -> None:
        self._http_get: Callable[[str, str], str] = _stdlib_http_get

    def fetch(self, ticker: str) -> EarningsRecord | None:  # noqa: ARG002
        logger.debug("EdgarEightKAdapter: stub, returning None for %s", ticker)
        return None


class YfinanceEarningsAdapter:
    """Final fallback — yfinance .calendar / .earnings_dates. Lazy-imports yfinance."""

    def fetch(self, ticker: str) -> EarningsRecord | None:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed — earnings fallback unavailable")
            return None
        ticker_u = ticker.upper().strip()
        try:
            t = yf.Ticker(ticker_u)
        except Exception as e:
            logger.warning("yfinance Ticker(%s) failed: %s", ticker_u, e)
            return None

        next_date: str | None = None
        next_est: float | None = None
        try:
            cal = t.calendar
            if cal is not None:
                # yfinance returns either a dict or a DataFrame depending on version.
                next_date, next_est = _yf_extract_calendar(cal)
        except Exception as e:
            logger.debug("yfinance calendar(%s) failed: %s", ticker_u, e)

        history: list[EarningsRow] = []
        try:
            ed = getattr(t, "earnings_dates", None)
            if ed is not None:
                history = _yf_extract_history(ed)
        except Exception as e:
            logger.debug("yfinance earnings_dates(%s) failed: %s", ticker_u, e)

        if not history and next_date is None:
            return None

        return EarningsRecord(
            ticker=ticker_u,
            next_earnings_date=next_date,
            next_earnings_estimate=next_est,
            history=history,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="yfinance",
        )


def _yf_extract_calendar(cal: Any) -> tuple[str | None, float | None]:
    """Best-effort extraction of next earnings date + EPS estimate from yfinance calendar.

    yfinance returns this as either a dict-ish or a DataFrame; we tolerate both.
    """
    try:
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if isinstance(ed, list) and ed:
                date = str(ed[0])[:10]
            else:
                date = str(ed)[:10] if ed else None
            est = cal.get("Earnings Average")
            est_f = float(est) if est is not None else None
            return (date, est_f)
        # Pandas DataFrame fallback.
        if hasattr(cal, "iloc") and hasattr(cal, "columns"):
            try:
                first_col = cal.iloc[:, 0]
                date = str(first_col.get("Earnings Date", ""))[:10] or None
                est = first_col.get("Earnings Average")
                est_f = float(est) if est is not None else None
                return (date, est_f)
            except Exception:
                return (None, None)
    except Exception:
        return (None, None)
    return (None, None)


def _yf_extract_history(ed: Any) -> list[EarningsRow]:
    """Best-effort extraction of historical EPS rows from yfinance earnings_dates."""
    rows: list[EarningsRow] = []
    try:
        if hasattr(ed, "iterrows"):
            for idx, row in ed.iterrows():
                date = str(idx)[:10]
                actual = row.get("Reported EPS") if hasattr(row, "get") else None
                estimate = row.get("EPS Estimate") if hasattr(row, "get") else None
                surprise = row.get("Surprise(%)") if hasattr(row, "get") else None
                rows.append({
                    "date": date,
                    "eps_actual": float(actual) if actual is not None and actual == actual else None,
                    "eps_estimate": float(estimate) if estimate is not None and estimate == estimate else None,
                    "surprise_pct": float(surprise) if surprise is not None and surprise == surprise else None,
                })
    except Exception as e:
        logger.debug("yfinance history extraction failed: %s", e)
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows[:8]


class EarningsCache:
    """On-disk JSON cache with TTL."""

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR, ttl_hours: int = DEFAULT_TTL_HOURS):
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_hours * 3600

    def _path_for(self, ticker: str) -> Path:
        return self.cache_dir / ticker.upper() / "latest.json"

    def get(self, ticker: str) -> EarningsRecord | None:
        path = self._path_for(ticker)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Earnings cache read failed for %s: %s", ticker, e)
            return None
        fetched_at = data.get("fetched_at", "")
        if fetched_at:
            try:
                fetched_dt = datetime.fromisoformat(fetched_at)
                age = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
                if age > self.ttl_seconds:
                    return None
            except ValueError:
                pass
        record = EarningsRecord(**data)
        record.cache_hit = True
        return record

    def put(self, record: EarningsRecord) -> None:
        # Never cache the missing stub — we want to retry next call.
        if record.source == "missing":
            return
        path = self._path_for(record.ticker)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(
                json.dumps(asdict(record), indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("Earnings cache write failed for %s: %s", record.ticker, e)


class EarningsCalendarFetcher:
    """Public facade. Failover: cache -> Finnhub -> EDGAR 8-K -> yfinance -> missing stub."""

    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        api_key: str | None = None,
    ):
        self.cache = EarningsCache(cache_dir, ttl_hours)
        self.finnhub = FinnhubEarningsAdapter(api_key=api_key)
        self.edgar_8k = EdgarEightKAdapter()
        self.yfinance = YfinanceEarningsAdapter()

    def fetch(self, ticker: str, *, force_refresh: bool = False) -> EarningsRecord:
        ticker_u = ticker.upper().strip()
        if not force_refresh:
            cached = self.cache.get(ticker_u)
            if cached is not None:
                return cached

        for adapter in (self.finnhub, self.edgar_8k, self.yfinance):
            try:
                record = adapter.fetch(ticker_u)
            except Exception as e:
                logger.warning(
                    "Earnings adapter %s raised for %s: %s",
                    type(adapter).__name__, ticker_u, e,
                )
                record = None
            if record is not None and record.is_complete():
                self.cache.put(record)
                return record

        # All adapters failed — return missing stub but DO NOT cache it.
        return EarningsRecord(
            ticker=ticker_u,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="missing",
        )

    def fetch_batch(
        self, tickers: list[str], *, force_refresh: bool = False
    ) -> dict[str, EarningsRecord]:
        return {t.upper().strip(): self.fetch(t, force_refresh=force_refresh) for t in tickers}
