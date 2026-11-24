#!/usr/bin/env python3
"""Walk-forward check for a cell that LOOKS profitable.

A point estimate over one window cannot distinguish an edge from a lucky slice.
This splits the series into sequential folds and reports the net result per fold.
The question is not "is the mean positive" but "is it positive in more than one
fold, and in the most recent one".

Reuses the signal and trade logic from tools/measure_cell.py so the definition is
identical to the cell that produced the numbers being checked - re-implementing
it here would make the check unfalsifiable.

    python3 tools/walkforward_check.py --symbol SOLUSDT --strategy breakout --folds 3
"""
import argparse
import json
import statistics as st
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.measure_cell import (COST_BP, DEFINITIONS, boot_ci,  # noqa: E402
                                dsr, load_bars, signals, trades)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--horizon", default="1d")
    ap.add_argument("--folds", type=int, default=3)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    closes, opens, src = load_bars(args.symbol, args.horizon)
    if len(closes) < 200:
        print(f"  not enough bars: {len(closes)}")
        return 1

    print(f"  {args.symbol}/{args.strategy}/{args.horizon}  bars={len(closes)}  ({src})")
    print(f"  definition: {DEFINITIONS.get(args.strategy)}\n")

    fold_size = len(closes) // args.folds
    rows, positives = [], 0
    print(f"  {'fold':>4}{'bars':>7}{'n':>6}{'gross bp':>11}{'net bp':>10}"
          f"{'CI95 net':>22}")
    for k in range(args.folds):
        lo_i = k * fold_size
        hi_i = len(closes) if k == args.folds - 1 else (k + 1) * fold_size
        c, o = closes[lo_i:hi_i], opens[lo_i:hi_i]
        # warm-up so SMA50 exists inside each fold
        warm = min(60, lo_i)
        c = closes[lo_i - warm:hi_i]
        o = opens[lo_i - warm:hi_i]
        sig = signals(c, args.strategy, o)
        rs = trades(sig, o, 1)
        if len(rs) < 10:
            print(f"  {k+1:>4}{hi_i-lo_i:>7}{len(rs):>6}{'-':>11}{'-':>10}   n<10")
            rows.append({"fold": k + 1, "n": len(rs), "net_bp": None})
            continue
        net = [r - COST_BP / 1e4 for r in rs]
        lo, hi = boot_ci(net)
        mean = st.mean(net) * 1e4
        if mean > 0:
            positives += 1
        rows.append({"fold": k + 1, "n": len(rs),
                     "gross_bp": round(st.mean(rs) * 1e4, 2),
                     "net_bp": round(mean, 2),
                     "ci95_bp": [round(lo * 1e4, 2), round(hi * 1e4, 2)]})
        print(f"  {k+1:>4}{hi_i-lo_i:>7}{len(rs):>6}{st.mean(rs)*1e4:>11.2f}"
              f"{mean:>10.2f}   [{lo*1e4:+.1f}, {hi*1e4:+.1f}]")

    valid = [r for r in rows if r.get("net_bp") is not None]
    verdict = "NOT_ROBUST"
    if len(valid) >= 2:
        if positives == len(valid):
            verdict = "CONSISTENT_SIGN"
        elif positives == 0:
            verdict = "CONSISTENTLY_NEGATIVE"
    print(f"\n  folds positive: {positives}/{len(valid)}  -> {verdict}")
    if valid:
        print(f"  most recent fold net: {valid[-1].get('net_bp')} bp")

    payload = {"cell": f"{args.symbol}/{args.strategy}/{args.horizon}",
               "definition": DEFINITIONS.get(args.strategy),
               "bar_source": src, "folds": rows,
               "folds_positive": positives, "folds_valid": len(valid),
               "verdict": verdict,
               "most_recent_fold_net_bp": valid[-1].get("net_bp") if valid else None}
    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"  wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
