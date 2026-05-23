#!/usr/bin/env python3
"""Forward-testing quality analyser — reads claudes_test_state.json and prints a rich report."""

import json
from pathlib import Path
from statistics import median, stdev
from collections import defaultdict
from datetime import datetime

STATE_PATH = Path(__file__).parent / "data" / "claudes_test_state.json"


def load_state(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"State file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def summarize_trades(state: dict):
    trades = []
    for portfolio_id, port in state.items():
        closed = port.get("closed", [])
        if not isinstance(closed, list):
            continue
        for t in closed:
            pnl_pct = float(t.get("pnl_pct", 0) or 0)
            net_usd = float(t.get("net_pnl_usd", 0) or 0)
            trades.append(
                {
                    "portfolio": portfolio_id,
                    "symbol": t.get("symbol", "?"),
                    "direction": t.get("direction", "?"),
                    "asset_class": t.get("asset_class", "UNKNOWN"),
                    "strategy": t.get("strategy", "?"),
                    "exit_reason": t.get("exit_reason", "?"),
                    "pnl_pct": pnl_pct,
                    "net_usd": net_usd,
                    "rr": float(t.get("rr", 0) or 0),
                    "confidence": float(t.get("confidence", 0) or 0),
                }
            )
    return trades


def compute_metrics(trades: list):
    if not trades:
        return None
    n = len(trades)
    pnl_vals = [t["pnl_pct"] for t in trades]
    net_vals = [t["net_usd"] for t in trades]
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    exit_counts = defaultdict(int)
    for t in trades:
        exit_counts[t["exit_reason"]] += 1
    ac_groups = defaultdict(list)
    for t in trades:
        ac_groups[t["asset_class"]].append(t["pnl_pct"])
    port_groups = defaultdict(list)
    for t in trades:
        port_groups[t["portfolio"]].append(t["pnl_pct"])
    sorted_trades = sorted(trades, key=lambda x: x["pnl_pct"])
    return {
        "total": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / n * 100,
        "avg_pnl": sum(pnl_vals) / n,
        "median_pnl": median(pnl_vals),
        "stdev_pnl": stdev(pnl_vals) if n > 1 else 0.0,
        "total_net_usd": sum(net_vals),
        "avg_win_pnl": sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0.0,
        "avg_loss_pnl": sum(t["pnl_pct"] for t in losses) / len(losses)
        if losses
        else 0.0,
        "exit_counts": dict(exit_counts),
        "ac_groups": dict(ac_groups),
        "port_groups": dict(port_groups),
        "best_trades": sorted_trades[-3:],
        "worst_trades": sorted_trades[:3],
    }


def print_report(metrics):
    if not metrics:
        print("No closed trades to analyse.")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'=' * 55}\n  FORWARD-TESTING PERFORMANCE  ({now})\n{'=' * 55}")
    n, wr, avg = metrics["total"], metrics["win_rate"], metrics["avg_pnl"]
    print(f"\n--- SUMMARY")
    print(f"  Total closed trades : {n}")
    print(f"  Wins / Losses       : {metrics['wins']} / {metrics['losses']}")
    print(f"  Win rate            : {wr:.2f}%")
    print(f"  Avg PnL / trade     : {avg:+.4f}%")
    print(f"  Median PnL / trade  : {metrics['median_pnl']:+.4f}%")
    print(f"  StdDev PnL          : {metrics['stdev_pnl']:.4f}%")
    print(f"  Avg win             : {metrics['avg_win_pnl']:+.4f}%")
    print(f"  Avg loss            : {metrics['avg_loss_pnl']:+.4f}%")
    print(f"  Total net P&L       : ${metrics['total_net_usd']:+.2f}")
    print(f"\n--- VERDICT")
    print(f"  Expectancy  : {'POSITIVE' if avg > 0 else 'NEGATIVE — review scoring'}")
    print(
        f"  Win rate    : {'Acceptable' if wr >= 50 else 'Below 50% — check filters'}"
    )
    verdict = (
        "STRONG EDGE"
        if wr >= 55 and avg > 0.5
        else ("MARGINAL EDGE" if wr >= 50 and avg > 0 else "NEEDS IMPROVEMENT")
    )
    print(f"  Overall     : {verdict}")
    print(f"\n--- EXIT REASONS")
    for reason, cnt in sorted(metrics["exit_counts"].items(), key=lambda x: -x[1]):
        print(f"  {reason:<20} {cnt:4}  ({cnt / n * 100:.1f}%)")
    print(f"\n--- BY ASSET CLASS")
    for ac, vals in sorted(metrics["ac_groups"].items()):
        ac_wr = sum(1 for v in vals if v > 0) / len(vals) * 100
        ac_avg = sum(vals) / len(vals)
        print(f"  {ac:<12}  n={len(vals):3}  WR={ac_wr:.1f}%  avg={ac_avg:+.4f}%")
    print(f"\n--- BY PORTFOLIO")
    for pid, vals in sorted(metrics["port_groups"].items()):
        p_wr = sum(1 for v in vals if v > 0) / len(vals) * 100
        p_avg = sum(vals) / len(vals)
        print(f"  {pid:<30}  n={len(vals):3}  WR={p_wr:.1f}%  avg={p_avg:+.4f}%")
    print(f"\n--- TOP 3 BEST TRADES")
    for t in reversed(metrics["best_trades"]):
        print(
            f"  {t['symbol']:<12} {t['direction']:<6} {t['pnl_pct']:+.4f}%  exit={t['exit_reason']}  strat={t['strategy']}"
        )
    print(f"\n--- TOP 3 WORST TRADES")
    for t in metrics["worst_trades"]:
        print(
            f"  {t['symbol']:<12} {t['direction']:<6} {t['pnl_pct']:+.4f}%  exit={t['exit_reason']}  strat={t['strategy']}"
        )
    print(f"\n{'=' * 55}\n")


def main():
    try:
        state = load_state(STATE_PATH)
        trades = summarize_trades(state)
        metrics = compute_metrics(trades)
        print_report(metrics)
    except Exception as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
