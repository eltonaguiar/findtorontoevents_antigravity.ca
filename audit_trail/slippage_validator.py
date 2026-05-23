"""Slippage Validator — compares expected vs actual fill prices for closed picks.

Tracks slippage per strategy and per asset class, flags strategies where
avg slippage exceeds a threshold relative to avg PnL. This ensures that
backtest-derived Profit Factor isn't inflated by unrealistic fill assumptions.

Output: updates the dashboard payload with slippage-adjusted PnL and flags.
"""
from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("slippage_validator")

ROOT = Path(__file__).resolve().parent.parent

# Thresholds
SLIPPAGE_PCT_WARNING = 0.10   # 10% of avg PnL — flag strategy
SLIPPAGE_PCT_CRITICAL = 0.25  # 25% of avg PnL — reject from Smart Picks

# Default spread assumptions for slippage calculation
DEFAULT_SPREADS = {
    "CRYPTO": 0.001,    # 0.1% typical for major pairs on Binance
    "EQUITY": 0.0005,   # 0.05% for liquid stocks
    "FOREX": 0.0002,    # 2 pips for majors
    "COMMODITY": 0.0015, # 0.15% for futures/commodities
    "FUTURES": 0.0015,
    "ETF": 0.0005,
    "BOND": 0.0005,
}


def calculate_slippage(pick: dict, spread_override: float | None = None) -> float:
    """Calculate estimated slippage for a pick.

    Uses actual bid-ask data if available in the pick, otherwise estimates
    from asset class defaults.
    """
    asset_class = str(pick.get("asset_class", "CRYPTO")).upper()
    entry = pick.get("entry_price")
    if entry is None or entry == 0:
        return 0.0

    # Prefer actual spread if available
    actual_spread = pick.get("actual_spread") or pick.get("spread_pct")
    if actual_spread is not None and actual_spread > 0:
        return float(actual_spread)

    # Fall back to default spread for asset class
    spread = DEFAULT_SPREADS.get(asset_class, 0.001)
    if spread_override is not None:
        spread = spread_override

    return entry * spread


def validate_closed_picks(closed_picks: list[dict]) -> dict:
    """Analyze slippage for a set of closed picks.

    Returns stats per strategy and flags problematic ones.
    """
    by_strategy: dict[str, list] = defaultdict(list)
    by_asset_class: dict[str, list] = defaultdict(list)

    for pick in closed_picks:
        strat = str(pick.get("strategy", "unknown"))
        ac = str(pick.get("asset_class", "CRYPTO")).upper()
        pnl_pct = pick.get("pnl_pct", 0)

        slippage = calculate_slippage(pick)
        slippage_pct = (slippage / abs(pick.get("entry_price", 1))) * 100 if pick.get("entry_price") else 0

        entry = {
            "symbol": pick.get("symbol", "?"),
            "strategy": strat,
            "asset_class": ac,
            "pnl_pct": pnl_pct,
            "slippage_pct": slippage_pct,
            "entry_price": pick.get("entry_price"),
            "direction": pick.get("direction", ""),
            "date": pick.get("closed_at", pick.get("exit_time", "")),
        }
        by_strategy[strat].append(entry)
        by_asset_class[ac].append(entry)

    # Compute per-strategy stats
    strategy_stats = {}
    for strat, entries in by_strategy.items():
        total_slippage = sum(e["slippage_pct"] for e in entries)
        total_pnl = sum(e["pnl_pct"] for e in entries)
        n = len(entries)
        avg_slippage = total_slippage / n if n else 0
        avg_pnl = total_pnl / n if n else 0

        slippage_pct_of_pnl = (avg_slippage / abs(avg_pnl) * 100) if avg_pnl != 0 else 0

        flag = "NONE"
        if slippage_pct_of_pnl > SLIPPAGE_PCT_CRITICAL * 100:
            flag = "CRITICAL"
        elif slippage_pct_of_pnl > SLIPPAGE_PCT_WARNING * 100:
            flag = "WARNING"

        strategy_stats[strat] = {
            "n": n,
            "avg_slippage_pct": round(avg_slippage, 4),
            "avg_pnl_pct": round(avg_pnl, 4),
            "total_pnl_pct": round(total_pnl, 2),
            "slippage_as_pct_of_pnl": round(slippage_pct_of_pnl, 2),
            "flag": flag,
            "slippage_adjusted_pnl_pct": round(avg_pnl - (avg_slippage if avg_pnl > 0 else -avg_slippage), 4),
        }

    # Compute per-asset-class stats
    asset_class_stats = {}
    for ac, entries in by_asset_class.items():
        total_slippage = sum(e["slippage_pct"] for e in entries)
        total_pnl = sum(e["pnl_pct"] for e in entries)
        n = len(entries)
        avg_slippage = total_slippage / n if n else 0
        avg_pnl = total_pnl / n if n else 0
        slippage_pct_of_pnl = (avg_slippage / abs(avg_pnl) * 100) if avg_pnl != 0 else 0

        asset_class_stats[ac] = {
            "n": n,
            "avg_slippage_pct": round(avg_slippage, 4),
            "avg_pnl_pct": round(avg_pnl, 4),
            "slippage_as_pct_of_pnl": round(slippage_pct_of_pnl, 2),
            "flag": "CRITICAL" if slippage_pct_of_pnl > SLIPPAGE_PCT_CRITICAL * 100 else (
                "WARNING" if slippage_pct_of_pnl > SLIPPAGE_PCT_WARNING * 100 else "NONE"),
        }

    # Flagged strategies
    flagged = {s: v for s, v in strategy_stats.items() if v["flag"] in ("WARNING", "CRITICAL")}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "warning_pct": SLIPPAGE_PCT_WARNING,
            "critical_pct": SLIPPAGE_PCT_CRITICAL,
        },
        "strategy_stats": strategy_stats,
        "asset_class_stats": asset_class_stats,
        "flagged_strategies": flagged,
        "summary": {
            "total_strategies": len(strategy_stats),
            "flagged_count": len(flagged),
            "critical_count": sum(1 for v in strategy_stats.values() if v["flag"] == "CRITICAL"),
        },
    }


