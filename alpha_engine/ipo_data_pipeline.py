"""
IPO Data Pipeline — Fetch IPO calendar, lock-up dates, and institutional data.

STATUS — OPT-IN RESEARCH SIDECAR (added 2026-05-17)
  This module is NOT wired into production pick generation. It is greenfield
  IPO / lock-up-expiry research, sourced from a Xiaomi-MiMo feasibility study
  and reviewed: the IPO lock-up-expiry SHORT anomaly (Field & Hanka 2001) is
  the one penny/IPO approach judged defensible — true penny stocks (<$1) were
  rejected (spreads eat all alpha).

  ## Wiring Plan
  Wire-up target: a new `source_system='ipo_pipeline'` admitted by
  `audit_trail/quality_gates.passes_active_gate`. It is admitted ONLY after
  `ipo_lockup_strategy.py --backtest` clears the §23 universal 5-gate
  (DSR>=0.95, PBO<0.05, walk-forward decay>=0, n>=100 clean, 30-day rolling).
  Until that gate passes this module emits NOTHING live — it is research-only.

  CAVEAT: live API endpoints (Nasdaq, SEC EDGAR, Yahoo) are unverified and may
  403 / rate-limit. WR estimates (58-62%) are from literature, not verified on
  this system. Backtest on >=2yr of data before trusting any number.

Data sources:
  - Nasdaq IPO Calendar (free, no key)
  - SEC EDGAR (free, no key, rate-limited)
  - Yahoo Finance (free, no key)

Usage:
  python3 -m alpha_engine.ipo_data_pipeline          # Full pipeline run
  python3 -m alpha_engine.ipo_data_pipeline --ipo    # Fetch IPO calendar only
  python3 -m alpha_engine.ipo_data_pipeline --lockup # Compute lock-up dates only

Output: alpha_engine/data/ipo_calendar.json
"""

from __future__ import annotations

import json
import os
import re
import time
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

LOG = logging.getLogger(__name__)
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

IPO_CALENDAR_PATH = DATA_DIR / "ipo_calendar.json"
IPO_HISTORY_PATH = DATA_DIR / "ipo_history.json"

# Lock-up defaults by IPO type
LOCKUP_DEFAULTS = {
    "traditional": 180,  # 6 months standard
    "spac": 365,         # 1 year for SPACs
    "direct": 0,         # No lock-up for direct listings
    "etf": 0,            # No lock-up for ETFs
}

USER_AGENT = "Mozilla/5.0 (compatible; AlphaEngine/1.0)"

# Rate limiting
SEC_DELAY = 0.15  # SEC asks for 10 req/sec max


def _get(url: str, headers: dict = None, timeout: int = 30) -> Optional[dict]:
    """HTTP GET with error handling."""
    if requests is None:
        LOG.error("requests library not available")
        return None
    try:
        h = {"User-Agent": USER_AGENT}
        if headers:
            h.update(headers)
        resp = requests.get(url, headers=h, timeout=timeout)
        resp.raise_for_status()
        return resp.json() if 'json' in resp.headers.get('content-type', '') else {"text": resp.text}
    except Exception as e:
        LOG.warning("GET %s failed: %s", url, e)
        return None


def _get_html(url: str, timeout: int = 30) -> Optional[str]:
    """HTTP GET returning text."""
    if requests is None:
        return None
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        LOG.warning("GET %s failed: %s", url, e)
        return None


# =========================================================================
# 1. IPO Calendar — Nasdaq API
# =========================================================================

def fetch_nasdaq_ipo_calendar() -> list[dict]:
    """
    Fetch upcoming and recent IPOs from Nasdaq.

    Returns list of dicts with:
      - symbol, company_name, ipo_date, price_range, exchange, shares
    """
    url = "https://api.nasdaq.com/api/ipo/calendar?date={}".format(
        datetime.now().strftime("%Y-%m")
    )
    data = _get(url)
    if not data:
        LOG.warning("Nasdaq IPO calendar fetch failed")
        return []

    results = []
    # Nasdaq returns data.data.upcoming and data.data.priced
    for section in ("upcoming", "priced", "filed"):
        items = (data.get("data") or {}).get(section, {}).get("rows", [])
        if isinstance(items, list):
            for item in items:
                results.append({
                    "symbol": item.get("proposedTickerSymbol", item.get("symbol", "")),
                    "company_name": item.get("companyName", ""),
                    "ipo_date": item.get("expectedPriceDate", item.get("pricedDate", "")),
                    "price_range": item.get("proposedSharePrice", ""),
                    "exchange": item.get("proposedExchange", ""),
                    "shares": item.get("sharesOffered", ""),
                    "status": section,
                    "source": "nasdaq",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })
    return results


