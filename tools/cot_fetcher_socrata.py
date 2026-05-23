#!/usr/bin/env python3
"""CFTC COT (Commitments of Traders) fetcher — free Socrata feed.

Per NS-B swarm verdict: DEFER paid Glassnode + paid CFTC tier. Start with
the free public Socrata feed. CFTC publishes Legacy COT reports as JSON
at https://publicreporting.cftc.gov/resource/6dca-aqww.json (Tuesday-of
report week; data is for prior Tuesday).

Use case:
  - Edge #1: multi_asset_cot strategy reads net-positioning to fade
    extreme commercial-vs-noncommercial divergences
  - Edge #9 prereq: Hyperliquid HLP carry replication needs CFTC perp
    positioning equivalents

Endpoint columns (Legacy report):
  market_and_exchange_names, report_date_as_yyyy_mm_dd, contract_market_code,
  open_interest_all, noncomm_positions_long_all, noncomm_positions_short_all,
  comm_positions_long_all, comm_positions_short_all,
  nonrept_positions_long_all, nonrept_positions_short_all,
  pct_of_oi_noncomm_long_all, pct_of_oi_comm_long_all, ...

Free tier: 1000 requests/hour without API token; 50000/hour with free token.
Token request: https://data.cftc.gov/profile/edit/developer_settings

Usage:
  python tools/cot_fetcher_socrata.py --symbol CT      # Cotton #2
  python tools/cot_fetcher_socrata.py --symbol GC      # Gold
  python tools/cot_fetcher_socrata.py --symbol CL      # WTI Crude
  python tools/cot_fetcher_socrata.py --weeks 12       # last 12 weekly reports

NFA — historical positioning data; no real-money sizing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOCRATA_BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

# Symbol → CFTC market identifier (Legacy COT field
# market_and_exchange_names usually contains the exchange-prefixed name)
SYMBOL_MAP = {
    "CT": "COTTON NO. 2",
    "GC": "GOLD",
    "SI": "SILVER",
    "CL": "WTI-PHYSICAL",
    "NG": "NAT GAS NYME",
    "ZW": "WHEAT-SRW",
    "ZC": "CORN",
    "ZS": "SOYBEANS",
    "HG": "COPPER",
    "PL": "PLATINUM",
    "PA": "PALLADIUM",
}


def fetch_cot(symbol: str, weeks: int = 12, app_token: str | None = None) -> list[dict]:
    """Pull last `weeks` weekly COT reports for `symbol`.

    Returns list of dicts (one per report week) with normalized keys.
    """
    market_name = SYMBOL_MAP.get(symbol.upper())
    if not market_name:
        raise ValueError(
            f"Unknown symbol {symbol!r}. Known: {sorted(SYMBOL_MAP.keys())}"
        )

    # SoQL where: `like '%CT%'` — `%` is SQL wildcard, not URL escape.
    # Need to URL-encode the spaces in market_name + the single quotes.
    inner = market_name.replace(" ", "%20").replace("'", "%27")
    where_clause = f"market_and_exchange_names%20like%20%27%25{inner}%25%27"
    order_clause = "report_date_as_yyyy_mm_dd%20DESC"
    qs = f"$where={where_clause}&$order={order_clause}&$limit={max(weeks, 1)}"
    url = f"{SOCRATA_BASE}?{qs}"

    req = urllib.request.Request(url)
    if app_token:
        req.add_header("X-App-Token", app_token)
    req.add_header("User-Agent", "ftev-audit/1.0")

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    out: list[dict] = []
    for r in data:
        try:
            nc_long = int(r.get("noncomm_positions_long_all") or 0)
            nc_short = int(r.get("noncomm_positions_short_all") or 0)
            c_long = int(r.get("comm_positions_long_all") or 0)
            c_short = int(r.get("comm_positions_short_all") or 0)
            oi = int(r.get("open_interest_all") or 0)
            net_noncomm = nc_long - nc_short
            net_comm = c_long - c_short
            out.append({
                "symbol": symbol.upper(),
                "market_name": r.get("market_and_exchange_names"),
                "report_date": r.get("report_date_as_yyyy_mm_dd"),
                "open_interest": oi,
                "noncomm_long": nc_long,
                "noncomm_short": nc_short,
                "noncomm_net": net_noncomm,
                "comm_long": c_long,
                "comm_short": c_short,
                "comm_net": net_comm,
                "noncomm_net_pct_of_oi": round(net_noncomm / oi * 100, 2) if oi else 0,
                "comm_net_pct_of_oi": round(net_comm / oi * 100, 2) if oi else 0,
            })
        except (TypeError, ValueError):
            continue
    return out


def compute_zscore(series: list[float], lookback: int = 52) -> float | None:
    """Z-score of latest value vs rolling window."""
    if len(series) < 2:
        return None
    n = min(lookback, len(series))
    sample = series[:n]
    mean = sum(sample) / n
    var = sum((x - mean) ** 2 for x in sample) / n
    if var == 0:
        return None
    sd = var ** 0.5
    latest = series[0]
    return round((latest - mean) / sd, 3)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", required=True, choices=sorted(SYMBOL_MAP.keys()))
    p.add_argument("--weeks", type=int, default=12,
                   help="Number of weekly reports to pull (default 12)")
    p.add_argument("--out", default=None,
                   help="Output JSON path; default = audit_dashboard/data/cot_<sym>.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    token = os.environ.get("CFTC_API_TOKEN") or os.environ.get("CFTC_API_KEY")
    if not token:
        print("# (no CFTC_API_TOKEN/CFTC_API_KEY set; using anonymous tier — 1k/hr cap)",
              file=sys.stderr)

    try:
        rows = fetch_cot(args.symbol, weeks=args.weeks, app_token=token)
    except Exception as exc:
        print(f"ERROR: COT fetch failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print(f"WARN: no COT rows returned for {args.symbol}", file=sys.stderr)
        sys.exit(2)

    # Add z-scores on net positioning series (most-recent-first)
    nc_series = [r["noncomm_net_pct_of_oi"] for r in rows]
    c_series = [r["comm_net_pct_of_oi"] for r in rows]
    z_noncomm = compute_zscore(nc_series, lookback=len(nc_series))
    z_comm = compute_zscore(c_series, lookback=len(c_series))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": args.symbol,
        "market_name": rows[0].get("market_name") if rows else None,
        "weeks_fetched": len(rows),
        "latest_report_date": rows[0].get("report_date") if rows else None,
        "noncomm_net_zscore": z_noncomm,
        "comm_net_zscore": z_comm,
        "signal": _interpret_signal(z_noncomm, z_comm),
        "reports": rows,
        "source": "CFTC Socrata 6dca-aqww (Legacy COT)",
        "nfa": "Public-data positioning snapshot. No sizing decisions.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2, default=str))
        return

    out_path = Path(args.out) if args.out else (
        ROOT / "audit_dashboard" / "data" / f"cot_{args.symbol.lower()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes)",
          file=sys.stderr)
    print(f"# {args.symbol} latest: noncomm_net_z={z_noncomm} comm_net_z={z_comm} "
          f"signal={payload['signal']}", file=sys.stderr)


def _interpret_signal(z_noncomm: float | None, z_comm: float | None) -> str:
    if z_noncomm is None or z_comm is None:
        return "INSUFFICIENT_DATA"
    # Standard COT contrarian read: extreme commercial net long while
    # speculators (noncomm) extreme short = bullish setup (smart money long)
    if z_comm > 1.5 and z_noncomm < -1.5:
        return "STRONG_BULL_COT"
    if z_comm > 1.0 and z_noncomm < -1.0:
        return "BULL_COT"
    if z_comm < -1.5 and z_noncomm > 1.5:
        return "STRONG_BEAR_COT"
    if z_comm < -1.0 and z_noncomm > 1.0:
        return "BEAR_COT"
    return "NEUTRAL"


if __name__ == "__main__":
    main()
