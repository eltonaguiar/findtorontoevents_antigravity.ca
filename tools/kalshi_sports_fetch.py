#!/usr/bin/env python3
"""
Kalshi sports-markets adapter (opt-in sidecar).

Pulls open prediction-market contracts for sports series from the public
Kalshi API and snapshots them to data/kalshi_snapshots/<UTC>.json. The goal
is to fill the per-event h2h coverage gap left by Polymarket: the existing
Polymarket verifier flags most curated UFC/Tennis/Golf picks as
`no_polymarket_match` because Polymarket sports breadth is narrow.

Read-only. Stdlib + standard urllib only. No third-party deps.

USAGE
    python tools/kalshi_sports_fetch.py --sport all
    python tools/kalshi_sports_fetch.py --sport ufc --stdout
    python tools/kalshi_sports_fetch.py --sport tennis --out data/kalshi_snapshots/test.json

API SURFACE NOTES (probed 2026-04-26)
- The original `https://trading-api.kalshi.com/trade-api/v2/...` host returns
  401 on every endpoint we tried (markets, series, exchange/status) without
  a signed Authorization header.
- The `https://api.elections.kalshi.com/trade-api/v2/...` host (the same
  service Kalshi exposes for the elections platform but unified across all
  exchange data) DOES allow unauthenticated reads of:
    * GET /markets?series_ticker=<TICKER>&status=open
    * GET /series?category=Sports
  and returns the full market object including yes_bid/yes_ask/no_bid/
  no_ask/volume/close_time. This is what we use.
- If Kalshi later closes the elections host as well, the operator must
  capture an API key (KALSHI_API_KEY_ID + KALSHI_API_PRIVATE_KEY_PEM) and
  this script will need RSA-PSS signed-headers added (see Kalshi docs).
  Until then, no auth required.

SPORT -> SERIES MAPPING (probed 2026-04-26)
Sports series are NOT one-per-sport — each league/event/market-type has its
own series ticker. The KXUFC h2h series in particular returned zero open
markets at probe time (no upcoming UFC card with open contracts), but the
endpoint shape is correct. The mappings below are the curated subset useful
for h2h / single-event picks; the broader catalog (futures, MVP, season
totals) is omitted because the verifier targets per-event picks.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNAP_DIR = REPO / "data" / "kalshi_snapshots"

# Public host that allows unauthenticated reads (probed 2026-04-26).
# trading-api.kalshi.com requires signed-request auth on every endpoint.
KALSHI_HOST = "https://api.elections.kalshi.com/trade-api/v2"
UA = "FindTorontoEvents-Kalshi-Adapter/1.0 (sidecar)"

# Per-sport series tickers. Keys are normalized sport names; values are
# the Kalshi series tickers we'll page through. Empty result is fine —
# the verifier handles "no Kalshi market for this pick" gracefully.
SPORT_SERIES: dict[str, list[str]] = {
    "ufc":    ["KXUFC", "KXUFCFIGHTNIGHT", "KXMMA"],
    "nba":    ["KXNBA", "KXNBAGAME", "KXNBASERIES"],
    "tennis": ["KXATPMATCH", "KXWTAMATCH", "KXAOMENSINGLES",
               "KXWMENSINGLES", "KXUSOPENMENS"],
    "golf":   ["KXPGA", "KXPGAGAME", "KXGOLFMAJOR", "KXTGLCHAMPION"],
    "nfl":    ["KXNFLGAME", "KXNFL"],
    "nhl":    ["KXNHLGAME", "KXNHL"],
    "mlb":    ["KXMLBGAME", "KXMLB"],
    "soccer": ["KXUELGAME", "KXLALIGA2GAME", "KXMLSEAST"],
}


def http_get_json(url: str, timeout: float = 30.0) -> dict | None:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 401 means the public host has been locked down — degrade gracefully.
        print(f"[kalshi] HTTP {e.code} on {url}", file=sys.stderr)
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[kalshi] {type(e).__name__} on {url}: {e}", file=sys.stderr)
        return None


def list_sports_series() -> list[dict]:
    """Probe /series?category=Sports. Useful for catalog discovery."""
    url = f"{KALSHI_HOST}/series?category=Sports&limit=200"
    data = http_get_json(url)
    if not data:
        return []
    return data.get("series", []) if isinstance(data, dict) else []


def fetch_series_markets(series_ticker: str, status: str = "open",
                          limit: int = 200) -> list[dict]:
    """Page through open markets in a series."""
    out: list[dict] = []
    cursor = ""
    pages = 0
    while True:
        params = {
            "series_ticker": series_ticker,
            "status": status,
            "limit": str(limit),
        }
        if cursor:
            params["cursor"] = cursor
        url = f"{KALSHI_HOST}/markets?{urllib.parse.urlencode(params)}"
        data = http_get_json(url)
        if not data:
            break
        markets = data.get("markets", []) if isinstance(data, dict) else []
        out.extend(markets)
        cursor = data.get("cursor") or "" if isinstance(data, dict) else ""
        pages += 1
        if not cursor or pages >= 10:
            break
        time.sleep(0.3)  # courtesy
    return out


def cents_to_dollar(v) -> float | None:
    """Kalshi prices are in cents (0..100). Convert to fractional dollars."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f > 1.5:  # cents
        return round(f / 100.0, 4)
    return round(f, 4)


