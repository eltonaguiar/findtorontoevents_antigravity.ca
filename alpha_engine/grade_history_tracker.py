#!/usr/bin/env python3
"""
Grade History Tracker -- builds comprehensive P&L history organized by grade,
strategy, symbol, asset class, and daily calendar.

Reads: alpha_engine/data/closed_picks.json, alpha_engine/data/active_picks.json
Writes: alpha_engine/data/grade_history.json
"""

import json
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

GRADE_ORDER = ["S", "A", "B", "C", "D", "F", "N/A"]

# Map raw category values to normalized asset classes
ASSET_CLASS_MAP = {
    "crypto": "crypto",
    "meme": "crypto",
    "on-chain": "crypto",
    "forex": "forex",
    "stock": "equity",
    "etf": "equity",
    "futures": "equity",
    "penny": "equity",
}


def load_json(path: Path) -> list:
    if not path.exists():
        print(f"[WARN] {path} not found, skipping")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_asset(category: str) -> str:
    return ASSET_CLASS_MAP.get(category, "crypto")


def pick_date(pick: dict) -> str:
    """Extract the date string from a pick (exit_date for closed, entry_date for active)."""
    return pick.get("exit_date") or pick.get("entry_date") or "unknown"


def is_win(pick: dict) -> bool:
    return pick.get("status") == "WON"


def is_loss(pick: dict) -> bool:
    return pick.get("status") == "LOST"


def pnl_pct(pick: dict) -> float:
    """Get P&L percentage. For closed picks use pnl_pct, for open use unrealized."""
    val = pick.get("pnl_pct")
    if val is not None:
        return float(val)
    val = pick.get("unrealized_pnl_pct")
    if val is not None:
        return float(val)
    return 0.0


def pnl_dollar(pick: dict) -> float:
    val = pick.get("pnl_dollar")
    if val is not None:
        return float(val)
    return 0.0


def build_summary(picks: list) -> dict:
    """Build stats summary for a group of picks."""
    total = len(picks)
    if total == 0:
        return {
            "total": 0, "wins": 0, "losses": 0, "expired": 0,
            "wr": 0, "avg_pnl": 0, "total_pnl": 0,
            "best_trade": 0, "worst_trade": 0,
        }
    wins = sum(1 for p in picks if is_win(p))
    losses = sum(1 for p in picks if is_loss(p))
    expired = sum(1 for p in picks if p.get("status") == "EXPIRED")
    decided = wins + losses
    wr = round(wins / decided * 100, 1) if decided > 0 else 0

    pnls = [pnl_pct(p) for p in picks]
    avg_pnl = round(sum(pnls) / len(pnls) * 100, 2) if pnls else 0
    total_pnl = round(sum(pnls) * 100, 2)
    best = round(max(pnls) * 100, 2) if pnls else 0
    worst = round(min(pnls) * 100, 2) if pnls else 0

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "expired": expired,
        "wr": wr,
        "avg_pnl": avg_pnl,
        "total_pnl": total_pnl,
        "best_trade": best,
        "worst_trade": worst,
    }


def pick_summary(pick: dict) -> dict:
    """Compact representation of a pick for the JSON output."""
    return {
        "id": pick.get("id", ""),
        "symbol": pick.get("symbol", ""),
        "strategy": pick.get("strategy", ""),
        "direction": pick.get("direction", ""),
        "status": pick.get("status", ""),
        "pnl_pct": round(pnl_pct(pick) * 100, 2),
        "entry_date": pick.get("entry_date", ""),
        "exit_date": pick.get("exit_date", ""),
        "elite_score": pick.get("elite_score"),
        "elite_grade": pick.get("elite_grade", "N/A"),
        "category": pick.get("category", ""),
        "asset_class": classify_asset(pick.get("category", "")),
    }


