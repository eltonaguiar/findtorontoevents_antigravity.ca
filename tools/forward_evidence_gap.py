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
import math
import statistics
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


def ci_summary(rows, cost_mult: float = 1.0) -> dict:
    """Mean net return and its 95% CI, with cost applied EXACTLY ONCE.

    ``slippage_bps`` is the only cost in a row, converted to percent and
    subtracted once (scaled by ``cost_mult`` for stress). An earlier version
    subtracted it inside the return and again outside, which flipped the sign
    of the reported mean.
    """
    nets = []
    for r in rows:
        try:
            entry, exit_ = float(r["entry_px"]), float(r["exit_px"])
        except (KeyError, TypeError, ValueError):
            continue
        if entry <= 0:
            continue
        ret = (exit_ / entry - 1.0) * 100.0
        if str(r.get("side") or "").upper() == "SHORT":
            ret = -ret
        slip = 0.0
        try:
            slip = float(r.get("slippage_bps") or 0.0) / 100.0
        except (TypeError, ValueError):
            slip = 0.0
        nets.append(ret - cost_mult * slip)
    n = len(nets)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "ci": None}
    mean = statistics.mean(nets)
    sd = statistics.stdev(nets) if n > 1 else 0.0
    half = 1.96 * sd / math.sqrt(n)
    return {"n": n, "mean": round(mean, 4), "sd": round(sd, 4),
            "ci": [round(mean - half, 4), round(mean + half, 4)]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default=str(DEFAULT))
    ap.add_argument("--threshold", type=int, default=THRESHOLD)
    ap.add_argument("--cost-mult", type=float, default=1.0,
                    help="stress multiplier on slippage (1 = measured, 2 = 2x)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.path)
    raw = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    counts = Counter(str(r.get("asset_class") or r.get("class") or "UNKNOWN").upper()
                     for r in raw)
    if not counts:
        print(f"no forward observations at {path}", file=sys.stderr)
        print("Every class is at 0 forward rows, so INVESTABLE is unreachable "
              "until forward evidence accumulates.", file=sys.stderr)
        return 3

    per_class = {}
    for cls in counts:
        rows = [r for r in raw
                if str(r.get("asset_class") or r.get("class") or "UNKNOWN").upper() == cls]
        per_class[cls] = ci_summary(rows, cost_mult=args.cost_mult)

    if args.json:
        print(json.dumps(per_class, indent=1))
        return 0
    print(f"{'class':<12}{'rows':>6}{'mean%':>9}{'95% CI':>22}  rows_ready")
    for cls, s in sorted(per_class.items(), key=lambda kv: -(kv[1]["n"] or 0)):
        gap = max(0, args.threshold - s["n"])
        ci = "n/a" if s["ci"] is None else f"({s['ci'][0]:+.4f}, {s['ci'][1]:+.4f})"
        clears = "CLEARS_0" if (s["ci"] and s["ci"][0] > 0) else "straddles_0"
        print(f"{cls:<12}{s['n']:>6}{str(s['mean']):>9}{ci:>22}  "
              f"{'READY' if gap == 0 else f'needs {gap}'} {clears}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
