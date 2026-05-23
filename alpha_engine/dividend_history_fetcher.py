"""Dividend history fetcher with yfinance primary + EDGAR 8-K stub.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 6 value_screener.py + Phase 11 dashboard.

Design (per findings/SYNTHESIS.md §1):
  Primary:   yfinance (.dividends Series) — lazy import
  Fallback:  SEC EDGAR 8-K parsing (Phase 14+ stub for now)
  Cache:     JSON at data/dividends/{ticker}/latest.json, TTL 168h (weekly)

Returns standardized `DividendRecord` records whose `history_5y` field conforms
exactly to the `DividendEvent` TypedDict in `alpha_engine.long_term_pick_contract`.

Pure helpers:
  - compute_consecutive_growth_years(history)        — aristocrat detection
  - compute_annual_yield(history, current_price)     — last-12-months sum / price
  - compute_payout_ratio(annual_div_per_share, eps)  — None when EPS <= 0
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable, Literal

from alpha_engine.long_term_pick_contract import DividendEvent

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path("data/dividends")
DEFAULT_TTL_HOURS = 168  # one week
DividendSource = Literal["yfinance", "edgar_8k", "missing"]


@dataclass
class DividendRecord:
    """Standardized dividend snapshot for one ticker.

    Mirrors the `DividendRecord` TypedDict in `long_term_pick_contract` plus
    housekeeping fields (ticker, fetched_at, source, cache_hit).
    """
    ticker: str
    annual_yield: float | None = None
    payout_ratio: float | None = None
    consecutive_growth_years: int = 0
    next_ex_div_date: str | None = None
    history_5y: list[DividendEvent] = field(default_factory=list)
    fetched_at: str = ""
    source: DividendSource = "missing"
    cache_hit: bool = False

    def is_complete(self) -> bool:
        """Complete = at least one historical dividend event OR a known next ex-div date.

        Non-payers will end up as `missing` unless we explicitly mark them.
        """
        return bool(self.history_5y) or self.next_ex_div_date is not None


# --------------------------------------------------------------------------- #
# Pure helpers (testable without any I/O)                                     #
# --------------------------------------------------------------------------- #

def compute_consecutive_growth_years(history: list[DividendEvent]) -> int:
    """Return the number of consecutive years of dividend growth, ending at the most
    recent complete fiscal year.

    Aristocrat thresholds (per CLAUDE.md MAJOR GOAL #1 / SYNTHESIS):
      5y  → "growth" track record
      10y → "Achiever"
      25y → "Aristocrat"

    Returns 0 for non-payers, single-year payers, or any year with a dividend cut /
    skip after the first payment year.
    """
    if not history:
        return 0
    by_year: dict[int, float] = defaultdict(float)
    for event in history:
        ex_date = event.get("ex_date", "")
        if not ex_date or len(ex_date) < 4:
            continue
        try:
            year = int(ex_date[:4])
        except ValueError:
            continue
        amount = event.get("amount", 0.0) or 0.0
        if amount <= 0:
            continue
        by_year[year] += float(amount)

    if not by_year:
        return 0

    years_sorted = sorted(by_year.keys())
    current_year = datetime.now(timezone.utc).year
    # Walk backward from the most recent COMPLETE year (not the current YTD).
    last_complete = current_year - 1 if current_year in by_year else years_sorted[-1]
    if last_complete not in by_year:
        return 0

    streak = 1
    prev_year = last_complete
    prev_amt = by_year[last_complete]
    while True:
        next_year = prev_year - 1
        if next_year not in by_year:
            break
        cur_amt = by_year[next_year]
        # Strict growth — require last_complete-year amount > prior-year amount, walking back.
        if prev_amt > cur_amt:
            streak += 1
            prev_year = next_year
            prev_amt = cur_amt
        else:
            break
    return streak


def compute_annual_yield(
    history: list[DividendEvent],
    current_price: float,
) -> float | None:
    """Sum dividends from the trailing 12 months, divided by current_price."""
    if current_price is None or current_price <= 0:
        return None
    if not history:
        return 0.0
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    total = 0.0
    for event in history:
        ex_date = event.get("ex_date", "")
        amount = event.get("amount", 0.0) or 0.0
        if not ex_date or amount <= 0:
            continue
        try:
            ev_dt = datetime.fromisoformat(ex_date[:10] + "T00:00:00+00:00")
        except ValueError:
            continue
        if ev_dt >= cutoff:
            total += float(amount)
    return total / current_price


def compute_payout_ratio(
    annual_div_per_share: float | None,
    eps: float | None,
) -> float | None:
    """Annual dividend per share / EPS. Returns None when EPS is non-positive
    (mathematical payout ratio breaks down for losses)."""
    if annual_div_per_share is None or eps is None:
        return None
    if eps <= 0:
        return None
    return annual_div_per_share / eps


# --------------------------------------------------------------------------- #
# Adapters                                                                    #
# --------------------------------------------------------------------------- #

class YfinanceDividendsAdapter:
    """Primary adapter — yfinance .dividends Series. Lazy yfinance import."""

    def fetch(self, ticker: str) -> DividendRecord | None:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed — dividend fetcher unavailable")
            return None
        ticker_u = ticker.upper().strip()
        try:
            t = yf.Ticker(ticker_u)
            divs = t.dividends
        except Exception as e:
            logger.warning("yfinance dividends fetch failed for %s: %s", ticker_u, e)
            return None

        events: list[DividendEvent] = []
        try:
            if divs is not None and hasattr(divs, "items"):
                cutoff = datetime.now(timezone.utc) - timedelta(days=5 * 365)
                for idx, amount in divs.items():
                    try:
                        ev_dt = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
                        if ev_dt.tzinfo is None:
                            ev_dt = ev_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        continue
                    if ev_dt < cutoff:
                        continue
                    if amount is None or float(amount) <= 0:
                        continue
                    events.append({
                        "ex_date": ev_dt.date().isoformat(),
                        "amount": float(amount),
                    })
        except Exception as e:
            logger.debug("yfinance dividend extraction failed for %s: %s", ticker_u, e)

        # Try info for current price + EPS to compute yield/payout.
        current_price: float | None = None
        eps: float | None = None
        try:
            info = t.info or {}
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            eps = info.get("trailingEps")
        except Exception:
            pass

        if not events and not current_price:
            return None

        annual_yield = compute_annual_yield(events, current_price) if current_price else None
        # Annualize last 4 quarterly payments for payout ratio.
        events_sorted = sorted(events, key=lambda e: e["ex_date"], reverse=True)
        annual_div = sum(e["amount"] for e in events_sorted[:4]) if events_sorted else None
        payout = compute_payout_ratio(annual_div, eps) if annual_div is not None else None
        streak = compute_consecutive_growth_years(events)

        return DividendRecord(
            ticker=ticker_u,
            annual_yield=annual_yield,
            payout_ratio=payout,
            consecutive_growth_years=streak,
            next_ex_div_date=None,  # yfinance .dividends gives history only.
            history_5y=events_sorted,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="yfinance",
        )


class Edgar8KDividendsAdapter:
    """Stub adapter — SEC 8-K parsing for dividend declarations is Phase 14+.

    Returns None unconditionally. Wired in for failover-chain symmetry only.
    """

    def __init__(self) -> None:
        self._http_get: Callable[[str, str], str] | None = None

    def fetch(self, ticker: str) -> DividendRecord | None:  # noqa: ARG002
        logger.debug("Edgar8KDividendsAdapter: stub, returning None for %s", ticker)
        return None


# --------------------------------------------------------------------------- #
# Cache                                                                       #
# --------------------------------------------------------------------------- #

class DividendCache:
    """On-disk JSON cache with TTL."""

    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_hours * 3600

    def _path_for(self, ticker: str) -> Path:
        return self.cache_dir / ticker.upper() / "latest.json"

    def get(self, ticker: str) -> DividendRecord | None:
        path = self._path_for(ticker)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Dividend cache read failed for %s: %s", ticker, e)
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
        record = DividendRecord(**data)
        record.cache_hit = True
        return record

    def put(self, record: DividendRecord) -> None:
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
            logger.warning("Dividend cache write failed for %s: %s", record.ticker, e)


# --------------------------------------------------------------------------- #
# Facade                                                                      #
# --------------------------------------------------------------------------- #

class DividendHistoryFetcher:
    """Public facade. Failover: cache -> yfinance -> EDGAR 8-K -> missing stub."""

    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ):
        self.cache = DividendCache(cache_dir, ttl_hours)
        self.yfinance = YfinanceDividendsAdapter()
        self.edgar_8k = Edgar8KDividendsAdapter()

    def fetch(self, ticker: str, *, force_refresh: bool = False) -> DividendRecord:
        ticker_u = ticker.upper().strip()
        if not force_refresh:
            cached = self.cache.get(ticker_u)
            if cached is not None:
                return cached

        for adapter in (self.yfinance, self.edgar_8k):
            try:
                record = adapter.fetch(ticker_u)
            except Exception as e:
                logger.warning(
                    "Dividend adapter %s raised for %s: %s",
                    type(adapter).__name__, ticker_u, e,
                )
                record = None
            if record is not None and record.is_complete():
                self.cache.put(record)
                return record

        return DividendRecord(
            ticker=ticker_u,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="missing",
        )

    def fetch_batch(
        self,
        tickers: list[str],
        *,
        force_refresh: bool = False,
    ) -> dict[str, DividendRecord]:
        return {t.upper().strip(): self.fetch(t, force_refresh=force_refresh) for t in tickers}
