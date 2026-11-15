#!/usr/bin/env python3
"""
Forward Test Tracker
====================

Implements the kill-fast / hold-longer protocol from
2026-11-15_AM_profitability_plan/parallel_agent_worktree/08_qa_validation/FORWARD_TEST_TRACKING_PROTOCOL.md

Kill signals (K1-K8) checked after every trade:
  K1: Negative net PnL after costs with 20+ trades
  K2: Win rate < 35% with 30+ trades
  K3: Profit factor < 0.80 with 25+ trades
  K4: Max drawdown > 15%
  K5: Sharpe < 0 with 30+ trades
  K6: No trades for 14 consecutive days
  K7: 8 consecutive losses
  K8: Cost ratio > 200% of gross profit

Promote signals (P1-P7) checked at trade 30:
  P1: Positive net expectancy after 20 trades
  P2: Win rate >= 45% after 30 trades
  P3: Profit factor >= 1.10 after 25 trades
  P4: Max drawdown < 10%
  P5: Sharpe > 0.5 after 30 trades
  P6: Trade frequency >= 1 per week
  P7: Max consecutive losses <= 5

Usage:
  python3 forward_tracker.py log --strategy <id> --symbol <sym> --entry <px> --exit <px> --qty <n> --fees <f> --opened <date> --closed <date> [--thesis <text>]
  python3 forward_tracker.py status
  python3 forward_tracker.py evaluate --strategy <id>

"""

import csv
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path("alpha_engine/data/forward_testing")
TRACKER_CSV = DATA_DIR / "forward_test_tracker.csv"
ELIMINATED_CSV = DATA_DIR / "forward_test_eliminated.csv"
MONEY_READY_CSV = DATA_DIR / "forward_test_money_ready.csv"

FIELDNAMES = [
    "strategy_id","asset_class","symbol","start_date","total_trades","winning_trades",
    "losing_trades","win_rate_pct","gross_profit_pct","gross_loss_pct","profit_factor",
    "net_pnl_pct","max_drawdown_pct","sharpe","consecutive_losses","max_consecutive_losses",
    "days_active","trades_per_week","cost_ratio_pct","status","kill_reason","last_updated"
]

ELIMINATED_FIELDNAMES = [
    "strategy_id","asset_class","symbol","start_date","eliminated_date","total_trades","winning_trades",
    "losing_trades","win_rate_pct","gross_profit_pct","gross_loss_pct","profit_factor",
    "net_pnl_pct","max_drawdown_pct","sharpe","consecutive_losses","max_consecutive_losses",
    "days_active","trades_per_week","cost_ratio_pct","kill_reason","kill_details","last_updated"
]

MONEY_READY_FIELDNAMES = [
    "strategy_id","asset_class","symbol","start_date","promoted_date","total_trades","winning_trades",
    "losing_trades","win_rate_pct","gross_profit_pct","gross_loss_pct","profit_factor",
    "net_pnl_pct","max_drawdown_pct","sharpe","dsr","pbo","max_dd_pct","gates_passed","gates_total",
    "next_review_date","last_updated"
]


def ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path, fields in [(TRACKER_CSV, FIELDNAMES), (ELIMINATED_CSV, ELIMINATED_FIELDNAMES), (MONEY_READY_CSV, MONEY_READY_FIELDNAMES)]:
        if not path.exists():
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()


def read_csv(path, fields):
    if not path.exists():
        return []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


def write_csv(path, fields, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def compute_stats(trades):
    """Compute stats from a list of trade dicts with pnl_pct values."""
    if not trades:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate_pct": 0.0, "gross_profit_pct": 0.0, "gross_loss_pct": 0.0,
            "profit_factor": 0.0, "net_pnl_pct": 0.0, "max_drawdown_pct": 0.0,
            "sharpe": 0.0, "consecutive_losses": 0, "max_consecutive_losses": 0,
            "cost_ratio_pct": 0.0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)
    wr = n_wins / total * 100
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    net_pnl = sum(pnls)

    # Max drawdown on cumulative equity
    cum = []
    running = 0.0
    for p in pnls:
        running += p
        cum.append(running)
    peak = 0.0
    max_dd = 0.0
    for v in cum:
        peak = max(peak, v)
        dd = peak - v
        max_dd = max(max_dd, dd)

    # Sharpe (simple, per-trade)
    import statistics
    if len(pnls) > 1 and statistics.pstdev(pnls) > 0:
        sharpe = (statistics.mean(pnls) / statistics.pstdev(pnls)) * (len(pnls) ** 0.5)
    else:
        sharpe = 0.0

    # Consecutive losses
    consec = 0
    max_consec = 0
    for p in pnls:
        if p <= 0:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0

    # Cost ratio
    cost_ratio = 0.0
    if gross_profit > 0:
        # Estimate costs as part of pnl already netted; approximate
        cost_ratio = 0.0  # will be set externally if costs tracked separately

    return {
        "total_trades": total,
        "winning_trades": n_wins,
        "losing_trades": n_losses,
        "win_rate_pct": round(wr, 2),
        "gross_profit_pct": round(gross_profit, 4),
        "gross_loss_pct": round(gross_loss, 4),
        "profit_factor": round(pf, 3),
        "net_pnl_pct": round(net_pnl, 4),
        "max_drawdown_pct": round(max_dd, 4),
        "sharpe": round(sharpe, 3),
        "consecutive_losses": consec,
        "max_consecutive_losses": max_consec,
        "cost_ratio_pct": cost_ratio,
    }


