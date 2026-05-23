"""
Alpha Engine Winning Trade Monitor
===================================
Detects newly closed trades (WON/LOST) and prints a summary.
Runs after forward_validator.py in the CI pipeline.

Usage:
    python alpha_engine_winning_monitor.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).resolve().parent / "alpha_engine" / "data"
ACTIVE_PATH = DATA_DIR / "active_picks.json"
CLOSED_PATH = DATA_DIR / "closed_picks.json"
PERF_PATH = DATA_DIR / "strategy_performance.json"


def load_json(path: Path) -> dict | list:
    if not path.exists():
        return [] if "picks" in path.name else {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {path.name}: {e}")
        return [] if "picks" in path.name else {}


def main():
    print("=" * 60)
    print("ALPHA ENGINE — Winning Trade Monitor")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    active = load_json(ACTIVE_PATH)
    closed = load_json(CLOSED_PATH)
    perf = load_json(PERF_PATH)

    # Handle both list and dict formats
    active_picks = active if isinstance(active, list) else active.get("picks", [])
    closed_picks = closed if isinstance(closed, list) else closed.get("picks", closed.get("closed_picks", []))

    # Count results
    open_count = len(active_picks)
    total_closed = len(closed_picks)
    wins = sum(1 for p in closed_picks if p.get("status") == "WON")
    losses = sum(1 for p in closed_picks if p.get("status") == "LOST")
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0

    # Recent closures (last 24h)
    now = datetime.now(timezone.utc)
    recent = []
    for p in closed_picks:
        exit_date = p.get("exit_date") or p.get("closed_at")
        if exit_date:
            try:
                dt = datetime.fromisoformat(str(exit_date).replace("Z", "+00:00"))
                if hasattr(dt, "tzinfo") and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                diff_hours = (now - dt).total_seconds() / 3600
                if diff_hours <= 24:
                    recent.append(p)
            except Exception:
                pass

    # Summary
    print(f"\nOpen positions:  {open_count}")
    print(f"Total closed:    {total_closed}")
    print(f"Wins / Losses:   {wins} / {losses}")
    print(f"Win rate:        {win_rate:.1f}%")

    # Total P&L
    total_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in closed_picks)
    total_dollar = sum(float(p.get("pnl_dollar", 0) or 0) for p in closed_picks)
    print(f"Total P&L:       {total_pnl:.4%} (${total_dollar:,.2f})")

    # Recent wins
    if recent:
        print(f"\n--- Recent closures (last 24h): {len(recent)} ---")
        for p in recent:
            symbol = p.get("symbol", p.get("pair", "?"))
            status = p.get("status", "?")
            pnl = float(p.get("pnl_pct", 0) or 0)
            reason = p.get("exit_reason", "?")
            emoji = "W" if status == "WON" else "L"
            print(f"  [{emoji}] {symbol}: {pnl:+.4%} ({reason})")
    else:
        print("\nNo closures in the last 24 hours.")

    # Strategy performance summary
    if perf:
        strategies = perf if isinstance(perf, dict) else {}
        if strategies:
            print(f"\n--- Strategy Performance ({len(strategies)} strategies) ---")
            top = sorted(
                [(k, v) for k, v in strategies.items() if isinstance(v, dict)],
                key=lambda x: x[1].get("win_rate", 0),
                reverse=True,
            )[:10]
            for name, stats in top:
                wr = stats.get("win_rate", 0)
                total = stats.get("total_trades", stats.get("wins", 0) + stats.get("losses", 0))
                sharpe = stats.get("sharpe_ratio", 0)
                if total > 0:
                    print(f"  {name}: {wr:.1f}% WR ({total} trades, Sharpe {sharpe:.2f})")

    print("\n" + "=" * 60)
    print("Monitor complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
