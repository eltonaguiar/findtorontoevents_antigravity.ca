#!/usr/bin/env python3
"""Sample live FX top-of-book (bid/ask) from Tiingo and record spread diagnostics.

Purpose: measure real FOREX round-trip cost instead of assuming it. Samples are
repeated over a window so a thin / reopened book can be distinguished from a
representative one (wide + high sample-to-sample variance = thin).

Endpoint: https://api.tiingo.com/tiingo/fx/top?tickers=<csv>&token=$TIINGO_API_KEY
Each row carries quoteTimestamp (UTC), bidPrice, askPrice, midPrice.

Usage:
    python3 tools/fx_cost_sampler.py --minutes 20 --interval 45 --out reports/cost_measurement_forex/fx_top_of_book_samples.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PAIRS = ["eurusd", "gbpusd", "usdjpy", "audusd", "usdcad", "usdchf", "eurgbp", "eurjpy"]
ENDPOINT = "https://api.tiingo.com/tiingo/fx/top"


def fetch(tickers: list[str], token: str, timeout: int = 20) -> list[dict]:
    url = f"{ENDPOINT}?tickers={','.join(tickers)}&token={token}"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=20.0)
    ap.add_argument("--interval", type=float, default=45.0)
    ap.add_argument("--out", default="reports/cost_measurement_forex/fx_top_of_book_samples.json")
    ap.add_argument("--pairs", default=",".join(PAIRS))
    args = ap.parse_args()

    token = os.environ.get("TIINGO_API_KEY")
    if not token:
        print("TIINGO_API_KEY not set", file=sys.stderr)
        return 2

    pairs = [p.strip().lower() for p in args.pairs.split(",") if p.strip()]
    started = datetime.now(timezone.utc)
    deadline = time.time() + args.minutes * 60
    samples: list[dict] = []
    n = 0

    while time.time() < deadline or n == 0:
        local_ts = datetime.now(timezone.utc).isoformat()
        try:
            rows = fetch(pairs, token)
        except Exception as exc:  # noqa: BLE001 - record and continue
            samples.append({"local_ts": local_ts, "error": repr(exc)})
            n += 1
            time.sleep(args.interval)
            continue
        for row in rows:
            bid, ask = row.get("bidPrice"), row.get("askPrice")
            mid = row.get("midPrice")
            rec = {
                "local_ts": local_ts,
                "quote_ts": row.get("quoteTimestamp"),
                "pair": row.get("ticker"),
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "bid_size": row.get("bidSize"),
                "ask_size": row.get("askSize"),
            }
            if bid and ask and mid and ask > bid > 0:
                rec["spread"] = ask - bid
                rec["full_spread_bp"] = (ask - bid) / mid * 1e4
                rec["half_spread_bp"] = (ask - bid) / 2.0 / mid * 1e4
                rec["plausible"] = True
            else:
                rec["plausible"] = False
            samples.append(rec)
        n += 1
        print(f"[{n}] {local_ts} rows={len(rows)}", flush=True)
        if time.time() < deadline:
            time.sleep(args.interval)

    finished = datetime.now(timezone.utc)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "endpoint": ENDPOINT,
        "pairs": pairs,
        "window_start_utc": started.isoformat(),
        "window_end_utc": finished.isoformat(),
        "interval_seconds": args.interval,
        "poll_count": n,
        "samples": samples,
    }
    out.write_text(json.dumps(payload, indent=2))

    # Diagnostics per pair
    print("\n=== per-pair diagnostics (full spread, bp of mid) ===")
    agg: dict[str, dict] = {}
    for p in pairs:
        vals = [s["full_spread_bp"] for s in samples if s.get("pair") == p and s.get("plausible")]
        qts = [s["quote_ts"] for s in samples if s.get("pair") == p]
        if not vals:
            print(f"{p}: NO PLAUSIBLE QUOTES (n_quotes={len(qts)})")
            continue
        agg[p] = {
            "n": len(vals),
            "min": min(vals),
            "median": statistics.median(vals),
            "max": max(vals),
            "stdev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            "mean": statistics.fmean(vals),
        }
        a = agg[p]
        print(f"{p}: n={a['n']} min={a['min']:.3f} med={a['median']:.3f} "
              f"max={a['max']:.3f} mean={a['mean']:.3f} sd={a['stdev']:.3f} "
              f"last_quote={qts[-1] if qts else None}")
    summary_path = out.with_name(out.stem + "_summary.json")
    summary_path.write_text(json.dumps(agg, indent=2))
    print(f"\nwrote {out} and {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
