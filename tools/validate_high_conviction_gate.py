#!/usr/bin/env python3
"""Historical stats for ``high_conviction_gate_passed`` / ``high_conviction`` on closed picks.

Reads dashboard JSON (default ``audit_dashboard/data/dashboard_data.json``), prints
win rate and expectancy for rows with the flag vs without. Sparse n is expected for forex.

Usage:
  python tools/validate_high_conviction_gate.py
  python tools/validate_high_conviction_gate.py --dashboard path/to/dashboard_data.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent


def _flagged(p: dict) -> bool:
    return bool(p.get("high_conviction_gate_passed") or p.get("high_conviction"))


def _stats(rows: list[dict]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    wins = losses = flat = 0
    t = 0.0
    for p in rows:
        try:
            x = float(p.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            continue
        t += x
        if x > 0.01:
            wins += 1
        elif x < -0.01:
            losses += 1
        else:
            flat += 1
    n = wins + losses + flat
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "win_rate_pct": round(100.0 * wins / n, 2) if n else None,
        "expectancy_pct": round(t / n, 4) if n else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dashboard",
        type=Path,
        default=REPO / "audit_dashboard" / "data" / "dashboard_data.json",
    )
    args = ap.parse_args()
    if not args.dashboard.is_file():
        print("missing", args.dashboard, file=sys.stderr)
        return 1
    data = json.loads(args.dashboard.read_text(encoding="utf-8", errors="replace"))
    closed = (data.get("picks") or {}).get("recent_closed") or []
    if not isinstance(closed, list):
        print("no recent_closed", file=sys.stderr)
        return 1
    on = [p for p in closed if isinstance(p, dict) and _flagged(p)]
    off = [p for p in closed if isinstance(p, dict) and not _flagged(p)]
    nc_on = [
        p
        for p in on
        if str(p.get("asset_class") or "").upper() != "CRYPTO"
    ]
    nc_off = [
        p
        for p in off
        if str(p.get("asset_class") or "").upper() != "CRYPTO"
    ]
    report = {
        "dashboard": str(args.dashboard).replace("\\", "/"),
        "high_conviction_on": _stats(on),
        "high_conviction_off": _stats(off),
        "non_crypto_on": _stats(nc_on),
        "non_crypto_off": _stats(nc_off),
        "note": "Sparse n for HC flags is normal; use for monitoring, not live gating.",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