def fetch_sec_recent_ipos(days_back: int = 90) -> list[dict]:
    """
    Fetch recent IPO filings from SEC EDGAR full-text search.
    Looks for S-1 and F-1 filings.
    """
    url = (
        "https://efts.sec.gov/LATEST/search-index?"
        "q=%22S-1%22+%22initial+public+offering%22&"
        "dateRange=custom&startdt={start}&enddt={end}&"
        "forms=S-1,F-1"
    ).format(
        start=(datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d"),
        end=datetime.now().strftime("%Y-%m-%d"),
    )

    data = _get(url)
    if not data:
        return []

    results = []
    for hit in (data.get("hits") or {}).get("hits", []):
        source = hit.get("_source", {})
        results.append({
            "company_name": source.get("display_names", [""])[0],
            "cik": source.get("entity_id", ""),
            "filing_date": source.get("file_date", ""),
            "form_type": source.get("form_type", ""),
            "source": "sec_edgar",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return results


# =========================================================================
# 2. Lock-Up Date Computation
# =========================================================================

def compute_lockup_expiry(ipo_date: str, lockup_days: int = 180) -> Optional[str]:
    """
    Compute lock-up expiry date.

    Args:
        ipo_date: ISO date string (YYYY-MM-DD)
        lockup_days: Days from IPO to lock-up expiry (default 180)

    Returns:
        ISO date string of lock-up expiry, or None if invalid
    """
    try:
        dt = datetime.strptime(ipo_date[:10], "%Y-%m-%d")
        expiry = dt + timedelta(days=lockup_days)
        return expiry.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def parse_lockup_from_filing(filing_text: str) -> int:
    """
    Parse lock-up period from SEC filing text.

    Looks for patterns like:
      - "180 days"
      - "six months"
      - "90-day lock-up"
      - "lock-up period of 180"

    Returns: lock-up days (0 if not found)
    """
    text = filing_text.lower()

    # Pattern: "N days" near "lock-up" or "lockup"
    patterns = [
        r'lock[- ]?up.{0,50}?(\d+)\s*days?',
        r'(\d+)\s*days?.{0,50}?lock[- ]?up',
        r'lock[- ]?up.{0,50}?(\d+)\s*months?',
        r'six\s*months?.{0,30}?lock[- ]?up',
        r'lock[- ]?up.{0,30}?six\s*months',
        r'180[- ]?day',
        r'90[- ]?day',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            if 'six' in pattern:
                return 180
            if '180' in pattern:
                return 180
            if '90' in pattern:
                return 90
            try:
                val = int(match.group(1))
                if 'month' in pattern:
                    return val * 30
                return val
            except (IndexError, ValueError):
                continue

    return 180  # Default assumption


# =========================================================================
# 3. Institutional Holdings (SEC 13F)
# =========================================================================

def fetch_institutional_holdings(cik: str) -> dict:
    """
    Fetch latest 13F institutional holdings for a company.

    Args:
        cik: SEC CIK number (e.g., "0001234567")

    Returns:
        Dict with total_shares, num_institutions, change_vs_prior
    """
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F&dateb=&owner=include&count=10&search_text=&action=getcompany"
    time.sleep(SEC_DELAY)

    html = _get_html(url)
    if not html:
        return {}

    # Parse filing links from HTML
    # This is simplified — production code should use the EDGAR API
    return {"cik": cik, "status": "pending_implementation"}


# =========================================================================
# 4. Price & Volume Data (Yahoo Finance)
# =========================================================================

def fetch_price_data(symbol: str, period: str = "1y") -> Optional[list[dict]]:
    """
    Fetch daily OHLCV data from Yahoo Finance.

    Args:
        symbol: Stock ticker (e.g., "AAPL")
        period: "1y", "6mo", "3mo", "1mo"

    Returns:
        List of {date, open, high, low, close, volume}
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={period}&interval=1d"
    data = _get(url)
    if not data:
        return None

    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        prices = []
        for i, ts in enumerate(timestamps):
            prices.append({
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                "open": quotes["open"][i],
                "high": quotes["high"][i],
                "low": quotes["low"][i],
                "close": quotes["close"][i],
                "volume": quotes["volume"][i],
            })
        return prices
    except (KeyError, IndexError) as e:
        LOG.warning("Yahoo parse error for %s: %s", symbol, e)
        return None


def get_market_cap(symbol: str) -> Optional[float]:
    """Get current market cap from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=price"
    data = _get(url)
    if not data:
        return None
    try:
        return data["quoteSummary"]["result"][0]["price"]["marketCap"]["raw"]
    except (KeyError, IndexError):
        return None


# =========================================================================
# 5. Short Interest Data
# =========================================================================

def get_short_interest(symbol: str) -> Optional[float]:
    """
    Get short interest as % of float.
    Uses Yahoo Finance quoteSummary.
    """
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=defaultKeyStatistics"
    data = _get(url)
    if not data:
        return None
    try:
        stats = data["quoteSummary"]["result"][0]["defaultKeyStatistics"]
        return stats.get("shortPercentOfFloat", {}).get("raw", None)
    except (KeyError, IndexError):
        return None


# =========================================================================
# 6. Full Pipeline
# =========================================================================

def run_pipeline(mode: str = "full"):
    """
    Run the IPO data pipeline.

    Modes:
      - "full": Fetch calendar + compute lock-ups + save
      - "ipo": Fetch IPO calendar only
      - "lockup": Compute lock-up dates from existing calendar
    """
    LOG.info("IPO pipeline starting (mode=%s)", mode)

    # Load existing data
    existing = {}
    if IPO_CALENDAR_PATH.exists():
        with open(IPO_CALENDAR_PATH) as f:
            existing = json.load(f)

    if mode in ("full", "ipo"):
        # Fetch Nasdaq IPO calendar
        LOG.info("Fetching Nasdaq IPO calendar...")
        nasdaq_ipos = fetch_nasdaq_ipo_calendar()
        LOG.info("Got %d IPOs from Nasdaq", len(nasdaq_ipos))

        # Merge with existing
        existing_symbols = {p.get("symbol") for p in existing.get("ipos", [])}
        new_ipos = [p for p in nasdaq_ipos if p.get("symbol") not in existing_symbols]

        if new_ipos:
            LOG.info("Adding %d new IPOs", len(new_ipos))
            existing.setdefault("ipos", []).extend(new_ipos)

    if mode in ("full", "lockup"):
        # Compute lock-up expiry dates
        LOG.info("Computing lock-up expiry dates...")
        for ipo in existing.get("ipos", []):
            if not ipo.get("lockup_expiry") and ipo.get("ipo_date"):
                ipo_type = ipo.get("ipo_type", "traditional")
                lockup_days = LOCKUP_DEFAULTS.get(ipo_type, 180)
                ipo["lockup_expiry"] = compute_lockup_expiry(ipo["ipo_date"], lockup_days)
                ipo["lockup_days"] = lockup_days

    # Save
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(IPO_CALENDAR_PATH, "w") as f:
        json.dump(existing, f, indent=2)

    LOG.info("Saved %d IPOs to %s", len(existing.get("ipos", [])), IPO_CALENDAR_PATH)
    return existing


def load_ipo_calendar() -> list[dict]:
    """Load the IPO calendar (list of IPO dicts) from disk."""
    if not IPO_CALENDAR_PATH.exists():
        return []
    with open(IPO_CALENDAR_PATH) as f:
        return json.load(f).get("ipos", [])


def generate_lockup_signals(ipos: list[dict], current_date: str = None) -> list[dict]:
    """
    Generate lock-up expiry short signals.

    Entry: 5 trading days before lock-up expiry
    Exit: 10 trading days after lock-up expiry

    Args:
        ipos: list of IPO dicts (from load_ipo_calendar() or run_pipeline()['ipos'])
        current_date: YYYY-MM-DD (defaults to today)

    Returns:
        List of signal dicts
    """
    if current_date is None:
        current_date = datetime.now().strftime("%Y-%m-%d")

    # Accept either a list of IPOs or the full pipeline dict
    if isinstance(ipos, dict):
        ipos = ipos.get("ipos", [])

    signals = []
    today = datetime.strptime(current_date, "%Y-%m-%d")

    for ipo in ipos:
        lockup_str = ipo.get("lockup_expiry")
        if not lockup_str:
            continue

        try:
            lockup_date = datetime.strptime(lockup_str, "%Y-%m-%d")
        except ValueError:
            continue

        days_to_lockup = (lockup_date - today).days

        # Entry window: ~5 trading days before lock-up
        if 3 <= days_to_lockup <= 7:
            symbol = ipo.get("symbol", "")
            if not symbol:
                continue

            signals.append({
                "symbol": symbol,
                "direction": "SHORT",
                "strategy": "ipo_lockup_expiry",
                "asset_class": "EQUITY",
                "source_system": "ipo_pipeline",
                "confidence": 0.65,
                "entry_date": current_date,
                "lockup_expiry": lockup_str,
                "days_to_lockup": days_to_lockup,
                "reason": (
                    f"IPO lock-up expires in {days_to_lockup} days. "
                    f"Expected insider selling pressure."
                ),
                "company_name": ipo.get("company_name", ""),
                "ipo_date": ipo.get("ipo_date", ""),
            })

    return signals


# =========================================================================
# CLI
# =========================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    mode = "full"
    if "--ipo" in sys.argv:
        mode = "ipo"
    elif "--lockup" in sys.argv:
        mode = "lockup"
    elif "--signals" in sys.argv:
        mode = "signals"

    if mode == "signals":
        if IPO_CALENDAR_PATH.exists():
            with open(IPO_CALENDAR_PATH) as f:
                data = json.load(f)
            signals = generate_lockup_signals(data)
            print(json.dumps(signals, indent=2))
        else:
            print("No IPO calendar data. Run pipeline first.")
    else:
        result = run_pipeline(mode)
        print(f"\nDone. {len(result.get('ipos', []))} IPOs in calendar.")
