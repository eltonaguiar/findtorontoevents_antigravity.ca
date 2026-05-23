#!/usr/bin/env python3
"""
Compare two compatibility matrix CSVs (system, symbol, trades, wins, wr_pct, ...).
Flags (system, symbol) pairs where win rate dropped by more than --threshold
percentage points (early strategy decay warning).

Usage:
  python tools/matrix_diff.py prev.csv curr.csv --threshold 15
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def _load_matrix(path: Path) -> dict[tuple[str, str], dict[str, float]]:
    out: dict[tuple[str, str], dict[str, float]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            sys_k = (row.get("system") or "").strip()
            sym = (row.get("symbol") or "").strip().upper()
            if not sys_k or not sym:
                continue
            try:
                wr = float(row.get("wr_pct") or row.get("wr") or 0)
                trades = float(row.get("trades") or 0)
            except ValueError:
                continue
            out[(sys_k, sym)] = {"wr_pct": wr, "trades": trades}
    return out


def run_diff(prev_path: Path, curr_path: Path, threshold_pp: float) -> list[str]:
    prev = _load_matrix(prev_path)
    curr = _load_matrix(curr_path)
    lines: list[str] = []
    for key, old in prev.items():
        if key not in curr:
            continue
        new = curr[key]
        drop = old["wr_pct"] - new["wr_pct"]
        if drop > threshold_pp:
            lines.append(
                f"{key[0]}\t{key[1]}\tWR {old['wr_pct']:.1f}% -> {new['wr_pct']:.1f}% "
                f"({drop:+.1f}pp)\ttrades {int(old['trades'])} -> {int(new['trades'])}"
            )
    lines.sort()
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff two matrix CSVs for WR decay")
    ap.add_argument("previous_csv", type=Path)
    ap.add_argument("current_csv", type=Path)
    ap.add_argument("--threshold", type=float, default=15.0, help="Min WR drop (pp) to flag")
    ap.add_argument("-o", "--output", type=Path, default=None, help="Write report file")
    args = ap.parse_args()

    if not args.previous_csv.is_file():
        print(f"Missing: {args.previous_csv}", file=sys.stderr)
        return 2
    if not args.current_csv.is_file():
        print(f"Missing: {args.current_csv}", file=sys.stderr)
        return 2

    lines = run_diff(args.previous_csv, args.current_csv, args.threshold)
    header = (
        f"# Matrix WR decay > {args.threshold:g}pp: {args.previous_csv.name} -> {args.current_csv.name}\n"
        f"# pairs flagged: {len(lines)}\n"
    )
    text = header + "\n".join(lines) + ("\n" if lines else "")
    print(text, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
