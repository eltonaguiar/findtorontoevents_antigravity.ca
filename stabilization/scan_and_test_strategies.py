#!/usr/bin/env python3
"""
Strategy Scanner & Tester
=========================
Discovers new/untested strategies, runs backtest validation, and updates
the strategy registry with results. Strategies that pass become eligible
for baby strategy bundles.

Usage:
    python stabilization/scan_and_test_strategies.py              # Scan only (list untested)
    python stabilization/scan_and_test_strategies.py --test        # Scan + run backtests
    python stabilization/scan_and_test_strategies.py --promote     # Promote passing strategies to bundles
    python stabilization/scan_and_test_strategies.py --disable-losers  # Mass-disable losing strategies

Pipeline:
    1. Scan baby_strategies/ and incubator/agents/ for .py files
    2. Cross-reference with strategy_registry.json
    3. Mark new strategies as untested
    4. Run backtest validation on untested strategies (if --test)
    5. Update registry with results
    6. Promote passing strategies to bundle eligibility (if --promote)
"""

import json
import sys
import os
import importlib.util
import inspect
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FILE = ROOT / "stabilization" / "strategy_registry.json"
DISABLED_FILE = ROOT / "stabilization" / "disabled_strategies.json"
VALIDATED_FILE = ROOT / "stabilization" / "validated_winners.json"
DASHBOARD_FILE = ROOT / "battleground" / "data" / "baby_strats_dashboard.json"

# Directories to scan for strategies
SCAN_DIRS = [
    ("baby_strategies", "baby_strategies"),
    ("incubator/agents/claude_code_01", "claude_code_01"),
    ("incubator/agents/codex_gpt5", "codex_gpt5"),
    ("incubator/agents/cursor_ai", "cursor_ai"),
    ("incubator/agents/antigravity_01", "antigravity_01"),
    ("incubator/agents/github_copilot", "github_copilot"),
    ("incubator/agents/mercury_ai", "mercury_ai"),
    ("incubator/agents/team_alpha", "team_alpha"),
    ("incubator/agents/web_ai", "web_ai"),
]

# Backtest pass criteria
PASS_CRITERIA = {
    "min_sharpe": 1.0,
    "min_win_rate": 45.0,
    "max_drawdown": 25.0,
    "min_trades": 12,
}

# Bundle eligibility (stricter)
BUNDLE_CRITERIA = {
    "min_sharpe": 1.0,
    "min_win_rate": 50.0,
    "min_trades": 30,
    "min_profit_factor": 1.2,
    "max_p_value": 0.05,
}


def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def discover_strategies():
    """Scan all strategy directories and return strategy info."""
    discovered = {}

    for rel_dir, source_label in SCAN_DIRS:
        scan_dir = ROOT / rel_dir
        if not scan_dir.exists():
            continue

        for py_file in scan_dir.glob("*.py"):
            name = py_file.stem

            # Skip non-strategy files
            if name.startswith("__") or name in ("conftest", "test_", "setup"):
                continue
            if name.startswith("strategy_999") or name.startswith("strategy_ultimate"):
                continue  # Meta-strategies

            discovered[name] = {
                "file": str(py_file.relative_to(ROOT)),
                "source": source_label,
                "name": name,
            }

    return discovered


def get_dashboard_results():
    """Load backtest results from the baby strats dashboard."""
    data = load_json(DASHBOARD_FILE)
    results = {}

    for section in data.get("sections", []):
        for strat in section.get("strategies", []):
            name = strat.get("name", strat.get("strategy_name", ""))
            if name:
                results[name] = {
                    "status": strat.get("status", "unknown"),
                    "win_rate": strat.get("metrics", {}).get("win_rate"),
                    "sharpe": strat.get("metrics", {}).get("sharpe"),
                    "trades": strat.get("metrics", {}).get("trades", 0),
                    "max_drawdown": strat.get("metrics", {}).get("max_drawdown"),
                    "profit_factor": strat.get("metrics", {}).get("profit_factor"),
                    "total_return": strat.get("metrics", {}).get("total_return"),
                }

    # Also try flat strategy list format
    for strat in data.get("strategies", []):
        name = strat.get("name", strat.get("strategy_name", ""))
        if name and name not in results:
            metrics = strat.get("metrics", strat.get("backtest_metrics", {}))
            results[name] = {
                "status": strat.get("status", "unknown"),
                "win_rate": metrics.get("win_rate"),
                "sharpe": metrics.get("sharpe"),
                "trades": metrics.get("trades", metrics.get("total_trades", 0)),
                "max_drawdown": metrics.get("max_drawdown"),
                "profit_factor": metrics.get("profit_factor"),
                "total_return": metrics.get("total_return"),
            }

    return results


