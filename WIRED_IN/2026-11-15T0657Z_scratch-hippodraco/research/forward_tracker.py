#!/usr/bin/env python3
"""Forward-test tracker. Stats are recomputed from an append-only trade ledger.

Kill/promote thresholds match the 2026-11-15 protocol. PnL is percent, not a
fraction, and is direction-aware. An eliminated strategy is not restarted by
the next log call.
"""
from __future__ import annotations

import argparse
import csv
import statistics
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("alpha_engine/data/forward_testing")
TRACKER_CSV = "forward_test_tracker.csv"
LEDGER_CSV = "forward_test_trades.csv"
ELIMINATED_CSV = "forward_test_eliminated.csv"

TRACKER_FIELDS = [
    "strategy_id", "asset_class", "symbol", "start_date", "total_trades",
    "winning_trades", "losing_trades", "win_rate_pct", "gross_profit_pct",
    "gross_loss_pct", "profit_factor", "net_pnl_pct", "max_drawdown_pct",
    "sharpe", "consecutive_losses", "max_consecutive_losses", "days_active",
    "trades_per_week", "cost_ratio_pct", "status", "kill_reason", "last_updated",
]
LEDGER_FIELDS = [
    "strategy_id", "asset_class", "symbol", "direction", "entry", "exit",
    "qty", "fees", "pnl_pct", "opened", "closed", "thesis", "logged_at",
]
ELIM_FIELDS = TRACKER_FIELDS + ["eliminated_date", "kill_details"]


def _p(name: str) -> Path:
    return DATA_DIR / name


def ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, fields in (
        (TRACKER_CSV, TRACKER_FIELDS),
        (LEDGER_CSV, LEDGER_FIELDS),
        (ELIMINATED_CSV, ELIM_FIELDS),
    ):
        path = _p(name)
        if not path.exists():
            with path.open("w", newline="") as fh:
                csv.DictWriter(fh, fieldnames=fields).writeheader()


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def write_csv(path: Path, fields, rows):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def trade_pnl_pct(entry, exit_px, fees, direction="LONG") -> float:
    entry_p = float(entry)
    exit_p = float(exit_px)
    if entry_p <= 0:
        raise ValueError("entry must be positive")
    if str(direction).upper() == "SHORT":
        gross = (entry_p - exit_p) / entry_p * 100.0
    else:
        gross = (exit_p - entry_p) / entry_p * 100.0
    return gross - (abs(float(fees)) / entry_p * 100.0)


def compute_stats(trades):
    pnls = [float(t["pnl_pct"]) for t in trades]
    if not pnls:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate_pct": 0.0, "gross_profit_pct": 0.0, "gross_loss_pct": 0.0,
            "profit_factor": 0.0, "net_pnl_pct": 0.0, "max_drawdown_pct": 0.0,
            "sharpe": 0.0, "consecutive_losses": 0, "max_consecutive_losses": 0,
            "cost_ratio_pct": 0.0, "days_active": 0, "trades_per_week": 0.0,
        }
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0)
    cum = peak = max_dd = 0.0
    consec = max_consec = 0
    for p in pnls:
        cum += p
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
        if p <= 0:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0
    if len(pnls) > 1 and statistics.pstdev(pnls) > 0:
        sharpe = statistics.mean(pnls) / statistics.pstdev(pnls) * (len(pnls) ** 0.5)
    else:
        sharpe = 0.0
    fee_pct = 0.0
    for t in trades:
        entry_p = float(t.get("entry") or 0)
        if entry_p > 0:
            fee_pct += abs(float(t.get("fees") or 0)) / entry_p * 100.0
    cost_ratio = (fee_pct / gross_profit * 100.0) if gross_profit > 0 else 0.0
    opened = [t.get("opened") or "" for t in trades if t.get("opened")]
    closed = [t.get("closed") or "" for t in trades if t.get("closed")]
    days = 1
    if opened and closed:
        try:
            a = datetime.fromisoformat(min(opened).replace("Z", "+00:00"))
            b = datetime.fromisoformat(max(closed).replace("Z", "+00:00"))
            days = max(1, int((b - a).total_seconds() / 86400) + 1)
        except ValueError:
            days = max(1, len(trades))
    return {
        "total_trades": len(pnls),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate_pct": round(len(wins) / len(pnls) * 100.0, 2),
        "gross_profit_pct": round(gross_profit, 4),
        "gross_loss_pct": round(gross_loss, 4),
        "profit_factor": round(pf, 3),
        "net_pnl_pct": round(sum(pnls), 4),
        "max_drawdown_pct": round(max_dd, 4),
        "sharpe": round(sharpe, 3),
        "consecutive_losses": consec,
        "max_consecutive_losses": max_consec,
        "cost_ratio_pct": round(cost_ratio, 2),
        "days_active": days,
        "trades_per_week": round(len(pnls) / max(days / 7.0, 0.1), 2),
    }


