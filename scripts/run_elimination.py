"""Weekly elimination: evaluates research cohort strategies against kill criteria."""
import json
import os
import csv
from datetime import datetime, timezone

TRACKER_PATH = os.path.join(os.path.dirname(__file__), "..", "cross_aggregation", "data", "beta_score_tracker.json")
KILL_WR = 0.45
KILL_PF = 1.0
MIN_TRADES = 30


def run():
    if not os.path.exists(TRACKER_PATH):
        print("No tracker file found.")
        return

    with open(TRACKER_PATH) as f:
        tracker = json.load(f)

    strategy_stats = {}
    for p in tracker.get("picks", []):
        if p.get("outcome") is None:
            continue
        strat = p.get("strategy", "unknown")
        if strat not in strategy_stats:
            strategy_stats[strat] = {"wins": 0, "losses": 0}
        if p["outcome"] in ("TP_HIT", "WON"):
            strategy_stats[strat]["wins"] += 1
        else:
            strategy_stats[strat]["losses"] += 1

    blocked = []
    report = []
    for strat, stats in strategy_stats.items():
        total = stats["wins"] + stats["losses"]
        wr = stats["wins"] / total if total > 0 else 0
        if total >= MIN_TRADES and wr < KILL_WR:
            blocked.append(strat)
        report.append({"strategy": strat, "trades": total, "wr": round(wr, 3), "blocked": strat in blocked})

    report_dir = os.path.join(os.path.dirname(__file__), "..", "cross_aggregation", "data")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"elimination_report_{datetime.now().strftime('%Y%m%d')}.csv")
    with open(report_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["strategy", "trades", "wr", "blocked"])
        w.writeheader()
        w.writerows(report)

    print(f"Evaluated {len(strategy_stats)} strategies. Blocked: {blocked}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    run()