def normalize_market(m: dict, sport: str) -> dict:
    return {
        "ticker": m.get("ticker"),
        "event_ticker": m.get("event_ticker"),
        "series_ticker": m.get("series_ticker"),
        "title": m.get("title") or m.get("subtitle") or m.get("yes_sub_title"),
        "sport": sport,
        "status": m.get("status"),
        "yes_bid": cents_to_dollar(m.get("yes_bid")),
        "yes_ask": cents_to_dollar(m.get("yes_ask")),
        "no_bid":  cents_to_dollar(m.get("no_bid")),
        "no_ask":  cents_to_dollar(m.get("no_ask")),
        "last_price": cents_to_dollar(m.get("last_price")),
        "volume": m.get("volume"),
        "volume_24h": m.get("volume_24h"),
        "open_interest": m.get("open_interest"),
        "volume_usd": m.get("dollar_volume"),
        "close_ts": m.get("close_time") or m.get("expiration_time"),
        "expected_expiration_time": m.get("expected_expiration_time"),
    }


def collect(sport_filter: str) -> dict:
    sports = (list(SPORT_SERIES.keys())
              if sport_filter == "all"
              else [sport_filter])
    rows: list[dict] = []
    series_probed: list[dict] = []
    for sport in sports:
        for series in SPORT_SERIES.get(sport, []):
            markets = fetch_series_markets(series)
            series_probed.append({
                "sport": sport,
                "series_ticker": series,
                "n_markets": len(markets),
            })
            for m in markets:
                rows.append(normalize_market(m, sport))
            time.sleep(0.2)
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": KALSHI_HOST,
        "sport_filter": sport_filter,
        "series_probed": series_probed,
        "n_markets": len(rows),
        "markets": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="all",
                    choices=list(SPORT_SERIES.keys()) + ["all"])
    ap.add_argument("--out", default=None,
                    help="Output path. Default: data/kalshi_snapshots/<UTC>.json")
    ap.add_argument("--stdout", action="store_true",
                    help="Print snapshot to stdout instead of writing.")
    ap.add_argument("--list-series", action="store_true",
                    help="List Kalshi sports series catalog and exit.")
    args = ap.parse_args()

    if args.list_series:
        series = list_sports_series()
        text = json.dumps({"n_series": len(series), "series": series}, indent=2)
        sys.stdout.write(text + "\n")
        return 0

    payload = collect(args.sport)
    text = json.dumps(payload, indent=2)
    if args.stdout:
        sys.stdout.write(text + "\n")
        return 0

    if args.out:
        out_path = Path(args.out)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = SNAP_DIR / f"{stamp}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote {out_path}  markets={payload['n_markets']}  "
          f"sport={args.sport}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