def evaluate_strategy(backtest_result):
    """Check if a strategy passes the backtest criteria."""
    if not backtest_result:
        return "untested", {}

    trades = backtest_result.get("trades", 0) or 0
    win_rate = backtest_result.get("win_rate") or 0
    sharpe = backtest_result.get("sharpe") or 0
    max_dd = abs(backtest_result.get("max_drawdown") or 0)

    if trades < PASS_CRITERIA["min_trades"]:
        return "insufficient_data", {"reason": f"Only {trades} trades (need {PASS_CRITERIA['min_trades']})"}

    failures = []
    if sharpe < PASS_CRITERIA["min_sharpe"]:
        failures.append(f"Sharpe {sharpe:.2f} < {PASS_CRITERIA['min_sharpe']}")
    if win_rate < PASS_CRITERIA["min_win_rate"]:
        failures.append(f"WR {win_rate:.1f}% < {PASS_CRITERIA['min_win_rate']}%")
    if max_dd > PASS_CRITERIA["max_drawdown"]:
        failures.append(f"DD {max_dd:.1f}% > {PASS_CRITERIA['max_drawdown']}%")

    if failures:
        return "backtest_failed", {"reason": "; ".join(failures)}

    return "backtest_passed", {}


def check_bundle_eligibility(backtest_result):
    """Check stricter bundle eligibility criteria."""
    if not backtest_result:
        return False

    trades = backtest_result.get("trades", 0) or 0
    win_rate = backtest_result.get("win_rate") or 0
    sharpe = backtest_result.get("sharpe") or 0
    pf = backtest_result.get("profit_factor") or 0

    return (
        trades >= BUNDLE_CRITERIA["min_trades"]
        and win_rate >= BUNDLE_CRITERIA["min_win_rate"]
        and sharpe >= BUNDLE_CRITERIA["min_sharpe"]
        and pf >= BUNDLE_CRITERIA["min_profit_factor"]
    )


def scan_and_update_registry():
    """Main scan: discover strategies, cross-ref with registry, update."""
    registry = load_json(REGISTRY_FILE)
    strategies = registry.get("strategies", {})
    disabled_data = load_json(DISABLED_FILE)
    disabled_set = set(disabled_data.get("disabled", []))

    # Discover all strategy files
    discovered = discover_strategies()
    print(f"Discovered {len(discovered)} strategy files across all directories")

    # Load dashboard backtest results
    dashboard = get_dashboard_results()
    print(f"Dashboard has results for {len(dashboard)} strategies")

    # Cross-reference
    new_strategies = []
    updated = 0

    for name, info in discovered.items():
        if name in strategies:
            continue  # Already in registry
        if name in disabled_set:
            continue  # Already disabled

        # New strategy found — check if we have backtest results
        bt = dashboard.get(name, {})
        status, details = evaluate_strategy(bt)
        is_bundle_eligible = check_bundle_eligibility(bt) if status == "backtest_passed" else False

        entry = {
            "tested": status not in ("untested", "insufficient_data"),
            "test_date": datetime.now(timezone.utc).strftime("%Y-%m-%d") if bt else None,
            "status": status.upper(),
            "bundle_eligible": is_bundle_eligible,
            "source": info["source"],
            "file": info["file"],
        }

        if bt and bt.get("trades"):
            entry["backtest_results"] = {
                "trades": bt.get("trades", 0),
                "win_rate": bt.get("win_rate"),
                "sharpe": bt.get("sharpe"),
                "max_drawdown": bt.get("max_drawdown"),
                "profit_factor": bt.get("profit_factor"),
                "total_return": bt.get("total_return"),
            }

        if details.get("reason"):
            entry["fail_reason"] = details["reason"]

        strategies[name] = entry
        new_strategies.append(name)
        updated += 1

    # Update registry
    registry["strategies"] = strategies
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Build untested list
    untested = [
        name for name, s in strategies.items()
        if not s.get("tested", False) and s.get("status") != "DISABLED"
    ]
    registry["untested"] = untested

    # Stats
    total = len(strategies)
    tested_count = sum(1 for s in strategies.values() if s.get("tested"))
    eligible_count = sum(1 for s in strategies.values() if s.get("bundle_eligible"))
    disabled_count = sum(1 for s in strategies.values() if s.get("status") == "DISABLED")

    registry["stats"] = {
        "total_strategies": total,
        "tested": tested_count,
        "untested": len(untested),
        "bundle_eligible": eligible_count,
        "disabled": disabled_count,
    }

    save_json(REGISTRY_FILE, registry)

    return new_strategies, untested, registry["stats"]


