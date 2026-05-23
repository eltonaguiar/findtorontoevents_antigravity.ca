#!/usr/bin/env python3
"""Print block / allow candidates from a compat matrix CSV (same thresholds as matrix_rules_from_csv)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--min-trades", type=int, default=5)
    ap.add_argument("--block-wr-lt", type=float, default=35.0)
    ap.add_argument("--allow-wr-gte", type=float, default=60.0)
    args = ap.parse_args()
    if not args.csv_path.is_file():
        print(f"Missing {args.csv_path}", file=sys.stderr)
        return 2

    blocks: list[tuple[str, str, float, int]] = []
    allows: list[tuple[str, str, float, int]] = []
    with args.csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                t = int(float(row.get("trades") or 0))
                wr = float(row.get("wr_pct") or 0)
            except ValueError:
                continue
            if t < args.min_trades:
                continue
            sys_k = (row.get("system") or "").strip()
            sym = (row.get("symbol") or "").strip().upper()
            if not sys_k or not sym:
                continue
            if wr < args.block_wr_lt:
                blocks.append((sys_k, sym, wr, t))
            if wr >= args.allow_wr_gte:
                allows.append((sys_k, sym, wr, t))

    blocks.sort()
    allows.sort()
    print("=== BLOCK candidates (WR < {:.0f}%, trades >= {}) ===".format(args.block_wr_lt, args.min_trades))
    for s, y, w, t in blocks:
        print(f"  {s}\t{y}\t{w:.1f}% WR\t{t} trades")
    print("\n=== ALLOW candidates (WR >= {:.0f}%, trades >= {}) ===".format(args.allow_wr_gte, args.min_trades))
    for s, y, w, t in allows:
        print(f"  {s}\t{y}\t{w:.1f}% WR\t{t} trades")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
