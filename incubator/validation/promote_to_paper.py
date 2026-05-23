#!/usr/bin/env python3
"""
Promote backtest-passed strategies to forward paper trading.
One-time script + utility for manual promotion.
"""

import json
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

INCUBATOR = Path(__file__).parent.parent
AGENTS = INCUBATOR / "agents"

# Quality thresholds for promotion
MIN_SHARPE = 1.0
MIN_WIN_RATE = 0.45
MAX_DRAWDOWN = -0.20


def load_meta(meta_file: Path) -> dict:
    """Load strategy metadata."""
    with open(meta_file) as f:
        return json.load(f)


def save_meta(meta_file: Path, meta: dict):
    """Save strategy metadata."""
    with open(meta_file, 'w') as f:
        json.dump(meta, f, indent=2)


def should_promote(meta: dict) -> tuple[bool, str]:
    """
    Check if strategy qualifies for paper trading promotion.
    Returns (should_promote, reason).
    """
    status = meta.get("status", "").lower()
    if status != "backtest_passed":
        return False, f"Status is '{status}', need 'backtest_passed'"
    
    # Already in paper trading?
    if meta.get("paper_trading", {}).get("started_at"):
        return False, "Already in paper trading"
    
    metrics = meta.get("backtest_metrics", {})
    sharpe = metrics.get("sharpe", 0) or 0
    win_rate = metrics.get("win_rate", 0) or 0
    max_dd = metrics.get("max_drawdown", 0) or 0
    
    if sharpe < MIN_SHARPE:
        return False, f"Sharpe {sharpe:.2f} < {MIN_SHARPE}"
    if win_rate < MIN_WIN_RATE:
        return False, f"Win rate {win_rate:.1%} < {MIN_WIN_RATE:.0%}"
    if max_dd < MAX_DRAWDOWN:
        return False, f"Max DD {max_dd:.1%} < {MAX_DRAWDOWN:.0%}"
    
    return True, "Qualifies"


def promote_strategy(meta_file: Path, dry_run: bool = False) -> dict:
    """
    Promote a single strategy to paper trading.
    Returns result dict with status info.
    """
    result = {
        "file": str(meta_file),
        "strategy": None,
        "agent": None,
        "promoted": False,
        "reason": None,
    }
    
    try:
        meta = load_meta(meta_file)
        result["strategy"] = meta.get("strategy_name", meta_file.stem.replace(".py", ""))
        result["agent"] = meta.get("agent_id", "unknown")
        
        should, reason = should_promote(meta)
        result["reason"] = reason
        
        if not should:
            return result
        
        if dry_run:
            result["promoted"] = True
            result["reason"] = "Would promote (dry run)"
            return result
        
        # Perform promotion
        now = datetime.now(timezone.utc)
        meta["status"] = "paper_trading"
        meta["paper_trading"] = {
            "started_at": now.isoformat(),
            "end_date": (now + timedelta(days=30)).isoformat(),
            "days_remaining": 30,
            "days_elapsed": 0,
            "trades_count": 0,
            "current_pnl": 0.0,
            "progress_pct": 0.0,
            "daily_pnl": [],
        }
        meta["forward_metrics"] = {
            "win_rate": None,
            "sharpe": None,
            "max_drawdown": None,
            "total_trades": 0,
        }
        
        save_meta(meta_file, meta)
        result["promoted"] = True
        result["reason"] = f"Promoted to 30-day paper trading (started {now.strftime('%Y-%m-%d')})"
        
    except Exception as e:
        result["reason"] = f"Error: {e}"
    
    return result


def batch_promote(dry_run: bool = False, agent_filter: str = None) -> list[dict]:
    """
    Promote all qualifying strategies.
    Returns list of results.
    """
    results = []
    
    for agent_dir in AGENTS.iterdir():
        if not agent_dir.is_dir():
            continue
        if agent_filter and agent_dir.name != agent_filter:
            continue
            
        for meta_file in agent_dir.glob("*.py.meta.json"):
            result = promote_strategy(meta_file, dry_run)
            results.append(result)
    
    return results


def print_results(results: list[dict]):
    """Print promotion results in a readable format."""
    promoted = [r for r in results if r["promoted"]]
    skipped = [r for r in results if not r["promoted"]]
    
    print(f"\n{'='*70}")
    print(f"PROMOTED: {len(promoted)} strategies")
    print(f"{'='*70}")
    for r in promoted:
        print(f"  [OK] {r['strategy']}")
        print(f"     Agent: {r['agent']}")
        print(f"     {r['reason']}")
        print()
    
    print(f"\n{'='*70}")
    print(f"SKIPPED: {len(skipped)} strategies")
    print(f"{'='*70}")
    # Group by reason
    by_reason = {}
    for r in skipped:
        reason = r["reason"]
        by_reason.setdefault(reason, []).append(r)
    
    for reason, items in sorted(by_reason.items(), key=lambda x: -len(x[1])):
        if len(items) == 0:
            continue
        print(f"\n  {reason}: {len(items)}")
        for r in items[:5]:  # Show first 5
            print(f"    - {r.get('strategy', 'unknown')} ({r.get('agent', 'unknown')})")
        if len(items) > 5:
            print(f"    ... and {len(items) - 5} more")
    
    print(f"\n{'='*70}")
    print(f"Total: {len(results)} strategies processed")
    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(description="Promote strategies to paper trading")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be promoted")
    parser.add_argument("--agent", type=str, help="Filter by agent ID")
    parser.add_argument("--file", type=str, help="Promote specific file only")
    
    args = parser.parse_args()
    
    if args.file:
        meta_file = Path(args.file)
        if not meta_file.exists():
            print(f"File not found: {meta_file}")
            sys.exit(1)
        result = promote_strategy(meta_file, args.dry_run)
        print_results([result])
    else:
        print(f"Scanning for strategies to promote...")
        print(f"Criteria: Sharpe >= {MIN_SHARPE}, Win Rate >= {MIN_WIN_RATE:.0%}, Max DD >= {MAX_DRAWDOWN:.0%}")
        if args.dry_run:
            print("(DRY RUN - no changes will be made)")
        print()
        
        results = batch_promote(args.dry_run, args.agent)
        print_results(results)
        
        # Return exit code based on promotions
        promoted = [r for r in results if r["promoted"]]
        sys.exit(0 if promoted else 1)


if __name__ == "__main__":
    main()
