#!/usr/bin/env python3
"""
Sync Strategy Performance from Dashboard Payload.
This implements Option B from PR #289: populates strategy_performance.json
directly from the unified closed picks in dashboard_payload.json, bridging
the naming mismatch between walk-forward native names and display names.
"""

import json
from pathlib import Path
import numpy as np
import sys

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
PERF_PATH = ROOT / "alpha_engine" / "data" / "strategy_performance.json"

def _compute_stats(picks):
    # Same stats computation as alpha_engine/forward_validator.py
    real_picks = [p for p in picks if p.get("exit_reason") != "STALE_DATA_NO_PRICE"]
    pnls = [float(p["pnl_pct"]) for p in real_picks if "pnl_pct" in p and p["pnl_pct"] is not None]
    if not pnls:
        return None

    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p <= 0)
    n = len(pnls)
    win_rate = wins / n

    arr = np.array(pnls)
    avg_pnl = float(arr.mean())
    total_pnl = float(arr.sum())
    sharpe = float(arr.mean() / arr.std() * np.sqrt(252)) if arr.std() > 0 else 0

    return {
        "wins": wins,
        "losses": losses,
        "closed_picks": n,
        "win_rate": win_rate,
        "avg_pnl_pct": avg_pnl,
        "total_pnl_pct": total_pnl,
        "sharpe": sharpe,
    }

def run():
    if not DASHBOARD_PATH.exists():
        print(f"File not found: {DASHBOARD_PATH}")
        return

    with open(DASHBOARD_PATH) as f:
        payload = json.load(f)

    closed = payload.get("picks", {}).get("recent_closed", [])
    
    # Group by strategy
    by_strategy = {}
    for p in closed:
        strat = str(p.get("strategy") or p.get("source_system") or "unknown").strip()
        if strat:
            by_strategy.setdefault(strat, []).append(p)
    
    # Compute new perf
    new_perf = {}
    for strat, picks in by_strategy.items():
        stats = _compute_stats(picks)
        if stats:
            new_perf[strat] = stats

    # Merge with existing
    existing_perf = {}
    if PERF_PATH.exists():
        with open(PERF_PATH) as f:
            existing_perf = json.load(f)
            
    merged = {**existing_perf, **new_perf}
    
    with open(PERF_PATH, "w") as f:
        json.dump(merged, f, indent=2)
        
    print(f"Updated {len(new_perf)} strategies from dashboard closed picks.")

if __name__ == "__main__":
    run()
