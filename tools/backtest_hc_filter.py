#!/usr/bin/env python3
"""
Backtest passes_high_conviction_pick on closed picks from dashboard export or closed_picks.json.

  python tools/backtest_hc_filter.py
  python tools/backtest_hc_filter.py --dashboard-json audit_dashboard/data/dashboard_data.json
  python tools/backtest_hc_filter.py --closed-json alpha_engine/data/closed_picks.json

Chronological split: first 60%% train, last 40%% test (by closed_at / timestamp / exit_time).
Uses the same filter as the audit dashboard (tools/dashboard_hc_rules.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO / "tools"))

from dashboard_hc_rules import passes_high_conviction_pick  # noqa: E402


def _parse_ts(p: dict[str, Any]) -> float:
    for k in ("closed_at", "exit_time", "timestamp", "close_date"):
        raw = p.get(k)
        if not raw:
            continue
        s = str(raw).replace("Z", "+00:00")
        if "T" not in s and " " in s:
            s = s.replace(" ", "T")
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.timestamp()
        except (ValueError, TypeError):
            continue
    return 0.0


def _pnl(p: dict[str, Any]) -> float:
    try:
        return float(p.get("pnl_pct") or 0)
    except (TypeError, ValueError):
        return 0.0


def _metrics(rows: list[dict[str, Any]]) -> tuple[int, float, float]:
    if not rows:
        return 0, 0.0, 0.0
    wins = sum(1 for p in rows if _pnl(p) > 0)
    n = len(rows)
    wr = 100.0 * wins / n
    avg = sum(_pnl(p) for p in rows) / n
    return n, wr, avg


def _load_closed(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    picks = data.get("picks") or {}
    if isinstance(picks, dict):
        for key in ("recent_closed", "closed_picks", "closed"):
            raw = picks.get(key)
            if isinstance(raw, list):
                return [x for x in raw if isinstance(x, dict)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dashboard-json",
        type=Path,
        default=_REPO / "audit_dashboard" / "data" / "dashboard_data.json",
    )
    ap.add_argument(
        "--closed-json",
        type=Path,
        default=_REPO / "alpha_engine" / "data" / "closed_picks.json",
        help="Fallback if --dashboard-json missing or use this only",
    )
    ap.add_argument("--use-closed-json-only", action="store_true")
    args = ap.parse_args()

    if args.use_closed_json_only or not args.dashboard_json.is_file():
        path = args.closed_json
        if not path.is_file():
            print("Missing %s" % path, file=sys.stderr)
            return 1
        closed = _load_closed(path)
        source = str(path)
    else:
        closed = _load_closed(args.dashboard_json)
        source = str(args.dashboard_json)
        if not closed and args.closed_json.is_file():
            closed = _load_closed(args.closed_json)
            source = str(args.closed_json) + " (fallback)"

    closed = sorted(closed, key=_parse_ts)
    split = int(len(closed) * 0.6)
    train, test = closed[:split], closed[split:]

    def run(label: str, subset: list[dict[str, Any]]) -> None:
        filtered = [p for p in subset if passes_high_conviction_pick(p)]
        n, wr, avg = _metrics(filtered)
        print(
            "%s FILTER: %s/%s picks pass  WR=%.1f%%  Avg PnL=%.2f%%"
            % (label, n, len(subset), wr if n else 0.0, avg if n else 0.0)
        )

    def baseline(label: str, subset: list[dict[str, Any]]) -> None:
        n, wr, avg = _metrics(subset)
        print(
            "%s BASELINE: %s picks  WR=%.1f%%  Avg PnL=%.2f%%"
            % (label, len(subset), wr if subset else 0.0, avg if subset else 0.0)
        )

    print("Source: %s  (n=%s closed, chronological split)" % (source, len(closed)))
    for label, subset in (("ALL", closed), ("TRAIN", train), ("TEST", test)):
        run(label, subset)
    for label, subset in (("ALL", closed), ("TEST", test)):
        baseline(label, subset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