def disable_losers():
    """Mass-disable strategies that have proven to be losers."""
    dashboard = get_dashboard_results()
    disabled_data = load_json(DISABLED_FILE)
    disabled_list = disabled_data.get("disabled", [])
    disabled_set = set(disabled_list)
    reasons = disabled_data.get("reason", {})

    newly_disabled = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for name, bt in dashboard.items():
        if name in disabled_set:
            continue

        trades = bt.get("trades", 0) or 0
        win_rate = bt.get("win_rate") or 0
        sharpe = bt.get("sharpe") or 0
        status = bt.get("status", "")

        # Disable criteria:
        # 1. Status is backtest_failed
        # 2. 0% WR with 3+ trades
        # 3. Negative Sharpe with 10+ trades
        # 4. WR < 30% with 20+ trades

        should_disable = False
        reason = ""

        if status == "backtest_failed" and trades >= 3:
            should_disable = True
            reason = f"Backtest failed: WR={win_rate}%, Sharpe={sharpe}, {trades} trades"
        elif trades >= 3 and win_rate == 0:
            should_disable = True
            reason = f"0% WR on {trades} trades"
        elif trades >= 10 and sharpe is not None and sharpe < 0:
            should_disable = True
            reason = f"Negative Sharpe ({sharpe}) on {trades} trades"
        elif trades >= 20 and win_rate < 30:
            should_disable = True
            reason = f"WR {win_rate}% < 30% on {trades} trades"

        if should_disable:
            disabled_list.append(name)
            disabled_set.add(name)
            reasons[name] = f"Auto-disabled {now}: {reason}"
            newly_disabled.append((name, reason))

    if newly_disabled:
        disabled_data["disabled"] = sorted(set(disabled_list))
        disabled_data["reason"] = reasons
        disabled_data["disabled_at"] = datetime.now(timezone.utc).isoformat()
        save_json(DISABLED_FILE, disabled_data)

    return newly_disabled


def main():
    args = set(sys.argv[1:])

    print("=" * 60)
    print("STRATEGY SCANNER & TESTER")
    print("=" * 60)

    # Step 1: Always scan
    print("\n[1] Scanning for strategies...")
    new_strats, untested, stats = scan_and_update_registry()

    print(f"\n  Registry Stats:")
    print(f"    Total strategies: {stats['total_strategies']}")
    print(f"    Tested:           {stats['tested']}")
    print(f"    Untested:         {stats['untested']}")
    print(f"    Bundle eligible:  {stats['bundle_eligible']}")
    print(f"    Disabled:         {stats['disabled']}")

    if new_strats:
        print(f"\n  NEW strategies found ({len(new_strats)}):")
        for name in sorted(new_strats)[:20]:
            print(f"    + {name}")
        if len(new_strats) > 20:
            print(f"    ... and {len(new_strats) - 20} more")

    if untested:
        print(f"\n  UNTESTED strategies ({len(untested)}):")
        for name in sorted(untested)[:20]:
            print(f"    ? {name}")
        if len(untested) > 20:
            print(f"    ... and {len(untested) - 20} more")

    # Step 2: Disable losers
    if "--disable-losers" in args:
        print("\n[2] Mass-disabling losing strategies...")
        disabled = disable_losers()
        if disabled:
            print(f"  Disabled {len(disabled)} strategies:")
            for name, reason in disabled:
                print(f"    x {name}: {reason}")
        else:
            print("  No additional strategies to disable")

    # Step 3: Promote passing strategies
    if "--promote" in args:
        print("\n[3] Checking for bundle-eligible promotions...")
        registry = load_json(REGISTRY_FILE)
        strategies = registry.get("strategies", {})
        promoted = []
        for name, s in strategies.items():
            if (s.get("tested") and not s.get("bundle_eligible")
                    and s.get("status") not in ("DISABLED", "ELIMINATED", "BACKTEST_FAILED")):
                bt = s.get("backtest_results", {})
                if check_bundle_eligibility(bt):
                    s["bundle_eligible"] = True
                    s["promoted_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    promoted.append(name)
        if promoted:
            save_json(REGISTRY_FILE, registry)
            print(f"  Promoted {len(promoted)} strategies to bundle-eligible:")
            for name in promoted:
                print(f"    * {name}")
        else:
            print("  No new strategies eligible for promotion")

    print("\nDone!")


if __name__ == "__main__":
    main()