def check_kill_signals(stats, days_active, trades_per_week, consecutive_losses_now):
    """Return (kill_bool, kill_reason) if any K1-K8 triggers."""
    if stats["total_trades"] >= 20 and stats["net_pnl_pct"] < 0:
        return True, "K1"
    if stats["total_trades"] >= 30 and stats["win_rate_pct"] < 35:
        return True, "K2"
    if stats["total_trades"] >= 25 and stats["profit_factor"] < 0.80:
        return True, "K3"
    if stats["max_drawdown_pct"] > 15:
        return True, "K4"
    if stats["total_trades"] >= 30 and stats["sharpe"] < 0:
        return True, "K5"
    if days_active >= 14 and stats["total_trades"] == 0:
        return True, "K6"
    if consecutive_losses_now >= 8:
        return True, "K7"
    if stats["cost_ratio_pct"] > 200:
        return True, "K8"
    return False, None


def check_promote_signals(stats, trades_per_week):
    """Return True if all P1-P7 hold (at trade 30 checkpoint)."""
    if stats["total_trades"] < 20:
        return False
    if stats["net_pnl_pct"] <= 0:
        return False  # P1
    if stats["total_trades"] < 30 or stats["win_rate_pct"] < 45:
        return False  # P2
    if stats["total_trades"] < 25 or stats["profit_factor"] < 1.10:
        return False  # P3
    if stats["max_drawdown_pct"] >= 10:
        return False  # P4
    if stats["total_trades"] < 30 or stats["sharpe"] <= 0.5:
        return False  # P5
    if trades_per_week < 1:
        return False  # P6
    if stats["max_consecutive_losses"] > 5:
        return False  # P7
    return True