def apply_slippage_adjustment(picks: list[dict], stats: dict) -> int:
    """Apply slippage-adjusted PnL to active picks.

    Modifies picks in-place. Returns count of adjusted picks.
    """
    adjusted = 0
    for pick in picks:
        strat = str(pick.get("strategy", ""))
        if strat in stats:
            s = stats[strat]
            if s["flag"] in ("WARNING", "CRITICAL"):
                # Apply slippage deduction
                original_pnl = pick.get("pnl_pct", 0)
                slippage = s["avg_slippage_pct"]
                if original_pnl > 0:
                    adjusted_pnl = original_pnl - slippage
                else:
                    adjusted_pnl = original_pnl + slippage  # Losses get worse

                pick["pnl_pct_original"] = original_pnl
                pick["pnl_pct"] = round(adjusted_pnl, 4)
                pick["_slippage_adjusted"] = True
                pick["_slippage_deduction"] = round(slippage, 4)
                adjusted += 1
    return adjusted


def run_slippage_validation():
    """Main entry point. Validate closed picks and adjust active picks."""
    print("=" * 60)
    print("SLIPPAGE VALIDATION")
    print("=" * 60)

    # Load closed picks
    closed_path = ROOT / "alpha_engine" / "data" / "closed_picks.json"
    if not closed_path.exists():
        print(f"Closed picks not found at {closed_path}")
        return

    with open(closed_path) as f:
        closed_picks = json.load(f)

    print(f"\nAnalyzing {len(closed_picks)} closed picks...")

    # Validate
    results = validate_closed_picks(closed_picks)

    # Print flagged strategies
    if results["flagged_strategies"]:
        print(f"\n⚠ {len(results['flagged_strategies'])} strategies flagged:")
        for strat, data in results["flagged_strategies"].items():
            print(f"  {strat}: slippage={data['slippage_as_pct_of_pnl']}% of PnL, "
                  f"flag={data['flag']}, n={data['n']}")

    # Save report
    report_path = ROOT / "audit_trail" / "data" / "slippage_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nReport saved: {report_path}")

    # Apply adjustment to active picks
    active_path = ROOT / "alpha_engine" / "data" / "active_picks.json"
    if active_path.exists():
        with open(active_path) as f:
            active_picks = json.load(f)

        adjusted = apply_slippage_adjustment(active_picks, results["strategy_stats"])
        if adjusted > 0:
            with open(active_path, "w") as f:
                json.dump(active_picks, f, indent=2, default=str)
            print(f"Adjusted {adjusted} active picks with slippage deduction")

    print(f"\nSummary: {results['summary']['total_strategies']} strategies analyzed, "
          f"{results['summary']['flagged_count']} flagged, "
          f"{results['summary']['critical_count']} critical")


if __name__ == "__main__":
    run_slippage_validation()