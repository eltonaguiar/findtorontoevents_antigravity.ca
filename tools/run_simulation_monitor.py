#!/usr/bin/env python3
"""
Simulation Candidate Monitoring Runner
======================================

Repeatable runner for monitoring simulation candidates against live prices.
Designed to be called on a schedule (cron / GitHub Action / CI).

Reads:  2026-11-15_AM_profitability_plan/parallel_agent_worktree/01_asset_class_plans/candidate_picks/simulation_candidate_picks.json
Writes: audit_dashboard/data/simulation_candidates_live.json

NOT FOR TRADING — all candidates FAILED money-ready gates (sizing_allowed: false).
Monitoring only.
"""

import json
import os
import sys
import yfinance as yf
from datetime import datetime, timezone

CANDIDATES_PATH = "2026-11-15_AM_profitability_plan/parallel_agent_worktree/01_asset_class_plans/candidate_picks/simulation_candidate_picks.json"
OUTPUT_PATH = "audit_dashboard/data/simulation_candidates_live.json"


def fetch_current_price(symbol):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def main():
    if not os.path.exists(CANDIDATES_PATH):
        print(f"Candidate file not found: {CANDIDATES_PATH}")
        sys.exit(1)

    with open(CANDIDATES_PATH) as f:
        candidates = json.load(f)

    results = []
    for pick in candidates:
        symbol = pick["symbol"]
        entry = pick["entry_price"]
        current = fetch_current_price(symbol)

        result = {
            "id": pick["id"],
            "symbol": symbol,
            "strategy": pick["strategy"],
            "asset_class": pick.get("asset_class", "UNKNOWN"),
            "direction": pick["direction"],
            "entry_price": entry,
            "current_price": current,
            "tp": pick["take_profit"],
            "sl": pick["stop_loss"],
            "status": pick["status"],
            "monitoring_only": pick.get("monitoring_only", True),
            "not_for_real_money": pick.get("not_for_real_money", True),
            "sizing_allowed": pick.get("sizing_allowed", False),
            "money_ready": pick.get("money_ready", False),
            "gates_passed": pick.get("gates_passed", 0),
            "gates_total": pick.get("gates_total", 7),
            "backtest_stats": pick.get("backtest_stats", {}),
            "monitored_at": datetime.now(timezone.utc).isoformat(),
        }

        if current is not None:
            if pick["direction"] == "LONG":
                unrealized_pct = (current - entry) / entry * 100
            else:
                unrealized_pct = (entry - current) / entry * 100
            result["unrealized_pnl_pct"] = round(unrealized_pct, 2)

            if pick["direction"] == "LONG":
                if current >= pick["take_profit"]:
                    result["live_signal"] = "TP_HIT"
                elif current <= pick["stop_loss"]:
                    result["live_signal"] = "SL_HIT"
                else:
                    result["live_signal"] = "ACTIVE"
            else:
                if current <= pick["take_profit"]:
                    result["live_signal"] = "TP_HIT"
                elif current >= pick["stop_loss"]:
                    result["live_signal"] = "SL_HIT"
                else:
                    result["live_signal"] = "ACTIVE"
        else:
            result["unrealized_pnl_pct"] = None
            result["live_signal"] = "DATA_UNAVAILABLE"

        results.append(result)

    results.sort(key=lambda x: (x["gates_passed"], x["symbol"]))

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "simulation_candidate_picks.json",
        "warning": "ALL CANDIDATES FAILED MONEY-READY GATES — NOT FOR REAL MONEY — MONITORING ONLY",
        "total_candidates": len(results),
        "candidates": results,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"Monitored {len(results)} simulation candidates → {OUTPUT_PATH}")
    print("-" * 90)
    for r in results:
        upnl = r["unrealized_pnl_pct"]
        upnl_str = f"{upnl:+.2f}%" if upnl is not None else "N/A"
        print(f"{r['symbol']:>10s} | {r['strategy']:<28s} | entry={r['entry_price']:>10.4f} | "
              f"current={r['current_price'] or 'N/A':>10} | unrealized={upnl_str:>8s} | "
              f"signal={r['live_signal']:<12s} | gates={r['gates_passed']}/{r['gates_total']} | "
              f"SIZING_ALLOWED={r['sizing_allowed']}")
    print("-" * 90)
    print("WARNING: None of these candidates are approved for real-money trading.")
    print("         They are simulation candidates that failed all money-ready gates.")


if __name__ == "__main__":
    main()