def log_trade(strategy_id, asset_class, symbol, entry, exit_px, qty, fees, opened, closed, thesis=""):
    """Log a closed trade and update the tracker."""
    ensure_files()
    trades = read_csv(TRACKER_CSV, FIELDNAMES)

    # Find existing strategy row
    row = None
    row_idx = None
    for i, r in enumerate(trades):
        if r["strategy_id"] == strategy_id:
            row = r
            row_idx = i
            break

    entry_p = float(entry)
    exit_p = float(exit_px)
    pnl_pct = (exit_p - entry_p) / entry_p * 100  # LONG assumption; adjust for SHORT if needed
    # Subtract fees as % of entry
    pnl_pct -= (float(fees) / entry_p) * 100

    pnl_value = pnl_pct / 100.0

    now = datetime.now(timezone.utc).isoformat()

    if row is None:
        # New strategy
        trades_list = [{"pnl_pct": pnl_value}]
        stats = compute_stats(trades_list)
        start = opened.split("T")[0] if "T" in opened else opened
        new_row = {
            "strategy_id": strategy_id,
            "asset_class": asset_class,
            "symbol": symbol,
            "start_date": start,
            "total_trades": stats["total_trades"],
            "winning_trades": stats["winning_trades"],
            "losing_trades": stats["losing_trades"],
            "win_rate_pct": stats["win_rate_pct"],
            "gross_profit_pct": stats["gross_profit_pct"],
            "gross_loss_pct": stats["gross_loss_pct"],
            "profit_factor": stats["profit_factor"],
            "net_pnl_pct": stats["net_pnl_pct"],
            "max_drawdown_pct": stats["max_drawdown_pct"],
            "sharpe": stats["sharpe"],
            "consecutive_losses": stats["consecutive_losses"],
            "max_consecutive_losses": stats["max_consecutive_losses"],
            "days_active": 1,
            "trades_per_week": 1.0,
            "cost_ratio_pct": stats["cost_ratio_pct"],
            "status": "TRIAL",
            "kill_reason": "",
            "last_updated": now,
        }
        trades.append(new_row)
        row = new_row
    else:
        # Update existing - need full trade history; for simplicity recompute from stored stats + new trade
        # In production, we'd store full trade history. Here we approximate by updating aggregates.
        old_n = int(row["total_trades"])
        old_net = float(row["net_pnl_pct"])
        old_wins = int(row["winning_trades"])
        old_dd = float(row["max_drawdown_pct"])

        new_n = old_n + 1
        new_net = old_net + pnl_pct
        new_wins = old_wins + (1 if pnl_value > 0 else 0)
        new_losses = new_n - new_wins
        new_wr = new_wins / new_n * 100

        # Gross profit/loss approximation
        old_gp = float(row["gross_profit_pct"])
        old_gl = float(row["gross_loss_pct"])
        new_gp = old_gp + (pnl_pct if pnl_value > 0 else 0)
        new_gl = old_gl + (abs(pnl_pct) if pnl_value <= 0 else 0)
        new_pf = new_gp / new_gl if new_gl > 0 else (999.0 if new_gp > 0 else 0.0)

        new_dd = max(old_dd, abs(min(0, new_net)))  # rough DD estimate
        new_sharpe = float(row["sharpe"]) if row.get("sharpe") else 0.0

        # Consecutive losses
        old_consec = int(row["consecutive_losses"])
        old_max_consec = int(row["max_consecutive_losses"])
        if pnl_value <= 0:
            new_consec = old_consec + 1
        else:
            new_consec = 0
        new_max_consec = max(old_max_consec, new_consec)

        days = int(row["days_active"]) + 1
        tpw = new_n / max(days / 7.0, 0.1)

        # Cost ratio estimate
        gross_profit_for_cost = new_gp if new_gp > 0 else 1
        cost_ratio = (abs(float(fees)) / entry_p * 100) / gross_profit_for_cost * 100 if gross_profit_for_cost > 0 else 0

        row.update({
            "total_trades": new_n,
            "winning_trades": new_wins,
            "losing_trades": new_losses,
            "win_rate_pct": round(new_wr, 2),
            "gross_profit_pct": round(new_gp, 4),
            "gross_loss_pct": round(new_gl, 4),
            "profit_factor": round(new_pf, 3),
            "net_pnl_pct": round(new_net, 4),
            "max_drawdown_pct": round(new_dd, 4),
            "sharpe": round(new_sharpe, 3),
            "consecutive_losses": new_consec,
            "max_consecutive_losses": new_max_consec,
            "days_active": days,
            "trades_per_week": round(tpw, 2),
            "cost_ratio_pct": round(cost_ratio, 2),
            "last_updated": now,
        })

    # Check kill signals
    stats = compute_stats([{"pnl_pct": float(row["net_pnl_pct"]) / 100}])  # rough
    kill, reason = check_kill_signals(
        {
            "total_trades": int(row["total_trades"]),
            "net_pnl_pct": float(row["net_pnl_pct"]),
            "win_rate_pct": float(row["win_rate_pct"]),
            "profit_factor": float(row["profit_factor"]),
            "max_drawdown_pct": float(row["max_drawdown_pct"]),
            "sharpe": float(row["sharpe"]),
            "cost_ratio_pct": float(row["cost_ratio_pct"]),
            "max_consecutive_losses": int(row["max_consecutive_losses"]),
        },
        int(row["days_active"]),
        float(row["trades_per_week"]),
        int(row["consecutive_losses"]),
    )

    if kill:
        row["status"] = "ELIMINATED"
        row["kill_reason"] = reason
        # Move to eliminated file
        eliminated = read_csv(ELIMINATED_CSV, ELIMINATED_FIELDNAMES)
        elim_row = {k: row.get(k, "") for k in ELIMINATED_FIELDNAMES}
        elim_row["eliminated_date"] = now
        elim_row["kill_details"] = f"Kill signal {reason} triggered at {row['total_trades']} trades"
        eliminated.append(elim_row)
        write_csv(ELIMINATED_CSV, ELIMINATED_FIELDNAMES, eliminated)
        trades = [r for r in trades if r["strategy_id"] != strategy_id]
        print(f"ELIMINATED: {strategy_id} — kill signal {reason}")
    else:
        # Check promote at trade 30
        if int(row["total_trades"]) >= 30:
            promote = check_promote_signals(
                {
                    "total_trades": int(row["total_trades"]),
                    "net_pnl_pct": float(row["net_pnl_pct"]),
                    "win_rate_pct": float(row["win_rate_pct"]),
                    "profit_factor": float(row["profit_factor"]),
                    "max_drawdown_pct": float(row["max_drawdown_pct"]),
                    "sharpe": float(row["sharpe"]),
                    "max_consecutive_losses": int(row["max_consecutive_losses"]),
                },
                float(row["trades_per_week"]),
            )
            if promote:
                row["status"] = "EXTENDED"
                print(f"PROMOTED: {strategy_id} — meets P1-P7 criteria, moving to EXTENDED TEST")

    write_csv(TRACKER_CSV, FIELDNAMES, trades)
    print(f"Logged trade for {strategy_id}: status={row['status']}, trades={row['total_trades']}, net_pnl={row['net_pnl_pct']}%")


