#!/usr/bin/env python3
"""
Pairwise correlation gate for strategy daily returns.

Feed a CSV with a date column and one column per strategy (simple returns).
Flags any pair with |rho| >= threshold (default 0.2).

Example:
  python correlation_prune_strategies.py --csv strategy_daily_returns.csv --threshold 0.2

Exporting daily returns: run your backtest engine on a common calendar, align
bars to UTC business days per asset class, and write one column per strategy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, required=True, help="CSV: date + one column per strategy return")
    ap.add_argument("--date-col", default="date", help="Date column name")
    ap.add_argument("--threshold", type=float, default=0.2, help="Max allowed |Pearson|")
    ap.add_argument("--json", action="store_true", help="Print violations as JSON")
    args = ap.parse_args()

    if not args.csv.is_file():
        print(f"File not found: {args.csv}", file=sys.stderr)
        return 2

    df = pd.read_csv(args.csv, parse_dates=[args.date_col])
    df = df.set_index(args.date_col).sort_index()
    num = df.select_dtypes(include=["number"])
    if num.shape[1] < 2:
        print("Need at least 2 numeric strategy columns.", file=sys.stderr)
        return 2

    corr = num.corr()
    viol = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            r = float(corr.loc[a, b])
            if abs(r) >= args.threshold:
                viol.append({"a": a, "b": b, "rho": round(r, 4)})

    if args.json:
        import json

        print(json.dumps({"threshold": args.threshold, "violations": viol}, indent=2))
    else:
        print(f"Correlation matrix ({len(cols)} strategies), threshold |rho| < {args.threshold}")
        if not viol:
            print("OK: no pairs exceed threshold.")
        else:
            print(f"FAIL: {len(viol)} pair(s) exceed threshold:")
            for v in viol:
                print(f"  {v['a']} vs {v['b']}: rho={v['rho']}")

    return 1 if viol else 0


if __name__ == "__main__":
    raise SystemExit(main())
