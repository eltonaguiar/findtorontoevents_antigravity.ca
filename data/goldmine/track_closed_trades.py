#!/usr/bin/env python3
"""
Goldmine Closed-Trade Tracker
==============================
Tracks when Goldmine picks are closed/removed and records their final return.
Runs via GitHub Actions after each goldmine collection cycle.

Output files:
- data/goldmine/closed_trades.json  — Full history of closed trades
- data/goldmine/trade_performance.json — Aggregate performance stats
- data/goldmine/pick_snapshots.json — Rolling snapshot for diff detection
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDMINE_DIR = ROOT / "data" / "goldmine"

STOCK_PICKS = GOLDMINE_DIR / "stock_picks.json"
CLOSED_TRADES = GOLDMINE_DIR / "closed_trades.json"
PERFORMANCE = GOLDMINE_DIR / "trade_performance.json"
SNAPSHOTS = GOLDMINE_DIR / "pick_snapshots.json"


def load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return {}


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def get_current_picks():
    """Load current stock picks and normalize to dict keyed by ticker."""
    data = load_json(STOCK_PICKS)
    picks = {}
    if isinstance(data, dict):
        for pick in data.get("consensus_picks", data.get("picks", [])):
            ticker = pick.get("ticker") or pick.get("symbol", "")
            if ticker:
                picks[ticker] = {
                    "ticker": ticker,
                    "name": pick.get("name", pick.get("company_name", "")),
                    "entry_price": pick.get("entry_price", pick.get("avg_entry_price")),
                    "current_price": pick.get("current_price", pick.get("last_price", pick.get("latest_price"))),
                    # BUG FIX: goldmine stock_picks.json uses tp_price/sl_price, not target_price/stop_loss
                    "target_price": pick.get("target_price") or pick.get("tp_price"),
                    "stop_loss": pick.get("stop_loss") or pick.get("stop_loss_price") or pick.get("sl_price"),
                    "return_pct": pick.get("return_pct", pick.get("current_return_pct", 0)),
                    "algo_count": pick.get("algo_count", pick.get("algorithm_count", pick.get("consensus_count", 1))),
                    "direction": pick.get("direction", "LONG"),
                    "confidence": pick.get("confidence", pick.get("confidence_score", pick.get("consensus_score", 0))),
                    "first_seen": pick.get("first_seen", pick.get("earliest_pick_date", datetime.now(timezone.utc).isoformat())),
                    "algorithms": pick.get("algorithms", pick.get("sources", []))
                }
    return picks


def load_previous_snapshot():
    """Load the previous pick snapshot for comparison."""
    data = load_json(SNAPSHOTS)
    return data.get("picks", {})


def detect_closed_trades(current_picks, previous_picks):
    """Find picks that were in previous snapshot but not in current."""
    closed = []
    now = datetime.now(timezone.utc).isoformat()

    for ticker, prev in previous_picks.items():
        if ticker not in current_picks:
            # Pick was removed — treat as closed
            exit_reason = "removed_from_consensus"
            final_return = prev.get("return_pct", 0)

            # Determine if it was a win or loss
            outcome = "WIN" if final_return and final_return > 0 else "LOSS"

            closed.append({
                "ticker": ticker,
                "name": prev.get("name", ""),
                "direction": prev.get("direction", "LONG"),
                "entry_price": prev.get("entry_price"),
                "exit_price": prev.get("current_price"),
                "final_return_pct": final_return,
                "outcome": outcome,
                "exit_reason": exit_reason,
                "exit_date": now,
                "entry_date": prev.get("first_seen", "unknown"),
                "algo_count": prev.get("algo_count", 1),
                "algorithms": prev.get("algorithms", [])
            })

    # Check for TP/SL hits in current picks
    for ticker, curr in current_picks.items():
        tp = curr.get("target_price")
        sl = curr.get("stop_loss")
        price = curr.get("current_price")

        if not price:
            continue

        if tp and price >= tp:
            closed.append({
                "ticker": ticker,
                "name": curr.get("name", ""),
                "direction": curr.get("direction", "LONG"),
                "entry_price": curr.get("entry_price"),
                "exit_price": price,
                "final_return_pct": curr.get("return_pct", 0),
                "outcome": "WIN",
                "exit_reason": "tp_hit",
                "exit_date": now,
                "entry_date": curr.get("first_seen", "unknown"),
                "algo_count": curr.get("algo_count", 1),
                "algorithms": curr.get("algorithms", [])
            })
        elif sl and price <= sl:
            closed.append({
                "ticker": ticker,
                "name": curr.get("name", ""),
                "direction": curr.get("direction", "LONG"),
                "entry_price": curr.get("entry_price"),
                "exit_price": price,
                "final_return_pct": curr.get("return_pct", 0),
                "outcome": "LOSS",
                "exit_reason": "sl_hit",
                "exit_date": now,
                "entry_date": curr.get("first_seen", "unknown"),
                "algo_count": curr.get("algo_count", 1),
                "algorithms": curr.get("algorithms", [])
            })

    return closed


def update_closed_trades(new_closed):
    """Append newly closed trades to the history file."""
    data = load_json(CLOSED_TRADES)
    if not isinstance(data, dict):
        data = {"trades": [], "updated_at": ""}

    existing_keys = set()
    for t in data.get("trades", []):
        existing_keys.add(f"{t['ticker']}:{t.get('exit_date','')[:10]}")

    added = 0
    for trade in new_closed:
        key = f"{trade['ticker']}:{trade.get('exit_date','')[:10]}"
        if key not in existing_keys:
            data.setdefault("trades", []).append(trade)
            existing_keys.add(key)
            added += 1

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_json(CLOSED_TRADES, data)
    return added


def compute_performance():
    """Calculate aggregate performance from closed trades."""
    data = load_json(CLOSED_TRADES)
    trades = data.get("trades", [])

    if not trades:
        perf = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_closed": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "avg_return_pct": 0,
            "total_return_pct": 0,
            "best_trade": None,
            "worst_trade": None,
            "by_exit_reason": {},
            "by_algo_count": {}
        }
        save_json(PERFORMANCE, perf)
        return perf

    wins = [t for t in trades if t.get("outcome") == "WIN"]
    losses = [t for t in trades if t.get("outcome") == "LOSS"]
    returns = [t.get("final_return_pct", 0) for t in trades if t.get("final_return_pct") is not None]

    best = max(trades, key=lambda t: t.get("final_return_pct", 0))
    worst = min(trades, key=lambda t: t.get("final_return_pct", 0))

    # By exit reason
    by_reason = {}
    for t in trades:
        reason = t.get("exit_reason", "unknown")
        by_reason.setdefault(reason, {"count": 0, "wins": 0, "losses": 0})
        by_reason[reason]["count"] += 1
        if t.get("outcome") == "WIN":
            by_reason[reason]["wins"] += 1
        else:
            by_reason[reason]["losses"] += 1

    # By algo count (consensus strength)
    by_algo = {}
    for t in trades:
        ac = str(t.get("algo_count", 1))
        by_algo.setdefault(ac, {"count": 0, "wins": 0, "avg_return": 0, "returns": []})
        by_algo[ac]["count"] += 1
        if t.get("outcome") == "WIN":
            by_algo[ac]["wins"] += 1
        by_algo[ac]["returns"].append(t.get("final_return_pct", 0))

    for ac in by_algo:
        rets = by_algo[ac]["returns"]
        by_algo[ac]["avg_return"] = round(sum(rets) / len(rets), 2) if rets else 0
        del by_algo[ac]["returns"]

    perf = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_closed": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "avg_return_pct": round(sum(returns) / len(returns), 2) if returns else 0,
        "total_return_pct": round(sum(returns), 2),
        "best_trade": {"ticker": best["ticker"], "return_pct": best.get("final_return_pct", 0)},
        "worst_trade": {"ticker": worst["ticker"], "return_pct": worst.get("final_return_pct", 0)},
        "by_exit_reason": by_reason,
        "by_algo_count": by_algo
    }

    save_json(PERFORMANCE, perf)
    return perf


def main():
    print("=== Goldmine Closed-Trade Tracker ===")

    # 1. Load current picks
    current = get_current_picks()
    print(f"Current picks: {len(current)}")

    # 2. Load previous snapshot
    previous = load_previous_snapshot()
    print(f"Previous snapshot: {len(previous)} picks")

    # 3. Detect closed trades
    if previous:
        closed = detect_closed_trades(current, previous)
        if closed:
            added = update_closed_trades(closed)
            print(f"Detected {len(closed)} closed trades, {added} new")
        else:
            print("No closed trades detected")
    else:
        print("First run — no previous snapshot to compare")

    # 4. Save current snapshot for next comparison
    save_json(SNAPSHOTS, {
        "snapshot_time": datetime.now(timezone.utc).isoformat(),
        "picks": current
    })
    print(f"Saved snapshot with {len(current)} picks")

    # 5. Compute performance stats
    perf = compute_performance()
    print(f"Performance: {perf['total_closed']} closed, {perf['win_rate']}% WR")

    print("Done!")


if __name__ == "__main__":
    main()
