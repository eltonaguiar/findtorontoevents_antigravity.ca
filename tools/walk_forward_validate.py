#!/usr/bin/env python3
"""
Walk-forward validation wrapper: runs tools/walk_forward_backtest engine and
checks aggregate OOS metrics against targets (optional exit 1).

Example:
  python tools/walk_forward_validate.py --max-oos-dd-pct 15 --min-sharpe 0.5
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_wfb():
    path = ROOT / "tools" / "walk_forward_backtest.py"
    spec = importlib.util.spec_from_file_location("walk_forward_backtest", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load walk_forward_backtest")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate walk-forward aggregate vs targets")
    ap.add_argument("--max-oos-dd-pct", type=float, default=10.0, help="Fail if aggregate max_dd %% exceeds this")
    ap.add_argument("--min-sharpe", type=float, default=-999, help="Fail if aggregate Sharpe below this")
    ap.add_argument("--min-wr", type=float, default=0.0, help="Fail if aggregate WR%% below this")
    ap.add_argument("--conf", type=float, default=0.0)
    ap.add_argument("--ml", type=float, default=0.0)
    ap.add_argument("--trust", type=float, default=0.0)
    args = ap.parse_args()

    wfb = _load_wfb()
    picks = wfb.load_picks()
    if len(picks) < 10:
        print("walk_forward_validate: insufficient closed picks for WF (need 10+).")
        return 1
    _windows, agg = wfb.walk_forward(picks, None, None, args.conf, args.ml, args.trust, False)
    print("Aggregate OOS:", agg)
    ok = True
    if agg.get("max_dd", 0) > args.max_oos_dd_pct:
        print(f"FAIL: max_dd {agg.get('max_dd')} > limit {args.max_oos_dd_pct}")
        ok = False
    if agg.get("sharpe", -999) < args.min_sharpe:
        print(f"FAIL: sharpe {agg.get('sharpe')} < min {args.min_sharpe}")
        ok = False
    if agg.get("wr", 0) < args.min_wr:
        print(f"FAIL: wr {agg.get('wr')} < min {args.min_wr}")
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