def main():
    closed_path = DATA_DIR / "closed_picks.json"
    active_path = DATA_DIR / "active_picks.json"

    closed = load_json(closed_path)
    active = load_json(active_path)

    print(f"Loaded {len(closed)} closed picks, {len(active)} active picks")

    # Only use closed picks for P&L stats (they have final outcomes)
    all_picks = closed

    # --- By Grade ---
    by_grade = defaultdict(list)
    for p in all_picks:
        grade = p.get("elite_grade", "N/A") or "N/A"
        by_grade[grade].append(p)

    grade_result = {}
    for g in GRADE_ORDER:
        picks = by_grade.get(g, [])
        summary = build_summary(picks)
        summary["picks"] = [pick_summary(p) for p in picks]
        grade_result[g] = summary

    # --- By Strategy ---
    by_strategy = defaultdict(list)
    for p in all_picks:
        by_strategy[p.get("strategy", "unknown")].append(p)

    strategy_result = {}
    for name, picks in sorted(by_strategy.items()):
        summary = build_summary(picks)
        # Also track grade distribution per strategy
        grade_dist = defaultdict(int)
        for p in picks:
            grade_dist[p.get("elite_grade", "N/A") or "N/A"] += 1
        summary["grade_distribution"] = dict(grade_dist)
        strategy_result[name] = summary

    # --- By Symbol ---
    by_symbol = defaultdict(list)
    for p in all_picks:
        by_symbol[p.get("symbol", "unknown")].append(p)

    symbol_result = {}
    for sym, picks in sorted(by_symbol.items()):
        symbol_result[sym] = build_summary(picks)

    # --- By Asset Class ---
    by_asset = defaultdict(list)
    for p in all_picks:
        ac = classify_asset(p.get("category", ""))
        by_asset[ac].append(p)

    asset_result = {}
    for ac in ["crypto", "forex", "equity"]:
        picks = by_asset.get(ac, [])
        summary = build_summary(picks)
        # Grade distribution within asset class
        grade_dist = defaultdict(int)
        for p in picks:
            grade_dist[p.get("elite_grade", "N/A") or "N/A"] += 1
        summary["grade_distribution"] = dict(grade_dist)
        asset_result[ac] = summary

    # --- Daily Calendar ---
    by_day = defaultdict(list)
    for p in all_picks:
        day = pick_date(p)
        if day and day != "unknown":
            by_day[day].append(p)

    daily_calendar = {}
    for day in sorted(by_day.keys()):
        picks = by_day[day]
        day_grade = defaultdict(list)
        for p in picks:
            grade = p.get("elite_grade", "N/A") or "N/A"
            day_grade[grade].append(p)

        grade_day_stats = {}
        for g, gp in day_grade.items():
            wins = sum(1 for x in gp if is_win(x))
            losses = sum(1 for x in gp if is_loss(x))
            pnl = round(sum(pnl_pct(x) for x in gp) * 100, 2)
            grade_day_stats[g] = {"wins": wins, "losses": losses, "pnl": pnl, "total": len(gp)}

        total_pnl = round(sum(pnl_pct(x) for x in picks) * 100, 2)
        total_wins = sum(1 for x in picks if is_win(x))
        total_losses = sum(1 for x in picks if is_loss(x))

        daily_calendar[day] = {
            "by_grade": grade_day_stats,
            "total_pnl": total_pnl,
            "total_picks": len(picks),
            "wins": total_wins,
            "losses": total_losses,
        }

    # --- Active picks summary (for reference, not in P&L stats) ---
    active_summary = defaultdict(list)
    for p in active:
        grade = p.get("elite_grade", "N/A") or "N/A"
        active_summary[grade].append(pick_summary(p))

    active_by_grade = {}
    for g in GRADE_ORDER:
        picks_list = active_summary.get(g, [])
        active_by_grade[g] = {
            "total": len(picks_list),
            "unrealized_pnl": round(sum(p["pnl_pct"] for p in picks_list), 2),
            "picks": picks_list,
        }

    # --- Assemble output ---
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_closed": len(closed),
            "total_active": len(active),
            "graded_closed": sum(1 for p in closed if p.get("elite_grade")),
            "ungraded_closed": sum(1 for p in closed if not p.get("elite_grade")),
        },
        "by_grade": grade_result,
        "by_strategy": strategy_result,
        "by_symbol": symbol_result,
        "by_asset_class": asset_result,
        "daily_calendar": daily_calendar,
        "active_by_grade": active_by_grade,
    }

    out_path = DATA_DIR / "grade_history.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nGrade History saved to {out_path}")
    print(f"  Closed picks: {len(closed)} ({sum(1 for p in closed if p.get('elite_grade'))} graded)")
    print(f"  Active picks: {len(active)}")
    print(f"  Strategies: {len(strategy_result)}")
    print(f"  Symbols: {len(symbol_result)}")
    print(f"  Days: {len(daily_calendar)}")
    print("\n  Grade breakdown (closed):")
    for g in GRADE_ORDER:
        info = grade_result[g]
        if info["total"] > 0:
            print(f"    {g}: {info['total']} picks, WR {info['wr']}%, total P&L {info['total_pnl']:+.1f}%")


if __name__ == "__main__":
    main()
