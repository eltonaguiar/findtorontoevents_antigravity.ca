#!/usr/bin/env python3
"""
Opt-in sidecar: fetch SPY 20-day price return and write alpha_engine/data/spy_20d_return.json.

## Wiring Plan
Target caller : alpha_engine/etf_quality_filters.py :: _read_spy_return()
Wire-up       : _read_spy_return() already reads alpha_engine/data/spy_20d_return.json;
                this script keeps that sidecar fresh so check_rs_filter() uses real data
                instead of the stub (spy_20d_return_pct=0.0) that causes fail-open behavior.
Expected PR   : this commit (2026-05-16); no code-path changes required — the caller is
                already wired to the JSON file.

This module is STANDALONE. It does NOT import from alpha_engine/, audit_trail/, or any
production pick/score path. Run independently:
    python tools/fetch_spy_20d_return.py
    python tools/fetch_spy_20d_return.py --dry-run

On success  : writes {"spy_20d_return_pct": <float>, "as_of": "<YYYY-MM-DD>", "source": "yfinance"}
On failure  : writes {"spy_20d_return_pct": 0.0, ..., "source": "rate_limit_fallback"}
              so the RS filter stays fail-open rather than silently broken.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "alpha_engine" / "data" / "spy_20d_return.json"
)
LOOKBACK_DAYS = 20           # trading days for return window
CALENDAR_BUFFER = 35         # calendar days to pull (covers 20 trading days + weekends/holidays)
TICKER = "SPY"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _fetch_via_yfinance() -> float:
    """Primary path: use yfinance to fetch SPY history.

    Returns the 20-trading-day price return in percentage points.
    Raises on any failure (caller catches and tries fallback).
    """
    import yfinance as yf  # type: ignore[import]

    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=CALENDAR_BUFFER)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ticker = yf.Ticker(TICKER)
        hist = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

    if hist is None or len(hist) < 2:
        raise ValueError(
            f"yfinance returned insufficient history "
            f"(rows={len(hist) if hist is not None else 0})"
        )

    # Use up to LOOKBACK_DAYS trading sessions
    close = hist["Close"]
    if len(close) > LOOKBACK_DAYS:
        close = close.iloc[-LOOKBACK_DAYS - 1:]   # oldest...newest: N+1 points -> N returns
    elif len(close) < 2:
        raise ValueError("Not enough rows after slice")

    ret_pct = (float(close.iloc[-1]) / float(close.iloc[0]) - 1.0) * 100.0
    return round(ret_pct, 4)


def _fetch_via_yahoo_direct() -> float:
    """Fallback path: hit Yahoo Finance v8 chart API directly without yfinance.

    Uses a 35-calendar-day window, then computes 20-trading-day return from
    the returned adjclose series.
    Raises on any failure.
    """
    import urllib.error
    import urllib.request

    end_ts = int(datetime.now(tz=timezone.utc).timestamp())
    start_ts = int(
        (datetime.now(tz=timezone.utc) - timedelta(days=CALENDAR_BUFFER)).timestamp()
    )

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}"
        f"?period1={start_ts}&period2={end_ts}&interval=1d"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; fetch_spy_20d_return/1.0; "
            "+https://findtorontoevents.ca)"
        ),
        "Accept": "application/json",
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Yahoo Finance HTTP {exc.code}: {exc.reason}") from exc

    result = raw.get("chart", {}).get("result")
    if not result:
        error_msg = raw.get("chart", {}).get("error", {})
        raise RuntimeError(f"Yahoo Finance API error: {error_msg}")

    adjclose_list = (
        result[0]
        .get("indicators", {})
        .get("adjclose", [{}])[0]
        .get("adjclose", [])
    )
    # Filter None values
    closes = [c for c in adjclose_list if c is not None]
    if len(closes) < 2:
        raise RuntimeError(
            f"Yahoo Finance returned too few adjclose points: {len(closes)}"
        )

    # Use up to LOOKBACK_DAYS points
    if len(closes) > LOOKBACK_DAYS + 1:
        closes = closes[-(LOOKBACK_DAYS + 1):]

    ret_pct = (closes[-1] / closes[0] - 1.0) * 100.0
    return round(ret_pct, 4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def fetch_spy_return() -> dict:
    """Try yfinance first, then Yahoo direct. Returns a result dict."""
    today = _today_utc()

    # --- Primary: yfinance ---
    try:
        ret = _fetch_via_yfinance()
        print(f"[fetch_spy_20d_return] yfinance OK: SPY 20d return = {ret:+.4f}%")
        return {"spy_20d_return_pct": ret, "as_of": today, "source": "yfinance"}
    except Exception as exc:
        print(f"[fetch_spy_20d_return] yfinance failed: {exc}", file=sys.stderr)

    # --- Fallback: Yahoo Finance direct URL ---
    try:
        ret = _fetch_via_yahoo_direct()
        print(f"[fetch_spy_20d_return] yahoo_direct OK: SPY 20d return = {ret:+.4f}%")
        return {"spy_20d_return_pct": ret, "as_of": today, "source": "yahoo_direct"}
    except Exception as exc:
        err_str = str(exc)
        print(f"[fetch_spy_20d_return] yahoo_direct failed: {exc}", file=sys.stderr)
        # Detect rate limit vs other errors for source tag
        source = (
            "rate_limit_fallback"
            if ("429" in err_str or "Too Many" in err_str)
            else "fetch_error_fallback"
        )
        print(
            f"[fetch_spy_20d_return] All fetch paths failed — writing stub "
            f"(fail-open). source={source}",
            file=sys.stderr,
        )
        return {
            "spy_20d_return_pct": 0.0,
            "as_of": today,
            "source": source,
            "error": err_str[:200],
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch SPY 20-day price return and write to "
            "alpha_engine/data/spy_20d_return.json"
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print result but do not write the JSON file",
    )
    args = parser.parse_args()

    result = fetch_spy_return()
    pretty = json.dumps(result, indent=2)

    if args.dry_run:
        print("[fetch_spy_20d_return] --dry-run: would write:")
        print(pretty)
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(pretty + "\n", encoding="utf-8")
    print(f"[fetch_spy_20d_return] Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
