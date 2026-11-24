#!/usr/bin/env python3
"""Forward-observation clock for the pre-registered SOL breakout cell.

The pre-registration (docs/edge_research/PREREG_sol_breakout20_2026-11-24.md)
freezes a specification. This makes it LIVE: each run appends any newly completed
FORWARD trade to a JSONL and reports progress against the three pass criteria.

Only trades whose ENTRY is strictly after the registration date count. Everything
before it is in-sample by definition and is excluded - including it would let the
hypothesis be graded on the data that generated it.

    python3 tools/sol_breakout_forward.py
"""
import argparse
import csv
import json
import math
import statistics as st
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.measure_cell import COST_BP, boot_ci  # noqa: E402

SYMBOL = "SOLUSDT"
LOOKBACK = 20
REGISTERED = "2026-11-24"
OUT = REPO_ROOT / "reports" / "forward_obs_sol_breakout20.jsonl"
NEED_N = 30


def bars():
    from tools.crypto_bars import fetch_klines  # noqa: PLC0415
    end = int(time.time() * 1000)
    start = end - 1000 * 24 * 3600 * 1000
    k = fetch_klines(SYMBOL, "1d", start, end)
    from datetime import date
    return [{"d": str(date.fromtimestamp(b["timestamp"] / 1000)),
             "o": float(b["open"]), "c": float(b["close"])} for b in k]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true",
                    help="append newly completed forward trades")
    args = ap.parse_args(argv)

    b = bars()
    if len(b) < LOOKBACK + 3:
        print(f"  not enough bars: {len(b)}")
        return 1

    # frozen signal: close > max of the PRIOR 20 closes
    trades = []
    for i in range(LOOKBACK, len(b) - 1):
        prior = [x["c"] for x in b[i - LOOKBACK:i]]
        if b[i]["c"] > max(prior):
            entry, exit_ = b[i + 1]["o"], b[i + 1]["o"]  # 1-bar hold
            if i + 2 < len(b):
                exit_ = b[i + 2]["o"]
            gross = exit_ / entry - 1.0
            trades.append({"entry_date": b[i + 1]["d"], "exit_date": b[i + 2]["d"] if i + 2 < len(b) else None,
                           "entry": entry, "exit": exit_,
                           "gross_bp": round(gross * 1e4, 2),
                           "net_bp": round(gross * 1e4 - COST_BP, 2)})

    fwd = [t for t in trades if t["entry_date"] > REGISTERED and t["exit_date"]]
    print(f"  {SYMBOL} breakout{LOOKBACK} d1   bars={len(b)} ({b[0]['d']}..{b[-1]['d']})")
    print(f"  registered {REGISTERED}; forward trades so far: {len(fwd)}/{NEED_N}")

    if args.refresh and fwd:
        seen = set()
        if OUT.exists():
            seen = {json.loads(l)["entry_date"] for l in OUT.read_text().splitlines() if l.strip()}
        added = 0
        with OUT.open("a") as fh:
            for t in fwd:
                if t["entry_date"] in seen:
                    continue
                fh.write(json.dumps(t) + "\n")
                added += 1
        print(f"  appended {added} new forward trade(s) to {OUT.name}")

    if not fwd:
        print("\n  PASS CRITERIA")
        print(f"    1. n >= {NEED_N} forward trades .......... NOT MET (0)")
        print("    2. 95% CI excludes zero ................ NOT MET (no data)")
        print("    3. DSR > 0.95 at trial count 1 ......... NOT MET (no data)")
        print("\n  The clock is running. Zero forward trades is the honest state on day 0.")
        return 0

    net = [t["net_bp"] for t in fwd]
    mean = st.mean(net)
    lo, hi = boot_ci([x / 1e4 for x in net]) if len(net) >= 5 else (float("nan"),) * 2
    print(f"\n  forward net mean {mean:+.2f} bp over n={len(net)}")
    if len(net) >= 5:
        print(f"  95% CI [{lo*1e4:+.2f}, {hi*1e4:+.2f}] bp")
    print(f"    1. n >= {NEED_N} .......................... "
          f"{'MET' if len(net) >= NEED_N else 'NOT MET'} ({len(net)})")
    print(f"    2. CI excludes zero .................... "
          f"{'MET' if len(net) >= 5 and lo > 0 else 'NOT MET'}")
    print("    3. DSR > 0.95 at trial count 1 ......... reported once n>=30")
    return 0


if __name__ == "__main__":
    sys.exit(main())