def status():
    """Print current status of all tracked strategies."""
    ensure_files()
    trades = read_csv(TRACKER_CSV, FIELDNAMES)
    eliminated = read_csv(ELIMINATED_CSV, ELIMINATED_FIELDNAMES)

    print("=" * 100)
    print("FORWARD TEST TRACKER — ACTIVE STRATEGIES")
    print("=" * 100)
    if not trades:
        print("(none)")
    else:
        for r in trades:
            print(f"{r['strategy_id']:<30s} | {r['symbol']:<10s} | {r['status']:<12s} | "
                  f"trades={int(r['total_trades']):>3d} | WR={r['win_rate_pct']:>6s}% | "
                  f"PF={r['profit_factor']:>6s} | netPnL={r['net_pnl_pct']:>8s}% | "
                  f"DD={r['max_drawdown_pct']:>6s}% | Sharpe={r['sharpe']:>6s} | "
                  f"kill={r['kill_reason'] or '-'}")

    print()
    print("=" * 100)
    print("ELIMINATED STRATEGIES")
    print("=" * 100)
    if not eliminated:
        print("(none)")
    else:
        for r in eliminated[-10:]:
            print(f"{r['strategy_id']:<30s} | {r['symbol']:<10s} | killed={r['kill_reason']} | "
                  f"trades={int(r['total_trades'])} | netPnL={r['net_pnl_pct']}% | "
                  f"details={r.get('kill_details','')}")


def evaluate(strategy_id):
    """Evaluate a specific strategy against kill/promote signals."""
    ensure_files()
    trades = read_csv(TRACKER_CSV, FIELDNAMES)
    row = next((r for r in trades if r["strategy_id"] == strategy_id), None)
    if not row:
        print(f"Strategy {strategy_id} not found in tracker.")
        return

    kill, reason = check_kill_signals(
        {
            "total_trades": int(row["total_trades"]),
            "net_pnl_pct": float(row["net_pnl_pct"]),
            "win_rate_pct": float(row["win_rate_pct"]),
            "profit_factor": float(row["profit_factor"]),
            "max_drawdown_pct": float(row["max_drawdown_pct"]),
            "sharpe": float(row["sharpe"]),
            "cost_ratio_pct": float(row["cost_ratio_pct"]),
            "max_consecutive_losses": int(row["max_consecutive_losses"]),
        },
        int(row["days_active"]),
        float(row["trades_per_week"]),
        int(row["consecutive_losses"]),
    )

    promote = check_promote_signals(
        {
            "total_trades": int(row["total_trades"]),
            "net_pnl_pct": float(row["net_pnl_pct"]),
            "win_rate_pct": float(row["win_rate_pct"]),
            "profit_factor": float(row["profit_factor"]),
            "max_drawdown_pct": float(row["max_drawdown_pct"]),
            "sharpe": float(row["sharpe"]),
            "max_consecutive_losses": int(row["max_consecutive_losses"]),
        },
        float(row["trades_per_week"]),
    )

    print(f"\nStrategy: {strategy_id} ({row['symbol']})")
    print(f"  Status: {row['status']}")
    print(f"  Trades: {row['total_trades']} | WR: {row['win_rate_pct']}% | PF: {row['profit_factor']}")
    print(f"  Net PnL: {row['net_pnl_pct']}% | Max DD: {row['max_drawdown_pct']}% | Sharpe: {row['sharpe']}")
    print(f"  Kill signal: {'YES — ' + reason if kill else 'none'}")
    print(f"  Promote (P1-P7): {'YES' if promote else 'no'}")


def main():
    parser = argparse.ArgumentParser(description="Forward Test Tracker")
    sub = parser.add_subparsers(dest="command")

    log_p = sub.add_parser("log", help="Log a closed trade")
    log_p.add_argument("--strategy", required=True)
    log_p.add_argument("--asset-class", default="EQUITY")
    log_p.add_argument("--symbol", required=True)
    log_p.add_argument("--entry", required=True, type=float)
    log_p.add_argument("--exit", required=True, type=float)
    log_p.add_argument("--qty", required=True, type=float)
    log_p.add_argument("--fees", required=True, type=float)
    log_p.add_argument("--opened", required=True)
    log_p.add_argument("--closed", required=True)
    log_p.add_argument("--thesis", default="")

    sub.add_parser("status", help="Show all strategy statuses")

    eval_p = sub.add_parser("evaluate", help="Evaluate a strategy against kill/promote signals")
    eval_p.add_argument("--strategy", required=True)

    args = parser.parse_args()

    if args.command == "log":
        log_trade(args.strategy, args.asset_class, args.symbol, args.entry, args.exit,
                  args.qty, args.fees, args.opened, args.closed, args.thesis)
    elif args.command == "status":
        status()
    elif args.command == "evaluate":
        evaluate(args.strategy)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
