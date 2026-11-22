#!/usr/bin/env python3
"""Fetch months-to-years of funding-rate history so H-228 has a real sample.

The OKX archive in data/funding_rate_archive/ holds ~9 months, which cannot
score a carry cell (8 monthly buckets). ccxt is already a dependency and
exposes funding history perpetual-by-perpetual, so this pulls it once into
data/funding_rate_archive_ccxt/ where the harness picks it up.

Usage:
  python3 tools/fetch_funding_history.py                 # since 2021-01-01
  python3 tools/fetch_funding_history.py --since 2022-06-01 --out data/funding_rate_archive_ccxt
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

# ccxt perpetual-swap notation: settle in USDT
PERPS = {
    "BTCUSDT": "BTC/USDT:USDT",
    "ETHUSDT": "ETH/USDT:USDT",
    "BNBUSDT": "BNB/USDT:USDT",
    "SOLUSDT": "SOL/USDT:USDT",
    "XRPUSDT": "XRP/USDT:USDT",
}


def to_ms(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch_one(ex, ccxt_sym: str, since: int) -> list[dict]:
    out: list[dict] = []
    cursor = since
    while True:
        try:
            batch = ex.fetch_funding_rate_history(ccxt_sym, since=cursor, limit=1000)
        except Exception as exc:                      # network / symbol problems
            print(f"    ! {ccxt_sym} page failed: {exc}")
            break
        if not batch:
            break
        out.extend(batch)
        last = int(batch[-1]["timestamp"])
        if last <= cursor or len(batch) < 1000:
            break
        cursor = last + 1
        time.sleep(ex.rateLimit / 1000.0 or 0.3)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2021-01-01")
    ap.add_argument("--out", default="data/funding_rate_archive_ccxt")
    ap.add_argument("--exchange", default="binance")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ex = getattr(ccxt, a.exchange)({"enableRateLimit": True})
    since = to_ms(a.since)
    total = 0
    for base, ccxt_sym in PERPS.items():
        if not ex.has.get("fetchFundingRateHistory"):
            print(f"{a.exchange} has no funding history endpoint")
            return 1
        rows = fetch_one(ex, ccxt_sym, since)
        if not rows:
            print(f"  {base}: 0 rows (symbol unsupported on {a.exchange})")
            continue
        path = out / f"{base}.jsonl"
        with path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps({"symbol": base,
                                     "funding_time_ms": int(r["timestamp"]),
                                     "funding_rate": float(r["fundingRate"]),
                                     "source": a.exchange}) + "\n")
        first = datetime.fromtimestamp(int(rows[0]["timestamp"]) / 1000, timezone.utc).date()
        last = datetime.fromtimestamp(int(rows[-1]["timestamp"]) / 1000, timezone.utc).date()
        print(f"  {base}: {len(rows)} rows {first} → {last}")
        total += len(rows)
    print(f"total {total} rows in {out}")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
