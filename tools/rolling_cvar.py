#!/usr/bin/env python3
"""
30-Day Rolling CVaR (Conditional Value-at-Risk) Monitor.

Computes CVaR95 and CVaR99 on rolling 30-day windows using closed pick
timestamps, tracking how portfolio tail risk evolves over time.

Usage:
    python tools/rolling_cvar.py
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(REPO, "audit_dashboard", "data", "dashboard_data.json")
OUT_PATH = os.path.join(REPO, "tools", "rolling_cvar_results.json")

WINDOW_DAYS = 30
MIN_TRADES_PER_WINDOW = 10


def parse_ts(ts_str):
    """Parse various timestamp formats to datetime."""
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(ts_str.replace("+00:00", "Z").rstrip("Z"), fmt.rstrip("Z"))
            return dt
        except (ValueError, AttributeError):
            continue
    return None


def compute_cvar(pnl_array, confidence=0.95):
    """CVaR at given confidence: mean of worst (1-confidence) fraction."""
    if len(pnl_array) == 0:
        return 0.0
    sorted_pnl = np.sort(pnl_array)
    cutoff_idx = max(1, int(len(sorted_pnl) * (1 - confidence)))
    return float(sorted_pnl[:cutoff_idx].mean())


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data["picks"]["recent_closed"]
    print(f"Loaded {len(picks)} closed picks")

    # Parse timestamps and filter
    dated_picks = []
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        ts = parse_ts(p.get("closed_at"))
        if ts is None:
            continue
        dated_picks.append({"ts": ts, "pnl": float(pnl)})

    dated_picks.sort(key=lambda x: x["ts"])
    print(f"Picks with valid timestamp + PnL: {len(dated_picks)}")

    if not dated_picks:
        print("No data to compute rolling CVaR.")
        return

    # Date range
    min_date = dated_picks[0]["ts"].date()
    max_date = dated_picks[-1]["ts"].date()
    print(f"Date range: {min_date} to {max_date}")

    # Group by date
    by_date = defaultdict(list)
    for p in dated_picks:
        by_date[p["ts"].date()].append(p["pnl"])

    # Compute rolling CVaR for each day
    rolling_series = []
    current = min_date + timedelta(days=WINDOW_DAYS)
    while current <= max_date:
        window_start = current - timedelta(days=WINDOW_DAYS)
        window_pnl = []
        d = window_start
        while d <= current:
            window_pnl.extend(by_date.get(d, []))
            d += timedelta(days=1)

        if len(window_pnl) >= MIN_TRADES_PER_WINDOW:
            arr = np.array(window_pnl)
            rolling_series.append({
                "date": str(current),
                "n_trades": len(window_pnl),
                "cvar_95": round(compute_cvar(arr, 0.95), 4),
                "cvar_99": round(compute_cvar(arr, 0.99), 4),
                "mean_pnl": round(float(arr.mean()), 4),
            })
        current += timedelta(days=1)

    if not rolling_series:
        print("Insufficient data for rolling windows.")
        return

    # All-time CVaR
    all_pnl = np.array([p["pnl"] for p in dated_picks])
    alltime_cvar95 = round(compute_cvar(all_pnl, 0.95), 4)
    alltime_cvar99 = round(compute_cvar(all_pnl, 0.99), 4)

    current_cvar95 = rolling_series[-1]["cvar_95"]
    current_cvar99 = rolling_series[-1]["cvar_99"]

    # 30 days ago CVaR (or earliest available)
    ago_idx = max(0, len(rolling_series) - 31)
    ago_cvar95 = rolling_series[ago_idx]["cvar_95"]
    ago_cvar99 = rolling_series[ago_idx]["cvar_99"]

    # Print summary
    print(f"\n{'='*70}")
    print("ROLLING 30-DAY CVaR SUMMARY")
    print(f"{'='*70}")
    print(f"{'Metric':<25} {'Current':>10} {'30d Ago':>10} {'All-Time':>10} {'Trend':>10}")
    print("-" * 70)
    trend95 = "IMPROVING" if current_cvar95 > ago_cvar95 else "WORSENING"
    trend99 = "IMPROVING" if current_cvar99 > ago_cvar99 else "WORSENING"
    print(f"{'CVaR 95%':<25} {current_cvar95:>+9.2f}% {ago_cvar95:>+9.2f}% {alltime_cvar95:>+9.2f}% {trend95:>10}")
    print(f"{'CVaR 99%':<25} {current_cvar99:>+9.2f}% {ago_cvar99:>+9.2f}% {alltime_cvar99:>+9.2f}% {trend99:>10}")
    print(f"\nRolling windows computed: {len(rolling_series)}")
    print(f"Current window trades: {rolling_series[-1]['n_trades']}")

    # Write JSON
    output = {
        "generated": datetime.now().isoformat() + "Z",
        "config": {"window_days": WINDOW_DAYS, "min_trades": MIN_TRADES_PER_WINDOW},
        "summary": {
            "current_cvar95": current_cvar95,
            "current_cvar99": current_cvar99,
            "ago_30d_cvar95": ago_cvar95,
            "ago_30d_cvar99": ago_cvar99,
            "alltime_cvar95": alltime_cvar95,
            "alltime_cvar99": alltime_cvar99,
            "trend_95": trend95,
            "trend_99": trend99,
        },
        "rolling_series": rolling_series,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults written to {OUT_PATH}")


if __name__ == "__main__":
    main()
