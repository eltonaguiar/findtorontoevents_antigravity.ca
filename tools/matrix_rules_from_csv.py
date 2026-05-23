#!/usr/bin/env python3
"""
Build matrix_symbol_gates.json from a compatibility matrix CSV (from mutation_analysis).

Block: wr_pct < --block-wr-lt and trades >= --min-trades
Allow (restrictive): wr_pct >= --allow-wr-gte and trades >= --min-trades — when non-empty
for a system, only listed symbols may pass the allow gate.

Usage:
  python tools/matrix_rules_from_csv.py -i mutation_artifacts/compat_matrix.csv \\
    -o alpha_engine/data/matrix_symbol_gates.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Build symbol allow/block JSON from matrix CSV")
    ap.add_argument("-i", "--input", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--min-trades", type=int, default=5)
    ap.add_argument("--block-wr-lt", type=float, default=35.0)
    ap.add_argument("--allow-wr-gte", type=float, default=60.0)
    args = ap.parse_args()

    if not args.input.is_file():
        print(f"Missing: {args.input}", file=sys.stderr)
        return 2

    block: dict[str, list[str]] = {}
    allow: dict[str, list[str]] = {}

    with args.input.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sys_k = (row.get("system") or "").strip()
            sym = (row.get("symbol") or "").strip().upper()
            if not sys_k or not sym:
                continue
            try:
                trades = int(float(row.get("trades") or 0))
                wr = float(row.get("wr_pct") or 0)
            except ValueError:
                continue
            if trades < args.min_trades:
                continue
            sk = sys_k.lower()
            if wr < args.block_wr_lt:
                block.setdefault(sk, []).append(sym)
            if wr >= args.allow_wr_gte:
                allow.setdefault(sk, []).append(sym)

    for d in (block, allow):
        for k in d:
            d[k] = sorted(set(d[k]))

    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_csv": str(args.input.as_posix()),
        "min_trades": args.min_trades,
        "block_wr_lt": args.block_wr_lt,
        "allow_wr_gte": args.allow_wr_gte,
        "block": block,
        "allow": allow,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"Wrote {args.output}: {sum(len(v) for v in block.values())} block rows, "
        f"{len(allow)} systems with allowlists",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
