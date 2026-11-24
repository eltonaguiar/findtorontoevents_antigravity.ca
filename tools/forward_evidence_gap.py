#!/usr/bin/env python3
"""Report how far each class is from the forward evidence INVESTABLE requires.

INVESTABLE cannot be granted by backtest (see class_backtest_sweep.py:109). It
needs forward rows whose out-of-sample CI stays positive after 2x cost. This
tool counts forward observations per class and reports the shortfall against a
threshold, so the gap is measured rather than assumed.

Forward rows are read from a JSONL file if present. If it is absent, every
class is reported at zero and the tool exits 3 - a measured absence, not an
error to be hidden.

Usage:
    python3 tools/forward_evidence_gap.py
    python3 tools/forward_evidence_gap.py --path reports/forward_observations.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "reports" / "forward_observations.jsonl"
THRESHOLD = 100


def count_rows(path: Path) -> Counter:
    c: Counter = Counter()
    if not path.exists():
        return c
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        cls = str(row.get("asset_class") or row.get("class") or "UNKNOWN").upper()
        c[cls] += 1
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default=str(DEFAULT))
    ap.add_argument("--threshold", type=int, default=THRESHOLD)
    args = ap.parse_args(argv)

    path = Path(args.path)
    counts = count_rows(path)
    if not counts:
        print(f"no forward observations at {path}", file=sys.stderr)
        print("Every class is at 0 forward rows, so INVESTABLE is unreachable "
              "until forward evidence accumulates.", file=sys.stderr)
        return 3
    for cls, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        gap = max(0, args.threshold - n)
        print(f"{cls:<14}{n:>7}  " + ("READY" if gap == 0 else f"needs {gap}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
