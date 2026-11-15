#!/usr/bin/env python3
"""
build_benchmark_prices.py — write audit_dashboard/data/benchmark_prices.json.

The dashboard's per-pick "Excess" column needs the benchmark close on the pick's
entry day and exit day. That is ~1,150 numbers (SPY 469 + BTC-USD 683 daily
closes), so it ships as a small sidecar the page fetches once, instead of adding
a field to the 18MB dashboard payload or embedding intraday bars (~500KB).

Source of truth for the prices is the same cache tools/pick_excess.py uses
(data/cache/pick_excess/*.csv) so the dashboard and the measured report cannot
disagree through a different price feed. If the cache is absent it fetches from
the Yahoo chart API and writes the cache.

Output shape (kept deliberately flat so the browser can bisect it):
  {"generated_utc": "...", "benchmarks": {"EQUITY": "SPY", ...},
   "series": {"SPY": {"dates": ["2025-01-02", ...], "closes": [590.1, ...]}, ...}}

Usage:
  python3 tools/build_benchmark_prices.py            # use cache, fetch if missing
  python3 tools/build_benchmark_prices.py --refresh  # ignore cache, re-fetch
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(REPO, "data", "cache", "pick_excess")
OUT = os.path.join(REPO, "audit_dashboard", "data", "benchmark_prices.json")
BENCH = {"EQUITY": "SPY", "ETF": "SPY", "CRYPTO": "BTC-USD"}
START_YEAR, END_YEAR = 2025, 2026
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research"}


def cache_path(sym):
    return os.path.join(CACHE, f"{sym.replace('/', '-').replace('^', '')}_{START_YEAR}_{END_YEAR}.csv")


def read_cache(sym):
    cp = cache_path(sym)
    if not os.path.exists(cp):
        return None
    rows = [l.strip().split(",") for l in open(cp) if l.strip()]
    if len(rows) < 30:
        return None
    return ([r[0] for r in rows], [float(r[1]) for r in rows])


def fetch(sym):
    """Adjusted daily closes. Explicit period1/period2: the range=max form returns
    monthly bars, which would silently make every benchmark window wrong."""
    import time
    import requests
    os.makedirs(CACHE, exist_ok=True)
    p1 = int(datetime(START_YEAR, 1, 1).timestamp())
    p2 = int(datetime(END_YEAR, 11, 20).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, params={"period1": p1, "period2": p2, "interval": "1d",
                                          "events": "div,splits"}, headers=H, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            res = r.json()["chart"]["result"][0]
            ts, ind = res["timestamp"], res["indicators"]
            px = None
            if ind.get("adjclose"):
                px = ind["adjclose"][0].get("adjclose")
            if not px or len(px) != len(ts):
                px = ind["quote"][0]["close"]
            rows = [(datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"), float(p))
                    for t, p in zip(ts, px) if p is not None and p == p and p > 0]
            if len(rows) < 30:
                raise RuntimeError(f"only {len(rows)} rows")
            with open(cache_path(sym), "w") as f:
                f.write("\n".join(f"{d},{p}" for d, p in rows))
            return [r[0] for r in rows], [r[1] for r in rows]
        except Exception as e:                                  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch {sym} failed: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and re-fetch")
    a = ap.parse_args()

    series = {}
    for sym in sorted(set(BENCH.values())):
        got = None if a.refresh else read_cache(sym)
        src = "cache"
        if got is None:
            got = fetch(sym)
            src = "yahoo"
        dates, closes = got
        # Keep the file bisectable: the JS lookup assumes ascending unique dates.
        pairs = sorted(set(zip(dates, closes)))
        series[sym] = {"dates": [d for d, _ in pairs], "closes": [round(c, 6) for _, c in pairs]}
        print(f"  {sym:8} {len(pairs):5} bars  {pairs[0][0]}..{pairs[-1][0]}  ({src})")

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "benchmarks": BENCH,
        "note": "Daily adjusted closes for the dashboard's per-pick excess column. "
                "Read by audit_dashboard/excess_column.js. Sub-day (same trading day) windows "
                "are not scored from this file; tools/pick_excess.py scores those from 60m bars.",
        "series": series,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    kb = os.path.getsize(a.out) / 1024.0
    print(f"wrote {a.out}  ({kb:.1f} KB, {sum(len(v['dates']) for v in series.values())} bars)")
    return payload


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
