#!/usr/bin/env python3
"""
Drawdown Alert — monitors per-strategy and portfolio drawdowns,
broadcasts alerts to Redis bus when thresholds are breached.

Thresholds:
  - Per-strategy: 5% drawdown from peak cumulative PnL
  - Portfolio-wide: 5% / 10% / 15% / 20% tiered alerts

Usage:
    python tools/dd_alert.py
"""

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(REPO, "audit_dashboard", "data", "dashboard_data.json")
REDIS_BUS = r"C:\Users\zerou\redis-bus\agent_bus.py"

STRATEGY_DD_THRESHOLD = 5.0  # percent
PORTFOLIO_TIERS = [5, 10, 15, 20]  # percent


def broadcast(message):
    """Send alert to Redis bus."""
    print(f"  [ALERT] {message}")
    try:
        subprocess.run(
            [sys.executable, REDIS_BUS, "broadcast", "dd-alert", message],
            timeout=10, capture_output=True, text=True,
        )
    except Exception as e:
        print(f"  [WARN] Redis broadcast failed: {e}")


def compute_drawdown(pnl_series):
    """Compute current drawdown from peak of cumulative PnL series."""
    if not pnl_series:
        return 0.0, 0.0, 0.0
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnl_series:
        cum += pnl
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    current_dd = peak - cum
    return current_dd, max_dd, cum


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data["picks"]["recent_closed"]
    print(f"Loaded {len(picks)} closed picks")

    # Group by strategy, preserving order
    by_strategy = defaultdict(list)
    all_pnl = []
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        pnl = float(pnl)
        strat = p.get("strategy", "unknown") or "unknown"
        by_strategy[strat].append(pnl)
        all_pnl.append(pnl)

    alerts_fired = []

    # Per-strategy drawdown check
    print(f"\n{'='*70}")
    print("PER-STRATEGY DRAWDOWN CHECK")
    print(f"{'='*70}")
    print(f"{'Strategy':<40} {'Trades':>6} {'CumPnL':>8} {'CurDD':>7} {'MaxDD':>7} {'Alert':>6}")
    print("-" * 70)

    strategy_results = []
    for strat in sorted(by_strategy.keys(), key=lambda s: len(by_strategy[s]), reverse=True):
        pnl_series = by_strategy[strat]
        if len(pnl_series) < 5:
            continue
        cur_dd, max_dd, cum_pnl = compute_drawdown(pnl_series)
        alert = cur_dd >= STRATEGY_DD_THRESHOLD
        flag = " !!!" if alert else ""
        print(f"{strat[:39]:<40} {len(pnl_series):>6} {cum_pnl:>+7.1f}% {cur_dd:>6.1f}% {max_dd:>6.1f}%{flag:>6}")

        strategy_results.append({
            "strategy": strat,
            "trades": len(pnl_series),
            "cum_pnl_pct": round(cum_pnl, 2),
            "current_dd_pct": round(cur_dd, 2),
            "max_dd_pct": round(max_dd, 2),
            "alert": alert,
        })

        if alert:
            msg = f"DRAWDOWN ALERT: {strat} at {cur_dd:.1f}% drawdown (threshold: {STRATEGY_DD_THRESHOLD}%)"
            broadcast(msg)
            alerts_fired.append(msg)

    # Portfolio-wide drawdown
    port_cur_dd, port_max_dd, port_cum = compute_drawdown(all_pnl)
    print(f"\n{'='*70}")
    print("PORTFOLIO-WIDE DRAWDOWN")
    print(f"{'='*70}")
    print(f"  Cumulative PnL: {port_cum:+.1f}%")
    print(f"  Current DD:     {port_cur_dd:.1f}%")
    print(f"  Max DD:         {port_max_dd:.1f}%")

    for tier in PORTFOLIO_TIERS:
        if port_cur_dd >= tier:
            msg = f"PORTFOLIO DRAWDOWN ALERT: Portfolio at {port_cur_dd:.1f}% drawdown (tier: {tier}%)"
            broadcast(msg)
            alerts_fired.append(msg)

    print(f"\nAlerts fired: {len(alerts_fired)}")
    for a in alerts_fired:
        print(f"  -> {a}")

    # Write summary (no separate JSON needed, but useful for automation)
    output = {
        "generated": datetime.now().isoformat() + "Z",
        "portfolio": {
            "cum_pnl_pct": round(port_cum, 2),
            "current_dd_pct": round(port_cur_dd, 2),
            "max_dd_pct": round(port_max_dd, 2),
        },
        "strategy_alerts": [r for r in strategy_results if r["alert"]],
        "alerts_fired": len(alerts_fired),
        "all_strategies": strategy_results,
    }
    out_path = os.path.join(REPO, "tools", "dd_alert_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
