#!/usr/bin/env python3
"""
Symbol Unblock Monitor — 2026-05-16

Monitors blocked symbols for recovery signals. When a blocked symbol meets
the unblock criteria, it flags it for review.

Usage:
    python tools/symbol_unblock_monitor.py [--shadow] [--dry-run]

Shadow mode: Tags picks as shadow_unblock_candidate instead of blocking.
Dry-run: Prints what would be done without modifying any files.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
CLOSED_PICKS_PATH = ROOT / "alpha_engine" / "data" / "closed_picks.json"
ACTIVE_PICKS_PATH = ROOT / "alpha_engine" / "data" / "active_picks.json"
UNBLOCK_REPORT_PATH = ROOT / "reports" / "symbol_unblock_status.json"

# ── Blocked symbol tiers ──────────────────────────────────────────────
# Tier 1: Hard blocks — NEVER unblock (structural/data quality issues)
HARD_BLOCKS = frozenset({
    "MATICUSDT",   # Delisted, phantom TIME_EXIT trades — 0% WR across 1,057 trades
    "UUSDT",       # Broken symbol — 0% WR across 34 trades
    "XMR",         # Most destructive symbol — -115% PnL
    "XMRUSDT",     # Alias for XMR
    "KATUSDT",     # Token redenomination — entry price jumped 13x
    "TRXUSDT",     # -10,064% PnL (103% of ALL negative crypto PnL)
})

# Tier 2: Conditional blocks — unblock if criteria met
CONDITIONAL_BLOCKS = {
    "KASUSDT":    {"min_trades": 100, "min_wr": 45.0, "min_pf": 1.0, "window_days": 30},
    "ICPUSDT":    {"min_trades": 100, "min_wr": 40.0, "min_pf": 1.0, "window_days": 30},
    "XLMUSDT":    {"min_trades": 100, "min_wr": 40.0, "min_pf": 1.0, "window_days": 30},
    "JTOUSDT":    {"min_trades": 50,  "min_wr": 45.0, "min_pf": 1.0, "window_days": 30},
    "RENDERUSDT": {"min_trades": 100, "min_wr": 45.0, "min_pf": 1.0, "window_days": 30},
    "ENAUSDT":    {"min_trades": 20,  "min_wr": 50.0, "min_pf": 1.0, "window_days": 30},
    "IMXUSDT":    {"min_trades": 20,  "min_wr": 50.0, "min_pf": 1.0, "window_days": 30},
}

# Tier 3: Equity blocks — review quarterly (14d shadow period)
EQUITY_BLOCKS = {
    "ADBE": {"min_trades": 14, "min_wr": 40.0, "window_days": 14},
    "CRM":  {"min_trades": 14, "min_wr": 40.0, "window_days": 14},
    "ACN":  {"min_trades": 14, "min_wr": 40.0, "window_days": 14},
    "MSFT": {"min_trades": 14, "min_wr": 45.0, "window_days": 14},
    "PLTR": {"min_trades": 14, "min_wr": 40.0, "window_days": 14},
    "TSLA": {"min_trades": 14, "min_wr": 45.0, "window_days": 14},
    "NVDA": {"min_trades": 14, "min_wr": 45.0, "window_days": 14},
    "NKE":  {"min_trades": 14, "min_wr": 40.0, "window_days": 14},
    "PG":   {"min_trades": 14, "min_wr": 40.0, "window_days": 14},
    "HD":   {"min_trades": 14, "min_wr": 40.0, "window_days": 14},
}


def load_closed_picks() -> list[dict]:
    """Load closed picks from JSON file."""
    if not CLOSED_PICKS_PATH.exists():
        print(f"[WARN] {CLOSED_PICKS_PATH} not found")
        return []
    with open(CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_symbol_performance(
    picks: list[dict],
    symbols: set[str],
    window_days: int = 30,
) -> dict[str, dict]:
    """Analyze performance for specific symbols over a time window."""
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - (window_days * 86400)

    results = {}
    for symbol in symbols:
        sym_picks = [
            p for p in picks
            if p.get("symbol", "").upper() == symbol.upper()
        ]

        # Filter by time window (use closed_at or resolved_at)
        window_picks = []
        for p in sym_picks:
            closed_at = p.get("closed_at") or p.get("resolved_at") or ""
            if closed_at:
                try:
                    # Handle various timestamp formats
                    ts_str = closed_at.replace("Z", "+00:00")
                    if "+" not in ts_str and ts_str.count("-") <= 2:
                        ts_str += "+00:00"
                    ts = datetime.fromisoformat(ts_str).timestamp()
                    if ts >= cutoff:
                        window_picks.append(p)
                except (ValueError, TypeError):
                    pass

        if not window_picks:
            # Fall back to all picks if no window data
            window_picks = sym_picks

        wins = sum(1 for p in window_picks if float(p.get("pnl_pct", 0) or 0) > 0)
        losses = sum(1 for p in window_picks if float(p.get("pnl_pct", 0) or 0) <= 0)
        total = wins + losses
        pnl_sum = sum(float(p.get("pnl_pct", 0) or 0) for p in window_picks)

        win_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in window_picks if float(p.get("pnl_pct", 0) or 0) > 0)
        loss_pnl = abs(sum(float(p.get("pnl_pct", 0) or 0) for p in window_picks if float(p.get("pnl_pct", 0) or 0) <= 0))
        pf = win_pnl / loss_pnl if loss_pnl > 0 else (float("inf") if win_pnl > 0 else 0)

        results[symbol] = {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "total_pnl": round(pnl_sum, 2),
            "profit_factor": round(pf, 2),
            "avg_pnl": round(pnl_sum / total, 2) if total > 0 else 0,
            "window_days": window_days,
        }

    return results


def check_unblock_criteria(
    performance: dict[str, dict],
    criteria: dict[str, dict],
) -> dict[str, dict]:
    """Check which symbols meet unblock criteria."""
    candidates = {}
    for symbol, crit in criteria.items():
        perf = performance.get(symbol, {})
        if not perf:
            continue

        meets_trades = perf["total_trades"] >= crit["min_trades"]
        meets_wr = perf["win_rate"] >= crit["min_wr"]
        meets_pf = perf["profit_factor"] >= crit.get("min_pf", 1.0)

        status = "PASS" if (meets_trades and meets_wr and meets_pf) else "FAIL"

        candidates[symbol] = {
            "status": status,
            "criteria": crit,
            "performance": perf,
            "meets_trades": meets_trades,
            "meets_wr": meets_wr,
            "meets_pf": meets_pf,
        }

    return candidates


def main():
    dry_run = "--dry-run" in sys.argv
    shadow_mode = "--shadow" in sys.argv

    print("=" * 60)
    print("Symbol Unblock Monitor — 2026-05-16")
    print("=" * 60)

    # Load data
    picks = load_closed_picks()
    print(f"Loaded {len(picks)} closed picks")

    # Analyze conditional blocks
    all_conditional = set(CONDITIONAL_BLOCKS.keys()) | set(EQUITY_BLOCKS.keys())
    performance = analyze_symbol_performance(picks, all_conditional, window_days=30)

    # Check unblock criteria
    cond_results = check_unblock_criteria(performance, CONDITIONAL_BLOCKS)
    equity_results = check_unblock_criteria(performance, EQUITY_BLOCKS)

    # Print results
    print("\n--- CONDITIONAL BLOCKS (Crypto) ---")
    for symbol, result in sorted(cond_results.items()):
        perf = result["performance"]
        crit = result["criteria"]
        status = result["status"]
        icon = "✅" if status == "PASS" else "❌"
        print(
            f"  {icon} {symbol}: WR={perf['win_rate']}% PF={perf['profit_factor']} "
            f"n={perf['total_trades']} pnl={perf['total_pnl']} "
            f"(need WR≥{crit['min_wr']}% PF≥{crit['min_pf']} n≥{crit['min_trades']})"
        )

    print("\n--- EQUITY BLOCKS (14d shadow) ---")
    for symbol, result in sorted(equity_results.items()):
        perf = result["performance"]
        crit = result["criteria"]
        status = result["status"]
        icon = "✅" if status == "PASS" else "❌"
        print(
            f"  {icon} {symbol}: WR={perf['win_rate']}% PF={perf['profit_factor']} "
            f"n={perf['total_trades']} pnl={perf['total_pnl']} "
            f"(need WR≥{crit['min_wr']}% n≥{crit['min_trades']})"
        )

    print("\n--- HARD BLOCKS (NEVER unblock) ---")
    for symbol in sorted(HARD_BLOCKS):
        perf = performance.get(symbol, {})
        if perf:
            print(
                f"  🔒 {symbol}: WR={perf.get('win_rate', 'N/A')}% "
                f"n={perf.get('total_trades', 0)} pnl={perf.get('total_pnl', 'N/A')}"
            )
        else:
            print(f"  🔒 {symbol}: No recent data")

    # Save report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hard_blocks": sorted(HARD_BLOCKS),
        "conditional_blocks": {
            k: {
                "status": v["status"],
                "performance": v["performance"],
                "criteria": v["criteria"],
            }
            for k, v in cond_results.items()
        },
        "equity_blocks": {
            k: {
                "status": v["status"],
                "performance": v["performance"],
                "criteria": v["criteria"],
            }
            for k, v in equity_results.items()
        },
    }

    if not dry_run:
        UNBLOCK_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(UNBLOCK_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {UNBLOCK_REPORT_PATH}")
    else:
        print("\n[Dry run] Report not saved")

    # Summary
    pass_count = sum(1 for v in cond_results.values() if v["status"] == "PASS")
    pass_count += sum(1 for v in equity_results.values() if v["status"] == "PASS")
    if pass_count:
        print(f"\n⚠️  {pass_count} symbol(s) meet unblock criteria — review recommended")
    else:
        print("\n✅ No symbols meet unblock criteria at this time")


if __name__ == "__main__":
    main()
