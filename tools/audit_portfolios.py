#!/usr/bin/env python3
"""
audit_portfolios.py — Reproducible WR/PnL stats for specific portfolio IDs.

Context
-------
DeepSeek APR12 audit (DEEPSEEK_APR122026.MD, Sec 6C) flagged:
  - rr_kings: "-4.75% avg PnL, most consistent negative"
  - multi_asset_diversified: "0% WR, -1.20% avg PnL"
  - fear_greed_contrarian: "80% WR +0.72% avg, only 5 trades"

Portfolio assignments are NOT tagged on the global closed_picks.json or
audit_trail/universal_resolved_picks.json ledgers — those are source-system
level. Per-portfolio closed trades live in:
    audit_dashboard/data/claudes_test_state.json

This script computes WR, avg pnl_pct, trade count, and date range from that
state file so the kill decision is grounded in real, reproducible numbers.

Usage
-----
    python tools/audit_portfolios.py
    python tools/audit_portfolios.py --portfolios rr_kings multi_asset_diversified
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

DEFAULT_PORTFOLIOS = [
    "rr_kings",
    "multi_asset_diversified",
    "fear_greed_contrarian",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = REPO_ROOT / "audit_dashboard" / "data" / "claudes_test_state.json"


def _load_state(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _pnl_values(closed: list[dict]) -> list[float]:
    out: list[float] = []
    for c in closed:
        v = c.get("pnl_pct")
        if v is None:
            v = c.get("pnl_percentage")
        if v is None:
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _date_range(closed: list[dict]) -> tuple[str, str]:
    dates: list[str] = []
    for c in closed:
        for k in ("closed_at", "exit_time", "resolved_at", "timestamp"):
            if c.get(k):
                dates.append(str(c[k]))
                break
    if not dates:
        return ("-", "-")
    dates.sort()
    return (dates[0], dates[-1])


def compute_stats(state: dict, portfolio_id: str) -> dict:
    port = state.get(portfolio_id)
    if not isinstance(port, dict):
        return {
            "id": portfolio_id,
            "found": False,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "wr_pct": None,
            "avg_pnl_pct": None,
            "first_close": "-",
            "last_close": "-",
        }

    closed = port.get("closed", []) or []
    pnls = _pnl_values(closed)
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p <= 0)
    n = len(pnls)
    wr = (100.0 * wins / n) if n else None
    avg = mean(pnls) if pnls else None
    first, last = _date_range(closed)

    return {
        "id": portfolio_id,
        "found": True,
        "trades": n,
        "wins": wins,
        "losses": losses,
        "wr_pct": wr,
        "avg_pnl_pct": avg,
        "equity": port.get("equity"),
        "initial_capital": port.get("initial_capital"),
        "first_close": first,
        "last_close": last,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--portfolios", nargs="*", default=DEFAULT_PORTFOLIOS)
    ap.add_argument("--state", default=str(STATE_FILE))
    ap.add_argument("--json", action="store_true", help="emit JSON instead of table")
    args = ap.parse_args()

    state = _load_state(Path(args.state))
    results = [compute_stats(state, pid) for pid in args.portfolios]

    if args.json:
        print(json.dumps(results, indent=2, default=str))
        return 0

    hdr = f"{'portfolio':<28} {'n':>4} {'wins':>5} {'loss':>5} {'wr%':>7} {'avg_pnl%':>10}  date_range"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        wr = f"{r['wr_pct']:.1f}" if r["wr_pct"] is not None else "-"
        avg = f"{r['avg_pnl_pct']:.3f}" if r["avg_pnl_pct"] is not None else "-"
        drange = f"{r['first_close']} .. {r['last_close']}"
        print(
            f"{r['id']:<28} {r['trades']:>4} {r['wins']:>5} {r['losses']:>5} "
            f"{wr:>7} {avg:>10}  {drange}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
