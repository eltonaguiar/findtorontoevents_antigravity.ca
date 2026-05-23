#!/usr/bin/env python3
"""
FOREX Unblock Tracker — monitors resolved FOREX picks and flags when a
strategy crosses the statistical threshold for real-money sizing.
"""

from collections import defaultdict
from edge_filter_engine_v3 import (
    load_dashboard,
    compute_filter_metrics,
    MIN_N_FILTER,
    MIN_PF_TARGET,
    MIN_WR_TARGET,
)


def run_tracker():
    dashboard = load_dashboard()
    recent_closed = dashboard["picks"].get("recent_closed", [])

    # Filter to resolved FOREX picks
    forex_picks = [p for p in recent_closed if p.get("asset_class") == "FOREX"]

    # Group by strategy
    by_strategy = defaultdict(list)
    for p in forex_picks:
        by_strategy[p.get("strategy", "unknown")].append(p)

    total_n = len(forex_picks)
    print("=" * 50)
    print("FOREX UNBLOCK TRACKER")
    print("=" * 50)
    print(f"Total resolved FOREX picks: {total_n}")
    print()

    best = None
    for strat, picks in sorted(by_strategy.items()):
        m = compute_filter_metrics(picks)
        n = m["n"]
        wr = m["wr"]
        pf = m["pf"]
        print(f"  {strat:40s}  n={n:3d}  WR={wr:6.1%}  PF={pf:5.2f}")
        if n >= MIN_N_FILTER and pf >= MIN_PF_TARGET and wr >= MIN_WR_TARGET:
            if best is None or n > best["n"]:
                best = {
                    "strategy": strat,
                    "n": n,
                    "wr": wr,
                    "pf": pf,
                }

    print()
    if best:
        print("UNBLOCK RECOMMENDED")
        print(f"  Strategy : {best['strategy']}")
        print(f"  N        : {best['n']}")
        print(f"  WR       : {best['wr']:.1%}")
        print(f"  PF       : {best['pf']:.2f}")
    else:
        # Identify the best candidate: highest n among strategies that already
        # meet PF and WR thresholds; fallback to highest n overall.
        candidates = []
        for strat, picks in by_strategy.items():
            m = compute_filter_metrics(picks)
            candidates.append({
                "strategy": strat,
                "n": m["n"],
                "wr": m["wr"],
                "pf": m["pf"],
            })
        qualified = [c for c in candidates if c["pf"] >= MIN_PF_TARGET and c["wr"] >= MIN_WR_TARGET]
        closest = max(qualified, key=lambda c: c["n"]) if qualified else max(candidates, key=lambda c: c["n"])
        needed = max(0, MIN_N_FILTER - closest["n"])
        print(f"BLOCKED: need {needed} more picks (closest strategy: {closest['strategy']}, n={closest['n']})")

    print("=" * 50)


if __name__ == "__main__":
    run_tracker()
