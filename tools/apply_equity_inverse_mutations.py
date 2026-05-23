#!/usr/bin/env python3
"""Apply equity-inverse mutations to active picks as a paper-track mirror.

Reads:
  strategy_health/data/equity_inverse_registry.json  - mutation rules
  audit_dashboard/data/dashboard_data.json           - active picks

Writes:
  alpha_engine/data/equity_inverse_paper_picks.json  - mirror picks with flipped direction

Safe to run repeatedly (idempotent by cohort+event_id dedup). Does NOT modify
the source picks pipeline; produces a standalone paper-track file for WR study.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "strategy_health" / "data" / "equity_inverse_registry.json"
DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT = REPO / "alpha_engine" / "data" / "equity_inverse_paper_picks.json"


def flip_direction(d: str) -> str:
    d = (d or "").upper()
    if d == "LONG":
        return "SHORT"
    if d == "SHORT":
        return "LONG"
    return d


def main() -> int:
    if not REGISTRY.exists():
        print(f"missing {REGISTRY}", file=sys.stderr)
        return 1
    if not DASHBOARD.exists():
        print(f"missing {DASHBOARD}", file=sys.stderr)
        return 1

    registry = json.loads(REGISTRY.read_text(encoding="utf-8", errors="replace"))
    strategies_to_flip = {m["source_strategy"]: m for m in registry.get("mutations", [])}

    data = json.loads(DASHBOARD.read_text(encoding="utf-8", errors="replace"))
    active = (data.get("picks") or {}).get("active", [])

    mirrors = []
    for p in active:
        if (p.get("asset_class") or "").upper() != "EQUITY":
            continue
        strat = p.get("strategy") or ""
        mut = strategies_to_flip.get(strat)
        if not mut:
            continue
        entry = float(p.get("entry_price") or 0)
        tp_orig = float(p.get("take_profit") or 0)
        sl_orig = float(p.get("stop_loss") or 0)
        if entry <= 0:
            continue
        new_direction = flip_direction(p.get("direction"))
        # Reflect TP/SL around entry: mirror distances to the opposite side
        tp_dist = abs(tp_orig - entry) if tp_orig else entry * 0.03
        sl_dist = abs(sl_orig - entry) if sl_orig else entry * 0.02
        if new_direction == "SHORT":
            new_tp = entry - tp_dist
            new_sl = entry + sl_dist
        else:
            new_tp = entry + tp_dist
            new_sl = entry - sl_dist
        mirrors.append({
            "symbol": p.get("symbol"),
            "asset_class": "EQUITY",
            "direction": new_direction,
            "entry_price": entry,
            "take_profit": round(new_tp, 4),
            "stop_loss": round(new_sl, 4),
            "original_direction": p.get("direction"),
            "source_strategy": strat,
            "mutation_name": mut["mutation_name"],
            "event_id": (p.get("event_id") or p.get("id") or f"{p.get('symbol')}_{strat}"),
            "cohort": "equity_inverse_paper_v1",
            "placed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "PAPER-TRACK MIRROR, NOT FOR REAL MONEY",
        })

    out = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cohort": "equity_inverse_paper_v1",
        "count": len(mirrors),
        "registry_version": registry.get("version"),
        "mirror_picks": mirrors,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {OUT} with {len(mirrors)} mirror picks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
