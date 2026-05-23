#!/usr/bin/env python3
"""Test Portfolio Tracker -- Multi-Tier Strategy Graduation Pipeline.

Monitors strategies as they progress through 4 validation tiers:

  SANDBOX    -> <10 trades          (virtual $1,000, max 5% per trade)
  INCUBATOR  -> 10+ trades, WR>45%  (virtual $5,000, max 3% per trade)
  VALIDATED  -> p-value < 0.05      (virtual $10,000, max 2% per trade)
  PRODUCTION -> p<0.01 and 50+ trades (real allocation eligible)

Reads walkforward_results.json for strategy validation metrics and
active/closed picks for PnL tracking.  Outputs a JSON report to
alpha_engine/data/test_portfolio_status.json.

Usage:
    PYTHONPATH=. python -m alpha_engine.test_portfolio_tracker
"""
from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------
TIERS = {
    "SANDBOX": {
        "virtual_capital": 1_000.0,
        "max_risk_pct": 5.0,
        "description": "Strategies with <10 trades -- early testing phase",
    },
    "INCUBATOR": {
        "virtual_capital": 5_000.0,
        "max_risk_pct": 3.0,
        "description": "10+ trades and WR>45% -- building track record",
    },
    "VALIDATED": {
        "virtual_capital": 10_000.0,
        "max_risk_pct": 2.0,
        "description": "Statistically significant (p<0.05) -- paper trading",
    },
    "PRODUCTION": {
        "virtual_capital": 0.0,  # real allocation -- not virtual
        "max_risk_pct": 1.5,
        "description": "p<0.01 and 50+ trades -- real money eligible",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _float(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _load_json(path: Path) -> Any:
    """Load a JSON file, returning empty dict/list on failure."""
    if not path.exists():
        log.warning("File not found: %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.warning("Failed to load %s: %s", path, exc)
        return {}


# ---------------------------------------------------------------------------
# 1. Load data sources
# ---------------------------------------------------------------------------
def load_walkforward() -> dict[str, dict]:
    """Load walkforward_results.json, return {strategy_name: metrics_dict}."""
    raw = _load_json(DATA_DIR / "walkforward_results.json")
    strategies = raw.get("strategies", [])
    return {s["strategy"]: s for s in strategies if "strategy" in s}


def load_active_picks() -> list[dict]:
    """Load active picks from the fast file."""
    data = _load_json(DATA_DIR / "active_picks.json")
    if isinstance(data, list):
        return data
    # Some versions wrap in a dict
    return data.get("picks", data.get("active", []))


def load_closed_picks() -> list[dict]:
    """Load closed picks for PnL tracking."""
    data = _load_json(DATA_DIR / "closed_picks_fast.json")
    if isinstance(data, list):
        return data
    return data.get("picks", data.get("closed", []))


# ---------------------------------------------------------------------------
# 2. Strategy tier classification
# ---------------------------------------------------------------------------
def classify_tier(wf_entry: dict | None, trade_count: int = 0) -> str:
    """Determine which tier a strategy belongs to based on validation metrics.

    Args:
        wf_entry: walkforward_results entry for the strategy (or None).
        trade_count: override trade count if wf_entry is missing.

    Returns:
        Tier name: SANDBOX, INCUBATOR, VALIDATED, or PRODUCTION.
    """
    if wf_entry is None:
        return "SANDBOX"

    trades = wf_entry.get("trades", trade_count)
    wr = _float(wf_entry.get("win_rate", 0))
    p_value = _float(wf_entry.get("p_value", 1.0))

    # PRODUCTION: p<0.01 AND 50+ trades
    if p_value < 0.01 and trades >= 50:
        return "PRODUCTION"

    # VALIDATED: p<0.05
    if p_value < 0.05:
        return "VALIDATED"

    # INCUBATOR: 10+ trades and WR>45%
    if trades >= 10 and wr > 45.0:
        return "INCUBATOR"

    # Default: SANDBOX
    return "SANDBOX"


def graduation_progress(wf_entry: dict | None) -> dict:
    """Compute progress toward next tier and what milestone is needed."""
    if wf_entry is None:
        return {
            "current_tier": "SANDBOX",
            "next_tier": "INCUBATOR",
            "next_milestone": "Need 10+ trades with WR>45%",
            "trades_progress": "0/10",
            "wr_progress": "N/A",
            "p_value_progress": "N/A",
        }

    tier = classify_tier(wf_entry)
    trades = wf_entry.get("trades", 0)
    wr = _float(wf_entry.get("win_rate", 0))
    p_value = _float(wf_entry.get("p_value", 1.0))

    if tier == "PRODUCTION":
        return {
            "current_tier": "PRODUCTION",
            "next_tier": "---",
            "next_milestone": "Fully graduated -- real allocation eligible",
            "trades_progress": f"{trades}/50 (met)",
            "wr_progress": f"{wr:.1f}%",
            "p_value_progress": f"{p_value:.4f} (met <0.01)",
        }

    if tier == "VALIDATED":
        trades_needed = max(0, 50 - trades)
        p_msg = f"{p_value:.4f}"
        if p_value >= 0.01:
            p_msg += " (need <0.01)"
        else:
            p_msg += " (met)"
        return {
            "current_tier": "VALIDATED",
            "next_tier": "PRODUCTION",
            "next_milestone": (
                f"Need p<0.01 AND 50+ trades ({trades_needed} more trades needed)"
                if trades < 50 or p_value >= 0.01
                else "Ready for promotion!"
            ),
            "trades_progress": f"{trades}/50",
            "wr_progress": f"{wr:.1f}%",
            "p_value_progress": p_msg,
        }

    if tier == "INCUBATOR":
        return {
            "current_tier": "INCUBATOR",
            "next_tier": "VALIDATED",
            "next_milestone": f"Need p-value<0.05 (currently {p_value:.4f})",
            "trades_progress": f"{trades}/10 (met)",
            "wr_progress": f"{wr:.1f}% (met >45%)" if wr > 45 else f"{wr:.1f}% (need >45%)",
            "p_value_progress": f"{p_value:.4f} (need <0.05)",
        }

    # SANDBOX
    return {
        "current_tier": "SANDBOX",
        "next_tier": "INCUBATOR",
        "next_milestone": f"Need 10+ trades (have {trades}) with WR>45% (currently {wr:.1f}%)",
        "trades_progress": f"{trades}/10",
        "wr_progress": f"{wr:.1f}%",
        "p_value_progress": f"{p_value:.4f}",
    }


# ---------------------------------------------------------------------------
# 3. Virtual PnL tracking per tier
# ---------------------------------------------------------------------------
def compute_tier_pnl(
    tier_picks: list[dict], virtual_capital: float, max_risk_pct: float
) -> dict:
    """Compute virtual PnL for a tier's assigned picks.

    Each pick gets a virtual allocation of min(max_risk_pct% of capital,
    equal split across picks).
    """
    if not tier_picks or virtual_capital <= 0:
        return {
            "total_picks": len(tier_picks),
            "open_picks": 0,
            "closed_picks": 0,
            "virtual_capital": virtual_capital,
            "allocated": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "total_pnl": 0.0,
            "total_pnl_pct": 0.0,
            "win_rate": 0.0,
            "wins": 0,
            "losses": 0,
        }

    max_per_trade = virtual_capital * (max_risk_pct / 100.0)
    open_picks = [p for p in tier_picks if p.get("status", "").upper() in ("OPEN", "ACTIVE")]
    closed_picks = [p for p in tier_picks if p.get("status", "").upper() not in ("OPEN", "ACTIVE")]

    # Open picks: unrealized PnL
    unrealized = 0.0
    allocated = 0.0
    for p in open_picks:
        alloc = min(max_per_trade, virtual_capital / max(len(open_picks), 1))
        pnl_pct = _float(p.get("unrealized_pnl_pct", 0))
        unrealized += alloc * pnl_pct
        allocated += alloc

    # Closed picks: realized PnL
    realized = 0.0
    wins = 0
    losses = 0
    for p in closed_picks:
        alloc = min(max_per_trade, virtual_capital / max(len(tier_picks), 1))
        pnl_pct = _float(p.get("pnl_pct", p.get("unrealized_pnl_pct", 0)))
        rpnl = alloc * pnl_pct
        realized += rpnl
        if rpnl > 0:
            wins += 1
        elif rpnl < 0:
            losses += 1

    total_closed = wins + losses
    wr = (wins / total_closed * 100.0) if total_closed > 0 else 0.0
    total_pnl = realized + unrealized

    return {
        "total_picks": len(tier_picks),
        "open_picks": len(open_picks),
        "closed_picks": len(closed_picks),
        "virtual_capital": round(virtual_capital, 2),
        "allocated": round(allocated, 2),
        "unrealized_pnl": round(unrealized, 4),
        "realized_pnl": round(realized, 4),
        "total_pnl": round(total_pnl, 4),
        "total_pnl_pct": round(total_pnl / virtual_capital * 100, 4) if virtual_capital else 0.0,
        "win_rate": round(wr, 1),
        "wins": wins,
        "losses": losses,
    }


# ---------------------------------------------------------------------------
# 4. Main report builder
# ---------------------------------------------------------------------------
def build_report() -> dict:
    """Build the full test portfolio status report."""
    wf_data = load_walkforward()
    active = load_active_picks()
    closed = load_closed_picks()

    # Merge all picks for assignment
    all_picks = []
    for p in active:
        pick = dict(p)
        pick["_source"] = "active"
        all_picks.append(pick)
    for p in closed:
        pick = dict(p)
        pick["_source"] = "closed"
        all_picks.append(pick)

    # Collect all known strategies (from walkforward + picks)
    all_strategy_names: set[str] = set(wf_data.keys())
    for p in all_picks:
        s = p.get("strategy")
        if s:
            all_strategy_names.add(s)

    # Count trades per strategy from closed picks
    strategy_trade_counts: dict[str, int] = defaultdict(int)
    for p in closed:
        s = p.get("strategy")
        if s:
            strategy_trade_counts[s] += 1

    # Classify each strategy
    strategy_tiers: dict[str, str] = {}
    strategy_details: dict[str, dict] = {}
    for sname in sorted(all_strategy_names):
        wf_entry = wf_data.get(sname)
        trade_count = strategy_trade_counts.get(sname, 0)
        tier = classify_tier(wf_entry, trade_count)
        strategy_tiers[sname] = tier
        progress = graduation_progress(wf_entry)

        detail = {
            "tier": tier,
            "graduation": progress,
            "wf_verdict": wf_entry.get("verdict", "N/A") if wf_entry else "NO_DATA",
            "wf_final_score": wf_entry.get("final_score", 0) if wf_entry else 0,
            "trades": wf_entry.get("trades", trade_count) if wf_entry else trade_count,
            "win_rate": wf_entry.get("win_rate", 0) if wf_entry else 0,
            "p_value": wf_entry.get("p_value", 1.0) if wf_entry else 1.0,
            "sharpe": wf_entry.get("sharpe", 0) if wf_entry else 0,
        }
        strategy_details[sname] = detail

    # Assign picks to tiers
    tier_picks: dict[str, list[dict]] = {t: [] for t in TIERS}
    for p in all_picks:
        sname = p.get("strategy", "unknown")
        tier = strategy_tiers.get(sname, "SANDBOX")
        tier_picks[tier].append(p)

    # Compute per-tier PnL
    tier_summaries: dict[str, dict] = {}
    for tier_name, tier_cfg in TIERS.items():
        picks = tier_picks[tier_name]
        pnl = compute_tier_pnl(
            picks,
            tier_cfg["virtual_capital"],
            tier_cfg["max_risk_pct"],
        )
        pnl["description"] = tier_cfg["description"]
        pnl["max_risk_pct"] = tier_cfg["max_risk_pct"]
        pnl["strategy_count"] = len(
            {p.get("strategy") for p in picks if p.get("strategy")}
        )
        tier_summaries[tier_name] = pnl

    # Summary counters
    tier_counts = defaultdict(int)
    for t in strategy_tiers.values():
        tier_counts[t] += 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_strategies_tracked": len(all_strategy_names),
            "total_picks_tracked": len(all_picks),
            "tier_distribution": dict(tier_counts),
            "strategies_with_walkforward": len(wf_data),
        },
        "tiers": tier_summaries,
        "strategies": strategy_details,
    }

    return report


# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 72)
    print("TEST PORTFOLIO TRACKER -- Strategy Graduation Pipeline")
    print("=" * 72)

    report = build_report()

    # Save
    out_path = DATA_DIR / "test_portfolio_status.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to {out_path}")

    # Print summary
    summary = report["summary"]
    print(f"\nStrategies tracked: {summary['total_strategies_tracked']}")
    print(f"Picks tracked:     {summary['total_picks_tracked']}")
    print(f"With walkforward:  {summary['strategies_with_walkforward']}")
    print(f"\nTier distribution:")
    for tier_name, count in sorted(summary["tier_distribution"].items()):
        print(f"  {tier_name:12s}: {count} strategies")

    print(f"\n{'Tier':<13s} {'Capital':>9s} {'Picks':>6s} {'Open':>5s} "
          f"{'Realized':>10s} {'Unrealized':>11s} {'WR':>6s}")
    print("-" * 72)
    for tier_name in ["SANDBOX", "INCUBATOR", "VALIDATED", "PRODUCTION"]:
        t = report["tiers"].get(tier_name, {})
        cap_str = f"${t.get('virtual_capital', 0):,.0f}" if t.get("virtual_capital") else "REAL"
        print(
            f"  {tier_name:<11s} {cap_str:>9s} {t.get('total_picks', 0):>6d} "
            f"{t.get('open_picks', 0):>5d} "
            f"${t.get('realized_pnl', 0):>+9.2f} "
            f"${t.get('unrealized_pnl', 0):>+9.2f} "
            f"{t.get('win_rate', 0):>5.1f}%"
        )

    # Show strategies closest to graduation
    print(f"\n{'='*72}")
    print("STRATEGIES CLOSEST TO GRADUATION:")
    print(f"{'='*72}")
    strats = report.get("strategies", {})
    # Sort by tier priority then by final_score descending
    tier_order = {"SANDBOX": 0, "INCUBATOR": 1, "VALIDATED": 2, "PRODUCTION": 3}
    graduating = [
        (name, info)
        for name, info in strats.items()
        if info["tier"] != "PRODUCTION"
    ]
    graduating.sort(
        key=lambda x: (tier_order.get(x[1]["tier"], 0), -x[1].get("wf_final_score", 0)),
        reverse=True,
    )

    for name, info in graduating[:15]:
        grad = info.get("graduation", {})
        print(f"  {name[:40]:<40s} [{info['tier']:>10s}] -> {grad.get('next_tier', '?')}")
        print(f"    {grad.get('next_milestone', 'N/A')}")

    print(f"\n{'='*72}")
    print("Done.")


if __name__ == "__main__":
    main()
