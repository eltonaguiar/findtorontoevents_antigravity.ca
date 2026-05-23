#!/usr/bin/env python3
"""
EMERGENCY TRIAGE SCRIPT - CLEAN & FIXED
Stops the bleed by disabling 9 losing strategies
Uses your real Alpha Engine forward data
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configuration
CLOSED_PICKS_FILE = Path("alpha_engine/data/closed_picks.json")
STRATEGY_PERF_FILE = Path("alpha_engine/data/strategy_performance.json")
DISABLED_FILE = Path("stabilization/disabled_strategies.json")
BACKUP_DIR = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")

# Your 9 losers to disable
LOSERS_TO_DISABLE = [
    "double_top_bottom_detector",
    "halloween_effect", 
    "monthly_seasonality",
    "fourier_cycle_detector",
    "smart_money_fvg",
    "m2_liquidity_lag",
    "price_touch_recurrence",
    "cross_sectional_momentum",
    "community_ict_fvg_selective"
]


def load_closed_picks():
    """Load actual forward trades from Alpha Engine"""
    if not CLOSED_PICKS_FILE.exists():
        print(f"[ERROR] File not found: {CLOSED_PICKS_FILE}")
        return []
    
    with open(CLOSED_PICKS_FILE, 'r') as f:
        return json.load(f)


def load_disabled():
    """Load currently disabled strategies"""
    if DISABLED_FILE.exists():
        with open(DISABLED_FILE, 'r') as f:
            return json.load(f)
    return {"disabled": [], "disabled_at": None, "reason": {}}


def save_disabled(disabled_data):
    """Save disabled strategies list"""
    DISABLED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DISABLED_FILE, 'w') as f:
        json.dump(disabled_data, f, indent=2)


def analyze_performance(picks):
    """Analyze strategy performance from closed picks"""
    strategy_stats = defaultdict(lambda: {
        "trades": 0, "wins": 0, "losses": 0, "net_pnl": 0.0, "pnl_list": []
    })
    
    for pick in picks:
        strategy = pick.get("strategy", "unknown")
        pnl = pick.get("pnl_pct") or pick.get("pnl", 0)
        
        stats = strategy_stats[strategy]
        stats["trades"] += 1
        stats["net_pnl"] += pnl
        stats["pnl_list"].append(pnl)
        
        if pnl > 0:
            stats["wins"] += 1
        else:
            stats["losses"] += 1
    
    # Calculate win rates
    for stats in strategy_stats.values():
        if stats["trades"] > 0:
            stats["win_rate"] = (stats["wins"] / stats["trades"]) * 100
        else:
            stats["win_rate"] = 0.0
    
    return strategy_stats


def display_report(stats):
    """Display performance report"""
    print("\n" + "=" * 80)
    print("STRATEGY PERFORMANCE REPORT (Alpha Engine Forward Data)")
    print("=" * 80)
    print(f"{'Strategy':<35} {'Trades':>6} {'Win%':>8} {'Net PnL%':>12} {'Status':>12}")
    print("-" * 80)
    
    # Sort by net PnL (worst first)
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["net_pnl"])
    
    total_pnl = 0
    total_trades = 0
    
    for strategy, s in sorted_stats:
        total_pnl += s["net_pnl"]
        total_trades += s["trades"]
        
        status = "ACTIVE"
        if strategy in LOSERS_TO_DISABLE:
            status = "[DISABLE]"
        elif s["win_rate"] < 42 and s["trades"] >= 5:
            status = "[WATCH]"
        elif s["net_pnl"] > 0:
            status = "[PROFIT]"
        
        print(f"{strategy:<35} {s['trades']:>6} {s['win_rate']:>7.1f}% "
              f"{s['net_pnl']:>+11.2f}% {status:>12}")
    
    print("-" * 80)
    print(f"{'TOTAL':<35} {total_trades:>6} {'':>8} {total_pnl:>+11.2f}%")
    print("=" * 80)


def execute_triage(stats, dry_run=True):
    """Execute the triage - disable losing strategies"""
    print("\n[!] EMERGENCY TRIAGE EXECUTION")
    
    # Create backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if CLOSED_PICKS_FILE.exists():
        shutil.copy(CLOSED_PICKS_FILE, BACKUP_DIR / "closed_picks_backup.json")
    if STRATEGY_PERF_FILE.exists():
        shutil.copy(STRATEGY_PERF_FILE, BACKUP_DIR / "strategy_performance_backup.json")
    print(f"[OK] Backup created: {BACKUP_DIR}")
    
    disabled_data = load_disabled()
    already_disabled = set(disabled_data.get("disabled", []))
    
    to_disable = [s for s in LOSERS_TO_DISABLE if s not in already_disabled]
    
    if not to_disable:
        print("[OK] All 9 losers are already disabled")
        return
    
    print(f"\n[!] STRATEGIES TO DISABLE: {len(to_disable)}")
    for s in to_disable:
        stats_s = stats.get(s, {})
        trades = stats_s.get("trades", 0)
        pnl = stats_s.get("net_pnl", 0)
        print(f"   [X] {s} ({trades} trades, {pnl:+.2f}%)")
    
    total_loss = sum(stats.get(s, {}).get("net_pnl", 0) for s in to_disable)
    print(f"\n[$] Estimated monthly savings: ~${abs(total_loss):.0f}")
    
    if dry_run:
        print("\n[DRY RUN] No changes made. Run with --execute to disable.")
        return
    
    # Execute disable
    disabled_data["disabled"].extend(to_disable)
    disabled_data["disabled_at"] = datetime.now().isoformat()
    disabled_data["reason"] = {s: "Negative expectancy in forward testing" for s in to_disable}
    save_disabled(disabled_data)
    
    print(f"\n[OK] DISABLED {len(to_disable)} strategies")
    print(f"   Saved to: {DISABLED_FILE}")


def main():
    print("=" * 80)
    print("EMERGENCY TRIAGE - ALPHA ENGINE CAPITAL PROTECTION")
    print("=" * 80)
    print(f"Date: {datetime.now()}")
    print(f"Data source: {CLOSED_PICKS_FILE}\n")
    
    picks = load_closed_picks()
    if not picks:
        print("[ERROR] No closed picks data found")
        return
    
    print(f"Loaded {len(picks)} closed trades\n")
    
    stats = analyze_performance(picks)
    display_report(stats)
    
    dry_run = "--execute" not in [arg.lower() for arg in sys.argv]
    execute_triage(stats, dry_run=dry_run)


if __name__ == "__main__":
    main()