def check_kill_signals(stats):
    n = stats["total_trades"]
    if n >= 20 and stats["net_pnl_pct"] < 0:
        return True, "K1"
    if n >= 30 and stats["win_rate_pct"] < 35:
        return True, "K2"
    if n >= 25 and stats["profit_factor"] < 0.80:
        return True, "K3"
    if stats["max_drawdown_pct"] > 15:
        return True, "K4"
    if n >= 30 and stats["sharpe"] < 0:
        return True, "K5"
    if stats["days_active"] >= 14 and n == 0:
        return True, "K6"
    if stats["consecutive_losses"] >= 8:
        return True, "K7"
    if n >= 10 and stats["cost_ratio_pct"] > 200:
        return True, "K8"
    return False, None


def check_promote_signals(stats):
    if stats["total_trades"] < 30:
        return False
    return (
        stats["net_pnl_pct"] > 0
        and stats["win_rate_pct"] >= 45
        and stats["profit_factor"] >= 1.10
        and stats["max_drawdown_pct"] < 10
        and stats["sharpe"] > 0.5
        and stats["trades_per_week"] >= 1
        and stats["max_consecutive_losses"] <= 5
    )


def _eliminated_ids():
    return {r.get("strategy_id") for r in read_csv(_p(ELIMINATED_CSV))}


def log_trade(strategy_id, asset_class, symbol, entry, exit_px, qty, fees, opened, closed, thesis="", direction="LONG"):
    ensure_files()
    if strategy_id in _eliminated_ids():
        print(f"REFUSED: {strategy_id} already eliminated — not restarted")
        return
    pnl = trade_pnl_pct(entry, exit_px, fees, direction)
    now = datetime.now(timezone.utc).isoformat()
    ledger = read_csv(_p(LEDGER_CSV))
    ledger.append({
        "strategy_id": strategy_id,
        "asset_class": asset_class,
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "exit": exit_px,
        "qty": qty,
        "fees": fees,
        "pnl_pct": round(pnl, 4),
        "opened": opened,
        "closed": closed,
        "thesis": thesis,
        "logged_at": now,
    })
    write_csv(_p(LEDGER_CSV), LEDGER_FIELDS, ledger)
    mine = [t for t in ledger if t["strategy_id"] == strategy_id]
    stats = compute_stats(mine)
    start = str(opened).split("T")[0]
    row = {
        "strategy_id": strategy_id,
        "asset_class": asset_class,
        "symbol": symbol,
        "start_date": start,
        "status": "TRIAL",
        "kill_reason": "",
        "last_updated": now,
        **{k: stats[k] for k in (
            "total_trades", "winning_trades", "losing_trades", "win_rate_pct",
            "gross_profit_pct", "gross_loss_pct", "profit_factor", "net_pnl_pct",
            "max_drawdown_pct", "sharpe", "consecutive_losses", "max_consecutive_losses",
            "days_active", "trades_per_week", "cost_ratio_pct",
        )},
    }
    kill, reason = check_kill_signals(stats)
    tracker = [r for r in read_csv(_p(TRACKER_CSV)) if r.get("strategy_id") != strategy_id]
    if kill:
        row["status"] = "ELIMINATED"
        row["kill_reason"] = reason
        eliminated = read_csv(_p(ELIMINATED_CSV))
        eliminated.append({
            **row,
            "eliminated_date": now,
            "kill_details": f"Kill signal {reason} at {row['total_trades']} trades",
        })
        write_csv(_p(ELIMINATED_CSV), ELIM_FIELDS, eliminated)
        print(f"ELIMINATED: {strategy_id} — kill signal {reason}")
    else:
        if check_promote_signals(stats):
            row["status"] = "EXTENDED"
            print(f"PROMOTED: {strategy_id} — P1-P7 from the full ledger")
        tracker.append(row)
    write_csv(_p(TRACKER_CSV), TRACKER_FIELDS, tracker)
    print(f"Logged trade for {strategy_id}: status={row['status']}, trades={row['total_trades']}, net_pnl={row['net_pnl_pct']}%")


def status():
    ensure_files()
    print("FORWARD TEST TRACKER — ACTIVE")
    for r in read_csv(_p(TRACKER_CSV)):
        print(f"{r['strategy_id']} | {r['symbol']} | {r['status']} | trades={r['total_trades']} | net={r['net_pnl_pct']}% | kill={r.get('kill_reason') or '-'}")
    print("ELIMINATED")
    for r in read_csv(_p(ELIMINATED_CSV))[-10:]:
        print(f"{r['strategy_id']} | {r.get('kill_reason')} | trades={r.get('total_trades')} | net={r.get('net_pnl_pct')}%")


def main():
    parser = argparse.ArgumentParser(description="Forward Test Tracker")
    sub = parser.add_subparsers(dest="command")
    log_p = sub.add_parser("log")
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
    log_p.add_argument("--direction", default="LONG")
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "log":
        log_trade(args.strategy, args.asset_class, args.symbol, args.entry, args.exit, args.qty, args.fees, args.opened, args.closed, args.thesis, args.direction)
    elif args.command == "status":
        status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
